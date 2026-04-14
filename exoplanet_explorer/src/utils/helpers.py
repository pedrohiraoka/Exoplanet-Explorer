"""Helper functions for Exoplanet Explorer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")


def validate_path(path: str | Path, must_exist: bool = False) -> Path:
    """Validate and return a Path object.

    Args:
        path: The path to validate.
        must_exist: If True, raise an error if the path doesn't exist.

    Returns:
        A validated Path object.

    Raises:
        FileNotFoundError: If must_exist is True and path doesn't exist.
        ValueError: If the path is invalid.
    """
    path_obj = Path(path).expanduser().resolve()

    if must_exist and not path_obj.exists():
        raise FileNotFoundError(f"Path does not exist: {path_obj}")

    return path_obj


def safe_convert(value: Any, target_type: type[T], default: T | None = None) -> T | None:
    """Safely convert a value to a target type.

    Args:
        value: The value to convert.
        target_type: The target type (e.g., float, int, str).
        default: Default value if conversion fails.

    Returns:
        The converted value or the default.
    """
    if value is None:
        return default

    if isinstance(value, target_type):
        return value

    try:
        if target_type == float:
            if isinstance(value, str) and value.lower() in ("nan", "null", "none", ""):
                return default
            return target_type(value)
        elif target_type == int:
            if isinstance(value, str) and value.lower() in ("nan", "null", "none", ""):
                return default
            return int(float(value))
        elif target_type == str:
            return str(value)
        else:
            return target_type(value)
    except (ValueError, TypeError):
        return default


def format_table(df: pd.DataFrame, max_rows: int = 20, max_width: int = 80) -> str:
    """Format a DataFrame as a text table.

    Args:
        df: The DataFrame to format.
        max_rows: Maximum number of rows to display.
        max_width: Maximum width of the output.

    Returns:
        A formatted string representation of the DataFrame.
    """
    if df.empty:
        return "(empty result)"

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console(width=max_width, force_terminal=False)
        table = Table(title="Exoplanet Results")

        for col in df.columns[:10]:
            table.add_column(str(col), overflow="ellipsis")

        display_df = df.head(max_rows)
        for _, row in display_df.iterrows():
            table.add_row(*[str(v)[:30] for v in row.values])

        from io import StringIO

        output = StringIO()
        console.file = output
        console.print(table)
        return output.getvalue()

    except ImportError:
        pass

    try:
        from tabulate import tabulate

        display_df = df.head(max_rows)
        return tabulate(display_df, headers="keys", tablefmt="pipe", showindex=False)

    except ImportError:
        pass

    display_df = df.head(max_rows)
    return display_df.to_string(max_cols=10, max_rows=max_rows)


def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate a string with ellipsis if too long.

    Args:
        s: The string to truncate.
        max_length: Maximum length before truncation.

    Returns:
        The truncated string.
    """
    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def parse_column_list(columns_str: str) -> list[str]:
    """Parse a comma-separated column list.

    Args:
        columns_str: Comma-separated column names.

    Returns:
        List of column names.
    """
    if not columns_str:
        return []

    columns = [c.strip() for c in columns_str.split(",")]
    return [c for c in columns if c]


def get_env_config() -> dict[str, Any]:
    """Get configuration from environment variables.

    Returns:
        Dictionary of configuration values.
    """
    return {
        "timeout": int(os.environ.get("EXOPLANET_EXPLORER_TIMEOUT", "30")),
        "max_retries": int(os.environ.get("EXOPLANET_EXPLORER_RETRIES", "3")),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        "default_limit": int(os.environ.get("EXOPLANET_EXPLORER_LIMIT", "100")),
    }


def chunk_dataframe(df: pd.DataFrame, chunk_size: int) -> list[pd.DataFrame]:
    """Split a DataFrame into chunks.

    Args:
        df: The DataFrame to split.
        chunk_size: Number of rows per chunk.

    Returns:
        List of DataFrame chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    return [df[i : i + chunk_size] for i in range(0, len(df), chunk_size)]


def merge_dataframes(
    dfs: list[pd.DataFrame], on: str | None = None, how: str = "outer"
) -> pd.DataFrame:
    """Merge multiple DataFrames.

    Args:
        dfs: List of DataFrames to merge.
        on: Column to merge on. If None, uses index.
        how: Merge strategy ('inner', 'outer', 'left', 'right').

    Returns:
        Merged DataFrame.
    """
    if not dfs:
        return pd.DataFrame()

    if len(dfs) == 1:
        return dfs[0].copy()

    result = dfs[0].copy()
    for df in dfs[1:]:
        if on:
            result = result.merge(df, on=on, how=how)
        else:
            result = result.merge(df, left_index=True, right_index=True, how=how)

    return result
