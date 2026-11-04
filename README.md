# Oropis

The source for [oropis.com](https://oropis.com) — an independent mobile esports desk covering
**PUBG Mobile / BGMI**, **Free Fire**, and **Call of Duty: Mobile**.

Published stories live in `src/content/news/` as Markdown. The `agg` pipeline owns that
directory: drafts are edited in the local admin app, published into `site.db`, and exported
here by the deploy timer.

## Local development

```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # static output in dist/
npm run preview    # serve the built site
```

## Project layout

```
src/
  content/news/          # published stories (generated from site.db)
  content.config.ts      # news collection schema
  components/            # StoryCard, NewsList, FactBox, SourceList, Pagination, …
  layouts/BaseLayout.astro
  lib/news.ts            # story helpers: URLs, sections, dates, related stories
  pages/
    index.astro          # homepage
    news/                # story index, pagination, story pages
    games/               # per-game hubs
    [section].astro      # results, transfers, patches, business
    tags/                # tag index and tag pages
    search.astro         # client-side search
    rss.xml.ts
  styles/global.css
```

## Editorial flow

Do not write story Markdown by hand for normal publishing. Use the `agg` admin at
`http://127.0.0.1:8091/admin` (SSH tunnel from a laptop), or the CLI:

```bash
agg -a gaming site sync --since 72
agg -a gaming site publish ID
agg -a gaming site deploy --dry-run
```

`site deploy` exports published stories into `src/content/news/`, builds the site, commits,
and pushes to `master`. It runs `git fetch` and `git reset --hard origin/master` first, so any
local site-code changes must be committed and pushed before the timer runs.

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) builds and publishes `dist/` to GitHub Pages
on every push to `master`.

DNS is already configured:

- `oropis.com` → GitHub Pages A records
- `www.oropis.com` → `falloficaruss.github.io`
- `public/CNAME` sets the custom domain
- Pages source: **GitHub Actions**, HTTPS enforced

## Images

Images are uploaded through the story editor in the admin.

- **Hero:** upload a JPEG/PNG/WebP, add alt text and credit, then save or publish.
- **Inline:** upload with required alt text and optional caption/credit; the editor
  inserts a responsive `<figure>` at the cursor.
- The server converts uploads to WebP, strips metadata, and resizes to 2000 px
  (hero) or 1600 px (inline).
- Source files live outside this repo in `gaming/site-media/uploads/`. The exporter
  copies them into `public/media/` and tracks them in `src/content/news/.export.json`.
- Do not hotlink images or add files directly to `public/media/`; the deploy timer
  resets the repo before exporting.

## Notes

- Every story needs a headline, body, at least one source, and an editor review.
- Byline is `OropisHQ`; credit other outlets and link primary sources.
- Hero images are cached locally with visible credit. No hotlinking.
- Do not publish source text wholesale; rewrite from the drafting packet.
