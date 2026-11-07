# Program charter: TPA claims feed contract and SLA monitor

> **Portfolio project.** Company, people, TPAs and numbers are fictional or synthetic.

- **Program:** a data contract, automated checks and an SLA scorecard for the daily claim files that three TPAs send to Northbridge Logistics.
- **TPM / owner:** Ethan Verduzco.
- **Sponsor (decision maker):** Claims-operations lead.
- **Status:** Signed off 2026-11-06.

## 1. Problem
The three TPAs (Harbor, Redwood, Summit) deliver about 2,500 claim transactions per day in three files. No one checks a file when it arrives. In the simulated baseline month, 15 of 90 files had a file-level problem: 3 late, 1 missing, 2 schema changes, 2 manifest mismatches and 7 with VIN completeness drift. A further 152 rows broke row-level rules. All of it was found only at month end, when the claims accrual moved.

## 2. Customer
| Customer / user | What they do today | What they need |
|---|---|---|
| Claims-operations lead | Hears about bad TPA data from finance, weeks later | A Monday scorecard that names the TPA to talk to |
| Controller | Uses TPA data for the month-end accrual without knowing its quality | A clear "usable as delivered" signal per TPA and month |
| TPA account manager | Escalates by memory and email threads | Alerts with the rule broken and the line that failed |
| TPA operations contact (×3) | Learns of a rejected file days later, if ever | An alert within minutes, with what to resend |

## 3. Goals
1. Detect 100% of the planted file and row defects, with 0 false alarms on clean rows, by **2026-11-12** (local grading).
2. Alert on a missing file within 15 minutes of the 06:00 CT deadline, proven on AWS by **2026-11-14**.
3. Publish a per-TPA scorecard that a non-engineer can read (HTML always; QuickSight only by exception), by **2026-11-14**.

## 4. Non-goals
- A real SFTP server (AWS Transfer Family bills by the hour; its place is shown in the README).
- A downstream claims warehouse, reserving models or financial postings.
- Fixing TPA data or editing claim amounts. Corrections arrive as new files from the TPA.
- Claimant personal data. The contract forbids names, addresses and medical details.

## 5. Success metrics
| Type | Metric | Baseline | Target | Source / query |
|---|---|---|---|---|
| **Output** | Planted defects detected / planted (recall), false alarms on clean rows | 0% detected at the time | 100%, 0 false alarms | `docs/evidence/grading.md` |
| **Output** | On-time delivery % per TPA (trailing 30 days) | not measured | Reported; ≥ 98% is the SLA | `sql/` scorecard query |
| **Input** | Time to detect a missing file | weeks | ≤ 15 min after the deadline | ledger + alert timestamps |
| **Input** | Validation result after arrival | none | ≤ 10 min | Lambda logs |
| **Input** | Scorecard published | none | by 07:00 CT | scorecard object timestamp |
| **Guardrail** | Run cost of the deployed demo | — | < $1 (hard cap $3) | Cost Explorer, tag `Project` |

## 6. Scope
| In scope | Out of scope |
|---|---|
| TPA feed simulator with planted defects and an answer key | See non-goals |
| Contract-as-code checker, SLA clock, arrival ledger | |
| Row-level data quality with quarantine | |
| Scorecard SQL, HTML scorecard, alerts, local Airflow DAG | |
| TPM paper trail, runbook, COE, evidence, teardown | |

## 7. Milestones
| # | Milestone | Date | Gate / evidence | Critical path? |
|---|---|---|---|---|
| M1 | PR/FAQ, charter, RACI, RAID, contract draft (level 0) | 2026-11-06 | this folder, `docs/spec.md` | Yes |
| M2 | Simulator, contract checker, SLA clock: local (levels 1–3) | 2026-11-08 | `make test` green, files + answer key | Yes |
| M3 | Terraform, row-level DQ, scorecard SQL, Airflow DAG (levels 4–6) | 2026-11-12 | grading 100% locally, `terraform validate` | Yes |
| M4 | Deploy window: evidence, go/no-go, COE | 2026-11-13 / 14 | `go-no-go.md`, `docs/evidence/` | Yes |
| M5 | Teardown verified, README final, published | 2026-11-14 | `make leftovers` empty | No (Nov 15 is buffer) |

The **contract sign-off comes before enforcement**: no TPA moves from warn-only to reject until the contract is agreed.

## 8. Top risks
| Risk | Score (L×I) | Mitigation | Owner |
|---|---|---|---|
| R1 Time pressure before the Nov 16 phone screen | 3×4=12 | Levels 0–3 are local and already demo-able; Nov 15 buffer | TPM |
| R2 Daylight-saving or time-zone error in the deadline | 3×3=9 | Deadline stored as local time + zone; tests for CST and CDT | Data engineering |
| R3 QuickSight price or trial terms differ | 2×3=6 | HTML scorecard built first; price checked on deploy day | TPM |

Full log: [raid-log.md](raid-log.md)

## 9. Stakeholders
| Role | Name / team | Interest | Involvement |
|---|---|---|---|
| Sponsor | Claims-operations lead | Decides the TPA agenda | Approves gates |
| Business owner | Controller | Uses the data for accruals | UAT, sign-off of the "usable" signal |
| Data producer | Harbor, Redwood, Summit (TPA operations) | Own their feeds | Data contract |
| Vendor management | TPA account manager | Owns the relationship | Escalations, TPA review |
| Engineering | Data engineering | Builds and runs | Design review, runbook |
| Security | Security and privacy | No personal data, least privilege | Access review |

Full matrix: [raci.md](raci.md)

## 10. Tenets
1. **The contract is code.** If the document and the checker disagree, the checker reads the document.
2. **Design for what does not happen.** A missing file is the most expensive defect, and it sends no event.
3. **Reject loudly, quarantine quietly.** A broken file stops; a bad row is set aside without blocking the good ones.
4. **Cost is a requirement.** The demo stays under the cap or it does not ship.

## 11. Approvals
| Role | Name | Date |
|---|---|---|
| Sponsor | Claims-operations lead (fictional) | 2026-11-06 |
| TPM | Ethan Verduzco | 2026-11-06 |
