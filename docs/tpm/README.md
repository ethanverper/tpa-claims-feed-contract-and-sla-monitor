# Program management artifacts (TPM folder)

<!--
TEMPLATE: this folder ships with the project template. Copy it with the rest of the template, fill each file at the
level shown below, and delete any file that does not apply (say so in the table, do not leave an empty template).
Keep every document to one page. Put the bottom line first. Give every risk a date and an owner.
-->

This folder holds the **program management artifacts** of the project: the documents a Technical Program Manager (TPM) writes so that a data pipeline is delivered on a date, with owners, measurable launch criteria and a plan for when things go wrong. They sit next to the code on purpose: the repo shows how the work was *run*, not only how it was *coded*.

> **Portfolio work.** Every project in this repository is a portfolio project built to learn the domain and to show how I work. The company, the stakeholders, the dates and the numbers are invented or come from synthetic data. Nothing here is work experience or confidential information from an employer. Fill the templates with the same honesty: mark anything illustrative as `EXAMPLE`.

## The artifacts and when each one is filled

| File | What it answers | Filled when | Gate it supports |
|---|---|---|---|
| [prfaq.md](prfaq.md) | Would the customer want this? Why now? | Before `docs/spec.md` (working backwards) | "Worth building?" |
| [charter.md](charter.md) | What are we doing, for whom, and what are we *not* doing? | With `docs/spec.md`, before any code | "Scope, date and owners credible?" |
| [../data-contract.yaml](../data-contract.yaml) | What exactly is promised about the data, and who checks it? | Before the ingestion code (level: design) | "Data agreed and testable?" |
| [raci.md](raci.md) | Who does it, and who answers for it? | With the charter; update when roles change | Plan |
| [raid-log.md](raid-log.md) | What could go wrong, what do we assume, what blocks us? | Created with the charter; reviewed weekly | Every gate |
| [status-report.md](status-report.md) | Are we on track, and what do I need from you? | Weekly, from the first build level to launch | Weekly review |
| [../lineage.md](../lineage.md) | Where does each KPI number come from? | Alongside the transforms (silver/gold levels) | Design review, audit questions |
| [go-no-go.md](go-no-go.md) | Do the launch criteria hold? | Criteria written **before testing**; results filled at deploy | "Go or no-go?" |
| [coe.md](coe.md) | What broke, why, and what mechanism changes? | After any real failure during build or deploy | Learning |

Related documents that already exist in the template: `docs/spec.md` (business case, KPIs, cost), `docs/kpi-dictionary.md`, `docs/decisions.md` (ADRs), `docs/runbook.md`, `docs/lessons-learned.md`.

## How it maps to the project levels

| Level | TPM artifacts touched |
|---|---|
| 0. Business first | `prfaq.md`, `charter.md`, `raci.md`, first `raid-log.md` |
| 1. Data and design | `../data-contract.yaml`, `../lineage.md` (source and target columns), `decisions.md` |
| 2. Build (small levels) | `status-report.md` each week, `raid-log.md` reviewed each week |
| 3. Deploy window (≤ 2 h) | `go-no-go.md` (results), `runbook.md` |
| 4. Teardown and review | `coe.md` (only if something failed), `lessons-learned.md`, final `status-report.md` |

## Rules

1. **Write criteria before results.** The go/no-go thresholds and the data-contract rules are set before the tests run, never adjusted afterwards to make a test pass.
2. **One owner and one date** on every risk, action and decision. A risk without a trigger is a worry, not a mechanism.
3. **Numbers, not adjectives.** "Reconciliation difference under $0.01", not "data looks fine".
4. **Blameless.** Corrective actions fix mechanisms, not people.
5. **Honest labels.** Anything illustrative is marked `EXAMPLE`. Costs and results are the real ones from the deployed run (see the cost cap in `docs/spec.md`).
6. **English only**, short, one page per document.
