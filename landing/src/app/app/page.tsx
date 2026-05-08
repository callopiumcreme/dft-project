import { Card } from '@/components/ui/card';

export const dynamic = 'force-dynamic';

export default function AppHomePage() {
  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Panoramica
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Dashboard</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          KPI mass balance ultimi 30 giorni — popolamento dati arriva con S3-6.
        </p>
      </header>

      <section className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {['Input totale', 'Output totale', 'Closure media', 'Alert giorni'].map((label) => (
          <Card key={label} className="p-5">
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">
              {label}
            </p>
            <p className="mt-3 font-display text-3xl tracking-editorial text-ink">—</p>
            <p className="mt-2 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-mute">
              In attesa S3-6
            </p>
          </Card>
        ))}
      </section>
    </div>
  );
}
