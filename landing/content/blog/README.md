# Blog content

Drop `.mdx` files into `content/blog/`. Frontmatter is parsed with a minimal
inline reader (no `gray-matter` dependency). Format:

```mdx
---
title: "Closing the mass balance: lessons from year-end 2024"
date: "2026-04-12"
excerpt: "How a 0.5% tolerance survives 8M kg of throughput."
---

Your MDX content here…
```

Files are sorted by `date` descending and exposed at `/blog/[slug]`.
