import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import mediaFolder from './integrations/media.mjs';

export default defineConfig({
  site: 'https://oropis.com',
  output: 'static',
  trailingSlash: 'always',
  integrations: [sitemap(), mediaFolder()],
});
