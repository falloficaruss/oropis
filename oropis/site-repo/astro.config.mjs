import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export default defineConfig({
  site: 'https://oropis.com',
  output: 'static',
  trailingSlash: 'always',
  markdown: {
    remarkPlugins: [remarkMath],
    rehypePlugins: [[rehypeKatex, { strict: false }]],
  },
  integrations: [
    sitemap({
      filter: (page) => !page.includes('/search/') && !page.includes('/search-index.json') && !page.includes('/admin/'),
    }),
  ],
});
