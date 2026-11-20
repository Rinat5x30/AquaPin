# TODOS

## Full open release (pip + Zenodo DOI + docs)
- **What:** Полный открытый релиз библиотеки Sentinel-2 -> Kc -> FAO-56 перед региональным финалом.
- **Why:** Цитируемость ценна для Stanford/ZJU/TUM; закрепляет нишу "открытый пайплайн".
- **Context:** Минимум (публичный репо + LICENSE + README с запуском бэктеста) уже в скоупе. Здесь: pip-пакет, документация, DOI через Zenodo, воспроизводимый ноутбук. Проверить лицензию pyfao56 до релиза.
- **Effort:** M (human) / S (CC). **Priority:** P2.
- **Depends on:** стабильный бэктест.

## Fitted Kc stage ("honest ML")
- **What:** Second stage: fit NDVI->Kcb coefficients on train sites, evaluate on held-out sites.
- **Why:** Eng review chose literature-only Kc; the ML direction dropped out.
- **Pros:** Possible accuracy gain, scientific depth. **Cons:** overfitting risk with few sites.
- **Context:** Literature baseline stays the headline result; backtest must be stable first.
- **Effort:** M. **Priority:** P3. **Depends on:** working backtest, enough validation sites (T2).

## CI (GitHub Actions)
- **What:** Ruff + Black + mypy + pytest (no live APIs) on every push, no auto-deploy.
- **Why:** Matches Black/Ruff/mypy standards; public repo implies checks.
- **Pros:** Cheap, catches errors before demo. **Cons:** small setup.
- **Context:** Design doc Distribution Plan defers CI/CD to the Build phase.
- **Effort:** S. **Priority:** P2. **Depends on:** public repo (T7).

## Desktop polygon drawing for fields
- **What:** Post-MVP: draw an exact field polygon on desktop instead of a radius.
- **Why:** A radius clips irregular fields.
- **Pros:** More accurate NDVI and advice. **Cons:** extra UI and geometry validation (two input paths).
- **Context:** Point + adjustable radius is the base input; Telegram sends only a point.
- **Effort:** M. **Priority:** P3. **Depends on:** MVP, area limit (T2).

## P1: Fix the ET overestimation found by the backtest
- **What:** The model overestimates ET by about 13% to 43% against towers (RMSE 1.0 mm/day). Investigate: Open-Meteo ET0 bias vs tower meteorology, soil evaporation (Ke) and initial soil water, NDVI_full cap (Chinese peaks 0.67-0.74 never reach 0.85), stage lengths. Any change must be tested on held-out site-seasons, not the same 20.
- **Why:** An ET overestimate means advice that comes too early. Satellite Kcb is not yet better than a well-chosen table curve in rainfed Europe.
- **Effort:** L.

## P1: Backtest in the pilot region
- **What:** No test site is in Azerbaijan. Find open or local ET / soil moisture data (e.g. nearest FLUXNET sites in similar climate; local agronomists) and add them.
- **Effort:** M-L.

## P2: Confirm the Chinese winter wheat seasons
- **What:** CN-Lch and CN-Yuc seasons (5 Oct to 10 Jun) are assumed from the literature; check site metadata or papers. NDVI peaks fall in April-May, which is consistent but not proof.
- **Effort:** S.

## P1: Run the Telegram bot against the real Telegram API
- **What:** Create a bot, set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_WEBHOOK_SECRET`, `setWebhook` with `secret_token`, send a real location.
- **Why:** The flow is covered by tests with a fake messenger only.
- **Effort:** S. **Depends on:** a public HTTPS host.

## P1: Production DB + hosting
- **What:** Postgres (job queue uses `skip_locked`, untested on SQLite), VPS or always-on host, cron `run_jobs`, stable URL before finals.
- **Effort:** M.

## P2: Translate model assumptions in the UI
- **What:** `AdviceResult.assumptions` are English strings; RU users see English in the "Why" panel.
- **Effort:** S.

## P2: Tile provider terms for the pin picker
- **What:** Confirm OpenStreetMap tile policy fits expected use or switch provider; verify Open-Meteo terms for production.
- **Effort:** S.

## P2: Soil parameters and season end
- **What:** Replace the generic loam default with soil data; detect harvest so advice stops after maturity.
- **Effort:** M.

## P2: Automate the 3 Playwright E2E tests
- **What:** Offline demo (network blocked), live pin loading/empty/error, mobile viewport. Checked manually in this session (same-origin resources only, slider, RU/EN).
- **Effort:** S.

## P3: HSTS include-subdomains/preload decision
- **What:** `check --deploy` warns W005/W021; enable only if all subdomains are HTTPS-only.

## P2: Speed up long season replays
- **What:** A 5-month replay took about 2 min (about 50 Sentinel-2 items x 3 small reads each). Options: more parallel reads, cache chips per (tile, date, window), smaller default window, partial result first (weather only).
- **Effort:** M.
