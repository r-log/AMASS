/**
 * Service Worker for Background Sync - replays offline queue when tab is closed.
 * Listens for 'sync' event, reads from IndexedDB, sends queued requests.
 */

const DB_NAME = "ElectricianLogOffline";
const DB_VERSION = 1;
const STORE_QUEUE = "offline_queue";
const STORE_BLOBS = "offline_queue_blobs";
const SYNC_TAG = "offline-queue";
const REPLAY_RETRIES = 3;
const RETRY_DELAY = 1000;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
  });
}

function getEntries(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_QUEUE, "readonly");
    const idx = tx.objectStore(STORE_QUEUE).index("createdAt");
    const req = idx.getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

function getBlob(db, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_BLOBS, "readonly");
    const req = tx.objectStore(STORE_BLOBS).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function deserializeFormData(db, entryId, formPartsMeta) {
  const formData = new FormData();
  for (const p of formPartsMeta) {
    if (p.type === "blob" && p.blobKey) {
      const blob = await getBlob(db, p.blobKey);
      if (blob) formData.append(p.key, blob);
    } else {
      formData.append(p.key, p.value);
    }
  }
  return formData;
}

function deleteBlobs(db, entry) {
  if (!entry.formPartsMeta) return Promise.resolve();
  const tx = db.transaction(STORE_BLOBS, "readwrite");
  const store = tx.objectStore(STORE_BLOBS);
  for (const p of entry.formPartsMeta) {
    if (p.type === "blob" && p.blobKey) store.delete(p.blobKey);
  }
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function deleteEntry(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_QUEUE, "readwrite");
    tx.objectStore(STORE_QUEUE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function replayEntry(db, entry) {
  const headers = new Headers(entry.headers || {});
  let body = null;

  if (entry.bodyType === "json" && entry.bodyJson) {
    body = entry.bodyJson;
  } else if (entry.bodyType === "form" && entry.formPartsMeta && entry.formPartsMeta.length > 0) {
    body = await deserializeFormData(db, entry.id, entry.formPartsMeta);
    headers.delete("Content-Type");
  }

  const timeoutMs = entry.timeoutMs || 60000;
  const controller = new AbortController();
  const tid = setTimeout(() => controller.abort(), timeoutMs);

  let lastError;
  for (let attempt = 0; attempt < REPLAY_RETRIES; attempt++) {
    try {
      const res = await fetch(entry.url, {
        method: entry.method,
        headers,
        body,
        signal: controller.signal,
      });
      clearTimeout(tid);
      if (res.ok) return { ok: true };
      lastError = new Error(`HTTP ${res.status}`);
    } catch (e) {
      lastError = e;
      if (attempt < REPLAY_RETRIES - 1) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY * (attempt + 1)));
      }
    }
  }
  clearTimeout(tid);
  return { ok: false, error: lastError };
}

async function processQueueInSW() {
  const db = await openDb();
  const entries = await getEntries(db);

  for (const entry of entries) {
    const result = await replayEntry(db, entry);
    if (result.ok) {
      await deleteBlobs(db, entry);
      await deleteEntry(db, entry.id);
    }
  }
}

self.addEventListener("sync", (event) => {
  if (event.tag === SYNC_TAG) {
    event.waitUntil(processQueueInSW());
  }
});
