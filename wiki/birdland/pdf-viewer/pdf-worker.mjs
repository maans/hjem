// The matching PDF.js 6.4.299 vendor bundle is CommonJS, preserved byte-for-byte.
// Adapt it to PDF.js's module-worker and fake-worker loading contracts.
const previousModule = globalThis.module;
globalThis.module = { exports: {} };
try {
  await import("./vendor/pdf-worker.js");
} finally {
  if (previousModule === undefined) delete globalThis.module;
  else globalThis.module = previousModule;
}
export const WorkerMessageHandler = globalThis.pdfjsWorker.WorkerMessageHandler;
