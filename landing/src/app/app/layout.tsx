import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { apiGet, ApiError, SESSION_COOKIE } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import { AppShell } from './_components/app-shell';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const token = cookies().get(SESSION_COOKIE)?.value;
  if (!token) redirect('/login');

  let user: UserRead;
  try {
    user = await apiGet<UserRead>('/auth/me');
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      redirect('/login');
    }
    throw e;
  }

  return (
    <AppShell user={{ email: user.email, role: user.role, full_name: user.full_name }}>
      {children}
    </AppShell>
  );
}
