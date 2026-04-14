"""Discovery engine for anomaly detection and clustering."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.utils.logger import get_logger

logger = get_logger(__name__)


class DiscoveryEngine:
    """Machine learning-based discovery tools for exoplanet analysis.

    This class provides methods for detecting anomalies, finding uncertain
    candidates, and clustering exoplanets by their characteristics.

    All methods are optimized for performance using vectorized operations
    and scikit-learn's efficient implementations.
    """

    @staticmethod
    def anomaly_detection(
        df: pd.DataFrame,
        features: list[str] | None = None,
        contamination: float = 0.1,
        random_state: int = 42,
    ) -> pd.DataFrame:
        """Detect anomalous exoplanets using Isolation Forest.

        Args:
            df: Input DataFrame with exoplanet data.
            features: List of feature columns to use. If None, uses common
                     physical parameters.
            contamination: Expected proportion of outliers (0-0.5).
            random_state: Random seed for reproducibility.

        Returns:
            DataFrame with added columns:
                - anomaly_score: Anomaly score (-1 = anomaly, 1 = normal)
                - anomaly_confidence: Confidence score (higher = more anomalous)
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if features is None:
            default_features = [
                "pl_rade",
                "pl_mass",
                "pl_orper",
                "pl_orbsmax",
                "pl_eccen",
                "st_mass",
                "st_rad",
            ]
            features = [f for f in default_features if f in result.columns]

        if len(features) < 2:
            logger.warning("Insufficient features for anomaly detection")
            result["anomaly_score"] = 0
            result["anomaly_confidence"] = 0.0
            return result

        data = result[features].dropna()
        original_indices = data.index

        if len(data) < 10:
            logger.warning("Insufficient data points for anomaly detection")
            result["anomaly_score"] = 0
            result["anomaly_confidence"] = 0.0
            return result

        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
        )

        predictions = iso_forest.fit_predict(scaled_data)
        scores = iso_forest.score_samples(scaled_data)

        result["anomaly_score"] = 0
        result["anomaly_confidence"] = 0.0

        result.loc[original_indices, "anomaly_score"] = predictions
        result.loc[original_indices, "anomaly_confidence"] = -scores

        logger.info(
            f"Detected {sum(predictions == -1)} anomalies out of {len(predictions)} planets"
        )

        return result

    @staticmethod
    def find_uncertain_candidates(
        df: pd.DataFrame,
        uncertainty_columns: list[str] | None = None,
        max_relative_error: float = 0.5,
    ) -> pd.DataFrame:
        """Identify measurements with high relative uncertainty.

        Args:
            df: Input DataFrame with exoplanet data.
            uncertainty_columns: Columns to check for uncertainty. If None,
                                uses common measurement columns.
            max_relative_error: Maximum acceptable relative error (0-1).

        Returns:
            DataFrame with added column 'high_uncertainty' indicating rows
            with measurements exceeding the relative error threshold.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if uncertainty_columns is None:
            uncertainty_columns = [
                "pl_rade",
                "pl_mass",
                "pl_orper",
                "pl_orbsmax",
                "pl_eccen",
            ]

        available_cols = [c for c in uncertainty_columns if c in result.columns]

        if not available_cols:
            result["high_uncertainty"] = False
            return result

        uncertainty_flags = []
        for col in available_cols:
            err_col = f"{col}err1"
            if err_col in result.columns:
                with np.errstate(divide="ignore", invalid="ignore"):
                    relative_error = np.abs(result[err_col] / result[col])
                    flag = relative_error > max_relative_error
                    flag = flag.fillna(False)
                    uncertainty_flags.append(flag)

        if uncertainty_flags:
            combined_flags = np.column_stack(uncertainty_flags).any(axis=1)
            result["high_uncertainty"] = combined_flags
        else:
            result["high_uncertainty"] = False

        uncertain_count = result["high_uncertainty"].sum()
        logger.info(f"Found {uncertain_count} candidates with high uncertainty")

        return result

    @staticmethod
    def cluster_by_characteristics(
        df: pd.DataFrame,
        features: list[str] | None = None,
        n_clusters: int = 4,
        random_state: int = 42,
    ) -> pd.DataFrame:
        """Cluster exoplanets by their physical characteristics.

        Args:
            df: Input DataFrame with exoplanet data.
            features: List of feature columns to use. If None, uses common
                     physical parameters.
            n_clusters: Number of clusters to create.
            random_state: Random seed for reproducibility.

        Returns:
            DataFrame with added columns:
                - cluster: Cluster assignment (0 to n_clusters-1)
                - cluster_distance: Distance to cluster centroid
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        if features is None:
            default_features = [
                "pl_rade",
                "pl_mass",
                "pl_orper",
                "pl_orbsmax",
            ]
            features = [f for f in default_features if f in result.columns]

        if len(features) < 2:
            logger.warning("Insufficient features for clustering")
            result["cluster"] = -1
            result["cluster_distance"] = np.nan
            return result

        data = result[features].dropna()
        original_indices = data.index

        if len(data) < n_clusters:
            logger.warning(f"Insufficient data for {n_clusters} clusters")
            result["cluster"] = -1
            result["cluster_distance"] = np.nan
            return result

        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=10,
            max_iter=300,
        )

        labels = kmeans.fit_predict(scaled_data)
        distances = np.min(kmeans.transform(scaled_data), axis=1)

        result["cluster"] = -1
        result["cluster_distance"] = np.nan

        result.loc[original_indices, "cluster"] = labels
        result.loc[original_indices, "cluster_distance"] = distances

        for i in range(n_clusters):
            count = sum(labels == i)
            logger.debug(f"Cluster {i}: {count} planets")

        logger.info(f"Clustered {len(labels)} planets into {n_clusters} groups")

        return result

    @staticmethod
    def calculate_similarity_matrix(
        df: pd.DataFrame,
        features: list[str] | None = None,
    ) -> pd.DataFrame:
        """Calculate pairwise similarity between exoplanets.

        Args:
            df: Input DataFrame with exoplanet data.
            features: List of feature columns to use.

        Returns:
            DataFrame containing the similarity matrix.
        """
        if df.empty:
            return pd.DataFrame()

        if features is None:
            features = ["pl_rade", "pl_mass", "pl_orper"]

        available_features = [f for f in features if f in df.columns]
        if not available_features:
            return pd.DataFrame()

        data = df[available_features].dropna()

        if len(data) == 0:
            return pd.DataFrame()

        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)

        similarity = np.dot(scaled_data, scaled_data.T)
        norms = np.linalg.norm(scaled_data, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        similarity = similarity / (norms * norms.T)

        similarity_df = pd.DataFrame(
            similarity,
            index=data.index,
            columns=data.index,
        )

        return similarity_df

    @staticmethod
    def rank_by_earth_similarity(
        df: pd.DataFrame,
        weight_radius: float = 0.57,
        weight_temperature: float = 0.43,
    ) -> pd.DataFrame:
        """Rank exoplanets by their similarity to Earth.

        Args:
            df: Input DataFrame with exoplanet data.
            weight_radius: Weight for radius similarity.
            weight_temperature: Weight for temperature similarity.

        Returns:
            DataFrame with added column 'esi_rank' containing the rank.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        earth_radius = 1.0
        earth_temp = 288.0

        esi_values = []
        indices = []

        for idx, row in result.iterrows():
            values = []
            weights = []

            if "pl_rade" in result.columns and pd.notna(row.get("pl_rade")):
                r = row["pl_rade"]
                if r > 0:
                    radius_term = 1 - abs((r - earth_radius) / (r + earth_radius))
                    values.append(radius_term)
                    weights.append(weight_radius)

            if "pl_eqt" in result.columns and pd.notna(row.get("pl_eqt")):
                t = row["pl_eqt"]
                if t > 0:
                    temp_term = 1 - abs((t - earth_temp) / (t + earth_temp))
                    values.append(temp_term)
                    weights.append(weight_temperature)
            elif "st_teff" in result.columns and "pl_orbsmax" in result.columns:
                if pd.notna(row.get("st_teff")) and pd.notna(row.get("pl_orbsmax")):
                    t_eff = row["st_teff"]
                    a = row["pl_orbsmax"]
                    if t_eff > 0 and a > 0:
                        t_eq = t_eff * np.sqrt(1 / (2 * a)) * 0.7
                        if t_eq > 0:
                            temp_term = 1 - abs((t_eq - earth_temp) / (t_eq + earth_temp))
                            values.append(temp_term)
                            weights.append(weight_temperature)

            if values and weights:
                total_weight = sum(weights)
                esi = sum(v * w for v, w in zip(values, weights)) / total_weight
            else:
                esi = 0.0

            esi_values.append(esi)
            indices.append(idx)

        result["esi"] = 0.0
        result.loc[indices, "esi"] = esi_values
        result["esi_rank"] = result["esi"].rank(ascending=False, method="dense")

        return result
