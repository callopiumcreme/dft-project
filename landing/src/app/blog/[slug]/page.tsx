import { notFound } from 'next/navigation';
import Link from 'next/link';
import { Nav } from '@/components/Nav';
import { Footer } from '@/components/Footer';
import { getAllPosts, getPostBySlug } from '@/lib/blog';
import type { Metadata } from 'next';

export function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const post = getPostBySlug(params.slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
  };
}

export default async function BlogPost({
  params,
}: {
  params: { slug: string };
}) {
  const post = getPostBySlug(params.slug);
  if (!post) notFound();

  const { default: MDXContent } = await import(
    `../../../../content/blog/${params.slug}.mdx`
  );

  return (
    <>
      <Nav />
      <main className="pt-32 pb-24">
        <article className="container-edit">
          <div className="border-t border-rule pt-12 max-w-3xl">
            <div className="eyebrow mb-6">{post.date}</div>
            <h1 className="text-balance text-[clamp(2.2rem,5.5vw,4rem)] font-light leading-[1.04]">
              {post.title}
            </h1>
            {post.excerpt && (
              <p className="mt-6 text-ink-soft text-lg md:text-xl text-pretty leading-relaxed">
                {post.excerpt}
              </p>
            )}
          </div>
          <div className="prose-editorial mt-16 max-w-3xl">
            <MDXContent />
          </div>
          <div className="mt-20 max-w-3xl border-t border-rule pt-6">
            <Link
              href="/blog"
              className="font-mono text-[0.78rem] uppercase tracking-[0.16em] text-ink-soft hover:text-olive"
            >
              ← Back to journal
            </Link>
          </div>
        </article>
      </main>
      <Footer />
    </>
  );
}
