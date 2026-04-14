"""TAP Client for NASA Exoplanet Archive API."""

from __future__ import annotations

import time
from typing import Literal
from urllib.parse import urlencode

import pandas as pd
import requests
from requests.adapters import HTTPAdapter, Retry

from src.utils.logger import get_logger

logger = get_logger(__name__)

TAP_BASE_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

SUPPORTED_FORMATS = ("csv", "json", "votable", "ipac")


class TAPQueryError(Exception):
    """Exception raised when a TAP query fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class TAPConnectionError(Exception):
    """Exception raised when connection to TAP service fails."""

    pass


class TAPClient:
    """Client for interacting with NASA Exoplanet Archive TAP service.

    This client provides a reusable session with configurable timeouts,
    automatic retries with exponential backoff, and support for multiple
    output formats.

    Attributes:
        base_url: The TAP service base URL.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        session: Reusable requests session with configured adapters.
    """

    def __init__(
        self,
        base_url: str = TAP_BASE_URL,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """Initialize the TAP client.

        Args:
            base_url: The TAP service base URL.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.session.headers.update(
            {
                "User-Agent": "ExoplanetExplorer/0.1.0",
                "Accept": "text/csv,application/json,text/xml",
            }
        )

    def _parse_response(self, response: requests.Response, format: str) -> pd.DataFrame:
        """Parse the HTTP response into a DataFrame.

        Args:
            response: The HTTP response object.
            format: The expected data format.

        Returns:
            A pandas DataFrame containing the query results.

        Raises:
            TAPQueryError: If the response cannot be parsed.
        """
        if format == "csv":
            return pd.read_csv(response.text)
        elif format == "json":
            return pd.read_json(response.text)
        elif format == "votable":
            try:
                from astropy.io.votable import parse
                from io import BytesIO

                votable = parse(BytesIO(response.content))
                return pd.DataFrame(votable.get_first_table().to_array())
            except ImportError:
                logger.warning("astropy not available, falling back to CSV parsing")
                return pd.read_csv(response.text)
        else:
            return pd.read_csv(response.text)

    def query(self, adql: str, format: str = "csv") -> pd.DataFrame:
        """Execute an ADQL query against the TAP service.

        Args:
            adql: The ADQL query string.
            format: The desired output format (csv, json, votable, ipac).

        Returns:
            A pandas DataFrame containing the query results.

        Raises:
            TAPQueryError: If the query fails or returns an error.
            TAPConnectionError: If the connection fails after retries.
        """
        if format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format}. Use one of {SUPPORTED_FORMATS}")

        params = {"query": adql, "format": format}

        attempt = 0
        while attempt <= self.max_retries:
            try:
                logger.debug(f"Executing query (attempt {attempt + 1}): {adql[:100]}...")
                response = self.session.get(
                    self.base_url, params=params, timeout=self.timeout
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "2")
                    wait_time = int(retry_after)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry.")
                    time.sleep(wait_time)
                    attempt += 1
                    continue

                if response.status_code != 200:
                    raise TAPQueryError(
                        f"TAP query failed with status {response.status_code}: {response.text[:200]}",
                        status_code=response.status_code,
                    )

                if not response.text.strip():
                    raise TAPQueryError("Empty response from TAP service")

                return self._parse_response(response, format)

            except requests.exceptions.Timeout as e:
                logger.warning(f"Request timeout (attempt {attempt + 1}): {e}")
                attempt += 1
                if attempt > self.max_retries:
                    raise TAPConnectionError(
                        f"Connection timed out after {attempt} attempts"
                    ) from e
                time.sleep(2**attempt)
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                attempt += 1
                if attempt > self.max_retries:
                    raise TAPConnectionError(
                        f"Connection failed after {attempt} attempts"
                    ) from e
                time.sleep(2**attempt)
            except Exception as e:
                if isinstance(e, TAPQueryError):
                    raise
                logger.error(f"Unexpected error during query: {e}")
                raise TAPQueryError(f"Query execution failed: {e}") from e

        raise TAPConnectionError("Max retries exceeded")

    def cone_search(
        self,
        ra: float,
        dec: float,
        radius: float,
        table: str = "ps",
        columns: list[str] | None = None,
    ) -> pd.DataFrame:
        """Perform a cone search around celestial coordinates.

        Args:
            ra: Right ascension in degrees.
            dec: Declination in degrees.
            radius: Search radius in degrees.
            table: The target table name.
            columns: List of columns to select. If None, selects all.

        Returns:
            A pandas DataFrame containing objects within the search radius.
        """
        if columns is None:
            col_str = "*"
        else:
            col_str = ", ".join(columns)

        adql = f"""
            SELECT {col_str}
            FROM {table}
            WHERE CONTAINS(
                POINT('ICRS', ra, dec),
                CIRCLE('ICRS', {ra}, {dec}, {radius})
            ) = 1
        """
        return self.query(adql)

    def close(self) -> None:
        """Close the underlying session."""
        self.session.close()

    def __enter__(self) -> TAPClient:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
