import { useEffect, useState } from 'react';
import { get } from './db.ts';
import type { ImageRecord } from './types.ts';

const FULL_MAX = 1600;
const THUMB_MAX = 400;

type Decoded = CanvasImageSource & { width: number; height: number };

/** HEIC/HEIF check by MIME type, extension, or the file's "ftyp" header. */
export async function isHeic(file: Blob): Promise<boolean> {
  if (/image\/hei[cf]/i.test(file.type)) return true;
  if ('name' in file && /\.(heic|heif)$/i.test((file as File).name)) return true;
  const head = new Uint8Array(await file.slice(4, 12).arrayBuffer());
  return /^ftyp(heic|heix|hevc|hevx|heim|heis|mif1|msf1)$/.test(String.fromCharCode(...head));
}

async function decodeNative(file: Blob): Promise<Decoded> {
  try {
    return await createImageBitmap(file, { imageOrientation: 'from-image' });
  } catch {
    // Fallback for browsers without createImageBitmap support for this type.
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return img;
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

/**
 * Decode any photo, including iPhone HEIC files. The browser's own decoder is
 * tried first (iOS decodes HEIC natively); if it can't, a bundled
 * WebAssembly HEIC decoder is loaded on demand. Everything is then stored as
 * JPEG, so it displays everywhere.
 */
async function decode(file: Blob): Promise<Decoded> {
  try {
    return await decodeNative(file);
  } catch (nativeError) {
    if (!(await isHeic(file))) throw nativeError;
    const { heicTo } = await import('heic-to');
    return heicTo({ blob: file, type: 'bitmap' });
  }
}

function resize(src: CanvasImageSource & { width: number; height: number }, max: number, quality: number): Promise<Blob> {
  const scale = Math.min(1, max / Math.max(src.width, src.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(src.width * scale));
  canvas.height = Math.max(1, Math.round(src.height * scale));
  canvas.getContext('2d')!.drawImage(src, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Could not encode image'))), 'image/jpeg', quality),
  );
}

/** Downscale a photo so hundreds of them fit comfortably in browser storage. */
export async function processImage(file: Blob): Promise<{ full: Blob; thumb: Blob }> {
  const src = await decode(file);
  const [full, thumb] = await Promise.all([resize(src, FULL_MAX, 0.85), resize(src, THUMB_MAX, 0.8)]);
  if ('close' in src && typeof src.close === 'function') src.close();
  return { full, thumb };
}

/** Turn "IMG_2034 pad-thai.jpg" into "Pad thai"-ish default names. */
export function nameFromFile(fileName: string): string {
  const base = fileName.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim();
  if (/^(img|dsc|pxl|photo|image|screenshot)?\s*\d[\d\s]*$/i.test(base) || base === '') return '';
  return base.charAt(0).toUpperCase() + base.slice(1);
}

const urlCache = new Map<string, string>();

export function forgetImage(id: string): void {
  for (const kind of ['thumb', 'full']) {
    const key = `${id}:${kind}`;
    const url = urlCache.get(key);
    if (url) URL.revokeObjectURL(url);
    urlCache.delete(key);
  }
}

export function useImageUrl(id: string | null | undefined, kind: 'thumb' | 'full' = 'thumb'): string | undefined {
  const key = id ? `${id}:${kind}` : '';
  const [url, setUrl] = useState(() => urlCache.get(key));
  useEffect(() => {
    if (!id) return setUrl(undefined);
    const cached = urlCache.get(key);
    if (cached) return setUrl(cached);
    let alive = true;
    get<ImageRecord>('images', id).then((rec) => {
      if (!rec) return;
      const u = urlCache.get(key) ?? URL.createObjectURL(rec[kind]);
      urlCache.set(key, u);
      if (alive) setUrl(u);
    });
    return () => {
      alive = false;
    };
  }, [id, key, kind]);
  return url;
}

export function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result as string);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(blob);
  });
}

export async function dataUrlToBlob(url: string): Promise<Blob> {
  return (await fetch(url)).blob();
}
