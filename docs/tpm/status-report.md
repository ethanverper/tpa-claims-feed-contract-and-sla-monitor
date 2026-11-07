# Weekly status report: {{PROJECT_NAME}}

<!--
TEMPLATE: copy this file for each week (e.g. docs/tpm/status/2026-W45.md) or append new weeks at the top.
Rules:
- Put the BOTTOM LINE in the first line. A busy reader stops after two lines.
- Say what changed since last week, not everything you did.
- Every risk has an owner and a date. Every ask names a person and a deadline.
- A status report is a tool for asking: end with asks and decisions needed.
- Keep it to one page. Delete these comments.
-->

**Week ending:** {{YYYY-MM-DD}}  **Author:** {{name}}

## Overall status: {{GREEN | AMBER | RED}}  (last week: {{GREEN | AMBER | RED}})

**Bottom line:** {{One sentence. What is the state, and what must happen for the date to hold? e.g. "On track for deploy on {{date}} provided the reference table arrives by {{date}}."}}

### RAG definitions
| Color | Meaning | What it triggers |
|---|---|---|
| **GREEN** | On track: milestones on date, no unresolved risk above score 12 | Nothing needed |
| **AMBER** | At risk: a milestone slips ≤ 1 week, or a risk is triggered but has a contingency | Mitigation plan in this report; ask for help if needed |
| **RED** | Off track: the date, the scope or the cost cap will be missed without a decision | Escalation, a decision from the sponsor, options with dates |

## Progress this week
- {{Completed item, with evidence (link, test result, number)}}
- {{Completed item}}

## Milestones
| # | Milestone | Planned | Forecast | Status | Note |
|---|---|---|---|---|---|
| M1 | PR/FAQ and spec agreed | {{date}} | {{date}} | {{G/A/R}} | |
| M2 | Data contract signed | {{date}} | {{date}} | {{G/A/R}} | |
| M3 | Built and tested locally | {{date}} | {{date}} | {{G/A/R}} | |
| M4 | Deployed, data reconciled | {{date}} | {{date}} | {{G/A/R}} | |

## Metrics
<!-- Input metrics first (what we control), then output metrics. Same metrics every week so the trend is visible. -->
| Metric | Target | This week | Last week | Trend |
|---|---|---|---|---|
| {{Input: e.g. Files delivered on time}} | {{value}} | {{value}} | {{value}} | {{up/down/flat}} |
| {{Input: e.g. Records passing validation}} | {{value}} | {{value}} | {{value}} | |
| {{Output: e.g. KPI reconciliation difference}} | {{value}} | {{value}} | {{value}} | |
| Cost to date (cap $3) | < $1 | ${{x.xx}} | ${{x.xx}} | |

## Risks (top 3, from [raid-log.md](raid-log.md))
| ID | Risk | Score | Owner | Next step | Due |
|---|---|---|---|---|---|
| {{R1}} | {{risk}} | {{L×I}} | {{owner}} | {{step}} | {{date}} |

## Asks
<!-- Specific, with a person and a date. If you have no asks, ask yourself whether the report is honest. -->
1. {{Person/role}}: {{what you need}} by {{date}}. Without it: {{consequence}}.

## Decisions needed
| Decision | Options | Recommendation | Needed by |
|---|---|---|---|
| {{decision}} | {{A / B}} | {{A, because...}} | {{date}} |

## Decisions made this week
- {{decision}} → recorded in `docs/decisions.md` as ADR-{{NNN}}

## Next week
- {{planned item}}
