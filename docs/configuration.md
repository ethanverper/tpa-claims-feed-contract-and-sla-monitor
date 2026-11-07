# Configuration and setup

Everything you can change, where it lives, and what to do after changing it. Someone running the project for the first time should only need this page and the README. This page grows with each level; it covers levels 0–1 today.

## 1. Prerequisites
| Tool | Version | Why | Check |
|---|---|---|---|
| Python | ≥ 3.10 | Simulator, checks, tests | `python3 --version` |
| PyYAML, pytest, ruff | see `requirements-dev.txt` | Read the config, run tests and lint | `make install` |
| Terraform | ≥ 1.6 | Infrastructure (from level 4) | `terraform version` |
| AWS CLI | v2 | Deploy window only (level 7) | `aws sts get-caller-identity` |

## 2. Configuration files at a glance
| File | In git? | What it holds | Who reads it |
|---|---|---|---|
| `docs/data-contract.yaml` | ✅ | The agreement with the TPAs: columns, allowed values, quality rules, SLAs | Simulator (columns, file name); the checker from level 2 |
| `config/settings.yaml` | ✅ | Every tunable value: calendar, deadline, simulation, planted defects | Python via `src/common/settings.py`; Terraform from level 4 |
| `config/master_data.yaml` | ✅ | The fictional business: TPAs, coverages, transaction mix, fleet | Python via `src/common/settings.py` |

## 3. What each file contains

### `docs/data-contract.yaml`
| Section | Meaning | Change it when… |
|---|---|---|
| `schema[name=claim_transactions].properties` | The 14 columns, in file order, with types and allowed values | A TPA agrees a layout change (bump `version`: MINOR for a new optional column, MAJOR for anything else) |
| `schema[name=claim_transactions].physicalName` | File name pattern, `{tpa_id}_claims_{YYYYMMDD}.csv` | The naming convention changes |
| `schema[name=manifest]` | The 6 fields of `_manifest.json` | Never without a MAJOR version |
| `slaProperties`, `customProperties` | Deadline, latency, SLA targets, warn/reject actions, breach handling, change process | The SLA is renegotiated |

### `config/settings.yaml`
| Key | Meaning | Change it when… |
|---|---|---|
| `contract.path` | Which contract file the code reads | Testing a new contract version |
| `contract.data_table`, `contract.manifest_table` | Names of the two schema entries in the contract | The contract renames them |
| `calendar.first_business_date`, `calendar.business_days` | The simulated period (2026-10-01, 30 business days, Monday to Friday) | You want another period |
| `calendar.timezone`, `calendar.deadline_local_time`, `calendar.critical_local_time` | The SLA clock: `America/Chicago`, 06:00 warning, 08:00 critical | The SLA changes |
| `simulation.seed` | Same seed → identical files and README numbers | You want a different random story |
| `simulation.output_dir`, `simulation.sample_dir` | Where generated files and README samples go | — |
| `simulation.volume_jitter` | Daily rows vary ± this share around each TPA's average | — |
| `simulation.arrival_window_local`, `simulation.extract_window_local` | When normal files arrive (D+1) and when rows were extracted (D) | — |
| `simulation.vin_blank_rate` | Normal share of blank VINs per clean file (exact count per file, see lesson 2) | Keep it under the contract's 2% |
| `simulation.max_report_lag_days`, `simulation.portfolio_age_days` | Loss-to-report delay; age of the claims open on day 1 | — |
| `defects.*` | Every planted defect: which TPA, which business day (1 = first date), and its size | You want another test story; the answer key follows automatically |

### `config/master_data.yaml`
| Key | Fields | Example |
|---|---|---|
| `tpas[]` | `tpa_id`, `name`, `delimiter`, `daily_rows`, `claim_ref_prefix`, `transaction_prefix`, `open_claims_at_start`, `new_claims_per_day` (all required) | `TPA-B`, Redwood Risk Administrators, `"|"`, 800 rows/day |
| `coverages[]` | `code`, `weight` (share of claims), `payment_median` (USD per bill) | `BODILY_INJURY`, 0.15, 2400 |
| `transaction_types` | type → share of rows | `PAYMENT: 0.45` |
| `fleet` | `size`, `manufacturer_codes`, `model_years` | 35,000 vans |

## 4. Values passed to AWS components
Filled from level 4 (Terraform reads `config/settings.yaml` with `yamldecode`).

## 5. Private and generated files (never committed)
| Path | What | Recreate with |
|---|---|---|
| `data/generated/deliveries/<seq>_<tpa>_<date>_<kind>/` | One folder per delivery: data file + `_manifest.json`. `kind` is `ORIGINAL`, `CORRECTED` or `DUPLICATE_COPY` | `make generate` |
| `data/generated/deliveries.csv` | Replay schedule: arrival time (UTC and CT), deadline, file, SHA-256 | `make generate` |
| `data/generated/answer_key/` | `file_defects.csv`, `row_defects.csv`, `summary.json`: what was planted. **Never uploaded**: the monitor must find defects on its own | `make generate` |

Committed on purpose: `data/sample/<TPA>_claims_sample.csv`, a few clean rows per TPA for the README.

## 6. Running it, in order
| Step | Command | What happens | Cost |
|---|---|---|---|
| 1 | `make install` | Installs the dev tools | $0 |
| 2 | `make test` | Unit tests, local, no AWS | $0 |
| 3 | `make generate` | 96 deliveries (~75,000 rows, 14 MB) and the answer key in `data/generated/` | $0 |
| Faster | `python3 -m src.generators.tpa_feed_simulator --scale 0.1` | Same story with 10% of the rows | $0 |

## 7. Common changes
| I want to… | Edit | Then |
|---|---|---|
| Plant another late file | `config/settings.yaml` → `defects.late_files` (add `tpa_id`, `day`, `arrival_local`) | `make generate`; the answer key includes it |
| Change a TPA's volume | `config/master_data.yaml` → `tpas[].daily_rows` | `make generate` |
| Move the deadline | `config/settings.yaml` → `calendar.deadline_local_time` | `make test` (the calendar tests cover daylight saving) |
| Add a column to the contract | `docs/data-contract.yaml` (bump `version`) and the simulator's row builder in `src/generators/claims.py` | `make test` |
