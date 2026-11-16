# Oropis

A static essay blog about robotics, artificial intelligence, and finance.

## Development

```bash
npm install
npm run dev
```

To preview drafts locally:

```bash
SHOW_DRAFTS=true npm run dev
```

## Build

```bash
npm run build
npm run preview
```

The production build enforces the launch gate: it fails until at least 12
published essays exist. Check readiness with:

```bash
npm run launch-check
```

It exits non-zero until the threshold is met. To build an incomplete preview
without changing the gate:

```bash
ALLOW_INCOMPLETE_LAUNCH=true npm run build
```

The override only affects the local build. The build is static and can be hosted
on GitHub Pages. There is no automatic deploy configured; publishing is a
deliberate manual step.

## Content

Essays live in `content/essays/` as Markdown files. Images live in
`media/<slug>/`. See `CONTENT-GUIDE.md` for the frontmatter, naming rules,
draft behavior, and media layout.
