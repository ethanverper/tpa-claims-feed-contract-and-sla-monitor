# Project spec (written BEFORE any code)

> **Portfolio project.** Northbridge Logistics, its three TPAs and every row of data are fictional.

## 1. Business case
- **Industry / function:** Insurance claims operations for a fleet. **Northbridge Logistics** runs about 35,000 leased delivery vans. It self-insures its auto liability and hires three outside **TPAs** (third-party administrators) to handle the claims:

  | TPA | Code | Daily file | Volume | Data discipline |
  |---|---|---|---|---|
  | Harbor Claims Services | `TPA-A` | CSV | ~1,200 rows | Good |
  | Redwood Risk Administrators | `TPA-B` | pipe-delimited | ~800 rows | Good, but changes its layout without notice |
  | Summit Adjusters | `TPA-C` | CSV | ~500 rows | Weakest |

- **Question to answer:** did every TPA deliver yesterday's claim transactions **on time, complete and as agreed**, and which TPA needs a remediation conversation this week?
- **Who decides what with it:**

  | Role | Decision |
  |---|---|
  | Claims-operations lead | Every Monday: which TPA gets a remediation conversation |
  | Controller | Whether the month-end claims accrual can use the TPA data as delivered |
  | TPA account manager | When to escalate a late or rejected file to the TPA |
  | Program owner (the TPM) | Whether to move a TPA from *warn-only* to *enforce* (go/no-go) |

- **Why now / cost of not knowing:** today a bad TPA file is discovered when finance asks why the accrual moved, weeks later. A file with a renamed column or 18% blank VINs silently corrupts reserving, accruals and safety analytics. The fix is a written **data contract**, checked automatically on every file, with an **SLA** that says what happens on a breach.

## 2. KPIs and hierarchy

| KPI | Formula | Dimensions (L1 → L2 → L3 → L4) | Threshold / alert | Frequency |
|---|---|---|---|---|
| **On-time delivery %** | feeds with arrival ≤ deadline ÷ feeds expected, trailing 30 days | TPA → week → business date → file | < 98% → TPA review agenda; missing at 06:00 CT → warning, at 08:00 CT → critical | Daily |
| **Completeness %** | 1 − rows with a required field blank ÷ rows received | TPA → week → field → file | Required fields ≤ 0.5% blank, `vin` ≤ 2%; warn up to 2× the limit, reject above | Daily, trended weekly |
| **Contract pass rate %** | files accepted ÷ files received | TPA → week → rule broken → file | < 97% → TPA review | Daily |
| **Error rate per 1,000 rows** | quarantined rows ÷ rows received × 1,000 | TPA → rule (validity, consistency, uniqueness, sign) → business date → row | > 5 → flagged in the scorecard | Daily |
| **Quarantined paid value ($)** | Σ `paid_amount` of quarantined rows, USD | TPA → coverage → business date → row | Any single day > $50,000 → flagged | Daily, reported weekly |

**Two internal, input KPIs** (how fast *we* react, not the TPA): time to detect a missing file (alert − deadline, target ≤ 15 min) and time to a corrected file (next accepted file − rejection alert, target ≤ 8 business hours).

## 3. Data
- **How it arrives:** one file per TPA per business day, plus a `_manifest.json`, simulated as an SFTP drop straight into S3:
  `landing/tpa=<TPA>/business_date=<YYYY-MM-DD>/<file>` + `_manifest.json` (tpa_id, business_date, file_name, row_count, control_total_paid, sha256).
  The **manifest's arrival** starts validation; a file without its manifest is never processed.
- **Deadline:** the file for business date D lands by **06:00 CT on D+1** (business days). A missing file produces no event, so a **schedule** checks at 06:00 and 08:00 CT.
- **Volume:** ~2,500 rows per day × 30 days ≈ **75,000 rows**, 90 expected files (~12 MB).
- **The contract:** 14 columns (`docs/data-contract.yaml`, read by the validator at run time, so the document and the checker cannot drift apart): transaction_id, tpa_claim_ref, claim_id, loss_date, report_date, transaction_date, transaction_type, coverage, claim_status, paid_amount, reserve_amount, currency, vin, as_of_ts.
- **Sample record:**
  ```csv
  transaction_id,tpa_claim_ref,claim_id,loss_date,report_date,transaction_date,transaction_type,coverage,claim_status,paid_amount,reserve_amount,currency,vin,as_of_ts
  HCS-20261012-000481,HCS-88213,NBL-CLM-004512,2026-10-08,2026-10-09,2026-10-12,PAYMENT,PHYSICAL_DAMAGE,OPEN,4120.50,0.00,USD,1FTBW3XM5HKA12345,2026-10-12T22:15:03-05:00
  ```
- **The story planted in the data** (the simulator writes an answer key, local only; detection is graded against it, target 100% recall and 0 false alarms):

  | Level | Defect | Count | Expected detection |
  |---|---|---|---|
  | Feed | Late files | 3 | Arrival SLA breach |
  | Feed | Missing file (TPA-C day 21, arrives 31 h late) | 1 | 06:00 warning, 08:00 critical |
  | File | Schema drift (TPA-B days 17–18 rename `paid_amount` → `amount_paid`) | 2 | Rejected; the COE is written about it |
  | File | Manifest mismatch (row count off by 12; control total off by $1,284.50) | 2 | Rejected |
  | File | Same file sent twice (same SHA-256) | 2 | Ignored, logged, never double counted |
  | File | Completeness drift (TPA-C days 8–14, 18% blank VINs) | 7 | Completeness SLA breach |
  | Row | Invalid currency (`US$`, `MXP`) | 40 | Quarantined (validity) |
  | Row | Bad VIN check digit | 15 | Quarantined (validity) |
  | Row | Loss date after report date | 12 | Quarantined (consistency) |
  | Row | Duplicate transaction_id | 60 | Second one quarantined (uniqueness) |
  | Row | Payment with a negative sign | 25 | Quarantined (sign rule) |

## 4. Design
- **Pattern:** event-driven per file + scheduled deadline checks + a daily batch for row-level quality and the scorecard.

  ```
  TPA drop (simulated) → S3 landing/ + _manifest.json
        │ EventBridge: manifest created              EventBridge schedules 06:00 / 08:00 CT (created disabled)
        ▼                                                     ▼
  Lambda contract_validator ──► DynamoDB arrival ledger ◄── Lambda deadline_checker
        │ pass / reject (quarantine/) + SNS                    │ "who hasn't delivered?" → SNS
        ▼
  Glue job + Glue Data Quality (row rules) → validated/ Parquet · quarantine/ rows · dq_results
        ▼
  Athena views (sql/01–07) → HTML scorecard (always) · QuickSight (by exception, deploy window only)
  Local Airflow DAG: load → validate → score → notify, against the same AWS resources
  ```

- **Services and why:**

  | Service | Role | Why this one (and not the alternative) |
  |---|---|---|
  | S3 | landing / validated / quarantine / scorecard zones | Files kept exactly as sent. *Transfer Family (real SFTP) bills per hour: only shown in the README.* |
  | **EventBridge** | Manifest-created rule + two schedule rules | One service for "a file arrived" and "a file did *not* arrive". *Direct S3 → Lambda can't express the schedule side.* |
  | Lambda | Contract validator, deadline checker, scorecard publisher | Seconds-long checks. *Glue would bill DPU-minutes for a 2-second check.* |
  | **DynamoDB** (on-demand) | Arrival ledger: `tpa_id + business_date`, conditional write on the SHA-256 | Idempotency and a fast "who is missing?" query. *Athena over S3 listings has no conditional writes.* |
  | Glue + Glue Data Quality | Row rules: completeness, validity, uniqueness, consistency, sign | Same pattern as the AP project; readable DQDL rules. |
  | Athena | One query per KPI | Same pattern; 1 GB scan cap. |
  | SNS | Two topics: `tpa-ops-alerts`, `program-alerts` | The right audience gets the right message. |
  | **Airflow (local, $0)** | The 4-step batch path as a DAG | Portfolio rule 13; compared with the event path. *MWAA: never (cost rule).* |
  | QuickSight (exception) | Scorecard screenshots for non-engineers | Only inside the deploy window, pricing checked that day, subscription deleted. The HTML scorecard is built first. |

- **New concepts this project introduces:**
  1. **Data contract as code + SLA vs SLO vs SLI:** a YAML contract the code reads; an SLA clock with business days and time zones (06:00 CT = 12:00 UTC in November, 11:00 UTC in summer).
  2. **Designing for what does not happen:** EventBridge schedules + a DynamoDB ledger to catch a missing file; idempotency by checksum with conditional writes.
  3. **The TPM paper trail:** PRFAQ, charter, RACI, RAID, go/no-go, status, runbook, COE in `docs/tpm/`.
- **Reused:** manifest/control-total validation, Glue Data Quality, Athena `ROLLUP`, answer-key grading, evidence and teardown scripts.
- **Out of scope:** a real SFTP server, a downstream claims warehouse, reserving models.
- **Depth:** Standard.
- **Levels:** 0 TPM pack → 1 simulator + answer key → 2 contract checker → 3 SLA clock → 4 event-driven validation (Terraform) → 5 row-level DQ + quarantine → 6 scorecard SQL, HTML scorecard, Airflow DAG → 7 deploy window, evidence, COE, teardown. Levels 0–3 are local and already demo-able; target deploy Nov 13–14, before the Nov 16 phone screen.

## 5. Cost estimate (goal < $1, hard cap $3)

| Service | Unit price (us-east-1) | Usage during the demo | Estimate |
|---|---|---|---|
| Glue (Spark) + Data Quality | $0.44 per DPU-hour, 1-minute minimum | 2 DPU × ~5 min × up to 3 runs | $0.15–0.20 |
| Lambda, EventBridge, SNS email | free tier | ~200 invocations, a few dozen events and emails | $0.00 |
| DynamoDB on-demand | per request | ~300 writes and reads | < $0.01 |
| S3, Athena, CloudWatch Logs | small | ~15 MB, ~20 queries (1 GB cap), 1-day log retention | < $0.05 |
| **Total (without QuickSight)** | | | **≈ $0.30** |

- **QuickSight is not in this number.** On deploy day I check current pricing and trial terms and tell you the cost before enabling it; if it would push the total near $3, we stay with the HTML scorecard.
- Nothing bills by the hour. Deploy window ≤ 2 hours, then `make destroy`, `make clean-glue-logs`, `make leftovers`. Schedules created disabled.

## 6. Definition of done
- [ ] Tests and CI green (`ruff format`, `ruff check`, `pytest`, `terraform fmt`)
- [ ] Detection graded against the answer key: 100% recall, 0 false alarms
- [ ] `docs/tpm/` complete: PRFAQ, charter, RACI, RAID, go/no-go, status, runbook, COE
- [ ] `docs/data-contract.yaml`, `docs/lineage.md`, `docs/kpi-dictionary.md`, `docs/configuration.md`
- [ ] Airflow DAG with an integrity test; run once against the real resources
- [ ] Deployed for real; screenshots indexed in `docs/evidence/README.md`, linked from the top of the README
- [ ] `make destroy` + `make leftovers` empty; actual cost recorded (≤ $3)
- [ ] README readable by a non-technical person; CV bullets and STAR stories drafted (portfolio project, described truthfully)
