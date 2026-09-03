class DownloadRegistry {
  constructor(storage = null) { this.storage = storage; this.bindings = new Map(); }
  register(downloadId, binding) {
    if (downloadId === undefined || !binding?.jobId || !binding.shotId || !binding.promptSha256 || !Number.isInteger(binding.attempt)) throw new TypeError('complete download binding is required');
    const record = { ...binding, downloadId: String(downloadId), status: 'started' };
    this.bindings.set(String(downloadId), record); this.#persist(); return { ...record };
  }
  complete(downloadId, filename) {
    const record = this.bindings.get(String(downloadId));
    if (!record) throw new Error('unknown download');
    if (!filename || !filename.includes(record.shotId + '__')) return { ...record, status: 'paused', code: 'DOWNLOAD_FILENAME_MISMATCH', filename };
    if (record.status === 'complete') return { ...record, filename };
    const result = { ...record, status: 'complete', filename };
    this.bindings.set(String(downloadId), result); this.#persist(); return result;
  }
  async restore(search) {
    for (const [id, binding] of this.bindings) {
      const item = await search({ id: Number.isNaN(Number(id)) ? id : Number(id) });
      if (!item || item.state !== 'complete') { binding.status = 'paused'; binding.code = item?.state === 'interrupted' ? 'DOWNLOAD_INTERRUPTED' : 'DOWNLOAD_MISSING'; }
      else this.complete(id, item.filename || '');
    }
    this.#persist(); return [...this.bindings.values()].map((item) => ({ ...item }));
  }
  #persist() { this.storage?.set?.({ downloadBindings: Object.fromEntries(this.bindings) }); }
}
export { DownloadRegistry };
