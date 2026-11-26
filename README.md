# Oropis

A minimal Jekyll publication about photonic computing and optical AI infrastructure. Built for GitHub Pages' native Jekyll build: no Node, no npm, no JavaScript frameworks, and no custom GitHub Actions.

## 1. Publish on GitHub Pages

1. Push this repository to GitHub.
2. In the repository, open **Settings → Pages**, set **Source** to **Deploy from a branch**, and choose `main` + `/ (root)`.
3. Set **Custom domain** to `oropis.com` and enable **Enforce HTTPS**. At your DNS provider, replace the existing records with GitHub Pages' apex `A` records (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) and a `www` `CNAME` to `<your-username>.github.io`. The included `CNAME` file pins the domain.

## 2. Add an essay

1. Copy `_drafts/post-template.md` to `_posts/YYYY-MM-DD-your-slug.md` (the filename date must match the `date` in frontmatter).
2. Fill in `title`, `date`, `pillar`, `subtitle`, and `math`; write the essay below the frontmatter in Markdown.
3. Commit and push to `main`. GitHub Pages rebuilds automatically, and the home page switches from "Coming soon." to the essay list on the first published post.

## 3. Plug in tracker data

1. Replace `[]` in `_data/bottlenecks.json` with an array of objects.
2. Each object uses this shape:

   ```json
   [
     {
       "name": "Bottleneck name",
       "track": "Interconnects",
       "stage": "L3",
       "metric": "pJ/bit · Tbps/mm",
       "status": "Open",
       "note": "One sentence on the current wall.",
       "updated": "2026-11-25",
       "source": "https://example.com"
     }
   ]
   ```

3. Commit and push to `main`. `/tracker/` renders the table automatically, and an empty array keeps the "Coming soon." state.

The local `workflow/` folder is excluded in `_config.yml` and is never published.
