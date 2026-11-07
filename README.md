# Know by 07:00 whether every claims administrator delivered good data

A data contract and SLA monitor for the daily claim files that three outside claims administrators (TPAs) send to a delivery fleet. Every file is checked against a written contract the moment it lands. A **missing** file raises an alarm at 06:00 even though nothing arrived. Each TPA gets a daily scorecard: on-time delivery, completeness, files accepted, error rate and dollars quarantined.

![CI](https://github.com/ethanverper/tpa-claims-feed-contract-and-sla-monitor/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC) ![AWS](https://img.shields.io/badge/AWS-S3%20·%20EventBridge%20·%20Lambda%20·%20DynamoDB%20·%20Glue%20Data%20Quality%20·%20Athena%20·%20SNS-FF9900)

> 🚧 **In progress, built level by level.** Third project of the portfolio. This one is run as a program, not only coded: the TPM paper trail (PR/FAQ, charter, RACI, RAID log, go/no-go, COE) lives in [docs/tpm/](docs/tpm/README.md), next to the code.
>
> **Portfolio project.** Northbridge Logistics, its three TPAs and all data are fictional and synthetic.

## Progress

| Level | What | Status |
|---|---|---|
| 0 | Business case, KPIs, planted data story, cost estimate ([docs/spec.md](docs/spec.md)) · [PR/FAQ](docs/tpm/prfaq.md) · [charter](docs/tpm/charter.md) · [RACI](docs/tpm/raci.md) · [RAID log](docs/tpm/raid-log.md) · first draft of the [data contract](docs/data-contract.yaml) | ✅ Done |
| 1 | TPA feed simulator: 3 TPAs × 30 business days, 96 deliveries (~75,000 rows), 17 file-level and 152 row-level planted defects with an answer key; two [lessons](docs/lessons-learned.md) from checking the synthetic data | ✅ Done |
| 2 | Contract-as-code checker: the validator reads `docs/data-contract.yaml` | ⏳ Next |
| 3 | SLA clock: business days and time zones (06:00 CT) | ⬜ |
| 4 | Event-driven validation on AWS: EventBridge, Lambda, DynamoDB arrival ledger, SNS | ⬜ |
| 5 | Row-level data quality and quarantine (Glue Data Quality) | ⬜ |
| 6 | Scorecard SQL, HTML scorecard, local Airflow DAG | ⬜ |
| 7 | Deploy window, evidence, COE, teardown | ⬜ |

## 1. The business problem

Northbridge Logistics (fictional) runs about 35,000 leased delivery vans, self-insures its auto liability and hires three TPAs to handle the claims. Each TPA sends one file of claim transactions per business day. Today nobody checks those files when they arrive. A late file, a renamed column or a week of blank vehicle numbers is found weeks later, when finance asks why the month-end claims accrual moved.

**Who uses it:**
- **Claims-operations lead:** which TPA gets a remediation conversation this Monday.
- **Controller:** can the month-end accrual use the TPA data as delivered?
- **TPA account manager:** when to escalate.
- **Each TPA's operations contact:** what to resend.

## 2. KPIs

| KPI | Formula | Target / alert |
|---|---|---|
| On-time delivery % | files by the deadline ÷ files expected (30 days) | ≥ 98%; missing at 06:00 CT → warning, 08:00 CT → critical |
| Completeness % | 1 − rows with a required field blank ÷ rows | ≥ 99.5%; VIN blank ≤ 2% |
| Contract pass rate % | files accepted ÷ files received | ≥ 97% |
| Error rate per 1,000 rows | quarantined rows ÷ rows × 1,000 | ≤ 5 |
| Quarantined paid value ($) | Σ paid_amount of quarantined rows | any day > $50,000 flagged |

Full definitions, hierarchy and the cost estimate (≈ $0.30): [docs/spec.md](docs/spec.md).

## 3. The data (simulated)

Three fictional TPAs send one file per business day for 30 business days (2026-10-01 to 2026-11-11), each with a `_manifest.json` that states its row count, total paid and SHA-256 fingerprint. About 75,000 claim transactions in all, roughly $1.4 million paid per business day across the fleet. Sample rows: [data/sample/](data/sample/).

```text
transaction_id|tpa_claim_ref|claim_id|loss_date|report_date|transaction_date|transaction_type|coverage|claim_status|paid_amount|reserve_amount|currency|vin|as_of_ts
RRA-20261001-000001|RRA-11601|NBL-CLM-006101|2026-10-01|2026-10-01|2026-10-01|RESERVE_CHANGE|AUTO_LIABILITY|OPEN|0.00|4066.77|USD|3C6C6UF24MS993360|2026-10-01T22:13:40-05:00
```

**The story planted in the data**, written to an answer key the monitor never sees, so detection is graded instead of eyeballed:

| Level | Planted | How many | What the monitor must do |
|---|---|---|---|
| Feed | Late file (07:10, 09:40, 06:50 CT) | 3 | SLA breach on arrival |
| Feed | File missing at the deadline (arrives 31 h late) | 1 | Warning at 06:00 CT, critical at 08:00 CT |
| File | `paid_amount` renamed to `amount_paid` without notice (TPA-B, two days) | 2 | Reject; COE |
| File | Manifest that does not match its file (row count +12; total +$1,284.50) | 2 | Reject |
| File | The same file sent twice (same SHA-256) | 2 | Ignore and log |
| File | A week of blank VINs at TPA-C (18% vs the 2% allowed) | 7 | Completeness SLA breach |
| Row | Invalid currency (`US$`, `MXP`), bad VIN check digit, loss after report, repeated transaction_id, negative payment | 40 + 15 + 12 + 60 + 25 | Quarantine the row, keep the rest |

Generate it yourself (local, no AWS, about one second):

```bash
make generate
```
