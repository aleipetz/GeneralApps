import { useCallback, useEffect, useMemo, useState } from 'react';
import { placeItem, updateItem, useData } from './store.ts';
import {
  BUCKET_INFO,
  BUCKETS,
  answer,
  isDone,
  pivotIndex,
  remainingComparisons,
  startSession,
  type Bucket,
  type InsertSession,
} from './ranking.ts';
import { ScorePill, Thumb, itemName, scoreMap } from './ui.tsx';
import type { Item } from './types.ts';

type Phase =
  | { kind: 'details' }
  | { kind: 'compare'; list: string[]; session: InsertSession; history: InsertSession[] }
  | { kind: 'result' };

/**
 * Full-screen flow that ranks each item in `queue`, one at a time:
 * 1. name it and pick a sentiment bucket, 2. answer "which did you prefer?"
 * until its position is known, 3. see its score.
 */
export function RankFlow({ categoryId, queue, onClose }: { categoryId: string; queue: string[]; onClose: () => void }) {
  const data = useData();
  const cat = data.categories.find((c) => c.id === categoryId);
  const [pos, setPos] = useState(0);
  const [phase, setPhase] = useState<Phase>({ kind: 'details' });
  // Items might be deleted elsewhere while the flow is open; skip those.
  const liveQueue = useMemo(() => queue.filter((id) => data.items.some((i) => i.id === id)), [queue, data.items]);
  const item = data.items.find((i) => i.id === liveQueue[pos]);

  // Form edits for the current item; falls back to the saved values whenever
  // we move to a different item, so it can never show a stale name.
  const [edits, setEdits] = useState<{ id: string; name: string; place: string; notes: string } | null>(null);
  const draft =
    edits && edits.id === item?.id ? edits : { id: item?.id ?? '', name: item?.name ?? '', place: item?.place ?? '', notes: item?.notes ?? '' };
  const setDraft = setEdits;

  const commit = useCallback(
    async (bucket: Bucket, index: number) => {
      if (!item) return;
      await placeItem(categoryId, item.id, bucket, index);
      setPhase({ kind: 'result' });
    },
    [categoryId, item],
  );

  const chooseBucket = async (bucket: Bucket) => {
    if (!item || !cat) return;
    await updateItem({ ...item, name: draft.name.trim(), place: draft.place.trim(), notes: draft.notes.trim() });
    const list = cat.rankings[bucket].filter((id) => id !== item.id);
    const session = startSession(bucket, list);
    if (isDone(session)) await commit(bucket, 0);
    else setPhase({ kind: 'compare', list, session, history: [] });
  };

  const respond = useCallback(
    async (choice: 'new' | 'pivot' | 'tie') => {
      if (phase.kind !== 'compare') return;
      const next = answer(phase.session, choice);
      if (isDone(next)) await commit(next.bucket, next.lo);
      else setPhase({ ...phase, session: next, history: [...phase.history, phase.session] });
    },
    [phase, commit],
  );

  const undo = () => {
    if (phase.kind !== 'compare') return;
    if (phase.history.length === 0) return setPhase({ kind: 'details' });
    setPhase({ ...phase, session: phase.history[phase.history.length - 1], history: phase.history.slice(0, -1) });
  };

  const next = () => {
    setPhase({ kind: 'details' });
    if (pos + 1 >= liveQueue.length) onClose();
    else setPos(pos + 1);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (phase.kind === 'compare') {
        if (e.key === 'ArrowLeft') respond('new');
        if (e.key === 'ArrowRight') respond('pivot');
        if (e.key === 'ArrowDown') respond('tie');
      }
      if (phase.kind === 'result' && e.key === 'Enter') next();
    };
    window.addEventListener('keydown', onKey);
    document.body.classList.add('no-scroll');
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.classList.remove('no-scroll');
    };
  });

  if (!cat || !item) {
    return (
      <div className="flow">
        <div className="flow-inner center">
          <p>Nothing left to rank.</p>
          <button className="btn primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    );
  }

  const header = (
    <div className="flow-header">
      <span className="muted">
        {cat.name} · {liveQueue.length > 1 ? `item ${pos + 1} of ${liveQueue.length}` : 'ranking'}
      </span>
      <button className="btn ghost" onClick={onClose}>
        Close
      </button>
    </div>
  );

  if (phase.kind === 'details') {
    return (
      <div className="flow">
        {header}
        <div className="flow-inner">
          <div className="flow-photo">
            <Thumb imageId={item.imageId} kind="full" size="100%" />
          </div>
          <div className="stack">
            <input
              className="input input-lg"
              placeholder="What was it? (e.g. Tonkotsu ramen)"
              value={draft.name}
              autoFocus={!draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
            <input
              className="input"
              placeholder="Where? (restaurant, stall, city — optional)"
              value={draft.place}
              onChange={(e) => setDraft({ ...draft, place: e.target.value })}
            />
            <textarea
              className="input"
              rows={2}
              placeholder="Notes (optional)"
              value={draft.notes}
              onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
            />
          </div>
          <h2 className="flow-question">How was it?</h2>
          <div className="bucket-buttons">
            {BUCKETS.map((b) => (
              <button key={b} className={`bucket-btn bucket-${b}`} onClick={() => chooseBucket(b)}>
                <span className="bucket-emoji">{BUCKET_INFO[b].emoji}</span>
                {BUCKET_INFO[b].label}
              </button>
            ))}
          </div>
          {liveQueue.length > 1 && (
            <button className="btn ghost center-self" onClick={next}>
              Skip for now →
            </button>
          )}
        </div>
      </div>
    );
  }

  if (phase.kind === 'compare') {
    const pivot = data.items.find((i) => i.id === phase.list[pivotIndex(phase.session)]);
    if (!pivot) return null;
    const left = remainingComparisons(phase.session);
    return (
      <div className="flow">
        {header}
        <div className="flow-inner">
          <h2 className="flow-question">Which did you prefer?</h2>
          <p className="muted center">
            {left <= 1 ? 'Last question' : `At most ${left} more questions`}
            <span className="desktop-only"> · ← / → keys work too</span>
          </p>
          <div className="versus">
            <CompareCard item={item} label="New" onPick={() => respond('new')} />
            <div className="vs">vs</div>
            <CompareCard item={pivot} onPick={() => respond('pivot')} />
          </div>
          <div className="row center">
            <button className="btn" onClick={undo}>
              ↶ Undo
            </button>
            <button className="btn" onClick={() => respond('tie')}>
              Too tough 🤷
            </button>
          </div>
        </div>
      </div>
    );
  }

  const entry = scoreMap(cat).get(item.id);
  const total = BUCKETS.reduce((n, b) => n + cat.rankings[b].length, 0);
  const remaining = liveQueue.length - pos - 1;
  return (
    <div className="flow">
      {header}
      <div className="flow-inner center">
        <Thumb imageId={item.imageId} size={160} />
        <h2>{itemName(item)}</h2>
        {entry && (
          <>
            <ScorePill score={entry.score} bucket={entry.bucket} big />
            <p className="muted">
              #{entry.rank} of {total} in {cat.name}
            </p>
          </>
        )}
        <button className="btn primary" onClick={next} autoFocus>
          {remaining > 0 ? `Next item (${remaining} left) →` : 'Done'}
        </button>
      </div>
    </div>
  );
}

function CompareCard({ item, label, onPick }: { item: Item; label?: string; onPick: () => void }) {
  return (
    <button className="compare-card" onClick={onPick}>
      {label && <span className="tag">{label}</span>}
      <Thumb imageId={item.imageId} size="100%" />
      <strong>{itemName(item)}</strong>
      {item.place && <span className="muted small">{item.place}</span>}
    </button>
  );
}
