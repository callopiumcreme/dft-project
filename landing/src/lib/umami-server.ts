import 'server-only';
import { cookies } from 'next/headers';

const PENDING_UMAMI_COOKIE = '__umami_pending';

/**
 * Queue a Umami event to fire on the next client page load.
 *
 * Server actions and route handlers cannot call `window.umami.track` directly
 * (no DOM). Instead they drop a short-lived, non-httpOnly cookie that the
 * client-side `<UmamiPendingEvent>` (mounted in the root layout) reads and
 * fires exactly once on the next mount — typically the page reached after the
 * action's `redirect()`. This is how we attribute server-side mutations
 * (create / update / delete / sign / refresh) to the identified user session.
 *
 * Only ONE event can be pending at a time; a second call before the client
 * consumes the first overwrites it. That is fine for our flow: every mutation
 * redirects, and each redirect's page load consumes the cookie.
 *
 * Keep `data` small and free of PII — it is sent to the external analytics
 * service. The backend `audit_log` remains the system of record.
 */
export function setPendingUmamiEvent(
  name: string,
  data: Record<string, unknown> = {},
): void {
  cookies().set(PENDING_UMAMI_COOKIE, JSON.stringify({ name, data }), {
    httpOnly: false, // client must read it
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60, // short-lived; consumed on next page load
  });
}
