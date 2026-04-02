/**
 * Offline Queue - Queues API requests when offline and replays when connected.
 * Queues only mutations (POST/PUT/PATCH/DELETE). GET requests fail when offline.
 */

const DB_NAME = "ElectricianLogOffline";
const DB_VERSION = 1;
const STORE_QUEUE = "offline_queue";
const STORE_BLOBS = "offline_queue_blobs";

const MUTATION_METHODS = ["POST", "PUT", "PATCH", "DELETE"];
const REPLAY_RETRIES = 3;
const REACHABILITY_RETRY_DELAY = 10000;
const REACHABILITY_MAX_DELAY = 60000;
const REACHABILITY_TIMEOUT_MS = 5000;

const OfflineQueue = {
  _db: null,
  _pendingPromises: new Map(),
  _processing: false,
  _retryDelay: 1000,
  _reachabilityRetryCount: 0,
  _reachabilityRetryTimer: null,

  async _openDb() {
    if (this._db) return this._db;
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => {
        this._db = req.result;
        resolve(this._db);
      };
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_QUEUE)) {
          const q = db.createObjectStore(STORE_QUEUE, { keyPath: "id" });
          q.createIndex("createdAt", "createdAt", { unique: false });
        }
        if (!db.objectStoreNames.contains(STORE_BLOBS)) {
          db.createObjectStore(STORE_BLOBS);
        }
      };
    });
  },

  _generateId() {
    return `oq_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  },

  isOnline() {
    return typeof navigator !== "undefined" && navigator.onLine;
  },

  _getHealthUrl() {
    const config = typeof window !== "undefined" && window.AppConfig;
    const base = config?.api?.baseUrl || "http://localhost:5000/api";
    const clean = base.replace(/\/$/, "");
    return `${clean}/auth/verify`;
  },

  async _isApiReachable() {
    const url = this._getHealthUrl();
    const token = typeof window !== "undefined" && window.authManager?.getToken();
    const headers = token ? { Authorization: `Bearer ${token}` } : {};
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), REACHABILITY_TIMEOUT_MS);
    try {
      const res = await fetch(url, { method: "GET", headers, signal: controller.signal });
      clearTimeout(tid);
      return true;
    } catch (e) {
      clearTimeout(tid);
      return false;
    }
  },

  /**
   * Fetch with offline queuing. Queues only mutations when offline.
   * @param {string} url
   * @param {Object} options - fetch options (method, headers, body, signal)
   * @returns {Promise<Response>}
   */
  async fetch(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    if (this.isOnline()) {
      return this._doFetch(url, options);
    }
    if (!MUTATION_METHODS.includes(method)) {
      throw new Error("Network error: offline (GET requests are not queued)");
    }
    return this._queueRequest(url, options, "json");
  },

  /**
   * Fetch FormData with offline queuing.
   * @param {string} url
   * @param {Object} options - { method, headers, body: FormData }
   * @returns {Promise<Response>}
   */
  async fetchFormData(url, options = {}) {
    if (this.isOnline()) {
      return this._doFetch(url, options);
    }
    const method = (options.method || "POST").toUpperCase();
    if (!MUTATION_METHODS.includes(method)) {
      throw new Error("Network error: offline (GET requests are not queued)");
    }
    return this._queueRequest(url, options, "form");
  },

  async _doFetch(url, options = {}, timeoutMs = 60000) {
    let controller = null;
    let tid = null;
    if (!options.signal) {
      controller = new AbortController();
      tid = setTimeout(() => controller.abort(), timeoutMs);
    }
    try {
      const res = await fetch(url, {
        ...options,
        signal: options.signal || (controller && controller.signal),
      });
      if (tid) clearTimeout(tid);
      return res;
    } catch (e) {
      if (tid) clearTimeout(tid);
      throw e;
    }
  },

  async _queueRequest(url, options, bodyType) {
    const id = this._generateId();
    const method = (options.method || "POST").toUpperCase();
    const headers = options.headers && typeof options.headers === "object"
      ? Object.fromEntries(
          options.headers instanceof Headers
            ? options.headers.entries()
            : Object.entries(options.headers)
        )
      : {};

    let bodyJson = null;
    let formPartsMeta = null;

    if (bodyType === "json" && options.body) {
      bodyJson = typeof options.body === "string" ? options.body : JSON.stringify(options.body);
    } else if (bodyType === "form" && options.body instanceof FormData) {
      formPartsMeta = await this._serializeFormData(id, options.body);
    }

    const entry = {
      id,
      url,
      method,
      headers,
      bodyType,
      bodyJson,
      formPartsMeta,
      createdAt: Date.now(),
      timeoutMs: options.timeout || 60000,
    };

    const db = await this._openDb();
    return new Promise((resolve, reject) => {
      this._pendingPromises.set(id, { resolve, reject });
      const tx = db.transaction([STORE_QUEUE, STORE_BLOBS], "readwrite");
      const store = tx.objectStore(STORE_QUEUE);
      store.add(entry);
      tx.oncomplete = () => {
        console.log(`📴 Queued request (offline): ${method} ${url}`);
        if ("serviceWorker" in navigator && navigator.serviceWorker.ready) {
          navigator.serviceWorker.ready
            .then((reg) => {
              if (reg.sync) reg.sync.register("offline-queue").catch(() => {});
            })
            .catch(() => {});
        }
      };
      tx.onerror = () => {
        this._pendingPromises.delete(id);
        reject(tx.error);
      };
    });
  },

  async _serializeFormData(queueId, formData) {
    const parts = [];
    let idx = 0;
    for (const [key, value] of formData.entries()) {
      if (value instanceof Blob || value instanceof File) {
        const blobKey = `${queueId}_${idx}`;
        const db = await this._openDb();
        await new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_BLOBS, "readwrite");
          tx.objectStore(STORE_BLOBS).put(value, blobKey);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        });
        parts.push({ key, type: "blob", blobKey });
      } else {
        parts.push({ key, type: "string", value: String(value) });
      }
      idx++;
    }
    return parts;
  },

  async _deserializeFormData(queueId, formPartsMeta) {
    const formData = new FormData();
    const db = await this._openDb();
    for (const p of formPartsMeta) {
      if (p.type === "blob") {
        const blob = await new Promise((resolve, reject) => {
          const tx = db.transaction(STORE_BLOBS, "readonly");
          const req = tx.objectStore(STORE_BLOBS).get(p.blobKey);
          req.onsuccess = () => resolve(req.result);
          req.onerror = () => reject(req.error);
        });
        if (blob) formData.append(p.key, blob);
      } else {
        formData.append(p.key, p.value);
      }
    }
    return formData;
  },

  async _replayEntry(entry) {
    const db = await this._openDb();
    let body = null;
    const headers = new Headers(entry.headers || {});

    if (entry.bodyType === "json" && entry.bodyJson) {
      body = entry.bodyJson;
    } else if (entry.bodyType === "form" && entry.formPartsMeta && entry.formPartsMeta.length > 0) {
      body = await this._deserializeFormData(entry.id, entry.formPartsMeta);
      headers.delete("Content-Type");
    }

    const opts = {
      method: entry.method,
      headers,
      body,
      timeout: entry.timeoutMs,
    };

    let lastError;
    for (let attempt = 0; attempt < REPLAY_RETRIES; attempt++) {
      try {
        const res = await this._doFetch(entry.url, opts, entry.timeoutMs || 60000);
        return { ok: true, response: res };
      } catch (e) {
        lastError = e;
        if (attempt < REPLAY_RETRIES - 1) {
          await new Promise((r) => setTimeout(r, this._retryDelay * (attempt + 1)));
        }
      }
    }
    return { ok: false, error: lastError };
  },

  async _deleteBlobsForEntry(entry) {
    if (entry.formPartsMeta) {
      const db = await this._openDb();
      const tx = db.transaction(STORE_BLOBS, "readwrite");
      const store = tx.objectStore(STORE_BLOBS);
      for (const p of entry.formPartsMeta) {
        if (p.type === "blob" && p.blobKey) {
          store.delete(p.blobKey);
        }
      }
    }
  },

  async processQueue() {
    if (this._processing || !this.isOnline()) return;
    this._processing = true;
    const db = await this._openDb();

    try {
      const entries = await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_QUEUE, "readonly");
        const idx = tx.objectStore(STORE_QUEUE).index("createdAt");
        const req = idx.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });

      for (const entry of entries) {
        const result = await this._replayEntry(entry);
        const { resolve, reject } = this._pendingPromises.get(entry.id) || {};

        if (result.ok) {
          if (resolve) resolve(result.response);
          await this._deleteBlobsForEntry(entry);
        } else {
          if (reject) reject(result.error);
          await this._deleteBlobsForEntry(entry);
        }
        this._pendingPromises.delete(entry.id);

        const tx = db.transaction(STORE_QUEUE, "readwrite");
        tx.objectStore(STORE_QUEUE).delete(entry.id);
        await new Promise((r, e) => {
          tx.oncomplete = r;
          tx.onerror = () => e(tx.error);
        });

        if (!result.ok) {
          console.warn(`📴 Replay failed for ${entry.method} ${entry.url}:`, result.error?.message);
        } else {
          console.log(`✅ Replayed (was offline): ${entry.method} ${entry.url}`);
        }
      }
    } finally {
      this._processing = false;
    }
  },

  onOnline() {
    if (this._reachabilityRetryTimer) {
      clearTimeout(this._reachabilityRetryTimer);
      this._reachabilityRetryTimer = null;
    }

    this._isApiReachable().then((reachable) => {
      if (reachable) {
        this._reachabilityRetryCount = 0;
        console.log("🌐 API reachable, processing queued requests...");
        this.processQueue();
      } else {
        this._reachabilityRetryCount += 1;
        const delay = Math.min(
          REACHABILITY_RETRY_DELAY * Math.pow(2, this._reachabilityRetryCount - 1),
          REACHABILITY_MAX_DELAY
        );
        console.warn(
          `🌐 API not reachable (retry ${this._reachabilityRetryCount}), scheduling in ${delay / 1000}s`
        );
        this._reachabilityRetryTimer = setTimeout(() => {
          this._reachabilityRetryTimer = null;
          this.onOnline();
        }, delay);
      }
    });
  },

  getQueuedCount() {
    return new Promise(async (resolve) => {
      try {
        const db = await this._openDb();
        const tx = db.transaction(STORE_QUEUE, "readonly");
        const req = tx.objectStore(STORE_QUEUE).count();
        req.onsuccess = () => resolve(req.result || 0);
        req.onerror = () => resolve(0);
      } catch {
        resolve(0);
      }
    });
  },

  init() {
    if (typeof window === "undefined") return;
    window.addEventListener("online", () => this.onOnline());
    if (this.isOnline()) {
      this.getQueuedCount().then((n) => {
        if (n > 0) this.onOnline();
      });
    }
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw-offline-sync.js").catch(() => {});
    }
  },
};

OfflineQueue.init();

if (typeof window !== "undefined") {
  window.offlineQueue = OfflineQueue;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = { OfflineQueue };
}

console.log("📴 Offline queue initialized");
