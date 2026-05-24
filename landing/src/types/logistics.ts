/**
 * Hand-crafted types for the logistics downstream model.
 * Matches ConsignmentDetail shape from the /consignments API (api-builder #2).
 * Regenerate from /openapi.json when backend is reachable:
 *   cd landing && npm run gen-types
 */

export type ConsignmentStatus =
  | 'draft'
  | 'loaded'
  | 'in_transit'
  | 'at_utb'
  | 'delivered_uk'
  | 'closed';

export type LegType =
  | 'plant_to_port'
  | 'port_loading'
  | 'bl_ocean'
  | 'utb_transload'
  | 'nl_to_uk_export'
  | 'delivery_uk';

export interface OffTaker {
  id: number;
  code: string;
  name: string;
  country: string;
  address: string | null;
  notes: string | null;
}

export interface ShipmentUnit {
  id: number;
  container_ref: string | null;
  flexitank_ref: string | null;
  kg_gross: string | null;
  kg_tare: string | null;
  kg_net: string | null;
}

export interface ShipmentLeg {
  id: number;
  seq: number;
  leg_type: LegType;
  document_type: string | null;
  document_ref: string | null;
  document_date: string | null;
  carrier: string | null;
  origin_node: string;
  destination_node: string;
  kg_in: string;
  kg_out: string;
  kg_stock_residual: string | null;
  notes: string | null;
  units: ShipmentUnit[];
}

export interface ConsignmentPos {
  consignment_id: number;
  pos_number: string;
  pdf_ref: string | null;
  kg_net: string | null;
  /** Per-PoS outbound eRSV number (CO/{yy}/{seq:03d}). Null until allocated. */
  ersv_outbound_no: string | null;
  /** GHG values (gCO2eq/MJ for Ep/Etd/total; percent for saving). */
  ghg_ep: string | null;
  ghg_etd: string | null;
  ghg_total: string | null;
  ghg_saving_pct: string | null;
  created_at: string;
  deleted_at: string | null;
}

export interface ProductionLink {
  prod_date: string;
  kg_allocated: string;
}

export interface ConsignmentSummary {
  id: number;
  code: string;
  off_taker_id: number;
  off_taker: OffTaker | null;
  product_grade: string;
  prod_date_from: string;
  prod_date_to: string;
  total_kg: string;
  ersv_outbound_no: string | null;
  port_rsv_no: string | null;
  status: ConsignmentStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  /** Chain-derived KPIs (computed backend from leg rows). */
  kg_residual_utb: string | null;
  kg_delivered_uk: string | null;
}

export interface ConsignmentDetail extends ConsignmentSummary {
  legs: ShipmentLeg[];
  pos: ConsignmentPos[];
  production_links: ProductionLink[];
}
