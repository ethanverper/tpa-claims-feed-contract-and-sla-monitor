"""Load the project's central configuration files (config/settings.yaml, config/master_data.yaml).

Why this module exists:
    Every tunable value (thresholds, simulation parameters, AWS sizing) and all master data live
    in the config/ folder, so nobody has to hunt through modules to change a rule. This module is
    the only place that reads those files; every other module asks it.

Where it is used:
    Code that runs locally (generators, scripts). Code that runs in AWS (Lambda, Glue) does not
    read YAML: Terraform reads the same files and passes the values as environment variables or
    job arguments, which those components read through src/common/config.py.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

# Repository root: src/common/settings.py -> three levels up
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


@cache
def load_yaml(file_name: str) -> dict[str, Any]:
    """Read and parse one YAML file from config/, once per process.

    Args:
        file_name: File name inside config/, e.g. "settings.yaml".

    Returns:
        The parsed content as nested dicts and lists.

    Raises:
        FileNotFoundError: If the file doesn't exist (a broken checkout should fail loudly).
    """
    # safe_load builds only plain data types (never executes code embedded in the file)
    with (CONFIG_DIR / file_name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def settings() -> dict[str, Any]:
    """Return config/settings.yaml: thresholds, simulation and AWS sizing."""
    return load_yaml("settings.yaml")


def master_data() -> dict[str, Any]:
    """Return config/master_data.yaml: the project's reference data."""
    return load_yaml("master_data.yaml")


def data_contract() -> dict[str, Any]:
    """Return docs/data-contract.yaml, the agreement every TPA file is written and checked against.

    Why it is read here and not copied into settings.yaml:
        The contract is the single source of truth for column names, allowed values and limits.
        The simulator writes files from it and the checker (level 2) validates files against it,
        so the two can never disagree about what a good file looks like.
    """
    # The path to the contract is itself a setting, so a second contract version could be tested
    with (REPO_ROOT / settings()["contract"]["path"]).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def contract_table(name: str) -> dict[str, Any]:
    """Return one schema entry of the data contract (e.g. "claim_transactions" or "manifest").

    Args:
        name: The schema entry's `name` in docs/data-contract.yaml.

    Returns:
        The entry: physicalName, properties (columns) and quality rules.

    Raises:
        KeyError: If the contract has no entry with that name.
    """
    # Look the entry up by name, so the order of entries in the YAML does not matter
    for table in data_contract()["schema"]:
        if table["name"] == name:
            return table
    raise KeyError(f"The data contract has no schema entry named {name!r}")


def contract_columns(name: str) -> list[str]:
    """Return the column names of one contract entry, in the order the file must have them."""
    return [prop["name"] for prop in contract_table(name)["properties"]]
