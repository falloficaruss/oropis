# Content guide

## Add a new essay

1. Pick a lowercase, hyphenated slug, for example `the-quiet-robot`.
2. Create `content/essays/the-quiet-robot.md`.
3. Start the file with this frontmatter:

```yaml
---
title: "The Quiet Robot"
slug: the-quiet-robot
date: 2026-11-16
topic: robotics
summary: "One or two sentences that explain the essay. This is used on cards, topic pages, and in search results."
hero_image: /media/the-quiet-robot/hero.webp
hero_alt: "Describe the image for someone who cannot see it."
medium_url: https://example.com/original-essay
draft: true
---
```

The filename and `slug` must match. Use `YYYY-MM-DD` for `date`.

`topic` must be one of:

- `robotics`
- `ai`
- `finance`

`hero_image` and `medium_url` are optional. If you set `hero_image`, you must
also set `hero_alt`. `hero_alt` is not needed when there is no hero image.

Do not add a reading-time field. Reading time is calculated automatically from
the word count.

## Drafts

Keep `draft: true` while writing. Drafts are hidden from production builds.

Preview drafts locally:

```bash
SHOW_DRAFTS=true npm run dev
```

Then open the local URL Astro prints. Drafts never appear in `npm run build`,
even if `SHOW_DRAFTS=true` is set.

Set `draft: false` when the essay is ready to publish.

## Media

Every essay has its own media folder:

```text
media/<slug>/
```

For the example above:

```text
media/the-quiet-robot/hero.webp
media/the-quiet-robot/a-second-image.webp
```

Rules:

- Use lowercase, hyphenated filenames.
- Reference hero images from frontmatter as `/media/<slug>/<filename>`.
- Reference inline images in Markdown as `![alt text](/media/<slug>/<filename>)`.
- Every image needs meaningful alt text. Do not leave alt text empty.
- Prefer WebP, AVIF, or SVG. Use `loading="lazy"` and explicit dimensions for
  inline images when possible.

## Essay body

Write normal Markdown below the frontmatter. Blockquotes and footnotes are
supported:

```markdown
> A pull quote.

A sentence with a footnote.[^1]

[^1]: The footnote text.
```

## Images in prose

Use Markdown image syntax with alt text:

```markdown
![A robot arm folding a towel](/media/the-quiet-robot/robot-arm.webp)
```

Do not hotlink images from other sites. Put the file in `media/<slug>/` and keep
a note of its source and credit in the essay or project records.
