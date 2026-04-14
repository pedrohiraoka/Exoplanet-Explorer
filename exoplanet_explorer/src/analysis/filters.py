"""Filtering utilities for exoplanet candidate selection."""

from __future__ import annotations

import pandas as pd


class CandidateFilter:
    """Static methods for filtering exoplanet candidates.

    This class provides scientific filters for identifying potentially
    interesting exoplanets based on various criteria such as Earth-likeness,
    habitable zone location, and data quality.

    All filter methods return a copy of the filtered DataFrame to avoid
    unintended side effects.
    """

    @staticmethod
    def earth_like(
        df: pd.DataFrame,
        min_esi: float = 0.8,
        min_radius: float = 0.8,
        max_radius: float = 1.5,
        min_period: float = 200,
        max_period: float = 500,
    ) -> pd.DataFrame:
        """Filter for Earth-like planets.

        Args:
            df: Input DataFrame with exoplanet data.
            min_esi: Minimum Earth Similarity Index (0-1).
            min_radius: Minimum planet radius in Earth radii.
            max_radius: Maximum planet radius in Earth radii.
            min_period: Minimum orbital period in days.
            max_period: Maximum orbital period in days.

        Returns:
            Filtered DataFrame containing Earth-like candidates.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if "pl_rade" in result.columns:
            result = result[
                (result["pl_rade"] >= min_radius) & (result["pl_rade"] <= max_radius)
            ]

        # Only apply period filter if column exists and has valid data
        if "pl_orper" in result.columns:
            # Use more lenient filtering - only filter if we have valid period data
            valid_periods = result["pl_orper"].notna()
            if valid_periods.any():
                period_mask = (result["pl_orper"] >= min_period) & (result["pl_orper"] <= max_period)
                # Include rows with NaN periods as they might still be candidates
                result = result[~valid_periods | period_mask]

        # Apply insolation filter only if data is available and in reasonable range
        if "pl_insol" in result.columns:
            insol_min = 0.3
            insol_max = 1.5
            valid_insol = result["pl_insol"].notna()
            if valid_insol.any():
                insol_mask = (result["pl_insol"] >= insol_min) & (result["pl_insol"] <= insol_max)
                # Include rows without insolation data as they might still be candidates
                result = result[~valid_insol | insol_mask]

        return result.reset_index(drop=True)

    @staticmethod
    def in_habitable_zone(df: pd.DataFrame, conservative: bool = True) -> pd.DataFrame:
        """Filter for planets in the habitable zone.

        Uses the insolation flux (pl_insol) column if available, or
        calculates based on stellar luminosity and semi-major axis.

        Args:
            df: Input DataFrame with exoplanet data.
            conservative: If True, use conservative HZ boundaries;
                         otherwise use optimistic boundaries.

        Returns:
            Filtered DataFrame containing planets in the habitable zone.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if "pl_insol" in result.columns:
            if conservative:
                insol_min, insol_max = 0.36, 1.11
            else:
                insol_min, insol_max = 0.25, 1.5

            mask = result["pl_insol"].between(insol_min, insol_max)
            result = result[mask]

        elif "pl_orbsmax" in result.columns and "st_lum" in result.columns:
            if conservative:
                hz_factor_inner, hz_factor_outer = 0.95, 1.67
            else:
                hz_factor_inner, hz_factor_outer = 0.75, 1.8

            result["hz_inner"] = hz_factor_inner * (result["st_lum"] ** 0.5)
            result["hz_outer"] = hz_factor_outer * (result["st_lum"] ** 0.5)

            mask = (result["pl_orbsmax"] >= result["hz_inner"]) & (
                result["pl_orbsmax"] <= result["hz_outer"]
            )
            result = result[mask]

            result = result.drop(columns=["hz_inner", "hz_outer"], errors="ignore")

        return result.reset_index(drop=True)

    @staticmethod
    def high_confidence(
        df: pd.DataFrame,
        min_signals: int = 3,
        require_radial_velocity: bool = False,
    ) -> pd.DataFrame:
        """Filter for high-confidence planet candidates.

        Args:
            df: Input DataFrame with exoplanet data.
            min_signals: Minimum number of detection signals/transits.
            require_radial_velocity: If True, only include planets confirmed
                                    by radial velocity method.

        Returns:
            Filtered DataFrame containing high-confidence candidates.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if "pl_numsp" in result.columns:
            result = result[result["pl_numsp"] >= min_signals]

        if "discoverymethod" in result.columns:
            if require_radial_velocity:
                rv_methods = ["Radial Velocity", "RV", "radial velocity"]
                mask = result["discoverymethod"].isin(rv_methods)
                result = result[mask]

        if "sy_snum" in result.columns:
            result = result[result["sy_snum"] > 0]

        return result.reset_index(drop=True)

    @staticmethod
    def by_discovery_method(
        df: pd.DataFrame, methods: list[str] | str
    ) -> pd.DataFrame:
        """Filter by discovery method.

        Args:
            df: Input DataFrame with exoplanet data.
            methods: Single method name or list of method names.

        Returns:
            Filtered DataFrame containing planets discovered by specified methods.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if "discoverymethod" not in result.columns:
            return result

        if isinstance(methods, str):
            methods = [methods]

        normalized_methods = [m.lower() for m in methods]
        mask = result["discoverymethod"].str.lower().isin(normalized_methods)
        result = result[mask]

        return result.reset_index(drop=True)

    @staticmethod
    def by_size_category(
        df: pd.DataFrame, category: str
    ) -> pd.DataFrame:
        """Filter by planet size category.

        Categories:
            - terrestrial: < 1.25 Earth radii
            - super_earth: 1.25 - 2 Earth radii
            - neptune: 2 - 6 Earth radii
            - jupiter: > 6 Earth radii

        Args:
            df: Input DataFrame with exoplanet data.
            category: Size category name.

        Returns:
            Filtered DataFrame containing planets in the specified size category.

        Raises:
            ValueError: If an invalid category is provided.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if "pl_rade" not in result.columns:
            return result

        categories = {
            "terrestrial": (0, 1.25),
            "super_earth": (1.25, 2.0),
            "neptune": (2.0, 6.0),
            "jupiter": (6.0, float("inf")),
        }

        if category not in categories:
            raise ValueError(
                f"Invalid category: {category}. Use one of {list(categories.keys())}"
            )

        min_r, max_r = categories[category]
        mask = (result["pl_rade"] >= min_r) & (result["pl_rade"] < max_r)
        result = result[mask]

        return result.reset_index(drop=True)

    @staticmethod
    def with_complete_data(
        df: pd.DataFrame, required_columns: list[str] | None = None
    ) -> pd.DataFrame:
        """Filter for rows with complete data.

        Args:
            df: Input DataFrame with exoplanet data.
            required_columns: List of columns that must have non-null values.
                             If None, uses common scientific parameters.

        Returns:
            Filtered DataFrame with complete data.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if required_columns is None:
            required_columns = [
                "pl_name",
                "pl_rade",
                "pl_orper",
                "pl_orbsmax",
                "st_mass",
                "st_rad",
            ]

        available_cols = [c for c in required_columns if c in result.columns]
        if available_cols:
            result = result.dropna(subset=available_cols)

        return result.reset_index(drop=True)
