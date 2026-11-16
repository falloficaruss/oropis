import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { SITE } from '../config/site';
import { essayUrl, getEssays } from '../lib/essays';

export async function GET(context: APIContext) {
  const essays = await getEssays();

  return rss({
    title: SITE.title,
    description: SITE.description,
    site: context.site ?? new URL(SITE.url),
    items: essays.map((essay) => ({
      title: essay.data.title,
      pubDate: essay.data.date,
      description: essay.data.summary,
      link: essayUrl(essay),
      categories: [essay.data.topic],
    })),
    customData: '<language>en-us</language>',
  });
}
