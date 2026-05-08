import type { Metadata } from 'next';
import { Fraunces, Instrument_Sans, JetBrains_Mono } from 'next/font/google';
import Script from 'next/script';
import './globals.css';

const fraunces = Fraunces({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-display',
  axes: ['opsz', 'SOFT'],
});

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-sans',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://dft-project.com';
const UMAMI_SRC = process.env.NEXT_PUBLIC_UMAMI_SRC;
const UMAMI_ID = process.env.NEXT_PUBLIC_UMAMI_ID;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: 'DFT — Mass balance & traceability for pyrolysis plants',
    template: '%s · DFT',
  },
  description:
    'ISCC EU and RED II compliant mass balance, load tracking, third-party C14 sign-off and immutable audit logs for industrial pyrolysis plants exporting biofuel to European refineries.',
  keywords: [
    'mass balance pyrolysis software',
    'ISCC compliance biofuel',
    'EU RED II tracking system',
    'pyrolysis plant management',
    'biofuel traceability',
    'C14 analysis sign-off',
  ],
  authors: [{ name: 'DFT Project' }],
  creator: 'DFT Project',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    alternateLocale: ['it_IT'],
    url: SITE_URL,
    siteName: 'DFT Project',
    title: 'DFT — Mass balance & traceability for pyrolysis plants',
    description:
      'Audit-grade mass balance, load tracking and POS document generation for ISCC EU certified biofuel export.',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'DFT — Mass balance for pyrolysis plants',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'DFT — Mass balance & traceability for pyrolysis plants',
    description: 'ISCC EU and RED II compliant traceability software.',
    images: ['/opengraph-image'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-image-preview': 'large',
    },
  },
  alternates: {
    canonical: '/',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${fraunces.variable} ${instrumentSans.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        {children}
        {UMAMI_SRC && UMAMI_ID && (
          <Script
            src={UMAMI_SRC}
            data-website-id={UMAMI_ID}
            strategy="afterInteractive"
            defer
          />
        )}
      </body>
    </html>
  );
}
