import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Contract = components['schemas']['ContractRead'];
type Supplier = components['schemas']['SupplierRead'];

export const dynamic = 'force-dynamic';

const numFmt = new Intl.NumberFormat('it-IT', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium' });

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return numFmt.format(n);
}

function sanitizeSupplierId(v: string | undefined): number | undefined {
  if (!v) return undefined;
  const n = Number(v);
  return Number.isInteger(n) && n > 0 ? n : undefined;
}

interface PageProps {
  searchParams: { supplier_id?: string };
}

export default async function ContractsPage({ searchParams }: PageProps) {
  const supplierId = sanitizeSupplierId(searchParams.supplier_id);

  let rows: Contract[] = [];
  let suppliers: Supplier[] = [];
  let fetchError: string | null = null;

  try {
    const [contractsRes, suppliersRes] = await Promise.all([
      apiGet<Contract[]>('/contracts', {
        query: supplierId ? { supplier_id: supplierId } : {},
      }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
    rows = contractsRes;
    suppliers = suppliersRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'errore sconosciuto';
  }

  const supplierMap = new Map(suppliers.map((s) => [s.id, s]));
  const placeholders = rows.filter((r) => r.is_placeholder).length;
  const totalCommitted = rows.reduce(
    (s, r) => s + (Number(r.total_kg_committed) || 0),
    0,
  );

  return (
    <div className="mx-auto max-w-editorial">
      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Anagrafica
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">Contratti</h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {rows.length} contratti
          {supplierId
            ? ` · supplier_id = ${supplierId}${
                supplierMap.has(supplierId) ? ` (${supplierMap.get(supplierId)!.code})` : ''
              }`
            : ''}
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-end gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/contracts"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Fornitore</span>
            <select
              name="supplier_id"
              defaultValue={supplierId ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— tutti —</option>
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} · {s.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Filtra
          </button>
          <a
            href="/app/contracts"
            className="border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink"
          >
            Reset
          </a>
        </form>
      </section>

      {fetchError && (
        <div className="mt-6 border border-rule bg-bg-soft p-4 font-mono text-[0.75rem] text-accent">
          Errore caricamento: {fetchError}
        </div>
      )}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiTile label="Contratti" value={String(rows.length)} />
        <KpiTile label="Placeholder" value={String(placeholders)} />
        <KpiTile label="Volume totale" value={`${numFmt.format(totalCommitted)} kg`} />
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Codice</Th>
              <Th>Fornitore</Th>
              <Th>Inizio</Th>
              <Th>Fine</Th>
              <ThNum>Volume kg</ThNum>
              <Th>Tipo</Th>
              <Th>Note</Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !fetchError && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-ink-mute">
                  Nessun contratto per il filtro selezionato.
                </td>
              </tr>
            )}
            {rows.map((r) => {
              const sup = r.supplier_id ? supplierMap.get(r.supplier_id) : undefined;
              return (
                <tr
                  key={r.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{r.code}</Td>
                  <Td className="text-ink-soft">
                    {sup ? `${sup.code} · ${sup.name}` : '—'}
                  </Td>
                  <Td className="text-ink-soft">{fmtDate(r.start_date)}</Td>
                  <Td className="text-ink-soft">{fmtDate(r.end_date)}</Td>
                  <TdNum>{fmtKg(r.total_kg_committed)}</TdNum>
                  <Td>
                    <span className="text-ink-soft">
                      {r.is_placeholder ? 'placeholder' : 'reale'}
                    </span>
                  </Td>
                  <Td className="text-ink-mute max-w-[20rem] truncate" title={r.notes ?? ''}>
                    {r.notes ?? '—'}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function KpiTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-rule bg-bg-soft p-4">
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-ink-mute">{label}</p>
      <p className="mt-2 font-display text-2xl tracking-editorial text-ink">{value}</p>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 font-normal">{children}</th>;
}
function ThNum({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2 text-right font-normal">{children}</th>;
}
function Td({
  className = '',
  children,
  title,
}: {
  className?: string;
  children: React.ReactNode;
  title?: string;
}) {
  return (
    <td className={`px-3 py-2 ${className}`} title={title}>
      {children}
    </td>
  );
}
function TdNum({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
