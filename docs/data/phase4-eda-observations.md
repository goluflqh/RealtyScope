# RealtyScope Phase 4 Observation-Based EDA

Date: 2026-06-02
Source: default RealtyScope database after Phase 4.0 data-readiness audit.
Notebook: `notebooks/phase4_eda_observations.ipynb`

## Dataset Snapshot

- Canonical `listings`: 2000 rows.
- `listing_observations`: 2000 rows.
- Listings with coordinates: 2000 rows, 100.00% coverage.
- ML-ready listings: 2000 rows, 100.00% coverage.
- Listings with multiple observations: 0.
- Listings with 0 price changes: 2000, so observation history validates persistence coverage but does not yet support time-series conclusions.

## Latest Listing Distributions

Price and area distributions are usable for cross-sectional EDA and a first baseline:

| Metric | Min | P25 | Median | P75 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `price_rub` | 4,699,000 | 17,000,000 | 24,387,349.5 | 38,456,904.5 | 103,751,048.5 | 1,905,387,907 |
| `price_per_m2` | 143,442.62 | 362,983.96 | 469,539.57 | 604,147.12 | 1,042,105.83 | 4,860,683.44 |
| `total_area_m2` | 10.00 | 39.38 | 55.80 | 76.40 | 127.82 | 438.00 |

Rooms distribution:

| Rooms | Listings |
| ---: | ---: |
| 0 | 194 |
| 1 | 510 |
| 2 | 646 |
| 3 | 483 |
| 4 | 132 |
| 5 | 30 |
| 6 | 4 |
| 7 | 1 |

The maximum price and price-per-square-meter rows should be treated as outlier candidates before model training, not silently dropped.

## Observation Count And Price-Change Analysis

Every canonical listing currently has exactly one row in `listing_observations`:

- Observation count min/median/max: 1 / 1 / 1.
- Listings with more than one observation: 0.
- Listings with 0 price changes: all 2000 listings.

This is enough to verify that the Phase 3.7 observation table is populated, but not enough to infer trend, volatility, listing lifetime, or temporal leakage behavior. Those analyses should wait until scheduled daily captures create multiple observations per listing and at least some changed raw payloads.

## Coordinate Coverage And OpenStreetMap Readiness

Coordinate coverage is complete, which makes Phase 4.2 OpenStreetMap enrichment feasible:

- `has_coordinates`, `latitude`, and `longitude` agree for all 2000 listings.
- Candidate OpenStreetMap features can start with transport, schools, parks, shops, healthcare counts, and nearest transport distance.
- Phase 4.1 did not call live OSM or Overpass. Future OSM-derived docs/UI must include OpenStreetMap attribution and should use bounded, cached, rate-limited access or local extracts.

## Naive Baseline Target Distribution

A naive baseline can be used as the first comparison point before scikit-learn models:

- Median `price_rub` baseline: 24,387,349.5 RUB.
- Median `price_per_m2` baseline: 469,539.57 RUB/m2.

This baseline is intentionally simple. It should be evaluated against later train/test splits after feature snapshots are deterministic and temporal leakage rules are explicit.

## Conclusion

Phase 4.1 can proceed with cross-sectional EDA and baseline preparation. The data is ready for candidate OSM enrichment because coordinate coverage is complete. The only important limitation is temporal maturity: `listing_observations` currently has one snapshot per listing and 0 price changes, so trend and price-change conclusions must remain conservative until future daily captures add history.
