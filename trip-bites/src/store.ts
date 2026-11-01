import { useSyncExternalStore } from 'react';
import { getAll, get, write, type WriteOp } from './db.ts';
import { blobToDataUrl, dataUrlToBlob, forgetImage, nameFromFile, processImage } from './images.ts';
import { emptyRankings, placeInRankings, removeFromRankings, type Bucket } from './ranking.ts';
import type { Category, ImageRecord, Item, Trip } from './types.ts';

export interface Data {
  loaded: boolean;
  trips: Trip[];
  categories: Category[];
  items: Item[];
}

let data: Data = { loaded: false, trips: [], categories: [], items: [] };
const listeners = new Set<() => void>();

function set(next: Partial<Data>) {
  data = { ...data, ...next };
  listeners.forEach((l) => l());
}

export function useData(): Data {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => data,
  );
}

export const uid = () =>
  globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

const byCreated = <T extends { createdAt: number }>(a: T, b: T) => a.createdAt - b.createdAt;

export async function load(): Promise<void> {
  const [trips, categories, items] = await Promise.all([
    getAll<Trip>('trips'),
    getAll<Category>('categories'),
    getAll<Item>('items'),
  ]);
  set({ loaded: true, trips: trips.sort(byCreated), categories: categories.sort(byCreated), items: items.sort(byCreated) });
}

// ---------- Trips ----------

export async function createTrip(fields: Omit<Trip, 'id' | 'createdAt'>, categoryNames: string[]): Promise<Trip> {
  const now = Date.now();
  const trip: Trip = { ...fields, id: uid(), createdAt: now };
  const cats: Category[] = categoryNames.map((name, i) => ({
    id: uid(),
    tripId: trip.id,
    name,
    createdAt: now + i,
    rankings: emptyRankings(),
  }));
  await write([
    { store: 'trips', put: [trip] },
    { store: 'categories', put: cats },
  ]);
  set({ trips: [...data.trips, trip], categories: [...data.categories, ...cats] });
  return trip;
}

export async function updateTrip(trip: Trip): Promise<void> {
  await write([{ store: 'trips', put: [trip] }]);
  set({ trips: data.trips.map((t) => (t.id === trip.id ? trip : t)) });
}

export async function deleteTrip(tripId: string): Promise<void> {
  const cats = data.categories.filter((c) => c.tripId === tripId);
  const items = data.items.filter((i) => i.tripId === tripId);
  await write(deletionOps([tripId], cats, items));
  items.forEach((i) => i.imageId && forgetImage(i.imageId));
  set({
    trips: data.trips.filter((t) => t.id !== tripId),
    categories: data.categories.filter((c) => c.tripId !== tripId),
    items: data.items.filter((i) => i.tripId !== tripId),
  });
}

function deletionOps(tripIds: string[], cats: Category[], items: Item[]): WriteOp[] {
  return [
    { store: 'trips', del: tripIds },
    { store: 'categories', del: cats.map((c) => c.id) },
    { store: 'items', del: items.map((i) => i.id) },
    { store: 'images', del: items.flatMap((i) => (i.imageId ? [i.imageId] : [])) },
  ];
}

// ---------- Categories ----------

export async function addCategory(tripId: string, name: string): Promise<Category> {
  const cat: Category = { id: uid(), tripId, name, createdAt: Date.now(), rankings: emptyRankings() };
  await write([{ store: 'categories', put: [cat] }]);
  set({ categories: [...data.categories, cat] });
  return cat;
}

async function saveCategory(cat: Category): Promise<void> {
  await write([{ store: 'categories', put: [cat] }]);
  set({ categories: data.categories.map((c) => (c.id === cat.id ? cat : c)) });
}

export async function renameCategory(id: string, name: string): Promise<void> {
  const cat = data.categories.find((c) => c.id === id);
  if (cat) await saveCategory({ ...cat, name });
}

export async function deleteCategory(id: string): Promise<void> {
  const items = data.items.filter((i) => i.categoryId === id);
  const cat = data.categories.find((c) => c.id === id);
  if (!cat) return;
  await write(deletionOps([], [cat], items));
  items.forEach((i) => i.imageId && forgetImage(i.imageId));
  set({
    categories: data.categories.filter((c) => c.id !== id),
    items: data.items.filter((i) => i.categoryId !== id),
  });
}

// ---------- Items ----------

/** Bulk upload: each photo becomes an unranked item in the category. */
export async function addPhotos(
  categoryId: string,
  files: File[],
  onProgress?: (done: number, total: number) => void,
): Promise<{ added: number; failed: string[] }> {
  const cat = data.categories.find((c) => c.id === categoryId);
  if (!cat) throw new Error('Category not found');
  const failed: string[] = [];
  let added = 0;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    try {
      const { full, thumb } = await processImage(file);
      const image: ImageRecord = { id: uid(), full, thumb };
      const item: Item = {
        id: uid(),
        tripId: cat.tripId,
        categoryId,
        name: nameFromFile(file.name),
        notes: '',
        place: '',
        imageId: image.id,
        createdAt: Date.now() + i / 1000,
      };
      await write([
        { store: 'images', put: [image] },
        { store: 'items', put: [item] },
      ]);
      set({ items: [...data.items, item] });
      added++;
    } catch {
      failed.push(file.name);
    }
    onProgress?.(i + 1, files.length);
  }
  return { added, failed };
}

export async function addItemWithoutPhoto(categoryId: string, name: string): Promise<Item> {
  const cat = data.categories.find((c) => c.id === categoryId)!;
  const item: Item = { id: uid(), tripId: cat.tripId, categoryId, name, notes: '', place: '', imageId: null, createdAt: Date.now() };
  await write([{ store: 'items', put: [item] }]);
  set({ items: [...data.items, item] });
  return item;
}

export async function updateItem(item: Item): Promise<void> {
  await write([{ store: 'items', put: [item] }]);
  set({ items: data.items.map((i) => (i.id === item.id ? item : i)) });
}

export async function deleteItem(id: string): Promise<void> {
  const item = data.items.find((i) => i.id === id);
  if (!item) return;
  const cat = data.categories.find((c) => c.id === item.categoryId);
  const ops: WriteOp[] = [{ store: 'items', del: [id] }];
  if (item.imageId) ops.push({ store: 'images', del: [item.imageId] });
  const nextCat = cat && { ...cat, rankings: removeFromRankings(cat.rankings, id) };
  if (nextCat) ops.push({ store: 'categories', put: [nextCat] });
  await write(ops);
  if (item.imageId) forgetImage(item.imageId);
  set({
    items: data.items.filter((i) => i.id !== id),
    categories: nextCat ? data.categories.map((c) => (c.id === nextCat.id ? nextCat : c)) : data.categories,
  });
}

/** Move an item to another category of the same trip. It becomes unranked there. */
export async function moveItem(id: string, toCategoryId: string): Promise<void> {
  const item = data.items.find((i) => i.id === id);
  const from = data.categories.find((c) => c.id === item?.categoryId);
  if (!item || !from || from.id === toCategoryId) return;
  const nextItem = { ...item, categoryId: toCategoryId };
  const nextFrom = { ...from, rankings: removeFromRankings(from.rankings, id) };
  await write([
    { store: 'items', put: [nextItem] },
    { store: 'categories', put: [nextFrom] },
  ]);
  set({
    items: data.items.map((i) => (i.id === id ? nextItem : i)),
    categories: data.categories.map((c) => (c.id === from.id ? nextFrom : c)),
  });
}

export async function placeItem(categoryId: string, itemId: string, bucket: Bucket, index: number): Promise<void> {
  const cat = data.categories.find((c) => c.id === categoryId)!;
  await saveCategory({ ...cat, rankings: placeInRankings(cat.rankings, itemId, bucket, index) });
}

export async function unrankItem(categoryId: string, itemId: string): Promise<void> {
  const cat = data.categories.find((c) => c.id === categoryId)!;
  await saveCategory({ ...cat, rankings: removeFromRankings(cat.rankings, itemId) });
}

// ---------- Backup ----------

interface Backup {
  app: 'trip-bites';
  version: 1;
  exportedAt: string;
  trips: Trip[];
  categories: Category[];
  items: Item[];
  images: { id: string; full: string; thumb: string }[];
}

export async function exportBackup(): Promise<Blob> {
  const images: Backup['images'] = [];
  for (const item of data.items) {
    if (!item.imageId) continue;
    const rec = await get<ImageRecord>('images', item.imageId);
    if (rec) images.push({ id: rec.id, full: await blobToDataUrl(rec.full), thumb: await blobToDataUrl(rec.thumb) });
  }
  const backup: Backup = {
    app: 'trip-bites',
    version: 1,
    exportedAt: new Date().toISOString(),
    trips: data.trips,
    categories: data.categories,
    items: data.items,
    images,
  };
  return new Blob([JSON.stringify(backup)], { type: 'application/json' });
}

/** Import a backup. Trips already present (same id) are replaced. */
export async function importBackup(file: File): Promise<number> {
  const backup = JSON.parse(await file.text()) as Backup;
  if (backup.app !== 'trip-bites' || !Array.isArray(backup.trips)) throw new Error('Not a Trip Bites backup file');
  const images: ImageRecord[] = [];
  for (const img of backup.images) {
    images.push({ id: img.id, full: await dataUrlToBlob(img.full), thumb: await dataUrlToBlob(img.thumb) });
  }
  const tripIds = backup.trips.map((t) => t.id);
  const oldCats = data.categories.filter((c) => tripIds.includes(c.tripId));
  const oldItems = data.items.filter((i) => tripIds.includes(i.tripId));
  await write([
    ...deletionOps(tripIds, oldCats, oldItems),
    { store: 'trips', put: backup.trips },
    { store: 'categories', put: backup.categories },
    { store: 'items', put: backup.items },
    { store: 'images', put: images },
  ]);
  await load();
  return backup.trips.length;
}
