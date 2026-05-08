'use client';

import { useTransition } from 'react';
import { logoutAction } from '@/lib/auth';
import { Button } from '@/components/ui/button';

export function LogoutButton() {
  const [pending, startTransition] = useTransition();
  return (
    <form action={() => startTransition(() => logoutAction())}>
      <Button type="submit" variant="secondary" size="sm" disabled={pending}>
        {pending ? 'Esco…' : 'Logout'}
      </Button>
    </form>
  );
}
