"""Vehicle identification numbers (VINs): build valid ones and check the check digit.

What a VIN is:
    A 17-character code stamped on every vehicle. Position 9 is a CHECK DIGIT computed from the
    other 16 characters, so a typo (one wrong character) is caught by arithmetic alone, the same
    idea as the last digit of a credit card number. The letters I, O and Q are never used, so
    they cannot be confused with 1 and 0.

Why it matters here:
    The contract says a non-blank VIN must have a valid check digit. A VIN that fails it points
    to a keying error at the TPA, so the row cannot be tied to the right van and is quarantined.

Used by: the simulator (to build the fleet) and, from level 2, the row checks.
"""

from __future__ import annotations

import random

# Every character allowed in a VIN: digits and letters except I, O and Q
VIN_ALPHABET = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"

# Each letter's numeric value in the check-digit formula (digits count as themselves)
TRANSLITERATION = {
    **{str(d): d for d in range(10)},
    **dict(zip("ABCDEFGH", range(1, 9), strict=True)),
    **dict(zip("JKLMN", range(1, 6), strict=True)),
    "P": 7,
    "R": 9,
    **dict(zip("STUVWXYZ", range(2, 10), strict=True)),
}

# The weight of each of the 17 positions; position 9 (the check digit itself) weighs 0
POSITION_WEIGHTS = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)

# Position 10 encodes the model year (protocol constant of the VIN standard)
MODEL_YEAR_CODES = {2021: "M", 2022: "N", 2023: "P", 2024: "R", 2025: "S", 2026: "T"}

VIN_LENGTH = 17
CHECK_DIGIT_INDEX = 8  # position 9, counted from 0


def check_digit(vin: str) -> str:
    """Compute the check digit a VIN must carry in position 9.

    Args:
        vin: A 17-character VIN (the current position 9 is ignored).

    Returns:
        "0".."9", or "X" when the remainder is 10.

    Raises:
        KeyError: If the VIN contains a character outside the VIN alphabet.
    """
    # Weighted sum of every character's value, then the remainder of dividing by 11
    total = sum(TRANSLITERATION[char] * weight for char, weight in zip(vin, POSITION_WEIGHTS, strict=True))
    remainder = total % 11
    # A remainder of 10 is written as "X" so the check digit stays one character
    return "X" if remainder == 10 else str(remainder)


def is_valid_vin(vin: str) -> bool:
    """True when the VIN has 17 allowed characters and a correct check digit.

    Args:
        vin: The value from the file (blank values are handled by the completeness rule, not here).

    Returns:
        Whether the VIN passes the structural and check-digit tests.
    """
    # Length and alphabet first: the check-digit formula only works on well-formed VINs
    if len(vin) != VIN_LENGTH or any(char not in VIN_ALPHABET for char in vin):
        return False
    # Then the arithmetic: the stored check digit must equal the computed one
    return vin[CHECK_DIGIT_INDEX] == check_digit(vin)


def make_vin(rng: random.Random, manufacturer_code: str, model_year: int) -> str:
    """Build a random but valid VIN for one van.

    Args:
        rng: The simulation's random generator (seeded, so the fleet is the same every run).
        manufacturer_code: The 3-character world manufacturer identifier, e.g. "1FT".
        model_year: Model year, encoded in position 10.

    Returns:
        A 17-character VIN whose check digit is correct.
    """
    # Positions 4-8: vehicle attributes (random here), position 9: placeholder for the check digit
    attributes = "".join(rng.choice(VIN_ALPHABET) for _ in range(5))
    # Positions 11-17: assembly plant letter and a 6-digit serial number
    plant = rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ")
    serial = f"{rng.randrange(1_000_000):06d}"
    draft = f"{manufacturer_code}{attributes}0{MODEL_YEAR_CODES[model_year]}{plant}{serial}"
    # Replace the placeholder with the computed check digit
    return draft[:CHECK_DIGIT_INDEX] + check_digit(draft) + draft[CHECK_DIGIT_INDEX + 1 :]


def break_check_digit(vin: str) -> str:
    """Return the same VIN with a wrong check digit (used to plant a keying error).

    Args:
        vin: A valid VIN.

    Returns:
        A VIN identical except for position 9, which no longer matches the formula.
    """
    # Pick the next character in "0123456789X" so the new digit is always different and still plausible
    digits = "0123456789X"
    wrong = digits[(digits.index(vin[CHECK_DIGIT_INDEX]) + 1) % len(digits)]
    return vin[:CHECK_DIGIT_INDEX] + wrong + vin[CHECK_DIGIT_INDEX + 1 :]
