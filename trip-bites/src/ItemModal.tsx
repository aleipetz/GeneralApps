import { useState } from 'react';
import { deleteItem, moveItem, unrankItem, updateItem, useData } from './store.ts';
import { BUCKET_INFO } from './ranking.ts';
import { Modal, ScorePill, Thumb, scoreMap } from './ui.tsx';

export function ItemModal({ itemId, onClose, onRerank }: { itemId: string; onClose: () => void; onRerank: (id: string) => void }) {
  const data = useData();
  const item = data.items.find((i) => i.id === itemId);
  const [draft, setDraft] = useState(() => ({ name: item?.name ?? '', place: item?.place ?? '', notes: item?.notes ?? '' }));
  if (!item) return null;
  const cat = data.categories.find((c) => c.id === item.categoryId);
  const entry = scoreMap(cat).get(item.id);
  const siblings = data.categories.filter((c) => c.tripId === item.tripId);
  const dirty = draft.name !== item.name || draft.place !== item.place || draft.notes !== item.notes;

  const save = () => updateItem({ ...item, name: draft.name.trim(), place: draft.place.trim(), notes: draft.notes.trim() });

  return (
    <Modal onClose={onClose} wide>
      <div className="item-modal">
        <div className="item-photo">
          <Thumb imageId={item.imageId} kind="full" size="100%" />
        </div>
        <div className="stack">
          <div className="row">
            {entry ? (
              <>
                <ScorePill score={entry.score} bucket={entry.bucket} big />
                <span className="muted">
                  #{entry.rank} in {cat?.name} · {BUCKET_INFO[entry.bucket].emoji} {BUCKET_INFO[entry.bucket].label}
                </span>
              </>
            ) : (
              <span className="tag">Not ranked yet</span>
            )}
          </div>
          <label className="label">
            Name
            <input className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </label>
          <label className="label">
            Where
            <input className="input" value={draft.place} onChange={(e) => setDraft({ ...draft, place: e.target.value })} />
          </label>
          <label className="label">
            Notes
            <textarea className="input" rows={3} value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} />
          </label>
          <label className="label">
            Category
            <select className="input" value={item.categoryId} onChange={(e) => moveItem(item.id, e.target.value)}>
              {siblings.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <div className="row wrap">
            <button className="btn primary" disabled={!dirty} onClick={save}>
              Save
            </button>
            <button
              className="btn"
              onClick={async () => {
                if (dirty) await save();
                onRerank(item.id);
              }}
            >
              {entry ? 'Re-rank' : 'Rank it'}
            </button>
            {entry && (
              <button className="btn" onClick={() => unrankItem(item.categoryId, item.id)}>
                Remove from ranking
              </button>
            )}
            <button
              className="btn danger"
              onClick={async () => {
                if (confirm('Delete this item and its photo?')) {
                  await deleteItem(item.id);
                  onClose();
                }
              }}
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
