import { getCollection, type CollectionEntry } from 'astro:content';

export type Essay = CollectionEntry<'essays'>;

export const TOPICS = ['robotics', 'ai', 'finance'] as const;
export type Topic = (typeof TOPICS)[number];

const DRAFTS_VISIBLE = import.meta.env.DEV && process.env.SHOW_DRAFTS === 'true';

export function draftsVisible(): boolean {
  return DRAFTS_VISIBLE;
}

export async function getEssays(): Promise<Essay[]> {
  const essays = await getCollection('essays');
  return essays
    .filter((essay) => !essay.data.draft || DRAFTS_VISIBLE)
    .sort((a, b) => b.data.date.getTime() - a.data.date.getTime());
}

export async function getEssaysByTopic(topic: Topic): Promise<Essay[]> {
  return (await getEssays()).filter((essay) => essay.data.topic === topic);
}

export function readingTime(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.ceil(words / 220));
}

export function readingMinutes(essay: Essay): number {
  return readingTime(essay.body ?? '');
}

export function essayUrl(essay: Essay): string {
  return `/essays/${essay.data.slug}/`;
}

export function topicLabel(topic: Topic): string {
  return topic === 'ai' ? 'AI' : topic.charAt(0).toUpperCase() + topic.slice(1);
}

export function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function relatedEssays(essay: Essay, all: Essay[], limit = 3): Essay[] {
  return all
    .filter((candidate) => candidate.data.slug !== essay.data.slug)
    .map((candidate) => ({
      candidate,
      score: candidate.data.topic === essay.data.topic ? 1 : 0,
    }))
    .sort(
      (a, b) =>
        b.score - a.score ||
        b.candidate.data.date.getTime() - a.candidate.data.date.getTime(),
    )
    .slice(0, limit)
    .map((item) => item.candidate);
}
