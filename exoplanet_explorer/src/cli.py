"""Command-line interface for Exoplanet Explorer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src.api.tap_client import TAPClient, TAPConnectionError, TAPQueryError
from src.api.query_builder import QueryBuilder
from src.analysis.discovery import DiscoveryEngine
from src.analysis.filters import CandidateFilter
from src.utils.helpers import format_table, get_env_config, parse_column_list
from src.utils.logger import get_logger, set_log_level

logger = get_logger(__name__)

DEFAULT_COLUMNS = [
    "pl_name",
    "pl_rade",
    "pl_bmasse",
    "pl_orbper",
    "pl_orbsmax",
    "pl_insol",
    "discoverymethod",
    "hostname",
]

AVAILABLE_TABLES = ["ps", "pscomppars", "koi_cumulative", "k2pandc"]


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="exoplanet-explorer",
        description="Explore exoplanet data from NASA Exoplanet Archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s search --limit 10
  %(prog)s search --table ps --columns pl_name,pl_rade,pl_orper --where "pl_rade > 1.0"
  %(prog)s earth-like --min-radius 0.8 --max-radius 1.5
  %(prog)s habitable --conservative
  %(prog)s analyze --input data.csv --anomalies
  %(prog)s search --output results.csv --format csv

Environment Variables:
  LOG_LEVEL                     Set logging level (DEBUG, INFO, WARNING, ERROR)
  EXOPLANET_EXPLORER_TIMEOUT    Request timeout in seconds (default: 30)
  EXOPLANET_EXPLORER_RETRIES    Max retry attempts (default: 3)
  EXOPLANET_EXPLORER_LIMIT      Default query limit (default: 100)
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    search_parser = subparsers.add_parser(
        "search",
        help="Search for exoplanets with custom filters",
    )
    search_parser.add_argument(
        "--table", "-t",
        default="ps",
        choices=AVAILABLE_TABLES,
        help="Target table (default: ps)",
    )
    search_parser.add_argument(
        "--columns", "-c",
        type=str,
        default=",".join(DEFAULT_COLUMNS),
        help="Comma-separated column names",
    )
    search_parser.add_argument(
        "--where", "-w",
        type=str,
        help="Custom WHERE clause (e.g., 'pl_rade > 1.0 AND pl_orper < 365')",
    )
    search_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=get_env_config().get("default_limit", 100),
        help="Maximum number of results",
    )
    search_parser.add_argument(
        "--order", "-o",
        type=str,
        help="Order by column (prefix with '-' for descending)",
    )
    search_parser.add_argument(
        "--method", "-m",
        type=str,
        help="Filter by discovery method",
    )
    search_parser.add_argument(
        "--output", "-O",
        type=str,
        help="Output file path",
    )
    search_parser.add_argument(
        "--format", "-f",
        choices=["csv", "json", "table"],
        default="table",
        help="Output format (default: table)",
    )

    earth_like_parser = subparsers.add_parser(
        "earth-like",
        help="Find Earth-like exoplanets",
    )
    earth_like_parser.add_argument(
        "--min-esi",
        type=float,
        default=0.8,
        help="Minimum Earth Similarity Index",
    )
    earth_like_parser.add_argument(
        "--min-radius",
        type=float,
        default=0.8,
        help="Minimum radius in Earth radii",
    )
    earth_like_parser.add_argument(
        "--max-radius",
        type=float,
        default=1.5,
        help="Maximum radius in Earth radii",
    )
    earth_like_parser.add_argument(
        "--min-period",
        type=float,
        default=200,
        help="Minimum orbital period in days",
    )
    earth_like_parser.add_argument(
        "--max-period",
        type=float,
        default=500,
        help="Maximum orbital period in days",
    )
    earth_like_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Maximum number of results",
    )
    earth_like_parser.add_argument(
        "--output", "-O",
        type=str,
        help="Output file path",
    )
    earth_like_parser.add_argument(
        "--format", "-f",
        choices=["csv", "json", "table"],
        default="table",
        help="Output format",
    )

    habitable_parser = subparsers.add_parser(
        "habitable",
        help="Find planets in the habitable zone",
    )
    habitable_parser.add_argument(
        "--conservative",
        action="store_true",
        help="Use conservative habitable zone boundaries",
    )
    habitable_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=100,
        help="Maximum number of results",
    )
    habitable_parser.add_argument(
        "--output", "-O",
        type=str,
        help="Output file path",
    )
    habitable_parser.add_argument(
        "--format", "-f",
        choices=["csv", "json", "table"],
        default="table",
        help="Output format",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze exoplanet data with ML techniques",
    )
    analyze_parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Input CSV file",
    )
    analyze_parser.add_argument(
        "--anomalies",
        action="store_true",
        help="Detect anomalies",
    )
    analyze_parser.add_argument(
        "--clusters",
        type=int,
        help="Cluster into N groups",
    )
    analyze_parser.add_argument(
        "--uncertain",
        action="store_true",
        help="Find uncertain candidates",
    )
    analyze_parser.add_argument(
        "--output", "-O",
        type=str,
        help="Output file path",
    )
    analyze_parser.add_argument(
        "--format", "-f",
        choices=["csv", "json", "table"],
        default="table",
        help="Output format",
    )

    return parser


def handle_search(args: argparse.Namespace) -> int:
    """Handle the search command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    if args.verbose:
        set_log_level("DEBUG")

    columns = parse_column_list(args.columns)
    if not columns:
        columns = DEFAULT_COLUMNS

    try:
        client = TAPClient()

        builder = QueryBuilder()
        builder.select(columns).from_table(args.table).set_limit(args.limit)

        # Build WHERE conditions
        where_parts = []
        
        if args.where:
            where_parts.append(args.where)

        if args.method:
            where_parts.append(f"discoverymethod = '{args.method}'")
        
        if where_parts:
            full_where = " AND ".join(where_parts)
            builder._conditions.insert(0, full_where)

        if args.order:
            ascending = not args.order.startswith("-")
            order_col = args.order.lstrip("-")
            builder.order(order_col, ascending=ascending)

        logger.info(f"Executing search on table '{args.table}'...")
        df = builder.execute(client)

        if df.empty:
            logger.info("No results found")
            print("No results found")
            return 0

        logger.info(f"Found {len(df)} exoplanets")

        return output_results(df, args)

    except TAPQueryError as e:
        logger.error(f"Query failed: {e}")
        print(f"Error: Query failed - {e}", file=sys.stderr)
        return 1
    except TAPConnectionError as e:
        logger.error(f"Connection failed: {e}")
        print(f"Error: Connection failed - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_earth_like(args: argparse.Namespace) -> int:
    """Handle the earth-like command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    if args.verbose:
        set_log_level("DEBUG")

    try:
        client = TAPClient()

        columns = [
            "pl_name", "pl_rade", "pl_bmasse", "pl_orbper", "pl_orbsmax",
            "pl_insol", "st_mass", "st_rad", "st_teff", "discoverymethod", "hostname"
        ]

        builder = QueryBuilder()
        builder.select(columns).from_table("ps").set_limit(args.limit)
        # Add filter for planets with radius data and reasonable insolation values
        builder._conditions.append("pl_rade IS NOT NULL AND pl_rade > 0.5 AND pl_rade < 3.0")

        logger.info("Searching for Earth-like exoplanets...")
        df = builder.execute(client)

        if df.empty:
            logger.info("No results found")
            print("No results found")
            return 0

        df_filtered = CandidateFilter.earth_like(
            df,
            min_esi=args.min_esi,
            min_radius=args.min_radius,
            max_radius=args.max_radius,
            min_period=args.min_period,
            max_period=args.max_period,
        )

        logger.info(f"Found {len(df_filtered)} Earth-like candidates")

        return output_results(df_filtered, args)

    except (TAPQueryError, TAPConnectionError) as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_habitable(args: argparse.Namespace) -> int:
    """Handle the habitable command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    if args.verbose:
        set_log_level("DEBUG")

    try:
        client = TAPClient()

        columns = [
            "pl_name", "pl_rade", "pl_orbper", "pl_orbsmax", "pl_insol",
            "st_lum", "st_mass", "st_rad", "discoverymethod", "hostname"
        ]

        builder = QueryBuilder()
        builder.select(columns).from_table("ps").set_limit(args.limit)
        # Add filter for planets with insolation data in a reasonable range
        builder._conditions.append("pl_insol IS NOT NULL AND pl_insol > 0.1 AND pl_insol < 10.0")

        logger.info("Searching for planets in habitable zone...")
        df = builder.execute(client)

        if df.empty:
            logger.info("No results found")
            print("No results found")
            return 0

        df_filtered = CandidateFilter.in_habitable_zone(df, conservative=args.conservative)

        logger.info(f"Found {len(df_filtered)} planets in habitable zone")

        return output_results(df_filtered, args)

    except (TAPQueryError, TAPConnectionError) as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def handle_analyze(args: argparse.Namespace) -> int:
    """Handle the analyze command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code.
    """
    if args.verbose:
        set_log_level("DEBUG")

    try:
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")

        df = pd.read_csv(input_path)
        logger.info(f"Loaded {len(df)} records from {args.input}")

        engine = DiscoveryEngine()

        if args.anomalies:
            logger.info("Running anomaly detection...")
            df = engine.anomaly_detection(df)
            anomalies = df[df["anomaly_score"] == -1]
            logger.info(f"Detected {len(anomalies)} anomalies")

        if args.clusters:
            logger.info(f"Clustering into {args.clusters} groups...")
            df = engine.cluster_by_characteristics(df, n_clusters=args.clusters)

        if args.uncertain:
            logger.info("Finding uncertain candidates...")
            df = engine.find_uncertain_candidates(df)
            uncertain = df[df["high_uncertainty"]]
            logger.info(f"Found {len(uncertain)} uncertain candidates")

        return output_results(df, args)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


def output_results(df: pd.DataFrame, args: argparse.Namespace) -> int:
    """Output results in the specified format.

    Args:
        df: DataFrame with results.
        args: Command-line arguments.

    Returns:
        Exit code.
    """
    output_format = getattr(args, "format", "table")
    output_path = getattr(args, "output", None)

    if output_path:
        output_file = Path(output_path)
        if output_format == "csv" or output_file.suffix == ".csv":
            df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            print(f"Results saved to {output_file}")
        elif output_format == "json" or output_file.suffix == ".json":
            df.to_json(output_file, orient="records", indent=2)
            logger.info(f"Results saved to {output_file}")
            print(f"Results saved to {output_file}")
        else:
            df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            print(f"Results saved to {output_file}")
    else:
        if output_format == "csv":
            print(df.to_csv(index=False))
        elif output_format == "json":
            print(df.to_json(orient="records", indent=2))
        else:
            print(format_table(df))

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "search":
        return handle_search(args)
    elif args.command == "earth-like":
        return handle_earth_like(args)
    elif args.command == "habitable":
        return handle_habitable(args)
    elif args.command == "analyze":
        return handle_analyze(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
