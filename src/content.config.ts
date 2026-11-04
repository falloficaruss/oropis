import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const source = z.object({
  name: z.string(),
  url: z.string().url(),
  publisher: z.string().optional(),
});

const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    updatedDate: z.coerce.date().optional(),
    author: z.string().default('OropisHQ'),
    game: z.string().default('Esports'),
    archetype: z.string().default('news'),
    format: z.string().default('news'),
    tags: z.array(z.string()).default([]),
    hero: z.string().optional(),
    heroCredit: z.string().optional(),
    sources: z.array(source).default([]),
    facts: z.record(z.string(), z.any()).default({}),
    xPostUrl: z.string().url().optional(),
  }),
});

export const collections = { news };
