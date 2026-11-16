import rss from '@astrojs/rss';
import type { APIRoute } from 'astro';
import { getAllNews, storyUrl } from '../lib/news';

export const prerender = true;

export const GET: APIRoute = async (context) => {
  const stories = await getAllNews();
  return rss({
    title: 'Oropis — Robotics & AI',
    description: 'Independent coverage of artificial intelligence and robotics: frontier models, research, humanoids, autonomy, policy, and the business of the machine economy.',
    site: context.site ?? 'https://oropis.com',
    items: stories.map((story) => ({
      title: story.data.title,
      description: story.data.description,
      pubDate: story.data.pubDate,
      link: storyUrl(story),
      categories: [story.data.beat, story.data.archetype, ...story.data.tags],
      author: story.data.author,
    })),
    customData: '<language>en-us</language>',
  });
};
