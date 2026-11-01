# 🍜 Trip Bites

Rank the foods (and teas, drinks, desserts…) you had on your trips — Beli-style, one head-to-head at a time.

## Features

- **Trips as collections** — name, place and dates.
- **Categories within each trip** — Foods, Teas, Drinks, Desserts by default, plus any custom ones.
- **Bulk photo upload** — pick or drag & drop many photos at once; each becomes an item waiting to be ranked. Photos are resized on your device to save space.
- **Beli-style ranking** — for each item, say whether you liked it, it was fine, or you didn't like it, then answer "Which did you prefer?" against items you already ranked. A binary search places it with only a few questions (about 4 for 15 items). "Too tough" places it next to the item you're comparing against, and Undo steps back.
- **Scores** — 6.8–10 for liked, 3.4–6.7 for fine, 0–3.3 for disliked, spread by position.
- **Rankings view** — ranked list per category, top 3 on each trip page, and a **Best across all trips** view that merges categories with the same name.
- **Keep it up to date** — add new photos anytime, rename, add notes and places, move items between categories, re-rank or delete.
- **Private and offline** — everything is stored in your browser (IndexedDB). Use **Export backup / Import backup** to move your data between devices.

## Development

```bash
npm install
npm run dev      # start the dev server
npm test         # ranking algorithm unit tests
npm run build    # type-check + production build into dist/
```

## Deploy

Pushing to `main` runs the repo-level workflow (`../.github/workflows/deploy.yml`), which tests, builds and publishes this app to `https://aleipetz.github.io/generalapps/trip-bites/`.
Turn it on once under **Settings → Pages → Source: GitHub Actions**.

> HEIC photos (the iPhone default) only decode in Safari. In other browsers, export them as JPEG first, or set the iPhone camera to "Most Compatible".
