"""Health Claims Register parser.

Epic 6, Story 6-1, Task 5: Register parser.

Parses the EU Health Claims Register from XLS/CSV format to a pandas DataFrame.
Handles format detection, column normalization, and date parsing.
"""

import logging
import re
from io import BytesIO
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when register parsing fails.

    Attributes:
        detail: Description of what failed
    """

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


# Required columns (post-normalization to snake_case)
REQUIRED_COLUMNS = frozenset({
    "claim_id",
    "substance",
    "status",
})

# Columns tracked for change detection
TRACKED_COLUMNS = (
    "claim_id",
    "claim_type",
    "substance",
    "health_relationship",
    "claim_text",
    "conditions_of_use",
    "food_category",
    "status",
    "efsa_opinion",
    "commission_regulation",
    "restrictions",
)


def _normalize_column_name(name: str) -> str:
    """Normalize column name to snake_case.

    Args:
        name: Raw column name from XLS/CSV

    Returns:
        snake_case normalized column name
    """
    # Remove leading/trailing whitespace
    name = name.strip()
    # Replace common separators with underscores
    name = re.sub(r"[\s\-/]+", "_", name)
    # Insert underscore before uppercase letters (camelCase -> camel_Case)
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    # Lowercase
    name = name.lower()
    # Remove consecutive underscores
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_")
    return name


class RegisterParser:
    """Parser for EU Health Claims Register data.

    Story 6-1, Task 5: Parse XLS/CSV to DataFrame.

    Tries XLS parse first (primary format), falls back to CSV.
    Validates required columns, normalizes names, parses dates.
    """

    def parse(self, data: bytes) -> pd.DataFrame:
        """Parse register data to DataFrame.

        Args:
            data: Raw bytes of XLS or CSV file

        Returns:
            DataFrame with normalized column names

        Raises:
            ParseError: If parsing fails or required columns missing
        """
        if not data:
            raise ParseError("Empty data provided")

        df = self._try_parse(data)
        df = self._normalize_columns(df)
        self._validate_columns(df)
        df = self._parse_dates(df)
        return df

    def _try_parse(self, data: bytes) -> pd.DataFrame:
        """Try XLS first, fall back to CSV.

        Args:
            data: Raw bytes to parse

        Returns:
            Parsed DataFrame

        Raises:
            ParseError: If both XLS and CSV parsing fail
        """
        xls_error: Optional[Exception] = None

        # Try XLS first (primary format from EU Open Data Portal)
        try:
            df = pd.read_excel(BytesIO(data), engine="openpyxl")
            if not df.empty:
                logger.info("Parsed register as XLS: %d rows, %d columns", len(df), len(df.columns))
                return df
        except Exception as e:
            xls_error = e
            logger.debug("XLS parse failed: %s, trying CSV", xls_error)

        # Fall back to CSV (semicolon-delimited, BOM encoding)
        try:
            df = pd.read_csv(
                BytesIO(data),
                sep=";",
                encoding="utf-8-sig",
            )
            if not df.empty:
                logger.info("Parsed register as CSV: %d rows, %d columns", len(df), len(df.columns))
                return df
        except Exception as csv_error:
            raise ParseError(
                f"Failed to parse as XLS or CSV. XLS error: {xls_error}, CSV error: {csv_error}"
            )

        raise ParseError("Parsed file is empty")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to snake_case.

        Args:
            df: DataFrame with raw column names

        Returns:
            DataFrame with normalized column names
        """
        df.columns = [_normalize_column_name(str(col)) for col in df.columns]
        return df

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate required columns exist.

        Args:
            df: DataFrame to validate

        Raises:
            ParseError: If required columns are missing
        """
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ParseError(
                f"Missing required columns: {sorted(missing)}. "
                f"Available columns: {sorted(df.columns)}"
            )

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date columns with EU format (DD/MM/YYYY).

        Args:
            df: DataFrame with string date columns

        Returns:
            DataFrame with parsed datetime columns
        """
        date_columns = ["date_of_entry", "last_update"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
        return df


__all__ = [
    "RegisterParser",
    "ParseError",
    "REQUIRED_COLUMNS",
    "TRACKED_COLUMNS",
]
