"""Simulate one TPA's claim portfolio and the transactions it reports each business day.

The business story behind the numbers:
    Every van accident becomes a claim. The TPA opens it at first notice of loss (FNOL) with an
    initial reserve (its estimate of what the claim will cost), then pays bills, revises the
    reserve, sometimes recovers money from the other driver's insurer, and finally closes the
    claim (or denies it, or reopens it later). Each of those events is one row of the daily file.

What this module does NOT do: plant defects (src/generators/defects.py) or write files
(src/generators/feed_files.py). Every row produced here is clean: it passes the contract.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from itertools import count
from typing import Any

from src.common.business_calendar import local_datetime
from src.common.vin import make_vin

# Spread of the log-normal payment curve: 0.8 gives many small bills and a few large ones
PAYMENT_SPREAD = 0.8
# A reserve change is usually larger than a single payment (it covers the rest of the claim)
RESERVE_TO_PAYMENT_RATIO = 1.5
# Recoveries bring back part of what was paid, so they are smaller than payments
RECOVERY_TO_PAYMENT_RATIO = 0.5
# Share of reserve changes that INCREASE the reserve (the rest decrease it)
RESERVE_INCREASE_SHARE = 0.75
# What a status change does to an open claim: close it most of the time, sometimes deny it
CLOSE_SHARE_OF_STATUS_CHANGES = 0.85
# Share of status changes that reopen a closed claim instead of acting on an open one
REOPEN_SHARE_OF_STATUS_CHANGES = 0.10


@dataclass
class Claim:
    """One claim as the TPA tracks it (only the fields the daily file needs)."""

    claim_id: str  # Northbridge's claim number
    tpa_claim_ref: str  # the TPA's own claim number
    coverage: str
    loss_date: date
    report_date: date
    vin: str
    status: str = "OPEN"


def build_fleet(rng: random.Random, fleet_cfg: dict[str, Any]) -> list[str]:
    """Generate the VINs of every leased van (each with a valid check digit).

    Args:
        rng: The seeded random generator.
        fleet_cfg: master_data.yaml -> fleet (size, manufacturer codes, model years).

    Returns:
        One VIN per van.
    """
    # A mixed fleet: each van gets a random manufacturer and model year from the master data
    return [
        make_vin(rng, rng.choice(fleet_cfg["manufacturer_codes"]), rng.choice(fleet_cfg["model_years"]))
        for _ in range(fleet_cfg["size"])
    ]


def money(value: float) -> str:
    """Format an amount as the contract requires: decimal with 2 places, never scientific notation."""
    return f"{value:.2f}"


@dataclass
class ClaimPortfolio:
    """The claims one TPA handles, and the transactions it records on each business day.

    Attributes:
        tpa: The TPA's entry in master_data.yaml -> tpas.
        coverages: master_data.yaml -> coverages.
        transaction_types: master_data.yaml -> transaction_types (type -> weight).
        fleet: The VINs of the vans.
        sim: settings.yaml -> simulation.
        timezone: The TPA works in Central Time (calendar.timezone).
        rng: The seeded random generator shared by the whole simulation.
        claim_numbers: Northbridge's claim counter, shared by the three TPAs so IDs never collide.
        claim_id_prefix: master_data.yaml -> company.claim_id_prefix.
    """

    tpa: dict[str, Any]
    coverages: list[dict[str, Any]]
    transaction_types: dict[str, float]
    fleet: list[str]
    sim: dict[str, Any]
    timezone: str
    rng: random.Random
    claim_numbers: count
    claim_id_prefix: str
    open_claims: list[Claim] = field(default_factory=list)
    closed_claims: list[Claim] = field(default_factory=list)
    _tpa_refs: count = field(default_factory=lambda: count(10_001))

    def new_claim(self, report_date: date) -> Claim:
        """Open a claim reported on `report_date` (its loss happened a few days earlier).

        Args:
            report_date: When the incident was reported to the TPA.

        Returns:
            The new open claim (already added to the portfolio).
        """
        # Pick the coverage line by its share of claims
        coverage = self.rng.choices(self.coverages, weights=[c["weight"] for c in self.coverages])[0]["code"]
        # The accident happened 0 to N days before it was reported
        loss_date = report_date - timedelta(days=self.rng.randint(0, self.sim["max_report_lag_days"]))
        claim = Claim(
            claim_id=f"{self.claim_id_prefix}-{next(self.claim_numbers):06d}",
            tpa_claim_ref=f"{self.tpa['claim_ref_prefix']}-{next(self._tpa_refs)}",
            coverage=coverage,
            loss_date=loss_date,
            report_date=report_date,
            vin=self.rng.choice(self.fleet),
        )
        self.open_claims.append(claim)
        return claim

    def seed_portfolio(self, first_business_date: date, size: int) -> None:
        """Create the claims already open on day 1, reported over the previous months.

        Args:
            first_business_date: The first simulated business date.
            size: How many claims are open at the start.
        """
        # Report dates spread over the portfolio's age, always before the first simulated day
        for _ in range(size):
            age_days = self.rng.randint(1, self.sim["portfolio_age_days"])
            self.new_claim(first_business_date - timedelta(days=age_days))

    def _payment_size(self, coverage: str) -> float:
        """A typical bill for the coverage line, drawn from a log-normal curve around its median."""
        median = next(c["payment_median"] for c in self.coverages if c["code"] == coverage)
        return median * math.exp(self.rng.gauss(0, PAYMENT_SPREAD))

    def _as_of(self, business_date: date) -> str:
        """When the TPA extracted the row: evening of the business date, ISO 8601 with the UTC offset."""
        # Random minute inside the extract window, written in Chicago time with its offset (-05:00 or -06:00)
        start, end = self.sim["extract_window_local"]
        first = local_datetime(business_date, start, self.timezone)
        last = local_datetime(business_date, end, self.timezone)
        moment: datetime = first + timedelta(seconds=self.rng.randint(0, int((last - first).total_seconds())))
        return moment.isoformat(timespec="seconds")

    def _row(
        self, claim: Claim, business_date: date, transaction_id: str, kind: str, paid: float, reserve: float
    ) -> dict[str, Any]:
        """Assemble one file row in the contract's column names (the VIN is blanked later, per file)."""
        return {
            "transaction_id": transaction_id,
            "tpa_claim_ref": claim.tpa_claim_ref,
            "claim_id": claim.claim_id,
            "loss_date": claim.loss_date.isoformat(),
            "report_date": claim.report_date.isoformat(),
            "transaction_date": business_date.isoformat(),
            "transaction_type": kind,
            "coverage": claim.coverage,
            "claim_status": claim.status,
            "paid_amount": money(paid),
            "reserve_amount": money(reserve),
            "currency": "USD",
            "vin": claim.vin,
            "as_of_ts": self._as_of(business_date),
        }

    def _status_change(self, business_date: date, transaction_id: str) -> dict[str, Any]:
        """Close, deny or reopen a claim, and report the new status (no money moves)."""
        # Sometimes a closed claim comes back (new medical bills, a lawsuit): reopen it
        if self.closed_claims and self.rng.random() < REOPEN_SHARE_OF_STATUS_CHANGES:
            claim = self.closed_claims.pop(self.rng.randrange(len(self.closed_claims)))
            claim.status = "REOPENED"
            self.open_claims.append(claim)
        else:
            # Otherwise an open claim is settled (closed) or rejected (denied)
            claim = self.open_claims.pop(self.rng.randrange(len(self.open_claims)))
            claim.status = "CLOSED" if self.rng.random() < CLOSE_SHARE_OF_STATUS_CHANGES else "DENIED"
            self.closed_claims.append(claim)
        return self._row(claim, business_date, transaction_id, "STATUS_CHANGE", 0.0, 0.0)

    def day_rows(self, business_date: date, row_count: int) -> list[dict[str, Any]]:
        """All the transactions the TPA records on one business date.

        Args:
            business_date: The date the file covers.
            row_count: How many transactions the file will have.

        Returns:
            The rows, in the order the TPA's system would export them.
        """
        rows: list[dict[str, Any]] = []
        prefix = f"{self.tpa['transaction_prefix']}-{business_date:%Y%m%d}"
        sequence = count(1)

        # 1. First notices of loss: each new claim starts with its initial reserve
        for _ in range(min(self.tpa["new_claims_per_day"], row_count)):
            claim = self.new_claim(business_date)
            reserve = self._payment_size(claim.coverage) * RESERVE_TO_PAYMENT_RATIO
            rows.append(self._row(claim, business_date, f"{prefix}-{next(sequence):06d}", "RESERVE_CHANGE", 0, reserve))

        # 2. The rest of the day: payments, reserve changes, recoveries and status changes on existing claims
        kinds, weights = zip(*self.transaction_types.items(), strict=True)
        while len(rows) < row_count:
            kind = self.rng.choices(kinds, weights=weights)[0]
            transaction_id = f"{prefix}-{next(sequence):06d}"
            if kind == "STATUS_CHANGE":
                rows.append(self._status_change(business_date, transaction_id))
                continue
            # Money moves on open claims (recoveries can also arrive on closed ones)
            pool = self.open_claims + self.closed_claims if kind == "RECOVERY" else self.open_claims
            claim = self.rng.choice(pool)
            size = self._payment_size(claim.coverage)
            if kind == "PAYMENT":
                # A payment is positive and draws the reserve down by the same amount
                rows.append(self._row(claim, business_date, transaction_id, kind, size, -size))
            elif kind == "RECOVERY":
                # Money coming back is negative paid_amount (the contract's sign rule)
                rows.append(self._row(claim, business_date, transaction_id, kind, -size * RECOVERY_TO_PAYMENT_RATIO, 0))
            else:
                # A reserve change: up most of the time, down when the claim looks cheaper than expected
                sign = 1 if self.rng.random() < RESERVE_INCREASE_SHARE else -1
                rows.append(
                    self._row(claim, business_date, transaction_id, kind, 0, sign * size * RESERVE_TO_PAYMENT_RATIO)
                )

        # 3. The normal share of blank VINs (vehicle not yet identified): an EXACT number of rows per file,
        #    not a coin flip per row, so a clean file never drifts over the 2% limit by chance
        for row in self.rng.sample(rows, math.floor(len(rows) * self.sim["vin_blank_rate"])):
            row["vin"] = ""
        return rows
