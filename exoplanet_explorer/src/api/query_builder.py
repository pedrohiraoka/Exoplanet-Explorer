"""ADQL Query Builder with fluent interface."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.api.tap_client import TAPClient


class QueryBuilder:
    """Fluent interface for building ADQL queries.

    This class provides a chainable API for constructing ADQL queries
    with automatic escaping and validation.

    Example:
        >>> query = (QueryBuilder()
        ...     .select(['pl_name', 'pl_rade', 'pl_orper'])
        ...     .where('rowtype', '=', 'planet')
        ...     .where_range('pl_rade', 0.8, 1.5)
        ...     .order('pl_insol')
        ...     .set_limit(100)
        ...     .build())
    """

    def __init__(self):
        """Initialize the QueryBuilder."""
        self._columns: list[str] = []
        self._table: str = "ps"
        self._conditions: list[str] = []
        self._order_by: str | None = None
        self._limit: int | None = None
        self._distinct: bool = False

    def select(self, columns: list[str] | str) -> QueryBuilder:
        """Set the columns to select.

        Args:
            columns: A single column name or list of column names.

        Returns:
            Self for method chaining.
        """
        if isinstance(columns, str):
            self._columns = [columns]
        else:
            self._columns = columns
        return self

    def from_table(self, table: str) -> QueryBuilder:
        """Set the source table.

        Args:
            table: The table name (e.g., 'ps', 'pscomppars', 'koi_cumulative').

        Returns:
            Self for method chaining.
        """
        self._table = table
        return self

    def where(self, column: str, operator: str, value: Any) -> QueryBuilder:
        """Add a WHERE condition.

        Args:
            column: The column name.
            operator: The comparison operator (=, !=, <, >, <=, >=, LIKE).
            value: The value to compare against.

        Returns:
            Self for method chaining.
        """
        escaped_value = self._escape_value(value)
        condition = f"{column} {operator} {escaped_value}"
        self._conditions.append(condition)
        return self

    def where_range(
        self, column: str, min_value: float | int, max_value: float | int
    ) -> QueryBuilder:
        """Add a BETWEEN condition.

        Args:
            column: The column name.
            min_value: The minimum value (inclusive).
            max_value: The maximum value (inclusive).

        Returns:
            Self for method chaining.
        """
        condition = f"{column} BETWEEN {min_value} AND {max_value}"
        self._conditions.append(condition)
        return self

    def where_like(self, column: str, pattern: str) -> QueryBuilder:
        """Add a LIKE condition.

        Args:
            column: The column name.
            pattern: The SQL LIKE pattern (use % as wildcard).

        Returns:
            Self for method chaining.
        """
        escaped_pattern = self._escape_value(pattern)
        condition = f"{column} LIKE {escaped_pattern}"
        self._conditions.append(condition)
        return self

    def where_in(self, column: str, values: list[Any]) -> QueryBuilder:
        """Add an IN condition.

        Args:
            column: The column name.
            values: List of values to match.

        Returns:
            Self for method chaining.
        """
        escaped_values = ", ".join(self._escape_value(v) for v in values)
        condition = f"{column} IN ({escaped_values})"
        self._conditions.append(condition)
        return self

    def order(self, column: str, ascending: bool = True) -> QueryBuilder:
        """Set the ORDER BY clause.

        Args:
            column: The column to order by.
            ascending: If True, order ascending; otherwise descending.

        Returns:
            Self for method chaining.
        """
        direction = "ASC" if ascending else "DESC"
        self._order_by = f"{column} {direction}"
        return self

    def set_limit(self, limit: int) -> QueryBuilder:
        """Set the LIMIT clause.

        Args:
            limit: Maximum number of rows to return.

        Returns:
            Self for method chaining.
        """
        self._limit = limit
        return self

    def set_distinct(self, distinct: bool = True) -> QueryBuilder:
        """Enable or disable DISTINCT.

        Args:
            distinct: Whether to select distinct rows.

        Returns:
            Self for method chaining.
        """
        self._distinct = distinct
        return self

    def _escape_value(self, value: Any) -> str:
        """Escape a value for use in ADQL.

        Args:
            value: The value to escape.

        Returns:
            The escaped value as a string.
        """
        if value is None:
            return "NULL"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        else:
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"

    def build(self) -> str:
        """Build the final ADQL query string.

        Returns:
            A valid ADQL query string.

        Raises:
            ValueError: If no columns are selected.
        """
        if not self._columns:
            raise ValueError("No columns selected. Use select() first.")

        distinct_clause = "DISTINCT " if self._distinct else ""
        columns_str = ", ".join(self._columns)

        # Use TOP instead of LIMIT for Oracle-based TAP services
        if self._limit is not None and self._table == "ps":
            query = f"SELECT {distinct_clause}TOP {self._limit} {columns_str} FROM {self._table}"
        else:
            query = f"SELECT {distinct_clause}{columns_str} FROM {self._table}"

        if self._conditions:
            where_clause = " AND ".join(self._conditions)
            query += f" WHERE {where_clause}"

        if self._order_by:
            query += f" ORDER BY {self._order_by}"

        # Only add LIMIT for non-ps tables that support it
        if self._limit is not None and self._table != "ps":
            query += f" LIMIT {self._limit}"

        return query

    def execute(self, client: TAPClient, format: str = "csv") -> pd.DataFrame:
        """Execute the built query using the provided client.

        Args:
            client: The TAPClient instance to use.
            format: The desired output format.

        Returns:
            A pandas DataFrame containing the query results.
        """
        adql = self.build()
        return client.query(adql, format=format)

    def reset(self) -> QueryBuilder:
        """Reset the builder to its initial state.

        Returns:
            Self for method chaining.
        """
        self._columns = []
        self._table = "ps"
        self._conditions = []
        self._order_by = None
        self._limit = None
        self._distinct = False
        return self
