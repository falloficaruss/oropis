import { getCollection, type CollectionEntry } from 'astro:content';

export type Story = CollectionEntry<'news'>;

export async function getAllNews(): Promise<Story[]> {
  const stories = await getCollection('news');
  return stories.sort((a, b) => b.data.pubDate.getTime() - a.data.pubDate.getTime());
}

export function storyUrl(story: Story): string {
  return `/news/${story.id}/`;
}

export function fmtDate(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function fmtDateLong(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function isoDate(date: Date): string {
  return date.toISOString();
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

export function beatSlug(beat: string): string {
  return slugify(beat);
}

export function tagSlug(tag: string): string {
  return slugify(tag);
}

export const COVERED_BEATS = ['AI', 'Robotics'] as const;

const BEAT_CODES: Record<string, string> = {
  AI: 'AI',
  Robotics: 'ROB',
};

export function beatCode(beat: string): string {
  return BEAT_CODES[beat] ?? beat.slice(0, 3).toUpperCase();
}

interface SectionDef {
  title: string;
  description: string;
  beats?: readonly string[];
  archetypes?: readonly string[];
}

export const SECTIONS: Record<string, SectionDef> = {
  ai: {
    title: 'Artificial intelligence',
    description: 'Frontier models, agents, products, and the state of the art — explained without the hype.',
    beats: ['AI'],
  },
  robotics: {
    title: 'Robotics',
    description: 'Humanoids, industrial arms, autonomous fleets, drones, and the systems moving into the physical world.',
    beats: ['Robotics'],
  },
  research: {
    title: 'Research',
    description: 'Papers, benchmarks, labs, and the results that change what machines can do.',
    archetypes: ['research'],
  },
  industry: {
    title: 'Industry',
    description: 'Funding, regulation, standards, and the business of building intelligent machines.',
    archetypes: ['funding', 'business', 'policy'],
  },
};

export type SectionKey = keyof typeof SECTIONS;

export function sectionStories(stories: Story[], key: SectionKey): Story[] {
  const section = SECTIONS[key];
  if (!section) return [];
  if (section.beats) {
    return stories.filter((story) => section.beats!.includes(story.data.beat));
  }
  const allowed = section.archetypes ?? [];
  return stories.filter((story) => allowed.includes(story.data.archetype));
}

export function relatedStories(story: Story, all: Story[], limit = 3): Story[] {
  return all
    .filter((candidate) => candidate.id !== story.id)
    .map((candidate) => {
      let score = 0;
      if (candidate.data.beat === story.data.beat) score += 3;
      const shared = candidate.data.tags.filter((tag) => story.data.tags.includes(tag));
      score += shared.length;
      return { candidate, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score || b.candidate.data.pubDate.getTime() - a.candidate.data.pubDate.getTime())
    .slice(0, limit)
    .map((item) => item.candidate);
}

export function formatArchetype(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
