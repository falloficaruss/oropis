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

export function gameSlug(game: string): string {
  return game
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

export function tagSlug(tag: string): string {
  return gameSlug(tag);
}

export const COVERED_GAMES = ['PUBG Mobile', 'Free Fire', 'Call of Duty: Mobile'] as const;

const GAME_CODES: Record<string, string> = {
  'PUBG Mobile': 'PUBGM',
  'Free Fire': 'FF',
  'Call of Duty: Mobile': 'CODM',
};

export function gameCode(game: string): string {
  return GAME_CODES[game] ?? game.slice(0, 2).toUpperCase();
}

export const SECTIONS = {
  results: {
    title: 'Results & schedule',
    description: 'Match results, upcoming series, brackets, and tournament schedules.',
    archetypes: ['match', 'tournament'],
  },
  transfers: {
    title: 'Roster moves',
    description: 'Signings, departures, free agents, and coach changes across the mobile scene.',
    archetypes: ['roster'],
  },
  patches: {
    title: 'Patches & meta',
    description: 'Patch notes, balance changes, and what they mean for competitive play.',
    archetypes: ['patch'],
  },
  business: {
    title: 'Esports business',
    description: 'Sponsorships, funding, layoffs, ownership, and the money behind mobile esports.',
    archetypes: ['business'],
  },
} as const;

export type SectionKey = keyof typeof SECTIONS;

export function sectionStories(stories: Story[], key: SectionKey): Story[] {
  const allowed = SECTIONS[key].archetypes as readonly string[];
  return stories.filter((story) => allowed.includes(story.data.archetype));
}

export function relatedStories(story: Story, all: Story[], limit = 3): Story[] {
  return all
    .filter((candidate) => candidate.id !== story.id)
    .map((candidate) => {
      let score = 0;
      if (candidate.data.game === story.data.game) score += 3;
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
