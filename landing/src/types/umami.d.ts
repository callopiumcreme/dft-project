export {};

declare global {
  interface Window {
    /** Loaded by analytics.xbitagency.com/script.js */
    umami?: {
      track: (name: string, data?: Record<string, unknown>) => void;
      identify: (userId: string, attrs?: Record<string, unknown>) => void;
    };
    /** Helper installed by UmamiTracker (root layout). */
    trackEvent?: (name: string, data?: Record<string, unknown>) => void;
    /** Helper installed by UmamiTracker (root layout). */
    identifyUser?: (userId: string, attrs?: Record<string, unknown>) => void;
    /** Per-login random UUID, written by UmamiIdentify. */
    __umamiSessionId?: string;
  }
}
