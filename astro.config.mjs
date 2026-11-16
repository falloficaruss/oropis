import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mediaFolder from './integrations/media.mjs';

export default defineConfig({
  site: 'https://oropis.com',
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/404') && !page.endsWith('/rss.xml'),
    }),
    mediaFolder(),
  ],
});
