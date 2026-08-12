# Oropis

The source for [oropis.com](https://oropis.com) — research releases and writing on small models, low-bit LLMs, and efficient inference.

Built with **Astro** (MDX + KaTeX) and deployed to **GitHub Pages**.

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
  content/posts/      # MDX posts (research + blog)
  content.config.ts   # content collection schema (title, date, type, art, …)
  components/
    art/              # hand-drawn SVG art + data-driven chart figures per post
    *.astro           # PostCard, Figure, Tldr, Outline, Cite, Refs, Sec, …
  layouts/            # BaseLayout (header/nav/footer, fonts)
  pages/              # / (blog landing), /research, /blog, /about, /posts/[slug], /rss.xml, 404
  styles/global.css   # design tokens & component styles
```

## Adding a post

Drop an MDX file in `src/content/posts/`. Frontmatter:

```yaml
title: "..."
description: "one-line excerpt used on cards"
date: 2026-08-01
type: research        # or blog
tags: [quantization, ...]
author: Abhishek Shinde
art: tetranet         # or ternary — selects the SVG hero art
```

Give every post an SVG hero (`art`) — each post is designed to carry one.

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) builds and publishes `dist/` to
GitHub Pages on every push to `master`.

### One-time DNS setup

1. In **GitHub → repo → Settings → Pages**:
   - Source: *GitHub Actions*
   - Custom domain: `oropis.com` (leave the enforce-HTTPS checkbox on)
2. At your DNS provider, point `oropis.com` to the Pages host with one of:
   - **A records** → the four IPs shown in GitHub Pages settings, or
   - **CNAME / ALIAS** → `falloficaruss.github.io` (subdomain-style records for the domain root)
3. The `public/CNAME` file (already committed) makes Pages use the custom domain.

SSL certificate issuance by GitHub can take a few minutes to a day after DNS propagates.

## Notes

- Research posts read as technical releases under the author's name; the About
  page doubles as the personal portfolio (bio, timeline, projects, writing).
- Figures in the TetraNet post are rebuilt as inline SVG charts from the
  paper's tables (the original `Quaternary_paper.pdf` is not stored in this
  repo; its text is preserved in the post).
