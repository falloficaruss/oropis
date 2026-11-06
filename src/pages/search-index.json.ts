import type { APIRoute } from 'astro';
import { getAllNews, storyUrl } from '../lib/news';

export const prerender = true;

export const GET: APIRoute = async () => {
  const stories = await getAllNews();
  const index = stories.map((story) => ({
    title: story.data.title,
    description: story.data.description,
    url: storyUrl(story),
    beat: story.data.beat,
    archetype: story.data.archetype,
    tags: story.data.tags,
    date: story.data.pubDate.toISOString(),
  }));

  return new Response(JSON.stringify(index), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
};
