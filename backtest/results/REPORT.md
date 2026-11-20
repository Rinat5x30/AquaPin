# AquaPin backtest report

Run on 2026-11-18. Protocol: `backtest/PROTOCOL.md` (written before the run; model unchanged, nothing tuned).
Seasons planned 20, evaluated 20, failed 0.

Compared quantity: daily model ETa vs tower ET (mm/day). RMSE in mm/day. Verdict baseline = the better of the two FAO-56 table curves per season (strongest honest baseline).

## Tower ET from LE_F_MDS (no energy-balance closure correction)

| Group | Seasons | Satellite better | Sign test p | Satellite RMSE | Table-Med RMSE | Table-Idaho RMSE | Sat bias | Best-table bias |
|---|---|---|---|---|---|---|---|---|
| all | 20 | 9/20 | 0.82 | 1.00 | 1.19 | 1.15 | 0.58 | 0.63 (table_idaho) |
| europe_rainfed | 14 | 4/14 | 0.18 | 1.02 | 1.13 | 1.01 | 0.64 | 0.61 (table_idaho) |
| china_irrigated | 6 | 5/6 | 0.22 | 0.94 | 1.40 | 1.62 | 0.37 | 0.61 (table_med) |

## Tower ET from LE_CORR (closure-corrected)

| Group | Seasons | Satellite better | Sign test p | Satellite RMSE | Table-Med RMSE | Table-Idaho RMSE | Sat bias | Best-table bias |
|---|---|---|---|---|---|---|---|---|
| all | 20 | 12/20 | 0.50 | 0.98 | 1.20 | 1.17 | 0.23 | 0.28 (table_idaho) |
| europe_rainfed | 14 | 7/14 | 1.00 | 0.99 | 1.16 | 1.05 | 0.29 | 0.26 (table_idaho) |
| china_irrigated | 6 | 5/6 | 0.22 | 0.97 | 1.33 | 1.60 | -0.00 | 0.24 (table_med) |

## Relative bias and weekly error

| Target | Set | Variant | Pooled RMSE (mm/d) | Mean weekly RMSE (mm/d) | Relative bias |
|---|---|---|---|---|---|
| le_mds | all 20 seasons (protocol) | satellite | 1.00 | 0.84 | +43% |
| le_mds | all 20 seasons (protocol) | table_med | 1.19 | 1.02 | +41% |
| le_mds | all 20 seasons (protocol) | table_idaho | 1.15 | 1.04 | +47% |
| le_mds | without FR-Gri 2017 (post-hoc sensitivity) | satellite | 1.01 | 0.84 | +42% |
| le_mds | without FR-Gri 2017 (post-hoc sensitivity) | table_med | 1.19 | 1.03 | +39% |
| le_mds | without FR-Gri 2017 (post-hoc sensitivity) | table_idaho | 1.16 | 1.05 | +45% |
| le_corr | all 20 seasons (protocol) | satellite | 0.98 | 0.77 | +13% |
| le_corr | all 20 seasons (protocol) | table_med | 1.20 | 0.99 | +11% |
| le_corr | all 20 seasons (protocol) | table_idaho | 1.17 | 1.02 | +16% |
| le_corr | without FR-Gri 2017 (post-hoc sensitivity) | satellite | 0.98 | 0.77 | +12% |
| le_corr | without FR-Gri 2017 (post-hoc sensitivity) | table_med | 1.21 | 0.99 | +10% |
| le_corr | without FR-Gri 2017 (post-hoc sensitivity) | table_idaho | 1.18 | 1.03 | +15% |

FR-Gri 2017-09-25 shows mean tower ET of 0.10 mm/day over 136 valid days, which is implausible for a wheat season (likely a data or crop-record problem). The protocol did not allow exclusions, so the main result keeps it.

## Per season (tower ET from LE_F_MDS; RMSE mm/day; r in brackets)

| Site | Season start | Irrig. | S2 obs | NDVI peak (date) | Days | Obs ET | Satellite | Table-Med | Table-Idaho | Sat < best table |
|---|---|---|---|---|---|---|---|---|---|---|
| DE-Geb | 2020-10-13 | no | 20 | 0.93 (2021-05-24) | 274 | 1.38 | 0.79 (0.94) | 0.96 (0.82) | 0.81 (0.93) | yes |
| DE-Geb | 2021-09-30 | no | 32 | 0.91 (2022-05-09) | 299 | 1.29 | 1.08 (0.75) | 1.29 (0.59) | 0.88 (0.85) | no |
| DE-Geb | 2023-10-01 | no | 18 | 0.91 (2024-05-23) | 174 | 1.49 | 1.11 (0.91) | 1.21 (0.69) | 1.34 (0.86) | yes |
| FR-Gri | 2017-09-25 | no | 28 | 0.89 (2018-04-19) | 136 | 0.10 | 0.94 (0.16) | 0.92 (0.17) | 0.92 (0.17) | no |
| FR-Gri | 2019-10-03 | no | 38 | 0.87 (2020-04-18) | 302 | 1.06 | 0.92 (0.82) | 1.02 (0.73) | 0.79 (0.90) | no |
| FR-Gri | 2021-10-09 | no | 44 | 0.92 (2022-05-13) | 295 | 1.14 | 1.04 (0.83) | 1.09 (0.79) | 1.02 (0.85) | no |
| FR-Gri | 2024-12-02 | no | 34 | 0.87 (2025-05-04) | 224 | 1.42 | 1.13 (0.85) | 1.10 (0.87) | 1.47 (0.62) | no |
| BE-Lon | 2018-10-10 | no | 29 | 0.93 (2019-05-13) | 293 | 0.87 | 1.26 (0.80) | 1.35 (0.58) | 1.14 (0.88) | no |
| BE-Lon | 2021-10-28 | no | 29 | 0.91 (2022-06-04) | 277 | 1.17 | 0.88 (0.86) | 1.07 (0.73) | 0.91 (0.88) | yes |
| BE-Lon | 2023-10-16 | no | 10 | 0.88 (2024-06-08) | 218 | 1.16 | 1.38 (0.86) | 1.34 (0.72) | 1.55 (0.83) | no |
| DE-RuS | 2017-10-25 | no | 13 | 0.93 (2018-05-08) | 276 | 1.41 | 0.81 (0.89) | 0.95 (0.80) | 0.87 (0.86) | yes |
| DE-RuS | 2019-10-26 | no | 20 | 0.88 (2020-05-07) | 256 | 1.53 | 0.96 (0.70) | 1.09 (0.63) | 0.64 (0.86) | no |
| DE-RuS | 2022-10-15 | no | 12 | 0.88 (2023-05-27) | 259 | 1.66 | 0.86 (0.90) | 1.17 (0.64) | 0.83 (0.91) | no |
| DE-RuS | 2024-10-25 | no | 16 | 0.91 (2025-05-11) | 278 | 1.45 | 0.99 (0.79) | 1.10 (0.72) | 0.82 (0.85) | no |
| CN-Lch | 2017-10-05 | yes | 16 | 0.67 (2018-05-08) | 88 | 0.62 | 0.82 (0.69) | 0.76 (0.67) | 1.08 (0.44) | no |
| CN-Lch | 2018-10-05 | yes | 20 | 0.67 (2019-04-03) | 160 | 2.10 | 0.95 (0.91) | 1.65 (0.80) | 1.83 (0.74) | yes |
| CN-Lch | 2019-10-05 | yes | 32 | 0.7 (2020-04-22) | 243 | 1.91 | 0.98 (0.86) | 1.41 (0.74) | 1.38 (0.79) | yes |
| CN-Yuc | 2017-10-05 | yes | 17 | 0.69 (2018-04-20) | 215 | 1.28 | 0.97 (0.89) | 1.47 (0.79) | 1.76 (0.78) | yes |
| CN-Yuc | 2018-10-05 | yes | 20 | 0.72 (2019-04-15) | 55 | 0.51 | 0.52 (0.34) | 0.53 (0.24) | 0.67 (-0.01) | yes |
| CN-Yuc | 2019-10-05 | yes | 21 | 0.74 (2020-04-24) | 102 | 3.33 | 0.99 (0.82) | 1.54 (0.65) | 2.16 (0.48) | yes |

## Notes

- Chinese seasons (CN-Lch, CN-Yuc) were ASSUMED to be winter wheat from the literature (not recorded in the archive); the NDVI peak date column is a sanity check (winter wheat should peak in March to May).
- Data: ICOS Carbon Portal FLUXNET-archive products (CC-BY 4.0): DE-Geb, FR-Gri, BE-Lon, DE-RuS (ICOS), CN-Lch, CN-Yuc (ChinaFLUX). Cite the site PIs when reusing.
- No site in the pilot region (Azerbaijan). Tower footprint and a 100 m circle differ. ET, not irrigation amounts, is validated.