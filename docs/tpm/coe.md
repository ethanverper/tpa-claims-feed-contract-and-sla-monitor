# Correction of Error (COE): {{SHORT TITLE OF THE FAILURE}}

<!--
TEMPLATE: a blameless write-up after a real failure (a failed deploy, wrong KPI, data loss, a cost overrun). Write it
within a few days while details are fresh. Rules:
- No names are blamed. Corrective actions fix MECHANISMS (a check, an alarm, a contract rule), not people.
- Impact is in numbers (records, dollars, hours, minutes to detect).
- The 5 Whys stop at a missing or weak mechanism, not at "someone made a mistake".
- Every corrective action has an owner, a due date and a metric showing it worked.
- Record the same finding in docs/lessons-learned.md and, if a choice changed, in docs/decisions.md.
- Delete these comments. Keep to 1–2 pages.
-->

**Date of incident:** {{YYYY-MM-DD}}  **Author:** {{name}}  **Status:** Draft | Reviewed  **Severity:** {{1–3}}

## 1. Summary
<!-- Three sentences: what happened, how it was found, the impact in numbers. -->
{{...}}

## 2. Impact
| Dimension | Measure |
|---|---|
| Records / data affected | {{count or %}} |
| Business effect | {{e.g. KPI wrong by $X for N hours; deploy window lost}} |
| Cost | {{$ extra, vs cap}} |
| Time to detect | {{minutes/hours from start to first signal}} |
| Time to resolve | {{minutes/hours from first signal to fix}} |

## 3. Timeline
<!-- Time-stamped events from the first signal to resolution. Include the detection time and the decision points. -->
| Time (UTC) | Event |
|---|---|
| {{hh:mm}} | {{first signal / change that started it}} |
| {{hh:mm}} | {{detected by: alarm / person / test}} |
| {{hh:mm}} | {{action taken}} |
| {{hh:mm}} | {{resolved / verified}} |

## 4. Root cause (5 Whys)
<!-- Ask why until you reach a missing or weak mechanism. Five is a guide, not a rule. -->
1. **Why** did {{the visible problem}} happen? Because {{...}}
2. **Why** {{...}}? Because {{...}}
3. **Why** {{...}}? Because {{...}}
4. **Why** {{...}}? Because {{...}}
5. **Why** {{...}}? Because {{missing or weak mechanism}}

**Root cause:** {{one sentence}}

## 5. What went well
- {{e.g. The alarm fired within 2 minutes}}
- {{e.g. Idempotent load made the rerun safe}}

## 6. What went poorly
- {{e.g. No test for this case}}
- {{e.g. Runbook did not cover it}}

## 7. Corrective actions
| # | Action | Fixes (mechanism) | Owner | Due | Metric that shows it worked | Status |
|---|---|---|---|---|---|---|
| 1 | {{e.g. Add contract rule for X}} | Prevent | {{owner}} | {{date}} | {{e.g. 0 rows with X in 14 days}} | Open |
| 2 | {{e.g. Add alarm on Y}} | Detect | {{owner}} | {{date}} | {{e.g. detect < 5 min}} | Open |
| 3 | {{e.g. Add runbook entry}} | Respond | {{owner}} | {{date}} | {{e.g. second person resolves in 1 try}} | Open |

## 8. Lessons
<!-- What changes in the checklist, the runbook, the data contract or the standards. Link the updates. -->
- {{lesson}} → updated {{docs/runbook.md / docs/data-contract.yaml / docs/tpm/go-no-go.md}}
