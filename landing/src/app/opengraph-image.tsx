import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'DFT — Mass balance & traceability for pyrolysis plants';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          background: '#F4EFE3',
          color: '#1B1A14',
          display: 'flex',
          flexDirection: 'column',
          padding: 72,
          fontFamily: 'Georgia, serif',
          position: 'relative',
        }}
      >
        {/* Header rule */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 18,
            letterSpacing: 4,
            color: '#7A7363',
            textTransform: 'uppercase',
            marginBottom: 48,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 14,
                height: 14,
                background: '#B23A1F',
                transform: 'rotate(45deg)',
              }}
            />
            <span style={{ fontFamily: 'system-ui', fontWeight: 600, color: '#1B1A14' }}>
              DFT
            </span>
            <span>Pyrolysis traceability</span>
          </div>
          <div>04°18′N · 74°48′W · Girardot CO</div>
        </div>

        {/* Headline */}
        <div style={{ fontSize: 92, lineHeight: 1.02, letterSpacing: -2, maxWidth: 1000, display: 'flex' }}>
          Mass balance,{' '}
          <span style={{ color: '#5C6E3C', fontStyle: 'italic', marginLeft: 16 }}>
            certifiable.
          </span>
        </div>

        <div
          style={{
            fontSize: 36,
            color: '#4A4538',
            marginTop: 32,
            maxWidth: 1000,
            lineHeight: 1.2,
            letterSpacing: -0.5,
            display: 'flex',
          }}
        >
          ISCC EU + RED II for industrial pyrolysis exporting biofuel to European refineries.
        </div>

        {/* Bottom rule */}
        <div style={{ flex: 1 }} />
        <div
          style={{
            borderTop: '1px solid #C7BFA9',
            paddingTop: 24,
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 18,
            letterSpacing: 3,
            textTransform: 'uppercase',
            color: '#7A7363',
            fontFamily: 'system-ui',
          }}
        >
          <div style={{ display: 'flex', gap: 32 }}>
            <span>· ISCC EU 205</span>
            <span>· EU 2018/2001</span>
            <span>· C14 sign-off</span>
          </div>
          <div>dft-project.com</div>
        </div>
      </div>
    ),
    size
  );
}
