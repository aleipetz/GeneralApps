import { useEffect, useRef, useState } from 'react';
import {
  addCategory,
  createTrip,
  deleteTrip,
  exportBackup,
  importBackup,
  updateTrip,
  useData,
  type Data,
} from './store.ts';
import { rankedEntries } from './ranking.ts';
import { CategoryView, NotFound } from './CategoryView.tsx';
import { ScorePill, Thumb, formatDates, go, itemName, scoreMap, unrankedItems } from './ui.tsx';
import { DEFAULT_CATEGORIES, SUGGESTED_CATEGORIES, type Category, type Trip } from './types.ts';

function useRoute(): string[] {
  const [hash, setHash] = useState(location.hash);
  useEffect(() => {
    const f = () => {
      setHash(location.hash);
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', f);
    return () => window.removeEventListener('hashchange', f);
  }, []);
  return hash.replace(/^#\/?/, '').split('/').filter(Boolean);
}

export function App() {
  const data = useData();
  const route = useRoute();
  if (!data.loaded) return <div className="page center muted">Loading…</div>;
  if (route[0] === 'trip' && route[2] === 'c' && route[3]) return <CategoryView tripId={route[1]} categoryId={route[3]} />;
  if (route[0] === 'trip' && route[1]) return <TripView tripId={route[1]} />;
  if (route[0] === 'best') return <BestView />;
  if (route.length === 0) return <Home />;
  return <NotFound />;
}

// ---------------- Home ----------------

function tripCover(data: Data, tripId: string): string | null {
  const cats = data.categories.filter((c) => c.tripId === tripId);
  for (const c of cats) {
    const top = data.items.find((i) => i.id === rankedEntries(c.rankings)[0]?.id);
    if (top?.imageId) return top.imageId;
  }
  return data.items.find((i) => i.tripId === tripId && i.imageId)?.imageId ?? null;
}

function Home() {
  const data = useData();
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState('');
  const importInput = useRef<HTMLInputElement>(null);

  const [backup, setBackup] = useState<File | null>(null);

  // Step 1: build the backup (can take a while with many photos).
  const prepareExport = async () => {
    setBusy('Preparing backup…');
    try {
      const blob = await exportBackup();
      setBackup(new File([blob], `trip-bites-backup-${new Date().toISOString().slice(0, 10)}.json`, { type: 'application/json' }));
    } finally {
      setBusy('');
    }
  };

  // Step 2, on a fresh tap: iOS only opens the share sheet right after a tap.
  const saveBackup = async () => {
    if (!backup) return;
    if (navigator.canShare?.({ files: [backup] })) {
      try {
        await navigator.share({ files: [backup], title: 'Trip Bites backup' });
        setBackup(null);
        return;
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
        // Fall through to a regular download.
      }
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(backup);
    a.download = backup.name;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 60_000);
    setBackup(null);
  };

  const doImport = async (file: File | undefined) => {
    if (!file) return;
    setBusy('Importing…');
    try {
      const n = await importBackup(file);
      alert(`Imported ${n} trip${n === 1 ? '' : 's'}.`);
    } catch (e) {
      alert(`Import failed: ${(e as Error).message}`);
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <h1>🍜 Trip Bites</h1>
        <p className="muted">Rank everything you ate and drank on your trips — one head-to-head at a time.</p>
      </header>

      <div className="row spread">
        <h2>Your trips</h2>
        {!creating && (
          <button className="btn primary" onClick={() => setCreating(true)}>
            + New trip
          </button>
        )}
      </div>

      {creating && (
        <TripForm
          onCancel={() => setCreating(false)}
          onSubmit={async (fields, cats) => {
            const trip = await createTrip(fields, cats);
            go(`/trip/${trip.id}`);
          }}
        />
      )}

      {data.trips.length === 0 && !creating ? (
        <div className="card center empty">
          <p>No trips yet. Create one, add categories like Foods or Teas, upload your photos and start ranking.</p>
        </div>
      ) : (
        <div className="grid">
          {[...data.trips].reverse().map((t) => {
            const items = data.items.filter((i) => i.tripId === t.id);
            const ranked = data.categories.filter((c) => c.tripId === t.id).reduce((n, c) => n + rankedEntries(c.rankings).length, 0);
            return (
              <a key={t.id} className="trip-card" href={`#/trip/${t.id}`}>
                <Thumb imageId={tripCover(data, t.id)} size="100%" />
                <div className="trip-card-body">
                  <strong>{t.name}</strong>
                  <span className="muted small">{[t.place, formatDates(t)].filter(Boolean).join(' · ')}</span>
                  <span className="small">
                    {items.length} item{items.length === 1 ? '' : 's'} · {ranked} ranked
                  </span>
                </div>
              </a>
            );
          })}
        </div>
      )}

      <footer className="footer row wrap">
        {data.trips.length > 0 && (
          <a className="btn" href="#/best">
            🏆 Best across all trips
          </a>
        )}
        {backup ? (
          <button className="btn primary" onClick={saveBackup}>
            💾 Save backup ({(backup.size / 1024 / 1024).toFixed(1)} MB)
          </button>
        ) : (
          <button className="btn ghost" onClick={prepareExport} disabled={!!busy || data.trips.length === 0}>
            Export backup
          </button>
        )}
        <button className="btn ghost" onClick={() => importInput.current?.click()} disabled={!!busy}>
          Import backup
        </button>
        <input ref={importInput} type="file" accept="application/json,.json" hidden onChange={(e) => doImport(e.target.files?.[0])} />
        {busy && <span className="muted small">{busy}</span>}
      </footer>
      <p className="muted small">
        Everything is stored privately in this browser. On iPhone, tap Share → <strong>Add to Home Screen</strong> to use it like an app and keep
        your data safest, and export a backup now and then.
      </p>
    </div>
  );
}

function TripForm({
  initial,
  onSubmit,
  onCancel,
}: {
  initial?: Trip;
  onSubmit: (fields: Omit<Trip, 'id' | 'createdAt'>, categories: string[]) => Promise<void>;
  onCancel: () => void;
}) {
  const [f, setF] = useState({
    name: initial?.name ?? '',
    place: initial?.place ?? '',
    startDate: initial?.startDate ?? '',
    endDate: initial?.endDate ?? '',
  });
  const [cats, setCats] = useState<string[]>(DEFAULT_CATEGORIES);
  const toggle = (c: string) => setCats(cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c]);
  return (
    <form
      className="card stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (f.name.trim()) onSubmit({ ...f, name: f.name.trim(), place: f.place.trim() }, cats);
      }}
    >
      <input className="input input-lg" placeholder="Trip name (e.g. Japan 2026)" value={f.name} autoFocus onChange={(e) => setF({ ...f, name: e.target.value })} />
      <input className="input" placeholder="Where (optional)" value={f.place} onChange={(e) => setF({ ...f, place: e.target.value })} />
      <div className="row wrap">
        <label className="label">
          From
          <input className="input" type="date" value={f.startDate} onChange={(e) => setF({ ...f, startDate: e.target.value })} />
        </label>
        <label className="label">
          To
          <input className="input" type="date" value={f.endDate} onChange={(e) => setF({ ...f, endDate: e.target.value })} />
        </label>
      </div>
      {!initial && (
        <div className="stack">
          <span className="label">Categories (you can add more later)</span>
          <div className="chips">
            {SUGGESTED_CATEGORIES.map((c) => (
              <button type="button" key={c} className={`chip${cats.includes(c) ? ' on' : ''}`} onClick={() => toggle(c)}>
                {c}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="row">
        <button className="btn primary" type="submit" disabled={!f.name.trim()}>
          {initial ? 'Save' : 'Create trip'}
        </button>
        <button className="btn ghost" type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

// ---------------- Trip ----------------

function TripView({ tripId }: { tripId: string }) {
  const data = useData();
  const trip = data.trips.find((t) => t.id === tripId);
  const [editing, setEditing] = useState(false);
  const [newCat, setNewCat] = useState('');
  if (!trip) return <NotFound />;
  const cats = data.categories.filter((c) => c.tripId === trip.id);
  const existing = new Set(cats.map((c) => c.name.toLowerCase()));
  const suggestions = SUGGESTED_CATEGORIES.filter((s) => !existing.has(s.toLowerCase()));

  const add = async (name: string) => {
    if (!name.trim()) return;
    const cat = await addCategory(trip.id, name.trim());
    setNewCat('');
    go(`/trip/${trip.id}/c/${cat.id}`);
  };

  return (
    <div className="page">
      <nav className="crumbs">
        <a href="#/">Trips</a>
      </nav>
      {editing ? (
        <TripForm
          initial={trip}
          onCancel={() => setEditing(false)}
          onSubmit={async (fields) => {
            await updateTrip({ ...trip, ...fields });
            setEditing(false);
          }}
        />
      ) : (
        <header className="page-header">
          <div>
            <h1>{trip.name}</h1>
            <p className="muted">{[trip.place, formatDates(trip)].filter(Boolean).join(' · ')}</p>
          </div>
          <div className="row">
            <button className="btn ghost" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button
              className="btn ghost danger"
              onClick={async () => {
                if (confirm(`Delete "${trip.name}" with all its categories, items and photos?`)) {
                  await deleteTrip(trip.id);
                  go('/');
                }
              }}
            >
              Delete
            </button>
          </div>
        </header>
      )}

      <div className="grid grid-cats">
        {cats.map((c) => (
          <CategoryCard key={c.id} cat={c} />
        ))}
      </div>

      <section className="card stack">
        <h2>Add a category</h2>
        {suggestions.length > 0 && (
          <div className="chips">
            {suggestions.map((s) => (
              <button key={s} className="chip" onClick={() => add(s)}>
                + {s}
              </button>
            ))}
          </div>
        )}
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            add(newCat);
          }}
        >
          <input className="input" placeholder="Custom category (e.g. Ramen)" value={newCat} onChange={(e) => setNewCat(e.target.value)} />
          <button className="btn" disabled={!newCat.trim()}>
            Add
          </button>
        </form>
      </section>
    </div>
  );
}

function CategoryCard({ cat }: { cat: Category }) {
  const data = useData();
  const entries = rankedEntries(cat.rankings);
  const unranked = unrankedItems(cat, data.items).length;
  return (
    <a className="card cat-card" href={`#/trip/${cat.tripId}/c/${cat.id}`}>
      <div className="row spread">
        <h2>{cat.name}</h2>
        {unranked > 0 && <span className="tag tag-alert">{unranked} to rank</span>}
      </div>
      {entries.length === 0 ? (
        <p className="muted small">{unranked > 0 ? 'Tap to start ranking' : 'Empty — tap to upload photos'}</p>
      ) : (
        <ol className="mini-list">
          {entries.slice(0, 3).map((e) => {
            const item = data.items.find((i) => i.id === e.id);
            return (
              item && (
                <li key={e.id}>
                  <span className="rank-num">{e.rank}</span>
                  <Thumb imageId={item.imageId} size={40} />
                  <span className="ellipsis grow">{itemName(item)}</span>
                  <ScorePill score={e.score} bucket={e.bucket} />
                </li>
              )
            );
          })}
        </ol>
      )}
      {entries.length > 3 && <span className="muted small">+ {entries.length - 3} more</span>}
    </a>
  );
}

// ---------------- Best across trips ----------------

function BestView() {
  const data = useData();
  // Group categories with the same name across trips (e.g. every "Desserts").
  const groups = new Map<string, Category[]>();
  for (const c of data.categories) {
    const key = c.name.trim().toLowerCase();
    groups.set(key, [...(groups.get(key) ?? []), c]);
  }
  const names = [...groups.keys()];
  const [selected, setSelected] = useState(names[0] ?? '');
  const cats = groups.get(selected) ?? [];
  const rows = cats
    .flatMap((c) => {
      const scores = scoreMap(c);
      return [...scores.values()].map((e) => ({ e, item: data.items.find((i) => i.id === e.id), trip: data.trips.find((t) => t.id === c.tripId) }));
    })
    .filter((r) => r.item)
    .sort((a, b) => b.e.score - a.e.score);

  return (
    <div className="page">
      <nav className="crumbs">
        <a href="#/">Trips</a>
      </nav>
      <h1>🏆 Best across all trips</h1>
      <p className="muted small">Scores come from each trip's own ranking, so this is a blended view.</p>
      <div className="chips">
        {names.map((n) => (
          <button key={n} className={`chip${n === selected ? ' on' : ''}`} onClick={() => setSelected(n)}>
            {groups.get(n)![0].name}
          </button>
        ))}
      </div>
      {rows.length === 0 ? (
        <p className="muted">Nothing ranked in this category yet.</p>
      ) : (
        <ol className="rank-list">
          {rows.map(({ e, item, trip }, i) => (
            <li key={e.id}>
              <a className="rank-row" href={`#/trip/${trip?.id}/c/${item!.categoryId}`}>
                <span className="rank-num">{i + 1}</span>
                <Thumb imageId={item!.imageId} size={56} />
                <span className="rank-text">
                  <strong>{itemName(item!)}</strong>
                  <span className="muted small ellipsis">{[trip?.name, item!.place].filter(Boolean).join(' · ')}</span>
                </span>
                <ScorePill score={e.score} bucket={e.bucket} />
              </a>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
