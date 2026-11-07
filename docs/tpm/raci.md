# RACI: TPA claims feed contract and SLA monitor

> **Portfolio project.** One person plays several roles; they stay separate here to show how the work would split in a team.

**R** = does the work · **A** = answers for the result (exactly one per row) · **C** = consulted before · **I** = informed after.

| Activity | Claims-ops lead (sponsor) | Controller | TPM / program owner | Data engineering | TPA ops (producer) | TPA account manager | Security |
|---|---|---|---|---|---|---|---|
| Approve PR/FAQ and charter | A | C | R | C | I | C | I |
| Define KPIs, thresholds and the SLA | A | C | R | C | C | C | I |
| Agree the data contract (per TPA) | C | I | R | C | A | C | C |
| Build the simulator, checker and SLA clock | I | I | C | A/R | I | I | I |
| Build the arrival ledger, alerts and row-level DQ | I | I | C | A/R | I | I | C |
| Access and privacy review (no personal data, least privilege) | I | I | R | C | I | I | A |
| Grade detection against the answer key | I | I | C | A/R | I | I | I |
| Go / no-go: warn-only → enforce, per TPA | A | C | R | C | C | C | C |
| Resend a corrected file after a rejection | I | I | I | I | A/R | C | I |
| Escalate a repeated SLA breach to the TPA review | C | I | R | I | I | A | I |
| Decide whether month-end accruals can use the data | C | A/R | C | C | I | I | I |
| Run the runbook (alerts, reruns) | I | I | C | A/R | I | I | I |
| Weekly status report and RAID review | I | I | A/R | C | I | I | I |
| Write the COE for a contract breach | I | I | A/R | R | C | C | I |

## Checks
- [x] Every row has exactly **one** A.
- [x] Every A row has someone who does the work (an R, or A/R).
- [x] No column is C on everything.
- [x] Every role appears in [charter.md](charter.md), section 9.

## Notes
- **The TPA is accountable for its own contract and its resends.** The program owner writes and maintains the contract (steward) but cannot accept it on the TPA's behalf.
- **Security has a veto** on any new column that could carry personal data.
- **The controller, not the program, decides** whether the accrual uses the data. The monitor provides the signal.
