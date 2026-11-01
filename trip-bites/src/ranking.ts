// Beli-style ranking: every item first goes into a sentiment bucket
// ("liked it" / "it was fine" / "didn't like it"), then is placed inside that
// bucket with a binary search driven by "which did you prefer?" questions.
// Scores are derived from the position within the bucket.

export type Bucket = 'liked' | 'fine' | 'disliked';

export const BUCKETS: Bucket[] = ['liked', 'fine', 'disliked'];

export const BUCKET_INFO: Record<Bucket, { label: string; emoji: string; range: [number, number] }> = {
  liked: { label: 'I liked it', emoji: '😍', range: [6.8, 10] },
  fine: { label: 'It was fine', emoji: '🙂', range: [3.4, 6.7] },
  disliked: { label: "I didn't like it", emoji: '😕', range: [0, 3.3] },
};

/** Ordered item ids per bucket, best first. */
export type Rankings = Record<Bucket, string[]>;

export function emptyRankings(): Rankings {
  return { liked: [], fine: [], disliked: [] };
}

/** State of an in-progress binary insertion into `list` (best first). */
export interface InsertSession {
  bucket: Bucket;
  /** The answer lies in the half-open range [lo, hi]. */
  lo: number;
  hi: number;
}

export function startSession(bucket: Bucket, list: readonly string[]): InsertSession {
  return { bucket, lo: 0, hi: list.length };
}

export function isDone(s: InsertSession): boolean {
  return s.lo >= s.hi;
}

/** Index in the bucket list of the item to compare against next. */
export function pivotIndex(s: InsertSession): number {
  return Math.floor((s.lo + s.hi) / 2);
}

/** Upper bound on how many comparisons are still needed. */
export function remainingComparisons(s: InsertSession): number {
  const n = s.hi - s.lo;
  return n <= 0 ? 0 : Math.ceil(Math.log2(n + 1));
}

/**
 * Record an answer. `'new'` = the new item is better than the pivot,
 * `'pivot'` = the pivot is better, `'tie'` = too tough to call (placed right
 * after the pivot).
 */
export function answer(s: InsertSession, choice: 'new' | 'pivot' | 'tie'): InsertSession {
  const mid = pivotIndex(s);
  if (choice === 'new') return { ...s, hi: mid };
  if (choice === 'pivot') return { ...s, lo: mid + 1 };
  return { ...s, lo: mid + 1, hi: mid + 1 };
}

export function removeFromRankings(r: Rankings, id: string): Rankings {
  return {
    liked: r.liked.filter((x) => x !== id),
    fine: r.fine.filter((x) => x !== id),
    disliked: r.disliked.filter((x) => x !== id),
  };
}

/** Remove `id` from wherever it is and insert it at `index` of `bucket`. */
export function placeInRankings(r: Rankings, id: string, bucket: Bucket, index: number): Rankings {
  const next = removeFromRankings(r, id);
  const list = [...next[bucket]];
  list.splice(Math.max(0, Math.min(index, list.length)), 0, id);
  return { ...next, [bucket]: list };
}

export function scoreAt(bucket: Bucket, index: number, size: number): number {
  const [lo, hi] = BUCKET_INFO[bucket].range;
  if (size <= 0) return hi;
  const raw = lo + ((hi - lo) * (size - index)) / size;
  return Math.round(raw * 10) / 10;
}

export interface RankedEntry {
  id: string;
  bucket: Bucket;
  /** 1-based overall rank in the category. */
  rank: number;
  score: number;
}

export function rankedEntries(r: Rankings): RankedEntry[] {
  const out: RankedEntry[] = [];
  for (const bucket of BUCKETS) {
    const list = r[bucket];
    list.forEach((id, i) => {
      out.push({ id, bucket, rank: out.length + 1, score: scoreAt(bucket, i, list.length) });
    });
  }
  return out;
}

export function isRanked(r: Rankings, id: string): boolean {
  return BUCKETS.some((b) => r[b].includes(id));
}
