// Map: lowercase email → custom landing path under /app.
// Visited on /app dashboard root; explicit deep-links (e.g. /app/logistics) are
// not affected so bookmarks keep working.
export const WELCOME_ROUTING: Record<string, string> = {
  'rtfo-compliance@dft.gov.uk': '/app/welcome',
};

export function welcomePathFor(email: string | null | undefined): string | null {
  if (!email) return null;
  return WELCOME_ROUTING[email.trim().toLowerCase()] ?? null;
}
