# RAID log: TPA claims feed contract and SLA monitor

Risks, assumptions, issues and dependencies, reviewed every week (and at each level gate).

- **Scoring:** Likelihood (1–5) × Impact (1–5). A score of 1–5 is low, 6–11 medium, 12 or more high.
- **Escalation:** impact 5 (data loss, personal data exposure, cost over the hard cap) is escalated whatever the score.

Last reviewed: 2026-11-06

| ID | Type | Description | Impact | Likelihood | Owner | Mitigation | Trigger | Status | Date |
|---|---|---|---|---|---|---|---|---|---|
| R1 | R | Because the phone screen is Nov 16, an incomplete build would be presented as finished | 4 | 3 | TPM | Levels 0–3 local first; deploy Nov 13–14; Nov 15 buffer; say "in progress" if it is | Levels 1–3 not green by 2026-11-08 | Open | 2026-11-06 |
| R2 | R | Because the deadline is local time (06:00 CT), a UTC-only clock alerts an hour off after daylight saving changes | 3 | 3 | Data engineering | Deadline stored as local time + IANA zone in `config/settings.yaml`; tests for CST and CDT; schedules in EventBridge Scheduler with a time zone | SLA-clock test fails for a CDT date | Open | 2026-11-06 |
| R3 | R | Because QuickSight pricing and trial terms change, the dashboard could push the cost toward the cap | 3 | 2 | TPM | HTML scorecard built first; check price on deploy day; delete the subscription the same day | Price check shows > $2 incremental | Open | 2026-11-06 |
| R4 | R | Because the TPAs could fight over thresholds, enforcing too early creates false rejections and alert fatigue | 3 | 3 | Claims-ops lead | Warn-only phase per TPA; go/no-go gate before reject; thresholds in config | > 2 alerts per TPA per day in warn-only, or a reject the TPA disputes | Open | 2026-11-06 |
| R5 | R | Because the Lambda concurrency limit of this account is 10 (learned in the AP project), a 90-file backfill could throttle | 2 | 3 | Data engineering | Async invocation retries; backfill paced in the simulator upload; throttles counted, not treated as failures | Throttles > 0 with any file left unvalidated after 15 min | Open | 2026-11-06 |
| R6 | R | Because SNS email delivery is not guaranteed (learned in the AP project), an alert could be lost | 3 | 2 | Data engineering | Every alert also recorded in the ledger and logs; durable SQS subscriber listed as next version | A test publish not received within 5 min | Open | 2026-11-06 |
| R7 | R | Because the demo deploys real resources, leftovers could keep billing | 5 | 1 | TPM | Destroy, clean Glue logs and leftovers check after every window; schedules created disabled; tag `Project` | `make leftovers` lists anything | Open | 2026-11-06 |
| A1 | A | The simulated volumes (~2,500 rows/day, 3 TPAs, 30 days) are realistic enough to show the mechanism | 2 | 2 | TPM | State volumes honestly in the README; never claim production scale | A reviewer asks about scale: answer with the design limits | Open | 2026-11-06 |
| A2 | A | The ODCS v3 field names in `docs/data-contract.yaml` are current | 2 | 3 | TPM | Check against the current ODCS spec before publishing | Spec check at level 2 shows a renamed key | Open | 2026-11-06 |
| D1 | D | Each TPA signs the contract before its feed moves from warn-only to enforce (simulated sign-off) | 4 | 2 | TPA ops (each) | Contract sent with a 30-day notice clause; sign-off recorded in the change log | No sign-off recorded at the go/no-go gate | Open | 2026-11-06 |
| D2 | D | AWS account access for the deploy window (CLI user, root console for screenshots only) | 4 | 1 | TPM | Same setup as the AP project, verified on 2026-11-05 | `aws sts get-caller-identity` fails on deploy day | Open | 2026-11-06 |

## Contingency (for triggered risks)
| ID | Contingency run | Date | Outcome |
|---|---|---|---|
| | | | |
