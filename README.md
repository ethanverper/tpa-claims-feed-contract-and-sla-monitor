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
| 1 | TPA feed simulator: 3 TPAs × 30 business days of claim files with manifests, planted defects and an answer key | ⏳ Next |
| 2 | Contract-as-code checker: the validator reads `docs/data-contract.yaml` | ⬜ |
| 3 | SLA clock: business days and time zones (06:00 CT) | ⬜ |
| 4 | Event-driven validation on AWS: EventBridge, Lambda, DynamoDB arrival ledger, SNS | ⬜ |
| 5 | Row-level data quality and quarantine (Glue Data Quality) | ⬜ |
| 6 | Scorecard SQL, HTML scorecard, local Airflow DAG | ⬜ |
| 7 | Deploy window, evidence, COE, teardown | ⬜ |

## 1. The business problem

Northbridge Logistics (fictional) runs about 3,500 leased delivery vans, self-insures its auto liability and hires three TPAs to handle the claims. Each TPA sends one file of claim transactions per business day. Today nobody checks those files when they arrive. A late file, a renamed column or a week of blank vehicle numbers is found weeks later, when finance asks why the month-end claims accrual moved.

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
