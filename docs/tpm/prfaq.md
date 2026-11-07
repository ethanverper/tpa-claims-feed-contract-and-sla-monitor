# PR/FAQ: TPA claims feed contract and SLA monitor

> **Portfolio project.** Northbridge Logistics, its TPAs, the people quoted and every number are fictional or come from synthetic data.

**Status:** Approved (level 0)  **Author:** Ethan Verduzco (TPM)  **Date:** 2026-11-06

---

## Press release

### Claims data you can trust by 07:00 every day

**Chicago, IL, 2026-11-13** — Northbridge Logistics launches the TPA claims feed monitor: every morning, before 07:00, the claims team knows whether each of its three claims administrators delivered yesterday's claim transactions on time, complete and in the agreed format, and which administrator needs a conversation this week.

**The problem.** Northbridge's 3,500 delivery vans generate claims that three outside administrators (TPAs) handle and report back in daily files. Today nobody checks those files when they arrive. A late file, a renamed column or a week of blank vehicle numbers is found weeks later, when finance asks why the month-end claims accrual moved. By then the bad data is already in reserving, accruals and safety reports.

**The solution.** What a good file looks like is now written down as a data contract that both sides agreed to. Every file is checked against it the moment it lands. Bad files are set aside with the exact rule they broke, bad rows are quarantined without blocking the good ones, and a missing file raises an alarm at 06:00 even though nothing arrived. Each TPA gets a daily scorecard.

**Customer quote.** "On Monday I used to ask finance which TPA had caused trouble. Now I open the scorecard and the agenda for the TPA review writes itself." — Claims-operations lead *(fictional; portfolio project)*

**How it works.** Each administrator drops one file per day with a small receipt listing its row count and total paid. The monitor checks the file against the contract, records when it arrived, and checks every row for blanks, invalid values and duplicates. Results land in a scorecard per administrator: on-time delivery, completeness, files accepted and dollars quarantined.

**Getting started.** The claims-operations lead receives the 07:00 digest and the Monday scorecard by email; the TPA operations contact receives an alert within minutes of any rejected or missing file.

---

## External FAQ (customer questions)

**1. Who is this for, and who is it not for?**
For the claims-operations lead, the controller, the TPA account manager and each TPA's operations contact. It is not a claims system or a reserving tool: it watches the data that feeds them.

**2. What decision can I make with it that I could not before?**
Which TPA gets a remediation conversation this week (claims operations), and whether the month-end accrual can use the TPA data as delivered (controller).

**3. How fresh is the data, and how accurate?**
Each file is checked within 10 minutes of arrival. The scorecard is published by 07:00 CT. Row counts and the paid total must match the receipt exactly; a file that does not match is rejected, never partly loaded.

**4. How do I know when something is wrong?**
- A file is missing at 06:00 CT: warning to the TPA operations contact.
- Still missing at 08:00 CT: critical alert to the program owner and the TPA account manager.
- A file is rejected: immediate alert listing the rules it broke.
- Quality warnings: rolled into one daily digest, so nobody gets twenty emails.

**5. What does it NOT do?**
It does not fix a TPA's data, change claim amounts or replace the TPA review. See the non-goals in [charter.md](charter.md).

**6. Is my data safe?**
The feed carries no claimant names, addresses or medical details; the contract forbids them. Files are encrypted at rest, only reachable over HTTPS, and the bucket is private. Everything is deleted after the demo.

**7. What if a TPA changes its file layout?**
The contract requires 30 days' written notice. An unannounced change is rejected on arrival, the TPA is told which column changed, and a COE is opened. Nothing silently loads into the wrong column.

---

## Internal FAQ (stakeholder and engineering questions)

**1. Why this problem, why now?**
Simulated baseline: in a 30-day month the three TPAs send 90 files. In that month, 3 arrived late, 1 never arrived on time, 2 changed layout without notice and 7 had 18% blank VINs, and none of it was detected at the time. Every week of silence pushes the problem into the month-end close.

**2. How will we know it worked? (success metrics)**
- **Output:** 100% of planted file and row defects detected (graded against the answer key) with 0 false alarms on clean rows.
- **Input:** time to detect a missing file ≤ 15 minutes after the deadline; file validation result ≤ 10 minutes after arrival; scorecard published by 07:00 CT.

See [charter.md](charter.md).

**3. What is the cost?**
About $0.30 to deploy, prove and destroy in one window of at most 2 hours, without QuickSight (hard cap $3). The cost of not doing it is a month-end accrual built on unchecked data.

**4. What are the biggest risks, and what is the trigger for each?**
- Time pressure before Nov 16: trigger is levels 1–3 not done by Nov 8.
- Daylight-saving errors in the deadline: trigger is an SLA-clock test failing in CDT.
- QuickSight cost or terms: trigger is the price check on deploy day.

See [raid-log.md](raid-log.md).

**5. What are the key design choices and the alternatives you rejected?**
- File drop vs API pull: file drop.
- Reject vs warn: per rule, written in the contract.
- EventBridge vs S3-to-Lambda notification: EventBridge, because it also runs the "file did not arrive" schedule.
- DynamoDB ledger vs S3 listing: DynamoDB, for conditional writes.

These are recorded as ADRs in `docs/decisions.md` from level 1.

**6. What is the data contract, and who owns each source?**
[../data-contract.yaml](../data-contract.yaml): 14 columns, a manifest per file, the quality rules and the SLA. Each TPA owns its feed; the program owner (TPM) is the contract steward.

**7. What is the rollout plan, and how do we roll back?**
- **Phase 1:** TPA-A runs in warn-only mode.
- **Phase 2:** TPA-A moves to enforcement. Then TPA-B, then TPA-C.
- **Gates:** each switch from warn to reject passes the checklist in `go-no-go.md`.
- **Rollback:** set the TPA back to warn-only in `config/settings.yaml`; nothing is deleted.

**8. What would make us stop?**
- Grading below 100% recall on file-level defects after two fixes.
- The demo cost forecast going over $3.
- Levels 1–3 not running locally by Nov 12: then we present the local version only, honestly labelled.

**9. What are we deliberately not building?**
A real SFTP server, a claims warehouse, reserving models, a TPA-facing portal.

**10. What is the next version?**
- API pulls for TPAs that offer them.
- Contract-change requests as pull requests.
- A durable alert queue (SQS) behind SNS email.
