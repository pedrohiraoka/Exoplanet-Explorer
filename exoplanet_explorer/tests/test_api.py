"""Tests for the API module."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import pandas as pd

from src.api.query_builder import QueryBuilder
from src.api.tap_client import TAPClient, TAPConnectionError, TAPQueryError


class TestTAPClient(unittest.TestCase):
    """Test cases for TAPClient class."""

    def test_initialization(self):
        """Test TAPClient initializes correctly."""
        client = TAPClient(timeout=60, max_retries=5)
        self.assertEqual(client.timeout, 60)
        self.assertEqual(client.max_retries, 5)
        self.assertIsNotNone(client.session)

    def test_default_configuration(self):
        """Test default configuration values."""
        client = TAPClient()
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.max_retries, 3)
        self.assertIn("User-Agent", client.session.headers)

    @patch("src.api.tap_client.requests.Session")
    def test_query_success(self, mock_session_class):
        """Test successful query execution."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "pl_name,pl_rade\nPlanet1,1.5\nPlanet2,2.0"
        mock_session.get.return_value = mock_response

        client = TAPClient()
        df = client.query("SELECT * FROM ps LIMIT 2")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertTrue(mock_session.get.called)

    @patch("src.api.tap_client.requests.Session")
    def test_query_error_status(self, mock_session_class):
        """Test query with error status code."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request: Invalid query"
        mock_session.get.return_value = mock_response

        client = TAPClient()

        with self.assertRaises(TAPQueryError) as context:
            client.query("INVALID QUERY")

        self.assertEqual(context.exception.status_code, 400)

    def test_unsupported_format(self):
        """Test query with unsupported format."""
        client = TAPClient()

        with self.assertRaises(ValueError):
            client.query("SELECT * FROM ps", format="xml")

    @patch("src.api.tap_client.requests.Session")
    def test_cone_search(self, mock_session_class):
        """Test cone search functionality."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ra,dec,name\n10.0,20.0,Star1"
        mock_session.get.return_value = mock_response

        client = TAPClient()
        df = client.cone_search(ra=10.0, dec=20.0, radius=0.5)

        self.assertIsInstance(df, pd.DataFrame)
        call_args = mock_session.get.call_args
        query_str = call_args[1]["params"]["query"]
        self.assertIn("CONTAINS", query_str)
        self.assertIn("CIRCLE", query_str)

    def test_context_manager(self):
        """Test context manager usage."""
        with TAPClient() as client:
            self.assertIsInstance(client, TAPClient)


class TestQueryBuilder(unittest.TestCase):
    """Test cases for QueryBuilder class."""

    def test_basic_select(self):
        """Test basic SELECT query building."""
        builder = QueryBuilder()
        query = builder.select(["pl_name", "pl_rade"]).from_table("ps").build()

        expected = "SELECT pl_name, pl_rade FROM ps"
        self.assertEqual(query.strip(), expected)

    def test_select_single_column(self):
        """Test SELECT with single column."""
        builder = QueryBuilder()
        query = builder.select("pl_name").from_table("ps").build()

        expected = "SELECT pl_name FROM ps"
        self.assertEqual(query.strip(), expected)

    def test_where_clause(self):
        """Test WHERE clause building."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .where("pl_rade", ">", 1.0)
            .build()
        )

        self.assertIn("WHERE", query)
        self.assertIn("pl_rade > 1.0", query)

    def test_where_range(self):
        """Test BETWEEN clause building."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .where_range("pl_rade", 0.8, 1.5)
            .build()
        )

        self.assertIn("BETWEEN 0.8 AND 1.5", query)

    def test_where_like(self):
        """Test LIKE clause building."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .where_like("pl_name", "%Earth%")
            .build()
        )

        self.assertIn("LIKE '%Earth%'", query)

    def test_string_escaping(self):
        """Test automatic string escaping."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .where("disc_method", "=", "Radial Velocity")
            .build()
        )

        self.assertIn("'Radial Velocity'", query)

    def test_order_by(self):
        """Test ORDER BY clause."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .order("pl_insol", ascending=True)
            .build()
        )

        self.assertIn("ORDER BY pl_insol ASC", query)

    def test_order_by_descending(self):
        """Test ORDER BY DESC clause."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .order("pl_insol", ascending=False)
            .build()
        )

        self.assertIn("ORDER BY pl_insol DESC", query)

    def test_limit(self):
        """Test LIMIT clause."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .set_limit(100)
            .build()
        )

        # For Oracle-based TAP (ps table), uses TOP instead of LIMIT
        self.assertIn("TOP 100", query)

    def test_distinct(self):
        """Test DISTINCT clause."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name"])
            .from_table("ps")
            .set_distinct(True)
            .build()
        )

        self.assertIn("DISTINCT", query)

    def test_complex_query(self):
        """Test complex query with multiple clauses."""
        builder = QueryBuilder()
        query = (
            builder.select(["pl_name", "pl_rade", "pl_orper"])
            .from_table("ps")
            .where("rowtype", "=", "planet")
            .where_range("pl_rade", 0.8, 1.5)
            .order("pl_insol", ascending=True)
            .set_limit(100)
            .build()
        )

        self.assertIn("SELECT", query)
        self.assertIn("FROM ps", query)
        self.assertIn("WHERE", query)
        self.assertIn("ORDER BY", query)
        # For Oracle-based TAP (ps table), uses TOP instead of LIMIT
        self.assertIn("TOP 100", query)

    def test_no_columns_raises_error(self):
        """Test that build raises error without columns."""
        builder = QueryBuilder()

        with self.assertRaises(ValueError):
            builder.build()

    def test_reset(self):
        """Test reset functionality."""
        builder = QueryBuilder()
        builder.select(["pl_name"]).from_table("ps").set_limit(100)
        builder.reset()

        with self.assertRaises(ValueError):
            builder.build()

    @patch("src.api.query_builder.TAPClient")
    def test_execute(self, mock_client_class):
        """Test execute method."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_df = pd.DataFrame({"pl_name": ["Planet1"]})
        mock_client.query.return_value = mock_df

        builder = QueryBuilder()
        builder.select(["pl_name"]).from_table("ps")

        result = builder.execute(mock_client)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(mock_client.query.called)


if __name__ == "__main__":
    unittest.main()
