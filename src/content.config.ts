import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const posts = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    type: z.enum(['research', 'blog']),
    tags: z.array(z.string()).default([]),
    author: z.string().default('Abhishek Shinde'),
    art: z.enum(['tetranet', 'ternary']),
  }),
});

export const collections = { posts };
