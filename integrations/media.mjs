import fs from 'node:fs';
import path from 'node:path';

const MIME = {
  '.avif': 'image/avif',
  '.gif': 'image/gif',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
};

function draftSlugs() {
  const essaysDir = path.join(process.cwd(), 'content', 'essays');
  const drafts = new Set();
  if (!fs.existsSync(essaysDir)) return drafts;

  for (const file of fs.readdirSync(essaysDir)) {
    if (!file.endsWith('.md')) continue;
    const text = fs.readFileSync(path.join(essaysDir, file), 'utf8');
    const frontmatter = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!frontmatter) continue;
    const slug = frontmatter[1].match(/^slug:\s*["']?([a-z0-9-]+)["']?\s*$/m)?.[1];
    const draft = frontmatter[1].match(/^draft:\s*(true|false)\s*$/m)?.[1] ?? 'true';
    if (slug && draft !== 'false') drafts.add(slug);
  }

  return drafts;
}

export default function mediaFolder() {
  const mediaRoot = path.join(process.cwd(), 'media');

  return {
    name: 'oropis-media',
    hooks: {
      'astro:server:setup': ({ server }) => {
        server.middlewares.use('/media', (req, res, next) => {
          const pathname = decodeURIComponent((req.url || '/').split('?')[0]);
          const filePath = path.join(mediaRoot, pathname);
          const relative = path.relative(mediaRoot, filePath);

          if (relative.startsWith('..') || path.isAbsolute(relative)) {
            next();
            return;
          }

          fs.stat(filePath, (error, stat) => {
            if (error || !stat.isFile()) {
              next();
              return;
            }
            res.setHeader(
              'Content-Type',
              MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream',
            );
            fs.createReadStream(filePath).pipe(res);
          });
        });
      },
      'astro:build:done': ({ dir }) => {
        if (!fs.existsSync(mediaRoot)) return;
        const drafts = draftSlugs();
        fs.cpSync(mediaRoot, new URL('media/', dir), {
          recursive: true,
          filter: (source) => {
            if (path.basename(source) === '.gitkeep') return false;
            const relative = path.relative(mediaRoot, source);
            if (!relative || relative.startsWith('..')) return true;
            const [slug] = relative.split(path.sep);
            return !drafts.has(slug);
          },
        });
      },
    },
  };
}
