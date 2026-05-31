import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import type { ProductPurchaseDetail } from '@/lib/product-purchase-client';
import { ProductPurchaseLink } from '@/components/product-purchases/product-purchase-link';
import { ProductPurchaseModalProvider } from '@/components/product-purchases/product-purchase-modal-provider';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';

type Supplier = components['schemas']['SupplierRead'];

export const dynamic = 'force-dynamic';

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 });
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
  };
}

export default async function ProductPurchasesPage({ searchParams }: PageProps) {
  const supplierId = sanitizeSupplierId(searchParams.supplier_id);
  const showAll = searchParams.active === 'all';

  let rows: ProductPurchaseDetail[] = [];
  let suppliers: Supplier[] = [];
  let fetchError: string | null = null;

  try {
    const [ppRes, suppliersRes] = await Promise.all([
      apiGet<ProductPurchaseDetail[]>('/product-purchases', {
        query: {
          ...(supplierId ? { supplier_id: supplierId } : {}),
          ...(showAll ? { include_deleted: true } : {}),
        },
      }),
      apiGet<Supplier[]>('/suppliers', { query: { active_only: false } }),
    ]);
    rows = ppRes;
    suppliers = suppliersRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const supplierMap = new Map(suppliers.map((s) => [s.id, s]));
  const totalKg = rows.reduce((s, r) => s + (Number(r.quantity_kg) || 0), 0);

  return (
    <ProductPurchaseModalProvider>
      <div className="mx-auto max-w-editorial">
        <UmamiViewEvent
          name="view_product_purchases_list"
          data={{
            ...(supplierId ? { supplier_id: supplierId } : {}),
            ...(showAll ? { include_deleted: true } : {}),
          }}
        />
        <header className="border-b border-rule pb-6">
          <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
            Operations
          </p>
          <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
            Product purchases
          </h1>
          <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
            {rows.length} supplier PoS
            {showAll ? ' · deleted included' : ' · active only'}
            {supplierId
              ? ` · supplier_id = ${supplierId}${
                  supplierMap.has(supplierId) ? ` (${supplierMap.get(supplierId)!.code})` : ''
                }`
              : ''}
          </p>
        </header>

        <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
          <nav className="flex gap-1 font-mono text-[0.7rem] uppercase tracking-[0.14em]">
            <a
              href={`/app/product-purchases${supplierId ? `?supplier_id=${supplierId}` : ''}`}
              className={
                !showAll
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              Active
            </a>
            <a
              href={`/app/product-purchases?active=all${supplierId ? `&supplier_id=${supplierId}` : ''}`}
              className={
                showAll
                  ? 'border border-ink bg-ink px-3 py-1.5 text-bg'
                  : 'border border-rule px-3 py-1.5 text-ink-soft hover:border-ink hover:text-ink'
              }
            >
              All
            </a>
          </nav>
          <form
            method="GET"
            action="/app/product-purchases"
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
              href="/app/product-purchases"
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

        <section className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <KpiTile label="PoS documents" value={String(rows.length)} />
          <KpiTile label="Total quantity" value={`${numFmt.format(totalKg)} kg`} />
        </section>

        <section className="mt-6 border border-rule bg-bg-soft overflow-x-auto">
          <table className="w-full border-collapse font-mono text-[0.72rem]">
            <thead className="border-b border-rule bg-bg">
              <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                <Th>PoS number</Th>
                <Th>Supplier</Th>
                <Th>Issued</Th>
                <Th>Dispatch</Th>
                <ThNum>Quantity kg</ThNum>
                <Th>Feedstock</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !fetchError && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-ink-mute">
                    No product purchases match the selected filter.
                  </td>
                </tr>
              )}
              {rows.map((r) => {
                const sup = r.supplier_id ? supplierMap.get(r.supplier_id) : undefined;
                const supplierLabel = r.supplier_name
                  ? r.supplier_name
                  : sup
                    ? `${sup.code} · ${sup.name}`
                    : '—';
                const deleted = !!r.deleted_at;
                return (
                  <tr
                    key={r.id}
                    className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                  >
                    <Td className="text-ink">
                      <ProductPurchaseLink ppId={r.id} posNumber={r.pos_number} />
                    </Td>
                    <Td className="text-ink-soft">{supplierLabel}</Td>
                    <Td className="text-ink-soft">{fmtDate(r.issuance_date)}</Td>
                    <Td className="text-ink-soft" title={r.dispatch_label ?? undefined}>
                      {r.dispatch_label ?? '—'}
                    </Td>
                    <TdNum>{fmtKg(r.quantity_kg)}</TdNum>
                    <Td className="text-ink-soft">{r.feedstock ?? '—'}</Td>
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
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      </div>
    </ProductPurchaseModalProvider>
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
