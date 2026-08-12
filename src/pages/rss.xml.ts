import rss from '@astrojs/rss';
import type { APIRoute } from 'astro';
import { getAllPosts, postUrl } from '../lib/posts';

export const GET: APIRoute = async (context) => {
  const posts = await getAllPosts();
  return rss({
    title: 'Oropis',
    description: 'Research and writing on small models.',
    site: context.site!,
    items: posts.map((post) => ({
      title: post.data.title,
      description: post.data.description,
      pubDate: post.data.date,
      link: postUrl(post),
    })),
  });
};
