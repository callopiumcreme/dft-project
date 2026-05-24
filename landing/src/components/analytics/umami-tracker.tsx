'use client';

import { useEffect } from 'react';

const FILE_RE =
  /\.(pdf|csv|xlsx?|docx?|pptx?|zip|rar|7z|tar|gz|txt|json|xml|mp4|mp3|wav|png|jpg|jpeg|svg)(\?|$)/i;
const SENSITIVE_FIELD_RE = /password|token|secret|cvv|card/i;

export function UmamiTracker() {
  useEffect(() => {
    let cancelled = false;
    let intervalId: number | undefined;

    const onClick = (e: MouseEvent) => {
      const target = e.target as Element | null;
      const a = target?.closest?.('a[href]') as HTMLAnchorElement | null;
      if (!a) return;
      const href = a.href || '';
      if (FILE_RE.test(href)) {
        window.umami?.track('download', {
          file: href.split('/').pop()?.split('?')[0] ?? '',
          url: href,
          ext: (href.match(/\.([a-z0-9]+)(\?|$)/i) || [])[1] || '',
        });
      }
      try {
        const url = new URL(href, location.href);
        if (url.host && url.host !== location.host) {
          window.umami?.track('outbound', { url: href, host: url.host });
        }
      } catch {
        /* ignore */
      }
    };

    const onSubmit = (e: SubmitEvent) => {
      const form = e.target as HTMLFormElement | null;
      if (!form || form.tagName !== 'FORM') return;
      const data: Record<string, string> = {};
      try {
        new FormData(form).forEach((v, k) => {
          if (SENSITIVE_FIELD_RE.test(k)) return;
          data[k] = String(v).slice(0, 200);
        });
      } catch {
        /* ignore */
      }
      window.umami?.track('form_submit', {
        form_id: form.id || '',
        form_name: form.name || '',
        action: form.action || location.pathname,
        fields: data,
      });
    };

    const install = () => {
      if (cancelled) return;
      document.addEventListener('click', onClick, true);
      document.addEventListener('submit', onSubmit, true);
      window.trackEvent = (name, data) => window.umami?.track(name, data ?? {});
      window.identifyUser = (userId, attrs) => window.umami?.identify(userId, attrs ?? {});
    };

    if (window.umami) {
      install();
    } else {
      intervalId = window.setInterval(() => {
        if (window.umami) {
          window.clearInterval(intervalId);
          install();
        }
      }, 100);
      window.setTimeout(() => {
        if (intervalId) window.clearInterval(intervalId);
      }, 10000);
    }

    return () => {
      cancelled = true;
      if (intervalId) window.clearInterval(intervalId);
      document.removeEventListener('click', onClick, true);
      document.removeEventListener('submit', onSubmit, true);
    };
  }, []);

  return null;
}
