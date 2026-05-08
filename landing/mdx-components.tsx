import type { MDXComponents } from 'mdx/types';

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: ({ children }) => (
      <h1 className="font-display text-4xl md:text-5xl font-light tracking-editorial leading-[1.05] mt-16 mb-6 text-balance">
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 className="font-display text-3xl md:text-4xl font-light tracking-editorial leading-[1.1] mt-14 mb-5 text-balance">
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 className="font-display text-2xl font-light tracking-editorial leading-snug mt-10 mb-3">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="text-lg text-ink-soft leading-relaxed mb-5 max-w-reading text-pretty">
        {children}
      </p>
    ),
    a: ({ children, href }) => (
      <a
        href={href}
        className="text-olive underline underline-offset-4 decoration-rule hover:decoration-olive transition-colors"
      >
        {children}
      </a>
    ),
    ul: ({ children }) => (
      <ul className="list-none mb-6 max-w-reading space-y-2 text-ink-soft">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal pl-6 mb-6 max-w-reading space-y-2 text-ink-soft marker:text-ink-mute marker:font-mono">
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li className="leading-relaxed pl-3 relative before:content-['›'] before:absolute before:left-0 before:text-olive">
        {children}
      </li>
    ),
    blockquote: ({ children }) => (
      <blockquote className="border-l border-olive pl-6 my-8 font-display italic font-light text-xl text-ink leading-relaxed">
        {children}
      </blockquote>
    ),
    code: ({ children }) => (
      <code className="font-mono text-[0.85em] bg-bg-soft px-1.5 py-0.5 rounded-sm text-accent border border-rule">
        {children}
      </code>
    ),
    pre: ({ children }) => (
      <pre className="font-mono text-sm bg-bg-deep text-bg p-6 my-6 overflow-x-auto border border-rule rounded-sm">
        {children}
      </pre>
    ),
    hr: () => <hr className="rule my-12" />,
    ...components,
  };
}
