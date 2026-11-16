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
        fs.cpSync(mediaRoot, new URL('media/', dir), {
          recursive: true,
          filter: (source) => path.basename(source) !== '.gitkeep',
        });
      },
    },
  };
}
