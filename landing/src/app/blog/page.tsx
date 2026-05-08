import Link from 'next/link';
import { Nav } from '@/components/Nav';
import { Footer } from '@/components/Footer';
import { getAllPosts } from '@/lib/blog';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Blog',
  description:
    'Notes on mass balance, ISCC EU, RED II, pyrolysis operations and the engineering behind DFT.',
};

export default function BlogIndex() {
  const posts = getAllPosts();

  return (
    <>
      <Nav />
      <main className="pt-32 pb-24 min-h-[60vh]">
        <div className="container-edit">
          <div className="border-t border-rule pt-12 mb-16">
            <div className="eyebrow mb-4">§ — Journal</div>
            <h1 className="text-balance text-[clamp(2.4rem,6vw,4.6rem)] font-light leading-[1.04]">
              Notes from the{' '}
              <em className="not-italic text-olive">audit floor</em>.
            </h1>
            <p className="mt-6 max-w-reading text-pretty text-ink-soft text-lg leading-relaxed">
              Engineering write-ups, regulatory dispatches, and field notes
              from pyrolysis operations.
            </p>
          </div>

          {posts.length === 0 ? (
            <div className="border-t border-rule pt-10 text-ink-mute font-mono text-sm">
              No posts yet.
            </div>
          ) : (
            <ul className="border-t border-rule">
              {posts.map((p) => (
                <li
                  key={p.slug}
                  className="border-b border-rule py-8 grid grid-cols-12 gap-4 md:gap-8 items-baseline"
                >
                  <div className="col-span-3 md:col-span-2 eyebrow">
                    {p.date}
                  </div>
                  <div className="col-span-9 md:col-span-10">
                    <Link
                      href={`/blog/${p.slug}`}
                      className="font-display text-2xl md:text-3xl font-light tracking-editorial hover:text-olive transition-colors"
                    >
                      {p.title}
                    </Link>
                    {p.excerpt && (
                      <p className="mt-3 max-w-reading text-ink-soft text-pretty">
                        {p.excerpt}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}
