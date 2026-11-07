"""Plant the defects the monitor must catch, and record each one in the answer key.

Why plant defects on purpose:
    "The checks look fine" is an opinion. Planting a known list of problems and grading the
    monitor against it (found vs planted, per defect type) turns detection into a number:
    recall (how many planted problems were found) and false alarms (clean rows flagged).

Two kinds of defect:
    - FILE level: the whole delivery is wrong (late, missing, renamed column, manifest that does
      not match, the same file twice, a week of blank VINs). Planted while building deliveries
      in src/generators/tpa_feed_simulator.py; this module only does the row edits they need.
    - ROW level: one row breaks a rule (bad currency, bad VIN, dates out of order, a repeated
      transaction_id, a payment with a negative sign). Planted here, only in files that are
      otherwise accepted, so a row defect is never hidden behind a rejected file.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from src.common.vin import break_check_digit

# A file is identified by (tpa_id, business_date); its rows are a list of dicts in file order
FileKey = tuple[str, date]

# The header is line 1 of every file, so the first data row is line 2
FIRST_DATA_LINE = 2
# How far loss_date is pushed after report_date when that defect is planted (days)
MAX_LOSS_AFTER_REPORT_DAYS = 5


@dataclass(frozen=True)
class RowDefect:
    """One planted row-level problem: where it is and what the monitor should do with it."""

    tpa_id: str
    business_date: str
    line_number: int  # line in the data file (header = line 1)
    transaction_id: str
    defect: str  # e.g. INVALID_CURRENCY
    expected_detection: str  # what the monitor must do: always quarantine the row
    detail: str

    def as_dict(self) -> dict[str, Any]:
        """The record as a plain dict, ready for the answer-key CSV."""
        return asdict(self)


def blank_vins(rows: list[dict[str, Any]], target_rate: float, rng: random.Random) -> int:
    """Blank the VIN on enough rows to reach `target_rate` (the completeness-drift defect).

    Args:
        rows: The rows of one file (edited in place).
        target_rate: Share of rows that should end up with a blank VIN, e.g. 0.18.
        rng: The seeded random generator.

    Returns:
        How many rows have a blank VIN after the edit.
    """
    # Count what is already blank, then blank random filled ones until the target is reached
    target = round(len(rows) * target_rate)
    filled = [row for row in rows if row["vin"]]
    already_blank = len(rows) - len(filled)
    for row in rng.sample(filled, max(0, target - already_blank)):
        row["vin"] = ""
    return sum(1 for row in rows if not row["vin"])


class RowDefectPlanter:
    """Plants row-level defects in a set of eligible files, one defect per row at most.

    Why one defect per row: if a row had two problems, the grading could not tell which rule
    caught it. Rows that are the FIRST occurrence of a duplicated transaction_id are also
    protected, so the original stays clean and only the second occurrence is the defect.
    """

    def __init__(self, files: dict[FileKey, list[dict[str, Any]]], eligible: list[FileKey], rng: random.Random):
        """Prepare the pool of rows that may receive a defect.

        Args:
            files: Every file's rows, by (tpa_id, business_date). Edited in place.
            eligible: The files that will be accepted, in business-date order.
            rng: The seeded random generator.
        """
        self.files = files
        self.eligible = eligible
        self.rng = rng
        self.used: set[tuple[FileKey, int]] = set()  # (file, row index) already edited or protected
        self.defects: list[RowDefect] = []

    def _pick(self, condition=lambda row: True, keys: list[FileKey] | None = None) -> tuple[FileKey, int]:
        """A random unused row (in the given files) that satisfies `condition`.

        Raises:
            RuntimeError: If no row qualifies, so a wrong configuration fails loudly instead of planting fewer.
        """
        pool = keys or self.eligible
        # Try random rows first (fast), then fall back to a full scan before giving up
        for _ in range(1000):
            key = self.rng.choice(pool)
            index = self.rng.randrange(len(self.files[key]))
            if (key, index) not in self.used and condition(self.files[key][index]):
                return key, index
        candidates = [
            (key, i)
            for key in pool
            for i, row in enumerate(self.files[key])
            if (key, i) not in self.used and condition(row)
        ]
        if not candidates:
            raise RuntimeError("No eligible row left for a planted defect: lower the counts in settings.yaml")
        return self.rng.choice(candidates)

    def _record(self, key: FileKey, index: int, defect: str, detail: str) -> None:
        """Mark the row as used and write the answer-key record."""
        self.used.add((key, index))
        row = self.files[key][index]
        self.defects.append(
            RowDefect(
                tpa_id=key[0],
                business_date=key[1].isoformat(),
                line_number=index + FIRST_DATA_LINE,
                transaction_id=row["transaction_id"],
                defect=defect,
                expected_detection="QUARANTINE_ROW",
                detail=detail,
            )
        )

    def invalid_currency(self, count: int, values: list[str]) -> None:
        """Rows whose currency is not an ISO 4217 code, e.g. "US$" (validity rule)."""
        for _ in range(count):
            key, index = self._pick()
            value = self.rng.choice(values)
            self.files[key][index]["currency"] = value
            self._record(key, index, "INVALID_CURRENCY", f"currency={value}")

    def bad_vin_check_digit(self, count: int) -> None:
        """Rows whose VIN fails the check digit: a keying error at the TPA (validity rule)."""
        for _ in range(count):
            # Only rows that have a VIN can carry a wrong one
            key, index = self._pick(lambda row: bool(row["vin"]))
            row = self.files[key][index]
            row["vin"] = break_check_digit(row["vin"])
            self._record(key, index, "BAD_VIN_CHECK_DIGIT", f"vin={row['vin']}")

    def loss_after_report(self, count: int) -> None:
        """Rows whose loss_date is after report_date: an accident reported before it happened (consistency)."""
        for _ in range(count):
            key, index = self._pick()
            row = self.files[key][index]
            report = date.fromisoformat(row["report_date"])
            row["loss_date"] = (report + timedelta(days=self.rng.randint(1, MAX_LOSS_AFTER_REPORT_DAYS))).isoformat()
            self._record(
                key, index, "LOSS_AFTER_REPORT", f"loss_date={row['loss_date']} report_date={row['report_date']}"
            )

    def negative_payment(self, count: int) -> None:
        """PAYMENT rows with a negative amount: the sign rule says payments are positive."""
        for _ in range(count):
            key, index = self._pick(lambda row: row["transaction_type"] == "PAYMENT")
            row = self.files[key][index]
            row["paid_amount"] = f"-{row['paid_amount']}"
            self._record(key, index, "NEGATIVE_PAYMENT", f"paid_amount={row['paid_amount']}")

    def duplicate_transaction_id(self, count: int, share_across_days: float) -> None:
        """Rows that reuse a transaction_id already sent by the same TPA (uniqueness rule).

        Two flavours, because a checker that only looks inside one file misses the second:
            - inside the same file (the TPA's export repeated an ID);
            - across days (an ID already received in an earlier file of the same TPA).
        """
        across_days = round(count * share_across_days)
        planted = 0
        while planted < count:
            if planted < across_days:
                # Second occurrence in a later file; first occurrence in an earlier file of the same TPA
                key, index = self._pick(lambda row: True, [k for k in self.eligible if self._has_earlier(k)])
                earlier = [k for k in self.eligible if k[0] == key[0] and k[1] < key[1]]
                first_key, first_index = self._pick(keys=earlier)
                where = f"first sent on {first_key[1].isoformat()}"
            else:
                # Second occurrence later in the same file
                key, index = self._pick(lambda row: True)
                choices = [i for i in range(index) if (key, i) not in self.used]
                if not choices:
                    # The row is at the top of the file (nothing before it): try another row
                    continue
                first_key, first_index = key, self.rng.choice(choices)
                where = f"first sent on line {first_index + FIRST_DATA_LINE} of the same file"
            # Copy the ID, protect the original row, record the duplicate
            self.files[key][index]["transaction_id"] = self.files[first_key][first_index]["transaction_id"]
            self.used.add((first_key, first_index))
            self._record(key, index, "DUPLICATE_TRANSACTION_ID", where)
            planted += 1

    def _has_earlier(self, key: FileKey) -> bool:
        """True when the same TPA has an eligible file on an earlier business date."""
        return any(k[0] == key[0] and k[1] < key[1] for k in self.eligible)

    def plant_all(self, config: dict[str, Any]) -> list[RowDefect]:
        """Plant every row defect listed in settings.yaml -> defects.row_defects.

        Args:
            config: The row_defects section of settings.yaml.

        Returns:
            The answer-key records, one per planted row.
        """
        # The duplicate IDs go first, so their protected originals are never edited by another defect
        self.duplicate_transaction_id(**config["duplicate_transaction_id"])
        self.invalid_currency(**config["invalid_currency"])
        self.bad_vin_check_digit(**config["bad_vin_check_digit"])
        self.loss_after_report(**config["loss_after_report"])
        self.negative_payment(**config["negative_payment"])
        return self.defects
