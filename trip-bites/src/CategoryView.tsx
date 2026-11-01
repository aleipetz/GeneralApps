import { useRef, useState } from 'react';
import { addItemWithoutPhoto, addPhotos, deleteCategory, renameCategory, useData } from './store.ts';
import { BUCKET_INFO, BUCKETS } from './ranking.ts';
import { RankFlow } from './RankFlow.tsx';
import { ItemModal } from './ItemModal.tsx';
import { ScorePill, Thumb, go, itemName, scoreMap, unrankedItems } from './ui.tsx';

export function CategoryView({ tripId, categoryId }: { tripId: string; categoryId: string }) {
  const data = useData();
  const trip = data.trips.find((t) => t.id === tripId);
  const cat = data.categories.find((c) => c.id === categoryId);
  const [rankQueue, setRankQueue] = useState<string[] | null>(null);
  const [openItem, setOpenItem] = useState<string | null>(null);
  const [upload, setUpload] = useState<{ done: number; total: number } | null>(null);
  const [message, setMessage] = useState('');
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  if (!trip || !cat) return <NotFound />;

  const scores = scoreMap(cat);
  const unranked = unrankedItems(cat, data.items);
  const itemsById = new Map(data.items.map((i) => [i.id, i]));

  const handleFiles = async (fileList: FileList | null) => {
    const files = [...(fileList ?? [])].filter((f) => f.type.startsWith('image/') || /\.(heic|heif)$/i.test(f.name));
    if (files.length === 0) return;
    setMessage('');
    setUpload({ done: 0, total: files.length });
    const { added, failed } = await addPhotos(cat.id, files, (done, total) => setUpload({ done, total }));
    setUpload(null);
    setMessage(
      `Added ${added} photo${added === 1 ? '' : 's'}.` +
        (failed.length ? ` Couldn't read ${failed.length} (${failed.slice(0, 3).join(', ')}${failed.length > 3 ? '…' : ''}) — HEIC photos only work in Safari; export as JPEG elsewhere.` : ''),
    );
  };

  const addByName = async () => {
    const name = prompt('What did you have?');
    if (name?.trim()) {
      const item = await addItemWithoutPhoto(cat.id, name.trim());
      setRankQueue([item.id]);
    }
  };

  return (
    <div
      className={`page${dragging ? ' dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => e.currentTarget === e.target && setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <nav className="crumbs">
        <a href="#/">Trips</a> / <a href={`#/trip/${trip.id}`}>{trip.name}</a>
      </nav>
      <header className="page-header">
        <h1>{cat.name}</h1>
        <div className="row">
          <button
            className="btn ghost"
            onClick={() => {
              const name = prompt('Rename category', cat.name);
              if (name?.trim()) renameCategory(cat.id, name.trim());
            }}
          >
            Rename
          </button>
          <button
            className="btn ghost danger"
            onClick={async () => {
              if (confirm(`Delete "${cat.name}" and all its items and photos?`)) {
                await deleteCategory(cat.id);
                go(`/trip/${trip.id}`);
              }
            }}
          >
            Delete
          </button>
        </div>
      </header>

      <section className="card upload">
        <input
          ref={fileInput}
          type="file"
          accept="image/*,.heic,.heif"
          multiple
          hidden
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
        {upload ? (
          <div className="stack">
            <span>
              Processing photos… {upload.done}/{upload.total}
            </span>
            <progress value={upload.done} max={upload.total} />
          </div>
        ) : (
          <div className="row wrap">
            <button className="btn primary" onClick={() => fileInput.current?.click()}>
              📷 Upload photos
            </button>
            <button className="btn" onClick={addByName}>
              + Add without photo
            </button>
            <span className="muted small">or drop photos anywhere on this page</span>
          </div>
        )}
        {message && <p className="small">{message}</p>}
      </section>

      {unranked.length > 0 && (
        <section className="card">
          <div className="row spread">
            <h2>To rank ({unranked.length})</h2>
            <button className="btn primary" onClick={() => setRankQueue(unranked.map((i) => i.id))}>
              Start ranking →
            </button>
          </div>
          <div className="strip">
            {unranked.map((i) => (
              <button
                key={i.id}
                className="strip-item"
                title={itemName(i)}
                onClick={() => setRankQueue([i.id, ...unranked.filter((u) => u.id !== i.id).map((u) => u.id)])}
              >
                <Thumb imageId={i.imageId} size={72} />
                <span className="small ellipsis">{i.name || '—'}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2>Your ranking</h2>
        {scores.size === 0 ? (
          <p className="muted">Nothing ranked yet. Upload photos, then rank them by picking favorites head-to-head.</p>
        ) : (
          BUCKETS.filter((b) => cat.rankings[b].length > 0).map((b) => (
            <div key={b} className="bucket-group">
              <h3 className={`bucket-title bucket-${b}`}>
                {BUCKET_INFO[b].emoji} {BUCKET_INFO[b].label}
              </h3>
              <ol className="rank-list">
                {cat.rankings[b].map((id) => {
                  const item = itemsById.get(id);
                  const entry = scores.get(id)!;
                  if (!item) return null;
                  return (
                    <li key={id}>
                      <button className="rank-row" onClick={() => setOpenItem(id)}>
                        <span className="rank-num">{entry.rank}</span>
                        <Thumb imageId={item.imageId} size={56} />
                        <span className="rank-text">
                          <strong>{itemName(item)}</strong>
                          {(item.place || item.notes) && (
                            <span className="muted small ellipsis">{[item.place, item.notes].filter(Boolean).join(' · ')}</span>
                          )}
                        </span>
                        <ScorePill score={entry.score} bucket={entry.bucket} />
                      </button>
                    </li>
                  );
                })}
              </ol>
            </div>
          ))
        )}
      </section>

      {openItem && (
        <ItemModal
          key={openItem}
          itemId={openItem}
          onClose={() => setOpenItem(null)}
          onRerank={(id) => {
            setOpenItem(null);
            setRankQueue([id]);
          }}
        />
      )}
      {rankQueue && <RankFlow categoryId={cat.id} queue={rankQueue} onClose={() => setRankQueue(null)} />}
    </div>
  );
}

export function NotFound() {
  return (
    <div className="page center">
      <p>That page doesn't exist (maybe it was deleted).</p>
      <a className="btn" href="#/">
        Back to trips
      </a>
    </div>
  );
}
