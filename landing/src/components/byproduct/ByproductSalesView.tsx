'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
  deleteBuyer,
  deleteSale,
  SELLABLE_KIND_LABELS,
  type ByproductBuyer,
  type ByproductSale,
  type SellableKind,
} from '@/lib/byproduct-client';
import { SaleForm } from './SaleForm';

interface Props {
  initialSales: ByproductSale[];
  initialBuyers: ByproductBuyer[];
  isAdmin: boolean;
  defaultProductKind?: SellableKind;
}

const kgFmt = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const eurFmt = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const dateFmt = new Intl.DateTimeFormat('it-IT', { dateStyle: 'medium' });
const dateTimeFmt = new Intl.DateTimeFormat('it-IT', {
  dateStyle: 'short',
  timeStyle: 'short',
});

function fmtKg(v: string | null | undefined): string {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return kgFmt.format(n);
}

function fmtEur(v: string | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (!Number.isFinite(n)) return '—';
  return eurFmt.format(n);
}

function fmtDate(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateFmt.format(d);
}

function fmtDateTime(v: string | null | undefined): string {
  if (!v) return '—';
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) return v;
  return dateTimeFmt.format(d);
}

export function ByproductSalesView({
  initialSales,
  initialBuyers,
  isAdmin,
  defaultProductKind,
}: Props) {
  const router = useRouter();
  const [sales, setSales] = React.useState<ByproductSale[]>(initialSales);
  const [buyers, setBuyers] = React.useState<ByproductBuyer[]>(initialBuyers);
  const [openNewSale, setOpenNewSale] = React.useState(false);
  const [pendingSaleDelete, setPendingSaleDelete] = React.useState<number | null>(null);
  const [pendingBuyerDelete, setPendingBuyerDelete] = React.useState<number | null>(null);
  const [showBuyers, setShowBuyers] = React.useState(false);

  // Keep state in sync if parent server-re-renders (filter changes).
  React.useEffect(() => {
    setSales(initialSales);
  }, [initialSales]);
  React.useEffect(() => {
    setBuyers(initialBuyers);
  }, [initialBuyers]);

  const handleSaleCreated = () => {
    // Server holds the source of truth — refresh the route so the new sale
    // shows up with the canonical buyer_name JOIN + ordering.
    router.refresh();
  };

  const onDeleteSale = async (id: number) => {
    setPendingSaleDelete(id);
    try {
      await deleteSale(id);
      toast.success('Sale deleted (soft) — ledger reversal posted');
      setSales((rows) => rows.filter((r) => r.id !== id));
      router.refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to delete sale';
      toast.error(msg);
    } finally {
      setPendingSaleDelete(null);
    }
  };

  const onDeleteBuyer = async (id: number) => {
    setPendingBuyerDelete(id);
    try {
      await deleteBuyer(id);
      toast.success('Buyer deleted (soft)');
      setBuyers((rows) => rows.filter((r) => r.id !== id));
      router.refresh();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to delete buyer';
      toast.error(msg);
    } finally {
      setPendingBuyerDelete(null);
    }
  };

  const confirmDeleteSale = (sale: ByproductSale) => {
    const label = `${SELLABLE_KIND_LABELS[sale.product_kind]} · ${fmtKg(sale.kg_net)} kg · ${fmtDate(sale.sale_date)}`;
    if (window.confirm(`Soft-delete this sale?\n\n${label}\n\nA correction row will be posted to the ledger.`)) {
      void onDeleteSale(sale.id);
    }
  };

  const confirmDeleteBuyer = (buyer: ByproductBuyer) => {
    if (window.confirm(`Soft-delete buyer "${buyer.name}"?\n\nExisting sales referencing this buyer remain intact.`)) {
      void onDeleteBuyer(buyer.id);
    }
  };

  const totalKg = sales.reduce((s, r) => s + (Number(r.kg_net) || 0), 0);
  const totalEur = sales.reduce(
    (s, r) => s + (r.price_eur ? Number(r.price_eur) || 0 : 0),
    0,
  );

  return (
    <>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-[0.78rem] text-ink-soft">
          {sales.length} sales · {kgFmt.format(totalKg)} kg · € {eurFmt.format(totalEur)}
        </p>
        <button
          type="button"
          onClick={() => setOpenNewSale(true)}
          className="border border-ink bg-ink px-4 py-2 font-mono text-[0.72rem] uppercase tracking-[0.14em] text-bg hover:bg-ink-soft"
        >
          + New sale
        </button>
      </div>

      <section className="mt-4 border border-rule bg-bg-soft overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[0.72rem]">
          <thead className="border-b border-rule bg-bg">
            <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
              <Th>Sale date</Th>
              <Th>Product</Th>
              <Th>Buyer</Th>
              <ThNum>kg net</ThNum>
              <Th>Invoice</Th>
              <ThNum>Price EUR</ThNum>
              <Th>Created at</Th>
              <Th className="text-right">
                <span className="sr-only">Actions</span>
              </Th>
            </tr>
          </thead>
          <tbody>
            {sales.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-center text-ink-mute">
                  No sales match the selected filter.
                </td>
              </tr>
            )}
            {sales.map((r) => {
              const deleting = pendingSaleDelete === r.id;
              return (
                <tr
                  key={r.id}
                  className="border-b border-rule/60 last:border-b-0 hover:bg-bg"
                >
                  <Td className="text-ink">{fmtDate(r.sale_date)}</Td>
                  <Td className="text-ink-soft">
                    {SELLABLE_KIND_LABELS[r.product_kind]}
                  </Td>
                  <Td className="text-ink-soft" title={`buyer_id=${r.buyer_id}`}>
                    {r.buyer_name ?? `#${r.buyer_id}`}
                  </Td>
                  <TdNum>{fmtKg(r.kg_net)}</TdNum>
                  <Td className="text-ink-soft">{r.invoice_no ?? '—'}</Td>
                  <TdNum>{fmtEur(r.price_eur)}</TdNum>
                  <Td className="text-ink-mute">{fmtDateTime(r.created_at)}</Td>
                  <Td className="text-right">
                    <button
                      type="button"
                      onClick={() => confirmDeleteSale(r)}
                      disabled={deleting}
                      className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                      aria-label={`Delete sale ${r.id}`}
                    >
                      {deleting ? 'Deleting…' : 'Delete'}
                    </button>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="mt-8 border border-rule bg-bg-soft">
        <button
          type="button"
          onClick={() => setShowBuyers((v) => !v)}
          className="flex w-full items-center justify-between border-b border-rule px-4 py-3 text-left font-mono text-[0.72rem] uppercase tracking-[0.14em] text-ink hover:bg-bg"
          aria-expanded={showBuyers}
        >
          <span>Manage buyers · {buyers.length}</span>
          <span aria-hidden="true">{showBuyers ? '−' : '+'}</span>
        </button>

        {showBuyers && (
          <div className="p-5 space-y-6">
            <div>
              <h3 className="mb-2 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
                Existing buyers
              </h3>
              <div className="overflow-x-auto border border-rule bg-bg">
                <table className="w-full border-collapse font-mono text-[0.72rem]">
                  <thead className="border-b border-rule">
                    <tr className="text-left uppercase tracking-[0.12em] text-ink-mute">
                      <Th>Name</Th>
                      <Th>Country</Th>
                      <Th>VAT</Th>
                      <Th>Contact</Th>
                      <Th className="text-right">
                        <span className="sr-only">Actions</span>
                      </Th>
                    </tr>
                  </thead>
                  <tbody>
                    {buyers.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-3 py-4 text-center text-ink-mute">
                          No buyers yet.
                        </td>
                      </tr>
                    )}
                    {buyers.map((b) => {
                      const deleting = pendingBuyerDelete === b.id;
                      return (
                        <tr
                          key={b.id}
                          className="border-b border-rule/60 last:border-b-0"
                        >
                          <Td className="text-ink">{b.name}</Td>
                          <Td className="text-ink-soft">{b.country ?? '—'}</Td>
                          <Td className="text-ink-soft">{b.vat ?? '—'}</Td>
                          <Td className="text-ink-soft">{b.contact ?? '—'}</Td>
                          <Td className="text-right">
                            {isAdmin ? (
                              <button
                                type="button"
                                onClick={() => confirmDeleteBuyer(b)}
                                disabled={deleting}
                                className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-accent hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                                aria-label={`Delete buyer ${b.name}`}
                              >
                                {deleting ? 'Deleting…' : 'Delete'}
                              </button>
                            ) : (
                              <span className="text-ink-mute">—</span>
                            )}
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <p className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-ink-mute">
              To create a new buyer, go to{' '}
              <a href="/app/buyers/new" className="text-ink underline hover:text-olive-deep">
                Master data → Buyers
              </a>
              .
            </p>
          </div>
        )}
      </section>

      <SaleForm
        open={openNewSale}
        onOpenChange={setOpenNewSale}
        initialBuyers={buyers}
        defaultProductKind={defaultProductKind}
        onCreated={handleSaleCreated}
      />
    </>
  );
}

function Th({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
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
function TdNum({
  className = '',
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return <td className={`px-3 py-2 text-right tabular-nums ${className}`}>{children}</td>;
}
