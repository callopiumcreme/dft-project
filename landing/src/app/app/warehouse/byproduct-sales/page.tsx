import { apiGet, ApiError } from '@/lib/api';
import type { components } from '@/lib/backend-types';
import type {
  ByproductBuyer,
  ByproductSale,
  SellableKind,
} from '@/lib/byproduct-client';
import { ByproductSalesView } from '@/components/byproduct/ByproductSalesView';
import { UmamiViewEvent } from '@/components/analytics/umami-view-event';

type UserRead = components['schemas']['UserRead'];

export const dynamic = 'force-dynamic';

const SELLABLE_KINDS: ReadonlySet<SellableKind> = new Set([
  'plus_oil',
  'carbon_black',
  'metal_scrap',
  'eu_oil',
  'dev_p200',
]);

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function sanitizeKind(v: string | undefined): SellableKind | undefined {
  if (!v) return undefined;
  return SELLABLE_KINDS.has(v as SellableKind) ? (v as SellableKind) : undefined;
}
function sanitizeId(v: string | undefined): number | undefined {
  if (!v) return undefined;
  const n = Number(v);
  return Number.isInteger(n) && n > 0 ? n : undefined;
}
function sanitizeDate(v: string | undefined): string | undefined {
  if (!v) return undefined;
  return ISO_DATE_RE.test(v) ? v : undefined;
}

interface PageProps {
  searchParams: {
    product?: string;
    buyer_id?: string;
    from_date?: string;
    to_date?: string;
  };
}

export default async function ByproductSalesPage({ searchParams }: PageProps) {
  const productKind = sanitizeKind(searchParams.product);
  const buyerId = sanitizeId(searchParams.buyer_id);
  const fromDate = sanitizeDate(searchParams.from_date);
  const toDate = sanitizeDate(searchParams.to_date);

  let sales: ByproductSale[] = [];
  let buyers: ByproductBuyer[] = [];
  let me: UserRead | null = null;
  let fetchError: string | null = null;

  try {
    const [salesRes, buyersRes, meRes] = await Promise.all([
      apiGet<ByproductSale[]>('/byproduct/sales', {
        query: {
          product_kind: productKind ?? undefined,
          buyer_id: buyerId ?? undefined,
          from_date: fromDate ?? undefined,
          to_date: toDate ?? undefined,
        },
      }),
      apiGet<ByproductBuyer[]>('/byproduct/buyers'),
      apiGet<UserRead>('/auth/me'),
    ]);
    sales = salesRes;
    buyers = buyersRes;
    me = meRes;
  } catch (e) {
    if (e instanceof ApiError) fetchError = `${e.status} · ${e.detail}`;
    else fetchError = 'unknown error';
  }

  const isAdmin = me?.role === 'admin';
  const buyerMap = new Map(buyers.map((b) => [b.id, b]));

  return (
    <div className="mx-auto max-w-editorial">
      <UmamiViewEvent
        name="view_byproduct_sales"
        data={{
          ...(productKind ? { product_kind: productKind } : {}),
          ...(buyerId ? { buyer_id: buyerId } : {}),
          ...(fromDate ? { from_date: fromDate } : {}),
          ...(toDate ? { to_date: toDate } : {}),
        }}
      />

      <header className="border-b border-rule pb-6">
        <p className="font-mono text-[0.7rem] uppercase tracking-[0.16em] text-ink-mute">
          Warehouse
        </p>
        <h1 className="mt-1 font-display text-4xl tracking-editorial text-ink">
          Sales
        </h1>
        <p className="mt-3 max-w-reading font-mono text-[0.78rem] text-ink-soft">
          Commercial invoices — DEV-P100 (Crown Oil, read-only from
          consignment workflow) + DEV-P200 + carbon black + metal scrap.
          Non-Crown sales also post a mass-balance ledger row.
        </p>
      </header>

      <section className="mt-6 flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <form
          method="GET"
          action="/app/warehouse/byproduct-sales"
          className="flex flex-wrap items-end gap-3 font-mono text-[0.7rem] uppercase tracking-[0.14em]"
        >
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Product</span>
            <select
              name="product"
              defaultValue={productKind ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— all —</option>
              <option value="eu_oil">DEV-P100 (Crown)</option>
              <option value="dev_p200">DEV-P200 (Conquer)</option>
              <option value="plus_oil">DEV-P200 (PLUS oil)</option>
              <option value="carbon_black">Carbon black</option>
              <option value="metal_scrap">Metal scrap</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">Buyer</span>
            <select
              name="buyer_id"
              defaultValue={buyerId ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            >
              <option value="">— all —</option>
              {buyers.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">From</span>
            <input
              type="date"
              name="from_date"
              defaultValue={fromDate ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-ink-mute">To</span>
            <input
              type="date"
              name="to_date"
              defaultValue={toDate ?? ''}
              className="border border-rule bg-bg-soft px-2 py-1 text-ink"
            />
          </label>
          <button
            type="submit"
            className="border border-ink bg-ink px-3 py-1.5 text-bg hover:bg-ink-soft"
          >
            Filter
          </button>
          <a
            href="/app/warehouse/byproduct-sales"
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

      {productKind && (
        <p className="mt-4 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
          Filter: product = {productKind}
          {buyerId
            ? ` · buyer = ${buyerMap.get(buyerId)?.name ?? `#${buyerId}`}`
            : ''}
        </p>
      )}

      <ByproductSalesView
        initialSales={sales}
        initialBuyers={buyers}
        isAdmin={isAdmin}
        defaultProductKind={productKind}
      />
    </div>
  );
}
