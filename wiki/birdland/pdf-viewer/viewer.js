import { advance, normalizeSpread, resolvePdfUrl, spreadStart, visiblePages } from "./viewer-core.mjs";

const parameters = new URLSearchParams(location.search);
const elements = Object.fromEntries(["title", "previous", "next", "page", "total", "spread", "fullscreen", "original", "status", "pages"].map(id => [id, document.getElementById(id)]));
const embedded = window.parent !== window;
const bookEmbedded = embedded && parameters.get("fullscreen-owner") === "book";
if (bookEmbedded) document.documentElement.classList.add("book-embedded");
let documentPdf = null;
let loadingTask = null;
let currentPage = 1;
let spread = normalizeSpread(parameters.get("spread"));
let revision = 0;
let readySent = false;
let resizeTimer;
const renderTasks = new Set();
elements.spread.value = String(spread);
if (parameters.get("fullscreen-active") === "yes") elements.fullscreen.textContent = "Luk fuldskærm";
if (parameters.get("embedded") === "1") elements.spread.closest("label").hidden = true;

function tellParent(type, extra = {}) {
  if (embedded) window.parent.postMessage({ type: `birdland-pdf:${type}`, pages: documentPdf?.numPages || 0, page: currentPage, spread, ...extra }, location.origin);
}

function status(text, error = false) {
  elements.status.textContent = text;
  elements.status.classList.toggle("error", error);
}

function updateControls() {
  const total = documentPdf?.numPages || 0;
  elements.previous.disabled = !total || (!embedded && currentPage === 1);
  elements.next.disabled = !total || (!embedded && currentPage + spread > total);
  elements.page.disabled = !total;
  elements.page.value = String(currentPage);
  elements.page.max = String(total || 1);
  elements.total.textContent = `/ ${total || "…"}`;
  const atStart = total && currentPage === 1;
  const atEnd = total && currentPage + spread > total;
  elements.previous.title = embedded && atStart ? "Forrige nummer" : "Forrige sider";
  elements.next.title = embedded && atEnd ? "Næste nummer" : "Næste sider";
}

async function loadPdfApi() {
  // Reuse the exact, locally hosted matching vendor pair, without a CDN.
  const previousModule = globalThis.module;
  globalThis.module = { exports: {} };
  try {
    await import("./vendor/pdf.js");
  } finally {
    if (previousModule === undefined) delete globalThis.module;
    else globalThis.module = previousModule;
  }
  const api = globalThis.pdfjsLib;
  if (!api?.getDocument) throw new Error("PDF-viseren kunne ikke indlæses.");
  api.GlobalWorkerOptions.workerSrc = new URL("./pdf-worker.mjs", location.href).href;
  return api;
}

async function renderPages(resetScroll = false) {
  if (!documentPdf) return;
  const token = ++revision;
  for (const task of renderTasks) task.cancel();
  renderTasks.clear();
  currentPage = spreadStart(currentPage, documentPdf.numPages, spread);
  const selected = visiblePages(currentPage, documentPdf.numPages, spread);
  elements.pages.classList.toggle("spread-two", spread === 2);
  elements.pages.setAttribute("aria-busy", "true");
  status("Gør sider klar …");
  updateControls();
  try {
    const fragment = document.createDocumentFragment();
    const narrow = window.matchMedia("(max-width:700px)").matches;
    const columns = spread === 2 && !narrow ? 2 : 1;
    const availableWidth = Math.max(120, (elements.pages.clientWidth - 24 - (columns - 1) * 12) / columns);
    const toolbar = document.querySelector(".toolbar").getBoundingClientRect().height;
    const availableHeight = Math.max(180, window.innerHeight - toolbar - (bookEmbedded ? 8 : 64));
    await Promise.all(selected.map(async pageNumber => {
      const page = await documentPdf.getPage(pageNumber);
      if (token !== revision) return;
      const original = page.getViewport({ scale: 1 });
      const scale = narrow ? availableWidth / original.width : Math.min(availableWidth / original.width, availableHeight / original.height);
      const viewport = page.getViewport({ scale });
      const figure = document.createElement("figure");
      figure.className = "sheet";
      figure.style.width = `${viewport.width}px`;
      figure.setAttribute("aria-label", `Side ${pageNumber} af ${documentPdf.numPages}`);
      const canvas = document.createElement("canvas");
      // Limit per-page memory on large or high-density screens.
      const density = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(9000000 / (viewport.width * viewport.height)));
      canvas.width = Math.ceil(viewport.width * density);
      canvas.height = Math.ceil(viewport.height * density);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      canvas.setAttribute("aria-label", `Nodeside ${pageNumber}`);
      const caption = document.createElement("figcaption");
      caption.textContent = String(pageNumber);
      figure.append(canvas, caption);
      // Preserve page order even when the second page finishes first.
      fragment.append(figure);
      const task = page.render({ canvasContext: canvas.getContext("2d", { alpha: false }), viewport, transform: density === 1 ? undefined : [density, 0, 0, density, 0, 0], background: "rgb(255,255,255)" });
      renderTasks.add(task);
      try { await task.promise; } finally { renderTasks.delete(task); }
    }));
    if (token !== revision) return;
    // getPage completion order is asynchronous; put pages in numerical order.
    const figures = [...fragment.children].sort((a, b) => Number(a.querySelector("figcaption").textContent) - Number(b.querySelector("figcaption").textContent));
    elements.pages.replaceChildren(...figures);
    if (resetScroll) window.scrollTo(0, 0);
    elements.pages.setAttribute("aria-busy", "false");
    status(selected.length === 1 ? `Side ${currentPage} af ${documentPdf.numPages}` : `Side ${selected[0]}–${selected.at(-1)} af ${documentPdf.numPages}`);
    tellParent(readySent ? "state" : "ready");
    readySent = true;
  } catch (error) {
    if (token !== revision || error?.name === "RenderingCancelledException") return;
    elements.pages.setAttribute("aria-busy", "false");
    status("Siderne kunne ikke vises. Brug “Åbn PDF / udskriv” for at åbne originalen.", true);
    tellParent("error", { message: "PDF-siderne kunne ikke vises." });
  }
}

function move(delta) {
  if (!documentPdf) return;
  const target = advance(currentPage, documentPdf.numPages, spread, delta);
  if (target.boundary) {
    tellParent("boundary", { direction: target.boundary, delta: delta < 0 ? -1 : 1 });
    return;
  }
  currentPage = target.page;
  renderPages(true);
}

function go(page) {
  if (!documentPdf) return;
  currentPage = spreadStart(page, documentPdf.numPages, spread);
  renderPages(true);
}

function setSpread(value) {
  const next = normalizeSpread(value);
  if (next === spread) return;
  spread = next;
  elements.spread.value = String(spread);
  if (documentPdf) {
    currentPage = spreadStart(currentPage, documentPdf.numPages, spread);
    renderPages(true);
  }
}

elements.previous.addEventListener("click", () => move(-1));
elements.next.addEventListener("click", () => move(1));
elements.page.addEventListener("change", () => go(elements.page.value));
elements.page.addEventListener("keydown", event => {
  if (event.key === "Enter") { event.preventDefault(); go(elements.page.value); }
});
elements.spread.addEventListener("change", () => setSpread(elements.spread.value));
elements.fullscreen.addEventListener("click", async () => {
  if (parameters.get("fullscreen-owner") === "book") { tellParent("fullscreen"); return; }
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch { status("Fuldskærm er ikke tilgængelig her. Åbn PDF-filen direkte for en større visning."); }
});
if (!document.documentElement.requestFullscreen && parameters.get("fullscreen-owner") !== "book") elements.fullscreen.hidden = true;
document.addEventListener("fullscreenchange", () => { elements.fullscreen.textContent = document.fullscreenElement ? "Luk fuldskærm" : "Fuldskærm"; });

window.addEventListener("keydown", event => {
  if (event.key === "Escape" && parameters.get("fullscreen-owner") === "book") { tellParent("fullscreen", {exit:true}); return; }
  if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest("input,select,textarea,[contenteditable]")) return;
  if (["ArrowRight", "PageDown", " "].includes(event.key)) { event.preventDefault(); move(1); }
  else if (["ArrowLeft", "PageUp"].includes(event.key)) { event.preventDefault(); move(-1); }
  else if (event.key === "Home") { event.preventDefault(); go(1); }
  else if (event.key === "End" && documentPdf) { event.preventDefault(); go(documentPdf.numPages); }
});

window.addEventListener("message", event => {
  if (!embedded || event.source !== window.parent || event.origin !== location.origin) return;
  const message = event.data;
  if (!message || typeof message !== "object" || message.type !== "birdland-pdf:command") return;
  if (message.command === "fullscreen-state") { elements.fullscreen.textContent = message.active ? "Luk fuldskærm" : "Fuldskærm"; return; }
  if (message.command === "spread") setSpread(message.spread);
  else if (message.command === "next") move(1);
  else if (message.command === "previous") move(-1);
  else if (message.command === "go") go(message.page);
});
window.addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(renderPages, 150); });
window.addEventListener("pagehide", () => { revision++; for (const task of renderTasks) task.cancel(); loadingTask?.destroy(); });

try {
  const url = resolvePdfUrl(parameters.get("file"), location.href);
  const title = parameters.get("title") || decodeURIComponent(url.pathname.split("/").at(-1)).replace(/\.pdf$/i, "").replaceAll("-", " ");
  elements.title.textContent = title;
  document.title = `${title} · Birdland`;
  elements.original.href = url.href;
  elements.original.hidden = false;
  const api = await loadPdfApi();
  loadingTask = api.getDocument({ url: url.href, isEvalSupported: false, enableXfa: false, useSystemFonts: true, useWasm: false, useWorkerFetch: false });
  loadingTask.onPassword = () => loadingTask.destroy();
  documentPdf = await loadingTask.promise;
  currentPage = spreadStart(parameters.get("page"), documentPdf.numPages, spread);
  await renderPages();
} catch (error) {
  elements.pages.setAttribute("aria-busy", "false");
  status(elements.original.hidden ? error.message : "PDF-filen kunne ikke indlæses. Brug “Åbn PDF / udskriv” for at prøve originalen.", true);
  tellParent("error", { message: "PDF-filen kunne ikke indlæses." });
}
