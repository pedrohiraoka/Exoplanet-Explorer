"""Exoplanet data model with scientific properties."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Exoplanet:
    """Data class representing an exoplanet.

    This class encapsulates the key physical and orbital parameters
    of an exoplanet as reported in the NASA Exoplanet Archive.

    Attributes:
        planet_name: The name of the planet.
        hostname: The name of the host star.
        orbital_period: Orbital period in days.
        semi_major_axis: Semi-major axis in AU.
        eccentricity: Orbital eccentricity (0-1).
        planet_radius: Planet radius in Earth radii.
        planet_mass: Planet mass in Earth masses.
        equilibrium_temperature: Equilibrium temperature in Kelvin.
        stellar_radius: Stellar radius in Solar radii.
        stellar_mass: Stellar mass in Solar masses.
        stellar_temperature: Stellar effective temperature in Kelvin.
        discovery_method: Method used to discover the planet.
        data_source: Source catalog or mission.
    """

    planet_name: Optional[str] = None
    hostname: Optional[str] = None
    orbital_period: Optional[float] = None
    semi_major_axis: Optional[float] = None
    eccentricity: Optional[float] = None
    planet_radius: Optional[float] = None
    planet_mass: Optional[float] = None
    equilibrium_temperature: Optional[float] = None
    stellar_radius: Optional[float] = None
    stellar_mass: Optional[float] = None
    stellar_temperature: Optional[float] = None
    discovery_method: Optional[str] = None
    data_source: Optional[str] = None

    _esi_cache: Optional[float] = field(default=None, init=False, repr=False)

    @property
    def is_potentially_habitable(self) -> bool:
        """Check if the planet is potentially habitable based on ESI.

        Returns:
            True if the Earth Similarity Index (ESI) is greater than 0.8.
        """
        esi = self.calculate_esi()
        return esi > 0.8 if esi is not None else False

    @property
    def is_in_habitable_zone(self) -> bool:
        """Check if the planet is in the habitable zone.

        Uses a simplified calculation based on stellar luminosity
        and planetary distance.

        Returns:
            True if the planet is within the conservative habitable zone.
        """
        if self.semi_major_axis is None or self.stellar_mass is None:
            return False

        if self.stellar_temperature is None or self.stellar_radius is None:
            return False

        try:
            luminosity = (self.stellar_radius**2) * (
                (self.stellar_temperature / 5778) ** 4
            )
            hz_inner = 0.95 * (luminosity**0.5)
            hz_outer = 1.67 * (luminosity**0.5)

            return hz_inner <= self.semi_major_axis <= hz_outer
        except (ZeroDivisionError, ValueError):
            return False

    def calculate_esi(self) -> Optional[float]:
        """Calculate the Earth Similarity Index (ESI).

        Uses a simplified formula based on available parameters.
        The ESI ranges from 0 (completely different from Earth) to
        1 (identical to Earth).

        Returns:
            The ESI value, or None if insufficient data.
        """
        values = []
        weights = []

        earth_radius = 1.0
        earth_temp = 288.0

        if self.planet_radius is not None and self.planet_radius > 0:
            radius_term = 1 - abs((self.planet_radius - earth_radius) / (self.planet_radius + earth_radius))
            values.append(radius_term)
            weights.append(0.57)

        if self.equilibrium_temperature is not None and self.equilibrium_temperature > 0:
            temp_term = 1 - abs((self.equilibrium_temperature - earth_temp) / (self.equilibrium_temperature + earth_temp))
            values.append(temp_term)
            weights.append(0.43)

        if not values:
            return None

        total_weight = sum(weights)
        if total_weight == 0:
            return None

        esi = sum(v * w for v, w in zip(values, weights)) / total_weight
        self._esi_cache = esi
        return esi

    @classmethod
    def from_dict(cls, data: dict) -> Exoplanet:
        """Create an Exoplanet instance from a dictionary.

        Args:
            data: Dictionary containing planet data with keys matching
                  the Exoplanet fields (with 'pl_' or 'st_' prefixes).

        Returns:
            An Exoplanet instance.
        """
        column_mapping = {
            "planet_name": ["pl_name", "planet_name"],
            "hostname": ["hostname", "star_name"],
            "orbital_period": ["pl_orper", "orbital_period"],
            "semi_major_axis": ["pl_orbsmax", "semi_major_axis"],
            "eccentricity": ["pl_eccen", "eccentricity"],
            "planet_radius": ["pl_rade", "planet_radius"],
            "planet_mass": ["pl_mass", "planet_mass"],
            "equilibrium_temperature": ["pl_eqt", "equilibrium_temperature"],
            "stellar_radius": ["st_rad", "stellar_radius"],
            "stellar_mass": ["st_mass", "stellar_mass"],
            "stellar_temperature": ["st_teff", "stellar_temperature"],
            "discovery_method": ["disc_method", "discovery_method"],
            "data_source": ["data_source", "source"],
        }

        kwargs = {}
        for attr, possible_keys in column_mapping.items():
            value = None
            for key in possible_keys:
                if key in data and data[key] is not None:
                    val = data[key]
                    if isinstance(val, (int, float)) and str(val).lower() in ("nan", ""):
                        value = None
                    else:
                        value = val
                    break
            kwargs[attr] = value

        return cls(**kwargs)

    def to_dict(self) -> dict:
        """Convert the Exoplanet to a dictionary.

        Returns:
            A dictionary representation of the exoplanet.
        """
        return {
            "planet_name": self.planet_name,
            "hostname": self.hostname,
            "orbital_period": self.orbital_period,
            "semi_major_axis": self.semi_major_axis,
            "eccentricity": self.eccentricity,
            "planet_radius": self.planet_radius,
            "planet_mass": self.planet_mass,
            "equilibrium_temperature": self.equilibrium_temperature,
            "stellar_radius": self.stellar_radius,
            "stellar_mass": self.stellar_mass,
            "stellar_temperature": self.stellar_temperature,
            "discovery_method": self.discovery_method,
            "data_source": self.data_source,
        }

    def __str__(self) -> str:
        """Return a human-readable string representation.

        Returns:
            A formatted string with planet information.
        """
        name = self.planet_name or "Unknown"
        return f"Exoplanet({name})"

    def __repr__(self) -> str:
        """Return a detailed string representation.

        Returns:
            A string suitable for debugging.
        """
        return (
            f"Exoplanet(planet_name={self.planet_name!r}, "
            f"hostname={self.hostname!r}, "
            f"orbital_period={self.orbital_period!r})"
        )
