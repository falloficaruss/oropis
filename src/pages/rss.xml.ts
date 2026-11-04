import rss from '@astrojs/rss';
import type { APIRoute } from 'astro';
import { getAllNews, storyUrl } from '../lib/news';

export const prerender = true;

export const GET: APIRoute = async (context) => {
  const stories = await getAllNews();
  return rss({
    title: 'Oropis — Mobile Esports',
    description: 'Independent mobile-esports coverage for PUBG Mobile and BGMI, Free Fire, and Call of Duty: Mobile.',
    site: context.site ?? 'https://oropis.com',
    items: stories.map((story) => ({
      title: story.data.title,
      description: story.data.description,
      pubDate: story.data.pubDate,
      link: storyUrl(story),
      categories: [story.data.game, story.data.archetype, ...story.data.tags],
      author: story.data.author,
    })),
    customData: '<language>en-us</language>',
  });
};
