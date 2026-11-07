# Go / no-go checklist: {{PROJECT_NAME}}

<!--
TEMPLATE: the launch decision, written as numbers. Rules:
- Write the thresholds BEFORE testing starts. Never move a threshold to make a test pass; if one was wrong, record
  why in docs/lessons-learned.md and docs/decisions.md.
- Every criterion has a threshold, a way to measure it, an owner and a result. "Looks good" is not a result.
- One failed criterion = NO-GO, unless the owner signs an explicit, dated exception with a mitigation.
- In a portfolio project the "launch" is the ≤ 2 h deploy window. The checklist still applies, because it is how a
  real launch would be decided.
- Delete these comments. Replace thresholds with the project's own where the defaults do not fit.
-->

**Decision date:** {{YYYY-MM-DD}}  **Decision owner:** {{role}}  **TPM running the checklist:** {{name}}

## 1. Data correctness
| # | Criterion | Threshold | Measured by | Owner | Result | Pass? |
|---|---|---|---|---|---|---|
| 1 | All records accounted for | 100% in curated, quarantine or rejected list | Row count by key, source vs target, both directions | Data eng | | ☐ |
| 2 | Amounts tie to source control totals | Difference ≤ $0.01 per file | Sum of amount vs control total | Data eng | | ☐ |
| 3 | KPI reconciliation | KPI values equal an independent recomputation (tolerance: {{value}}) | `sql/` KPI query vs recompute script | Business owner | | ☐ |
| 4 | Duplicate rate | ≤ 0.1% (idempotent re-run adds 0 rows) | Re-run the load twice and compare counts | Data eng | | ☐ |
| 5 | Data contract rules pass | 100% of mandatory rules; completeness ≥ {{99.5}}% | Contract check on sample files ([data-contract.yaml](../data-contract.yaml)) | Data eng | | ☐ |
| 6 | Freshness | Data available within {{value}} of arrival | Arrival vs gold timestamp | TPM | | ☐ |

## 2. Operations
| # | Criterion | Threshold | Measured by | Owner | Result | Pass? |
|---|---|---|---|---|---|---|
| 7 | Every alarm tested | 100% of alarms fired once on purpose and reached the channel | Test log | Engineering | | ☐ |
| 8 | Every alarm has an owner | 100% | Alert table in README section 6 | TPM | | ☐ |
| 9 | Runbook ready | Every alarm has a runbook entry; a second person followed it once | `docs/runbook.md` | Engineering | | ☐ |
| 10 | Rollback rehearsed | Executed once end to end; time ≤ {{15}} min | Rehearsal record | Engineering | | ☐ |
| 11 | Teardown rehearsed | `make destroy` then `make leftovers` prints nothing | Command output | Engineering | | ☐ |

## 3. Cost and security
| # | Criterion | Threshold | Measured by | Owner | Result | Pass? |
|---|---|---|---|---|---|---|
| 12 | Cost check | Forecast < $1; hard cap $3; scheduled triggers disabled | `docs/spec.md` estimate vs Cost Explorer (tag `Project`) | TPM | | ☐ |
| 13 | Least-privilege IAM | No wildcard actions on data resources; role per component | IAM review | Security | | ☐ |
| 14 | Encryption and access | SSE on, TLS-only bucket policy, no public access | Terraform plan + checks | Security | | ☐ |
| 15 | Sensitive fields | Masked or excluded before the gold layer | Field list vs [lineage.md](../lineage.md) | Security | | ☐ |

## 4. Readiness
| # | Criterion | Threshold | Measured by | Owner | Result | Pass? |
|---|---|---|---|---|---|---|
| 16 | Open high-score risks | None with score ≥ 12 without a mitigation | [raid-log.md](raid-log.md) | TPM | | ☐ |
| 17 | Documentation | README sections filled; `docs/configuration.md` lets a stranger run it | Review | TPM | | ☐ |
| 18 | Tests and CI | `ruff`, `pytest`, `terraform fmt` all green | CI run | Engineering | | ☐ |

## 5. Decision
<!-- One line. Then the reasoning. If NO-GO: what must change, who owns it, the date of the next review. -->
**Decision:** ☐ GO  ☐ NO-GO  ☐ GO WITH EXCEPTION

**Rationale:** {{...}}

**Exceptions (each needs owner, mitigation and expiry date):**
| Criterion # | Why it is accepted | Mitigation | Owner | Expires |
|---|---|---|---|---|
| | | | | |

## 6. Sign-offs
| Role | Name | Decision | Date |
|---|---|---|---|
| Business owner | | GO / NO-GO | |
| Engineering | | GO / NO-GO | |
| Security | | GO / NO-GO | |
| TPM (runs the checklist) | | GO / NO-GO | |
