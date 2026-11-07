# Lessons learned

Decisions that changed because of evidence, while building this project. Each entry: what we assumed, what the data showed, what we changed, and the measured result.

## 1. Check the synthetic data against the business before trusting it
- **Assumption:** the fleet of about 3,500 vans in the first draft of the spec, with the volumes the backlog fixed (about 2,500 claim transactions per business day across three TPAs), and payment sizes typical of a whole claim.
- **What the data showed:** the first full simulation paid **$2.3 million per day through one TPA alone**. For 3,500 vans that is roughly $580 million a year, or $165,000 per van: no fleet operator pays that. Two inputs disagreed with each other. 145 new claims per business day means about 36,000 claims a year, which only fits a fleet ten times bigger. And the payment sizes described a whole claim, while each row is one bill (a tow, a rental, one medical invoice).
- **Why it matters:** an interviewer or a finance reader checks the order of magnitude first. A number that is off by 10× makes every other number on the page look invented, including the ones that are right.
- **Change:**
  - the fleet is **35,000 vans** (about 1 claim per van per year);
  - payment medians are sized per bill (`config/master_data.yaml` -> `coverages`);
  - the spec, the PR/FAQ and the README were corrected in the same commit.
- **Result:** the three TPAs now pay about **$1.4 million per business day** together, roughly $10,000 per van per year. The KPI threshold of "$50,000 quarantined in one day" now reads as a real signal instead of noise.
- **Takeaway:** a simulator is a model of the business, so it needs the same sanity check as a forecast. Before building on it, compute one or two totals (per day, per unit, per year) and compare them with what a person in the business would expect.

## 2. A defect rate drawn row by row breaks the contract by chance
- **Assumption:** blanking each VIN with a 0.8% probability gives every clean file about 0.8% blank VINs, safely under the contract's 2% limit.
- **What the data showed:** a small test file of 41 rows came out with **4 blank VINs (9.8%)**. Drawing row by row is a coin flip per row, so the count per file varies. With small files, or enough of them, a clean file crosses the limit just by chance. The checker would then flag it, and grading would count a **false alarm the simulator created**, not the monitor.
- **Why it matters:** the answer key must be exact. If clean files can break a rule, "0 false alarms" can never be proven, and a real false alarm cannot be told apart from noise in the generator.
- **Change:** the simulator now blanks an **exact number** of VINs per file (`floor(rows × vin_blank_rate)`), chosen at random. A test asserts that every clean file stays at or under 2%.
- **Result:** the highest blank-VIN share in any clean file is now **0.80%** (full run, 90 files). Only the 7 planted completeness-drift files exceed the limit, at 18%.
- **Takeaway:** when synthetic data must stay on the right side of a threshold, control the count, not only the probability. Keep randomness in *which* rows are affected, not in *how many*.
