export function resolvePdfUrl(value, baseHref) {
  if (typeof value !== "string" || !value.trim()) throw new Error("Vælg en PDF-fil.");
  const base = new URL(baseHref);
  const url = new URL(value, base);
  if (!/^https?:$/.test(url.protocol) || url.origin !== base.origin || url.username || url.password || !/\.pdf$/i.test(url.pathname)) {
    throw new Error("PDF-filen skal ligge på samme hjemmeside som nodeviseren.");
  }
  url.hash = "";
  return url;
}

export function normalizeSpread(value) {
  return Number(value) === 1 ? 1 : 2;
}

export function spreadStart(value, total, spread = 2) {
  const count = Math.max(1, Math.trunc(Number(total)) || 1);
  const width = normalizeSpread(spread);
  const number = Number(value);
  const page = Math.min(count, Math.max(1, Number.isFinite(number) ? Math.trunc(number) : 1));
  return 1 + Math.floor((page - 1) / width) * width;
}

export function visiblePages(page, total, spread = 2) {
  const start = spreadStart(page, total, spread);
  return Array.from({ length: Math.min(normalizeSpread(spread), total - start + 1) }, (_, index) => start + index);
}

export function advance(page, total, spread, delta) {
  const width = normalizeSpread(spread);
  const start = spreadStart(page, total, width);
  const target = start + (delta < 0 ? -width : width);
  return target < 1 || target > total
    ? { page: start, boundary: delta < 0 ? "previous" : "next" }
    : { page: target, boundary: null };
}
