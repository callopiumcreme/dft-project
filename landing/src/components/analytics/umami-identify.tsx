'use client';

import { useEffect } from 'react';

interface Props {
  /** Hash of email — never plain PII. */
  userId: string;
  role: string;
}

function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem('__umami_session_id');
    if (existing) return existing;
    const fresh =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem('__umami_session_id', fresh);
    return fresh;
  } catch {
    // sessionStorage may be unavailable (privacy mode) — fall back to per-mount UUID
    return Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
}

export function UmamiIdentify({ userId, role }: Props) {
  useEffect(() => {
    const sessionId = getOrCreateSessionId();
    window.__umamiSessionId = sessionId;

    const fire = () =>
      window.umami?.identify(userId, {
        role,
        tenant: 'oistebio',
        session_id: sessionId,
      });

    if (window.umami) {
      fire();
      return;
    }
    const t = window.setInterval(() => {
      if (window.umami) {
        window.clearInterval(t);
        fire();
      }
    }, 100);
    const timeout = window.setTimeout(() => window.clearInterval(t), 10000);
    return () => {
      window.clearInterval(t);
      window.clearTimeout(timeout);
    };
  }, [userId, role]);

  return null;
}
