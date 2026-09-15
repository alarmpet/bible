(async () => {
  try {
    const src = chrome.runtime.getURL('content/flow-adapter.js');
    await import(src);
  } catch (error) {
    console.error('[NOLLAM] Failed to load flow-adapter ESM:', error);
  }
})();
