import 'server-only';
import { apiGet } from '@/lib/api';

export type ProductKind =
  | 'eu_oil'
  | 'plus_oil'
  | 'carbon_black'
  | 'metal_scrap'
  | 'syngas'
  | 'h2o';

export interface WarehouseStockRow {
  product_kind: ProductKind;
  stock_kg: string;
  produced_total_kg: string;
  dispatched_total_kg: string;
  reserved_kg: string;
  last_movement_at: string | null;
}

export interface WarehouseMovement {
  id: number;
  event_date: string;
  event_type: string;
  product_kind: ProductKind;
  kg_in: string;
  kg_out: string;
  post_balance_kg: string | null;
  ref_doc_no: string | null;
  consignment_id: number | null;
  notes: string | null;
}

export interface WarehouseMovementsOpts {
  limit?: number;
  product_kind?: ProductKind;
  event_type?: string;
}

export function getWarehouseStock(): Promise<WarehouseStockRow[]> {
  return apiGet<WarehouseStockRow[]>('/warehouse/stock');
}

export function getWarehouseMovements(
  opts: WarehouseMovementsOpts = {},
): Promise<WarehouseMovement[]> {
  return apiGet<WarehouseMovement[]>('/warehouse/movements', {
    query: {
      limit: opts.limit ?? undefined,
      product_kind: opts.product_kind ?? undefined,
      event_type: opts.event_type ?? undefined,
    },
  });
}
