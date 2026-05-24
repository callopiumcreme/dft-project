'use client';

import { useEffect } from 'react';

interface Props {
  name: string;
  data?: Record<string, unknown>;
}

export function UmamiViewEvent({ name, data }: Props) {
  useEffect(() => {
    const payload = data ?? {};
    const fire = () => window.umami?.track(name, payload);
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
    const to = window.setTimeout(() => window.clearInterval(t), 10000);
    return () => {
      window.clearInterval(t);
      window.clearTimeout(to);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name, JSON.stringify(data)]);

  return null;
}
