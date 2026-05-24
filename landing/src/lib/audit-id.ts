import 'server-only';
import { createHash } from 'crypto';

/**
 * Deterministic short hash of an email for use as Umami `user_id`.
 *
 * Email is lowercased + trimmed + salted with project tenant, SHA-256,
 * truncated to 16 hex chars (64 bit). Collision probability negligible
 * for project user count (<1000). Backend `audit_log` keeps plaintext
 * email; this is only the value sent to the external analytics service.
 *
 * Pure + sync — call from server components or server actions only
 * (uses node:crypto).
 */
export function auditUserId(email: string): string {
  return createHash('sha256')
    .update(email.toLowerCase().trim() + ':oistebio')
    .digest('hex')
    .slice(0, 16);
}
