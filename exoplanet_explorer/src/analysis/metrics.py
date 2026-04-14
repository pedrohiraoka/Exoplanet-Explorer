"""Scientific metrics for exoplanet characterization."""

from __future__ import annotations

import numpy as np


class PlanetaryMetrics:
    """Calculate scientific metrics for exoplanets.

    This class provides methods for computing various planetary metrics
    including the Earth Similarity Index (ESI) and habitable zone parameters.

    All methods are static and designed for vectorized operations on pandas
    DataFrames or numpy arrays.
    """

    @staticmethod
    def earth_similarity_index(
        radius: float | np.ndarray,
        density: float | np.ndarray | None = None,
        escape_velocity: float | np.ndarray | None = None,
        surface_temperature: float | np.ndarray | None = None,
        earth_values: dict | None = None,
    ) -> float | np.ndarray:
        """Calculate the Earth Similarity Index (ESI).

        The ESI is calculated using the Schulze-Makuch formula:
        ESI = product((1 - |x_i - x_earth_i| / |x_i + x_earth_i|) ^ w_i)

        where x_i are planetary parameters and w_i are weights.

        Args:
            radius: Planet radius in Earth radii.
            density: Planet density in g/cm³ (optional).
            escape_velocity: Escape velocity in km/s (optional).
            surface_temperature: Surface temperature in K (optional).
            earth_values: Dictionary of Earth reference values. If None,
                         uses default values.

        Returns:
            ESI value(s) between 0 and 1, where 1 is identical to Earth.
        """
        if earth_values is None:
            earth_values = {
                "radius": 1.0,
                "density": 5.51,
                "escape_velocity": 11.186,
                "temperature": 288.0,
            }

        weights = {
            "radius": 0.57,
            "density": 1.07,
            "escape_velocity": 0.70,
            "temperature": 0.43,
        }

        params = [
            (radius, earth_values["radius"], weights["radius"]),
        ]

        if density is not None:
            params.append((density, earth_values["density"], weights["density"]))
        if escape_velocity is not None:
            params.append(
                (escape_velocity, earth_values["escape_velocity"], weights["escape_velocity"])
            )
        if surface_temperature is not None:
            params.append(
                (surface_temperature, earth_values["temperature"], weights["temperature"])
            )

        esi = 1.0
        for value, earth_val, weight in params:
            if value is not None:
                value = np.asarray(value)
                denominator = value + earth_val
                mask = denominator != 0
                term = np.ones_like(value, dtype=float)
                if np.any(mask):
                    diff = np.abs(value[mask] - earth_val)
                    sum_val = np.abs(value[mask] + earth_val)
                    term[mask] = 1 - diff / sum_val
                term = np.clip(term, 0, 1)
                esi *= term**weight

        return esi

    @staticmethod
    def habitable_zone_distance(
        semi_major_axis: float | np.ndarray,
        stellar_luminosity: float | np.ndarray | None = None,
        stellar_temperature: float | np.ndarray | None = None,
        stellar_radius: float | np.ndarray | None = None,
    ) -> dict[str, float | np.ndarray | bool]:
        """Calculate habitable zone parameters.

        Args:
            semi_major_axis: Planet's semi-major axis in AU.
            stellar_luminosity: Stellar luminosity in Solar units (optional).
            stellar_temperature: Stellar effective temperature in K (optional).
            stellar_radius: Stellar radius in Solar radii (optional).

        Returns:
            Dictionary containing:
                - hz_factor: Distance from optimal HZ position (0 = optimal)
                - optimal: Optimal HZ distance in AU
                - in_conservative_hz: Boolean indicating if in conservative HZ
                - in_optimistic_hz: Boolean indicating if in optimistic HZ
                - hz_inner_conservative: Inner edge of conservative HZ
                - hz_outer_conservative: Outer edge of conservative HZ
        """
        if stellar_luminosity is None:
            if stellar_radius is not None and stellar_temperature is not None:
                stellar_luminosity = (stellar_radius**2) * (
                    (stellar_temperature / 5778) ** 4
                )
            else:
                stellar_luminosity = 1.0

        luminosity = np.asarray(stellar_luminosity)
        axis = np.asarray(semi_major_axis)

        hz_inner_conservative = 0.95 * np.sqrt(luminosity)
        hz_outer_conservative = 1.67 * np.sqrt(luminosity)
        hz_inner_optimistic = 0.75 * np.sqrt(luminosity)
        hz_outer_optimistic = 1.8 * np.sqrt(luminosity)

        optimal_hz = 1.0 * np.sqrt(luminosity)

        hz_factor = np.abs(axis - optimal_hz) / optimal_hz

        in_conservative = (axis >= hz_inner_conservative) & (
            axis <= hz_outer_conservative
        )
        in_optimistic = (axis >= hz_inner_optimistic) & (
            axis <= hz_outer_optimistic
        )

        if np.ndim(hz_factor) == 0:
            return {
                "hz_factor": float(hz_factor),
                "optimal": float(optimal_hz),
                "in_conservative_hz": bool(in_conservative),
                "in_optimistic_hz": bool(in_optimistic),
                "hz_inner_conservative": float(hz_inner_conservative),
                "hz_outer_conservative": float(hz_outer_conservative),
            }
        else:
            return {
                "hz_factor": hz_factor,
                "optimal": optimal_hz,
                "in_conservative_hz": in_conservative,
                "in_optimistic_hz": in_optimistic,
                "hz_inner_conservative": hz_inner_conservative,
                "hz_outer_conservative": hz_outer_conservative,
            }

    @staticmethod
    def equilibrium_temperature(
        semi_major_axis: float | np.ndarray,
        stellar_temperature: float | np.ndarray,
        stellar_radius: float | np.ndarray,
        albedo: float | np.ndarray = 0.3,
    ) -> float | np.ndarray:
        """Calculate the equilibrium temperature of a planet.

        Args:
            semi_major_axis: Semi-major axis in AU.
            stellar_temperature: Stellar effective temperature in K.
            stellar_radius: Stellar radius in Solar radii.
            albedo: Bond albedo (0-1), default 0.3 (Earth-like).

        Returns:
            Equilibrium temperature in Kelvin.
        """
        au_in_meters = 1.496e11
        solar_radius_in_meters = 6.957e8
        sigma = 5.670374419e-8

        axis_m = np.asarray(semi_major_axis) * au_in_meters
        radius_m = np.asarray(stellar_radius) * solar_radius_in_meters
        temp_star = np.asarray(stellar_temperature)
        albedo_val = np.asarray(albedo)

        luminosity = 4 * np.pi * (radius_m**2) * sigma * (temp_star**4)
        flux = luminosity / (4 * np.pi * (axis_m**2))
        t_eq = ((flux * (1 - albedo_val)) / (4 * sigma)) ** 0.25

        return t_eq

    @staticmethod
    def minimum_mass(
        mass_sin_i: float | np.ndarray,
        inclination: float | np.ndarray | None = None,
    ) -> float | np.ndarray:
        """Calculate minimum mass from m*sin(i) measurement.

        Args:
            mass_sin_i: m*sin(i) value (minimum mass).
            inclination: Orbital inclination in degrees (optional).

        Returns:
            True mass if inclination is known, otherwise m*sin(i).
        """
        if inclination is None:
            return mass_sin_i

        inc_rad = np.radians(np.asarray(inclination))
        sin_i = np.sin(inc_rad)
        sin_i = np.where(sin_i == 0, 1e-10, sin_i)

        true_mass = np.asarray(mass_sin_i) / sin_i
        return true_mass

    @staticmethod
    def density(
        mass: float | np.ndarray, radius: float | np.ndarray
    ) -> float | np.ndarray:
        """Calculate bulk density.

        Args:
            mass: Planet mass in Earth masses.
            radius: Planet radius in Earth radii.

        Returns:
            Density in g/cm³ (relative to Earth's density of 5.51 g/cm³).
        """
        mass = np.asarray(mass)
        radius = np.asarray(radius)

        radius_cubed = radius**3
        radius_cubed = np.where(radius_cubed == 0, 1e-10, radius_cubed)

        density_relative = mass / radius_cubed
        density_g_cm3 = density_relative * 5.51

        return density_g_cm3
