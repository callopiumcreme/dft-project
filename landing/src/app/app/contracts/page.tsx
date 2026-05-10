import Link from 'next/link';
import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';

type Contract = components['schemas']['ContractRead'];
type Supplier = components['schemas']['SupplierRead'];
type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 });
const dateFmt = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium' });

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
  searchParams: {
    supplier_id?: string;
    active?: string;
    created?: string;
    deleted?: string;
    error?: string;
  };
}

export default async function ContractsPage({ searchParams }: PageProps) {
  const supplierId = sanitizeSupplierId(searchParams.supplier_id);
  const showAll = searchParams.active === 'all';
  const showCreated = searchParams.created === '1';
  const showDeleted = searchParams.deleted === '1';
  const showError = searchParams.error;

  let rows: Contract[] = [];
  let suppliers: Supplier[] = [];
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    const [contractsRes, suppliersRes, meRes] = await Promise.all([
      apiGet<Contract[]>('/contracts', {
        query: {
          ...(supplierId ? { supplier_id: supplierId } : {}),
          ...(showAll ? { include_deleted: true } : {}),
        },
      }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
      apiGet<UserRead>('/auth/me'),
    ]);
    rows = contractsRes;
    suppliers = suppliersRes;
    me = meRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const isAdmin = me?.role === 'admin';
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
          Master data
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <h1 className="font-display text-4xl tracking-editorial text-ink">Contracts</h1>
          {isAdmin && (
            <Link
              href="/app/contracts/new"
              className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
            >
              + New contract
            </Link>
          )}
        </div>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          {rows.length} contracts
          {showAll ? ' · deleted included' : ' · active only'}
          {supplierId
            ? ` · supplier_id = ${supplierId}${
                supplierMap.has(supplierId) ? ` (${supplierMap.get(supplierId)!.code})` : ''
              }`
            : ''}
        </p>
      </header>

      {showCreated && <Banner kind="ok">Contract created</Banner>}
      {showDeleted && <Banner kind="ok">Contract deleted (soft)</Banner>}
      {showError && <Banner kind="err">{showError}</Banner>}

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <nav className="flex gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
          <Link
            href={`/app/contracts${supplierId ? `?supplier_id=${supplierId}` : ''}`}
            className={
              !showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            Active
          </Link>
          <Link
            href={`/app/contracts?active=all${supplierId ? `&supplier_id=${supplierId}` : ''}`}
            className={
              showAll
                ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
            }
          >
            All
          </Link>
        </nav>
        <form
          method="GET"
          action="/app/contracts"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          {showAll && <input type="hidden" name="active" value="all" />}
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Supplier</span>
            <select
              name="supplier_id"
              defaultValue={supplierId ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— all —</option>
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
            Filter
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
          Loading error: {fetchError}
        </div>
      )}

      <section className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiTile label="Contracts" value={String(rows.length)} />
        <KpiTile label="Placeholder" value={String(placeholders)} />
        <KpiTile label="Total volume" value={`${numFmt.format(totalCommitted)} kg`} />
      </section>

      <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Code</Th>
              <Th>Supplier</Th>
              <Th>Start</Th>
              <Th>End</Th>
              <ThNum>Volume kg</ThNum>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th className="text-right">
                <span className="sr-only">Open</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !fetchError && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-ink-mute">
                  No contracts match the selected filter.
                </td>
              </tr>
            )}
            {rows.map((r) => {
              const sup = r.supplier_id ? supplierMap.get(r.supplier_id) : undefined;
              const deleted = !!r.deleted_at;
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
                      {r.is_placeholder ? 'placeholder' : 'real'}
                    </span>
                  </Td>
                  <Td>
                    {deleted ? (
                      <span className="inline-block border border-accent bg-accent/5 px-2 py-0.5 text-[0.65rem] uppercase text-accent">
                        deleted
                      </span>
                    ) : (
                      <span className="inline-block border border-olive-deep bg-olive-deep/10 px-2 py-0.5 text-[0.65rem] uppercase text-olive-deep">
                        active
                      </span>
                    )}
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/app/contracts/${r.id}`}
                      className="text-ink-soft hover:text-ink"
                      aria-label={`Open contract ${r.code}`}
                    >
                      →
                    </Link>
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

function Banner({ kind, children }: { kind: 'ok' | 'err'; children: React.ReactNode }) {
  const cls =
    kind === 'ok'
      ? 'border-olive-deep bg-olive-deep/5 text-olive-deep'
      : 'border-accent bg-accent/5 text-accent';
  return (
    <p
      role={kind === 'ok' ? 'status' : 'alert'}
      className={`mt-6 border ${cls} px-3 py-2 font-mono text-[0.7rem] uppercase tracking-[0.14em]`}
    >
      {children}
    </p>
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

function Th({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <th className={`px-3 py-2 font-normal ${className}`}>{children}</th>;
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
