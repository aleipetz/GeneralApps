import { useEffect, type ReactNode } from 'react';
import { useImageUrl } from './images.ts';
import { rankedEntries, type Bucket, type RankedEntry } from './ranking.ts';
import type { Category, Item, Trip } from './types.ts';

export function Thumb({ imageId, size = 56, kind = 'thumb', alt = '' }: { imageId: string | null; size?: number | string; kind?: 'thumb' | 'full'; alt?: string }) {
  const url = useImageUrl(imageId, kind);
  const style = { width: size, height: size };
  if (!imageId) return <div className="thumb thumb-empty" style={style}>🍽️</div>;
  return url ? <img className="thumb" style={style} src={url} alt={alt} /> : <div className="thumb thumb-loading" style={style} />;
}

export function ScorePill({ score, bucket, big }: { score: number; bucket: Bucket; big?: boolean }) {
  return <span className={`score score-${bucket}${big ? ' score-big' : ''}`}>{score.toFixed(1)}</span>;
}

export function Modal({ onClose, children, wide }: { onClose: () => void; children: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    document.body.classList.add('no-scroll');
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.classList.remove('no-scroll');
    };
  }, [onClose]);
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal${wide ? ' modal-wide' : ''}`} role="dialog" aria-modal="true">
        <button className="modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
        {children}
      </div>
    </div>
  );
}

export function scoreMap(cat: Category | undefined): Map<string, RankedEntry> {
  return new Map(cat ? rankedEntries(cat.rankings).map((e) => [e.id, e]) : []);
}

export function unrankedItems(cat: Category, items: Item[]): Item[] {
  const ranked = scoreMap(cat);
  return items.filter((i) => i.categoryId === cat.id && !ranked.has(i.id));
}

export function itemName(item: Item): string {
  return item.name.trim() || 'Unnamed';
}

export function formatDates(trip: Trip): string {
  const fmt = (d: string) =>
    new Date(d + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  if (trip.startDate && trip.endDate) return `${fmt(trip.startDate)} – ${fmt(trip.endDate)}`;
  return trip.startDate ? fmt(trip.startDate) : trip.endDate ? fmt(trip.endDate) : '';
}

export function go(path: string) {
  location.hash = path;
}
