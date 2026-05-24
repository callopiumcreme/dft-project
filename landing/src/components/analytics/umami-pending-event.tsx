'use client';

import { useEffect } from 'react';

const COOKIE_NAME = '__umami_pending';

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[1]) : null;
}

function deleteCookie(name: string): void {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax`;
}

export function UmamiPendingEvent() {
  useEffect(() => {
    const raw = readCookie(COOKIE_NAME);
    if (!raw) return;
    let parsed: { name?: string; data?: Record<string, unknown> } = {};
    try {
      parsed = JSON.parse(raw);
    } catch {
      deleteCookie(COOKIE_NAME);
      return;
    }
    if (!parsed.name || typeof parsed.name !== 'string') {
      deleteCookie(COOKIE_NAME);
      return;
    }
    const eventName = parsed.name;
    const eventData = parsed.data ?? {};
    const fire = () => {
      window.umami?.track(eventName, eventData);
      deleteCookie(COOKIE_NAME);
    };
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
    const to = window.setTimeout(() => {
      window.clearInterval(t);
      // Cookie remains for next mount; do not delete on timeout.
    }, 10000);
    return () => {
      window.clearInterval(t);
      window.clearTimeout(to);
    };
  }, []);

  return null;
}
