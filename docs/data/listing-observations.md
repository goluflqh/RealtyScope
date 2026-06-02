# Listing Observations and Price History

Date: 2026-06-02
Phase: 3.7 Observation / Price History Layer

RealtyScope now separates the latest canonical listing state from historical observations. This is the foundation for price-change analysis, trend dashboards, time-aware EDA, and future ML validation.

## Data Layers

| Layer | Table | Purpose | Mutation rule |
| --- | --- | --- | --- |
| Raw source snapshot | `raw_listings` | Stores the original source payload and `payload_hash` for audit/replay. | Insert once per unique `(source_id, payload_hash)`. Replaying the exact same payload reuses the row. |
| Canonical latest listing | `listings` + `listing_source_links` | Stores the latest normalized facts for each source listing/canonical listing: current price, area, rooms, floor, coordinates, quality flags. | Updated when a later normalized record for the same `(source_id, source_listing_id)` is persisted. |
| Historical observation | `listing_observations` | Stores the normalized snapshot observed from a raw listing: observed time, price, price per m2, area, rooms, floor, active/status snapshot. | Insert once per `(source_id, source_listing_id, observed_at)`. Exact same-time replays do not create duplicate observations. A later deliberate observation timestamp may create a new observation even when the raw payload row is reused. |

## Why Canonical and Observation Tables Are Both Needed

`listings` answers: "What is the latest known state of this apartment listing?"

`listing_observations` answers: "What states did we observe over time, and when did price or listing facts change?"

Keeping both avoids two common problems:

- dashboards and API read paths can stay simple by reading the latest listing rows;
- trend/EDA/ML work does not lose history when the canonical row is updated.

## Observation Schema

The Phase 3.7 observation row includes:

- `listing_id`: canonical listing FK;
- `source_id` and `source_listing_id`: source identity used for grouping and source-specific trends;
- `raw_listing_id`: raw snapshot FK used for audit/replay;
- `observed_at`: timestamp from the normalized listing;
- `price_rub` and `price_per_m2`: price history measures;
- `total_area_m2`, `rooms`, `floor`, `floors_total`: listing snapshot fields that may affect comparisons;
- `active` and `status`: current status snapshot, initialized as `active=true`, `status=observed`.

Indexes support the main future reads:

- `ix_listing_observations_listing_observed` for one listing's history ordered by time;
- `ix_listing_observations_source_listing_observed` for source-specific history and comparisons.

The unique constraint `uq_listing_observations_source_listing_observed` prevents duplicate observations for the same source listing at the same observed timestamp. It intentionally allows a repeated raw payload to produce a later observation when a scheduled run records a new `observed_at`.

## Persistence Behavior

When an `IngestionBatch` is persisted:

1. `raw_listings` is inserted or reused by `payload_hash`.
2. `listings` is created or updated by `(source_id, source_listing_id)` through `listing_source_links`.
3. `listing_observations` is inserted only if the same source listing has not already produced an observation at the same `observed_at`.

Expected outcomes:

- First time a listing appears: one raw row, one canonical listing row, one observation row.
- Same payload replayed at the same `observed_at`: raw row reused, canonical listing refreshed, no duplicate observation row.
- Same payload replayed at a later deliberate `observed_at`: raw row reused, canonical listing refreshed, new observation row.
- Same source listing with changed price or changed material payload: new raw row, canonical listing updated to the latest price, new observation row.

## Current Boundary

Phase 3.7 adds backend history storage only. It does not yet add trend API endpoints, period filters, seasonality charts, or Streamlit comparison charts. Those should read from `listing_observations` in the dashboard/API phase.
