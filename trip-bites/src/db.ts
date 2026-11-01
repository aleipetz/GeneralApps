// Tiny promise wrapper around IndexedDB. Everything (including photos) is
// stored locally in the browser; nothing leaves the device.

export type StoreName = 'trips' | 'categories' | 'items' | 'images';
const STORES: StoreName[] = ['trips', 'categories', 'items', 'images'];

let dbPromise: Promise<IDBDatabase> | null = null;

function open(): Promise<IDBDatabase> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open('trip-bites', 1);
      req.onupgradeneeded = () => {
        for (const s of STORES) {
          if (!req.result.objectStoreNames.contains(s)) req.result.createObjectStore(s, { keyPath: 'id' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

function done(tx: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error ?? new Error('Transaction aborted'));
  });
}

export async function getAll<T>(store: StoreName): Promise<T[]> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const req = db.transaction(store).objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result as T[]);
    req.onerror = () => reject(req.error);
  });
}

export async function get<T>(store: StoreName, id: string): Promise<T | undefined> {
  const db = await open();
  return new Promise((resolve, reject) => {
    const req = db.transaction(store).objectStore(store).get(id);
    req.onsuccess = () => resolve(req.result as T | undefined);
    req.onerror = () => reject(req.error);
  });
}

export interface WriteOp {
  store: StoreName;
  put?: unknown[];
  del?: string[];
  clear?: boolean;
}

/** Apply several writes atomically in one transaction. */
export async function write(ops: WriteOp[]): Promise<void> {
  const db = await open();
  const names = [...new Set(ops.map((o) => o.store))];
  if (names.length === 0) return;
  const tx = db.transaction(names, 'readwrite');
  for (const op of ops) {
    const s = tx.objectStore(op.store);
    if (op.clear) s.clear();
    op.del?.forEach((id) => s.delete(id));
    op.put?.forEach((v) => s.put(v));
  }
  return done(tx);
}

/** Ask the browser not to evict our data under storage pressure. */
export function requestPersistence(): void {
  navigator.storage?.persist?.().catch(() => {});
}
