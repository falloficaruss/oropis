import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const topics = ['robotics', 'ai', 'finance'] as const;

const essays = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './content/essays' }),
  schema: z
    .object({
      title: z.string().min(1),
      slug: z
        .string()
        .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'slug must be lowercase and hyphenated'),
      date: z.coerce.date(),
      topic: z.enum(topics),
      summary: z.string().min(1),
      hero_image: z.string().optional(),
      hero_alt: z.string().optional(),
      medium_url: z.string().url().optional(),
      draft: z.boolean().default(true),
    })
    .refine((data) => !data.hero_image || Boolean(data.hero_alt), {
      message: 'hero_alt is required when hero_image is set',
      path: ['hero_alt'],
    }),
});

export const collections = { essays };
