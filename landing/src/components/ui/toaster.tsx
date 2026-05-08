'use client';

import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-bg group-[.toaster]:text-ink group-[.toaster]:border group-[.toaster]:border-rule group-[.toaster]:shadow-lg',
          description: 'group-[.toast]:text-ink-mute',
          actionButton:
            'group-[.toast]:bg-ink group-[.toast]:text-bg',
          cancelButton:
            'group-[.toast]:bg-bg-soft group-[.toast]:text-ink-mute',
        },
      }}
    />
  );
}
