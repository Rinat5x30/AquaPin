# Backtest protocol (written BEFORE running; not changed after seeing results)

Question: does a satellite-driven Kcb (Sentinel-2 NDVI) estimate evapotranspiration (ET) better than the
FAO-56 table Kcb curve, when compared with ET measured by eddy-covariance flux towers?

## Data (open, CC-BY 4.0)
- ICOS Carbon Portal FLUXNET-archive products (daily `FLUXMET_DD`, metadata `BIF`), downloaded via the open
  SPARQL + licence_accept endpoints. Sites: DE-Geb, FR-Gri, BE-Lon, DE-RuS (wheat seasons from BIF
  `GRP_SPP`: species Triticum aestivum + sowing date) and CN-Lch, CN-Yuc (winter wheat - summer maize; seasons
  ASSUMED from literature as 5 Oct to 10 Jun, not recorded in the archive).
- Only seasons with sowing >= 2017-03-01 (Sentinel-2 L2A era).
- Measured ET: `LE_F_MDS` (and closure-corrected `LE_CORR` as a second target), converted with
  lambda = 2.501 - 0.002361*TA (MJ/kg). Only days with `LE_F_MDS_QC >= 0.7`.

## Model (exactly the production pipeline, no tuning on these data)
- Open-Meteo ET0 + rain (the real production weather source, not the tower's own meteorology).
- Field radius 100 m at the tower location. `aquapin_core` unchanged: NDVI_soil 0.15, NDVI_full 0.85,
  Kcb range from FAO-56 Table 17, generic loam soil, soil starts at field capacity.
- Compared quantity: model ETa (daily).

## Variants
1. `satellite`: Kcb from Sentinel-2 NDVI (production method), FAO-56 Table 11 "Mediterranean" stage lengths for
   the base curve.
2. `table_med`: FAO-56 table curve, Mediterranean stage lengths (30/140/40/30 d).
3. `table_idaho`: FAO-56 table curve, Idaho stage lengths (160/75/75/25 d; colder climate). 
   The baseline used for the verdict is the BETTER of 2 and 3 per season (strongest honest baseline).
- Irrigation: CN sites assumed irrigated: every advised irrigation is applied (same rule in all variants).
  European sites assumed rainfed: no irrigation.

## Metrics
Per season and pooled over matched days: bias (model - obs, mm/day), RMSE, MAE, Pearson r, season-total bias %.
Also 7-day mean RMSE (reduces tower noise). Paired comparison across seasons: satellite vs better baseline,
number of seasons where satellite RMSE is lower, two-sided sign test.

## Pre-declared limits
- Few sites, mostly Europe + 2 Chinese sites; no site in the pilot region (Azerbaijan).
- Tower footprint vs 100 m circle and Sentinel-2 pixels are not identical.
- Tower ET is itself uncertain (energy balance closure gap); both LE_F_MDS and LE_CORR are reported.
- ET is validated, not irrigation advice itself (real irrigation amounts are unknown).
- The result may be negative; it will be reported as it is.
