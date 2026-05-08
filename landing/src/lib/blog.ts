import fs from 'node:fs';
import path from 'node:path';

const BLOG_DIR = path.join(process.cwd(), 'content', 'blog');

export type Post = {
  slug: string;
  title: string;
  date: string;
  excerpt?: string;
};

/**
 * Very lightweight MDX frontmatter reader (no extra deps).
 * Frontmatter is delimited by `---` and parses simple key: value pairs.
 */
function readFrontmatter(file: string): Record<string, string> {
  const raw = fs.readFileSync(file, 'utf8');
  if (!raw.startsWith('---')) return {};
  const end = raw.indexOf('\n---', 3);
  if (end === -1) return {};
  const block = raw.slice(3, end).trim();
  const out: Record<string, string> = {};
  for (const line of block.split('\n')) {
    const m = line.match(/^([\w-]+):\s*(.*)$/);
    if (!m) continue;
    let v = m[2].trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    out[m[1]] = v;
  }
  return out;
}

export function getAllPosts(): Post[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  const files = fs
    .readdirSync(BLOG_DIR)
    .filter((f) => f.endsWith('.mdx'));
  return files
    .map((f) => {
      const slug = f.replace(/\.mdx?$/, '');
      const fm = readFrontmatter(path.join(BLOG_DIR, f));
      return {
        slug,
        title: fm.title ?? slug,
        date: fm.date ?? '',
        excerpt: fm.excerpt,
      };
    })
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}

export function getPostBySlug(slug: string): Post | null {
  const file = path.join(BLOG_DIR, `${slug}.mdx`);
  if (!fs.existsSync(file)) return null;
  const fm = readFrontmatter(file);
  return {
    slug,
    title: fm.title ?? slug,
    date: fm.date ?? '',
    excerpt: fm.excerpt,
  };
}
