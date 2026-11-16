import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const LAUNCH_TARGET = 12;

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const essaysDir = path.join(root, 'content', 'essays');

function frontmatter(text) {
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  return match ? match[1] : '';
}

function value(block, key) {
  const match = block.match(new RegExp(`^${key}:\\s*(.*)$`, 'm'));
  if (!match) return undefined;

  const raw = match[1].trim();
  if (raw.startsWith('"')) {
    const end = raw.lastIndexOf('"');
    if (end > 0) return raw.slice(1, end).replace(/\\"/g, '"');
  }
  if (raw.startsWith("'")) {
    const end = raw.lastIndexOf("'");
    if (end > 0) return raw.slice(1, end).replace(/''/g, "'");
  }

  return raw.replace(/\s+#.*$/, '').trim();
}

function boolean(block, key, fallback) {
  const raw = value(block, key);
  if (raw === undefined) return fallback;

  const normalized = raw.toLowerCase();
  if (normalized === 'true') return true;
  if (normalized === 'false') return false;
  return fallback;
}

export function readEssays() {
  if (!fs.existsSync(essaysDir)) return [];

  return fs
    .readdirSync(essaysDir)
    .filter((file) => file.endsWith('.md'))
    .sort()
    .map((file) => {
      const text = fs.readFileSync(path.join(essaysDir, file), 'utf8');
      const block = frontmatter(text);
      const slug = value(block, 'slug') ?? path.basename(file, '.md');

      return {
        file,
        slug,
        title: value(block, 'title') ?? slug,
        draft: boolean(block, 'draft', true),
      };
    });
}

export function publishedEssays() {
  return readEssays().filter((essay) => !essay.draft);
}

export function draftSlugs() {
  return new Set(readEssays().filter((essay) => essay.draft).map((essay) => essay.slug));
}

export function allowIncompleteLaunch() {
  const raw = (process.env.ALLOW_INCOMPLETE_LAUNCH ?? '').toLowerCase();
  return raw === '1' || raw === 'true' || raw === 'yes' || raw === 'on';
}
