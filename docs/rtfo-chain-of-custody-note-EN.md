# Technical Note for the RTFO Administrator and the United Kingdom Department for Transport (DfT)

**Document type:** Chain-of-Custody and Traceability System Description (extended technical edition)

**Subject:** Detailed Description of the Chain-of-Custody Architecture, Documentary Substrate, Quantitative-Reconciliation Logic, and Audit-Extraction Functionality Governing the End-of-Life Tyres (ELT) Feedstock Stream, the Certified Pyrolysis-Oil Product Fractions, and the Associated Process Co-Products, as Operated Under the ISCC Certification System (ISCC EU and ISCC PLUS) in Support of Demonstrable Conformity with the Renewable Transport Fuel Obligation (RTFO)

---

## 0. Purpose, Scope, and Interpretative Framework

This technical note has been prepared for the express benefit of the RTFO Administrator and of any verifying party acting on behalf of, or under instruction from, the United Kingdom Department for Transport. Its purpose is to describe — exhaustively, sequentially, and at the level of granularity expected of an audit-grade system narrative — the complete operational architecture, the underlying documentary substrate, the data-capture and data-retention logic, the quantitative mass-and-volume reconciliation methodology, and the on-demand audit-extraction functionality of the integrated traceability and chain-of-custody system applied to the End-of-Life Tyres (hereinafter "ELT") feedstock stream and to each of its derived product and co-product fractions.

The system is operated within, and is fully subordinate to, the methodological and documentary requirements of the ISCC certification system, encompassing both the ISCC EU certification scheme (recognised for the purposes of demonstrating compliance with sustainability and greenhouse-gas-saving criteria) and the ISCC PLUS certification scheme (applied to those fractions and markets falling outside the ISCC EU regulatory perimeter). All chain-of-custody handling described herein is conducted under the **mass-balance** chain-of-custody methodology, in which sustainability characteristics are administratively assigned to, and withdrawn from, a defined accounting pool over a defined reconciliation period, without any requirement for physical segregation of certified and non-certified material, and with strict preservation of quantitative equivalence between the credited inputs and the corresponding allocated outputs.

The scope of the system extends, without interruption, across the entire physical and custodial journey of the material: from the point of origin and first reception of the ELT at the collecting point in Colombia; through inland logistics; through reception, registration, and thermochemical conversion at the OISTEBIO Girardot processing facility; through the generation, classification, and registration of all output streams; through the export documentation chain from Colombia; through the intermediate logistical transfer and optional repacking operation in the Netherlands; and finally through the closing movement and commercial delivery of the certified product to the end customer in the United Kingdom.

A central design objective of the system is **reconstructability**: at any moment, and for any selected lot, consignment, day, or accounting period, the system permits the complete reconstruction of the chain of custody from origin to final delivery, together with the on-demand extraction of every supporting document — including, but not limited to, contracts, Proofs of Sustainability (PoS), electronic and port receipts of material (eRSV / RSV), transport documents, Bills of Lading, commercial invoices, weighbridge registers, daily-intake registers, production registers, and warehouse and mass-reconciliation records. The system further supports the independent quantitative verification of: (i) the daily quantities of ELT received; (ii) the quantities produced, expressed simultaneously in units of mass (kilograms) and units of volume (litres); (iii) the conversion between mass and volume by means of density-variable conversion tables; and (iv) the biogenic-matrix value attributed to the product by accredited laboratory determination, including Carbon-14 (C14) radiocarbon analysis and correlated analytical methods.

---

## 1. Reception of the Feedstock at the Collecting Point

### 1.1 Function of the collecting-point node

The material flow originates at the **collecting point**, which constitutes the first verifiable node of the chain of custody and the boundary at which sustainability characteristics formally enter the mass-balance accounting system. At this node, the incoming ELT consignments are received, identified, weighed, recorded, and linked — individually and unambiguously — to the ISCC documentary chain, such that no quantity of material can enter the downstream accounting pool without a corresponding, retrievable, and internally consistent set of supporting records.

### 1.2 Documentary set captured at reception

Each incoming consignment of ELT is received against, and is associated with, the following minimum documentary set:

1. an **electronic eRSV** (electronic receipt of material) issued by the supplier, which constitutes the originating instrument of the chain of custody and which carries the supplier identity, the consignment reference, the declared quantity, and the relevant transport and dating particulars;
2. the **Proof of Sustainability (PoS)** associated with the specific batch or lot, establishing the sustainability characteristics and the certified status attributable to the material;
3. the **daily-intake registration**, recording the consignment within the chronological intake ledger of the collecting point; and
4. the corresponding **weighbridge evidence and logistical-traceability records**, documenting the measured quantity and the physical movement of the material.

### 1.3 Outcome of the reception step

Taken together, this documentary set permits: the unambiguous identification of the incoming material; the determination of its associated lot reference; the quantification of the delivered quantity; and the explicit, retrievable linkage of each consignment to the ISCC system. The reception step therefore both establishes the first node of the chain of custody and defines the point of entry of the sustainability characteristics into the mass-balance accounting boundary.

---

## 2. OISTEBIO Girardot — Reception, Registration, and Processing

### 2.1 Transfer and reception as certified feedstock

Following reception at the collecting point, the material is transferred to the **OISTEBIO Girardot** processing facility, where it is received as **certified feedstock** and is formally incorporated into the certified-mass management system of the facility. The act of reception at Girardot constitutes a discrete, recorded custodial event, distinct from and subsequent to the collecting-point reception, and is itself fully evidenced within the system.

### 2.2 Lot-level registration fields

Upon reception at Girardot, **each lot** is registered with the following minimum data fields:

- **date and time of arrival** of the consignment at the facility;
- **gross weight** of the laden vehicle or unit;
- **tare** weight;
- **net discharged weight**, computed as the difference between gross and tare and representing the quantity of certified feedstock effectively entering the facility;
- the **reference of the governing transport document** under which the material moved; and
- the **reference of the linked PoS**, preserving the continuity of the sustainability characteristics from the collecting-point node into the facility's accounting pool.

### 2.3 Thermochemical conversion

The facility subjects the registered feedstock to thermochemical conversion by means of **pyrolysis**. The conversion process generates multiple distinct output streams, each of which is either certified or otherwise registered within the facility's mass-balance management system. Each output stream is allocated against the certified input pool in accordance with the applicable ISCC mass-balance methodology, such that the certified characteristics assigned to the outputs do not, in aggregate and over the reconciliation period, exceed the certified characteristics credited to the inputs.

---

## 3. Process Outputs and Stream Classification

### 3.1 Enumerated output streams

The production process yields the following enumerated streams:

1. a **certified EU light fraction**, designated internally as **DEV-P100**, which represents approximately **30% of the total oil output** and constitutes the principal certified product fraction directed to the regulated end market;
2. a **certified PLUS heavy fraction**, designated internally as **DEV-P200**; and
3. **further co-products and process streams**, comprising in particular **carbon black**, **syngas**, **process water**, and **metal scrap**.

### 3.2 Registration and reconciliation of outputs

All of the foregoing outputs are recorded in the facility management system. The purpose and effect of this comprehensive registration is to guarantee **full reconciliation between input, production yield, and aggregate output** — that is, to preserve mass continuity across the conversion boundary and to enable the quantitative closure of the mass balance at any selected accounting interval. By recording not only the certified product fractions but also the co-products and residual process streams, the system ensures that the entirety of the converted mass is accounted for, and that no output stream remains outside the reconciliation perimeter.

---

## 4. Quantitative Control, Conversions, and Biogenic-Matrix Determination

### 4.1 Verifiable quantitative dimensions

The system permits the independent verification of the following quantitative dimensions:

- the **daily volumes of ELT received** at the entry nodes;
- the **production expressed in both kilograms and litres**, enabling cross-checking between mass-based and volume-based accounting;
- the **conversion between mass and volume**, performed by means of **density-variable conversion tables** (that is, conversion factors that vary with the density of the relevant stream rather than a single fixed coefficient); and
- the **coherence between weighbridge records, production figures, and the quantities declared in the sustainability documentation**, such that any discrepancy between physically measured, internally produced, and documentarily declared quantities can be detected and investigated.

### 4.2 Biogenic-matrix value and C14 determination

The system further permits the **association, with the product, of the biogenic-matrix value** resulting from accredited laboratory analysis, including **C14 radiocarbon determinations** where applicable. This biogenic-content value substantiates the renewable/biogenic claim attaching to the product and underpins the eligibility considerations relevant to the RTFO framework, by providing an analytically grounded basis for the proportion of the product attributable to biogenic carbon.

---

## 5. Export Documentation — Colombia → Netherlands → United Kingdom

The export segment of the flow is supported by a complete, sequential documentary set, structured around three successive legs:

### 5.1 Departure from Colombia

The outbound flow from Colombia is accompanied by: the **port RSV**; the **Bill of Lading**; and the **PoS associated with the exported consignment**. These instruments jointly evidence the quantity, the certified status, and the maritime carriage particulars of the material leaving the country of origin.

### 5.2 Logistical transfer in the Netherlands

Upon arrival in the Netherlands, the consignment undergoes a **stop-and-go** logistical operation at **UTB BV, Dordrecht**, which may include an **ISO-to-ISO repacking** (transfer between ISO-tank units) while **maintaining the continuity of the chain of custody**. The intermediate node is documented such that the custodial linkage between the inbound and outbound legs is preserved without interruption.

### 5.3 Final movement to the United Kingdom

The closing leg towards the United Kingdom is supported by: the **Bill of Lading from the Netherlands to the United Kingdom**; and the **commercial invoice to Crown Oil Ltd**; together with the batch-level and product-level supporting documentation for the certified product. These instruments evidence the final carriage and the commercial delivery of the certified product to the end customer.

---

## 6. Audit and Traceability Functionality

### 6.1 End-to-end reconstruction

The system enables the **end-to-end reconstruction** of the entire chain of custody, from the first reception of the feedstock to the final delivery of the certified product, by linking each custodial node to its supporting records and to the adjacent nodes.

### 6.2 On-demand document extraction

Upon request, the system permits the extraction of all documents material to audit or verification, including: **contracts; PoS; eRSV / RSV; Bills of Lading; commercial invoices; weighbridge registers; production registers; and warehouse and mass-reconciliation records.**

### 6.3 Verifiable coherence

This functionality permits verification, at any point in time, of the **coherence between**: the incoming material; the processed quantity; the produced quantity; the EU-certified and PLUS-certified streams; the co-products; the export shipments; and the final delivery to the UK customer — thereby allowing a verifying party to test the internal consistency of the entire flow against the documentary evidence at each node.

---

## 7. Conclusion

The system is structured to guarantee **complete and verifiable traceability** of the entire ELT flow — from collection, through thermochemical transformation, through the intermediate logistical transfer in the Netherlands, and to final delivery in the United Kingdom. The combination of electronic documents, PoS, weighbridge records, densimetric conversions, process registers, and accredited laboratory analyses sustains a **robust chain of custody, conformant with the audit requirements of the RTFO / UK DfT framework**, and supports, at every node and for every reconciliation period, the demonstrable equivalence between the material received, the quantity processed, the quantity produced, the certified streams allocated, and the product ultimately delivered to the United Kingdom customer.
