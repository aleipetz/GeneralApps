# GeneralApps
General purpose app repository. Each top-level folder is a standalone app.

| App | Description |
| --- | --- |
| [trip-bites](trip-bites/) | Rank the foods, teas, drinks and desserts from your trips, Beli-style. |

## Adding an app

Create a new top-level folder with its own `package.json` whose `npm run build` writes a static site to `dist/` (use relative asset paths, e.g. Vite `base: './'`). An optional `npm test` script runs before the build.

## Deployment

Pushing to `main` runs `.github/workflows/deploy.yml`, which builds every app and publishes them to GitHub Pages at `https://aleipetz.github.io/generalapps/<app>/`, with an index page at the root. Enable it once under **Settings → Pages → Source: GitHub Actions**.
