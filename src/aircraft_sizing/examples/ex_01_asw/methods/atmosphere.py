"""International Standard Atmosphere lookup for the ASW example.

The sizing model is written in US customary units (ft, lb, ft/s) while the
``ambiance`` package -- an implementation of the ICAO standard atmosphere 1993 --
speaks SI.  This module is the single conversion boundary: give it a cruise
altitude in feet and it returns an :class:`AtmosphereState` in the units the rest
of the example already uses.

Why the lookup lives *here* rather than inside an OpenMDAO component: ``ambiance``
is NumPy/SciPy code, so JAX cannot trace it, and a component wrapping it would have
to fall back to finite-difference partials.  That would break the property every
other discipline in ``components.py`` has -- an exact, analytic, autodiffed
Jacobian.  Altitude is instead resolved once, up front, into the constants the
model consumes, which keeps the group unchanged and still lets a study sweep
altitude by re-solving (see ``config.input_sensitivity_sweep``).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite

from ambiance import CONST, Atmosphere

__all__ = [
    "AtmosphereState",
    "standard_atmosphere",
    "MINIMUM_ALTITUDE_FT",
    "MAXIMUM_ALTITUDE_FT",
]

# --------------------------------------------------------------------------- #
# Unit conversions (SI -> US customary)
# --------------------------------------------------------------------------- #
METERS_PER_FOOT = 0.3048  # exact, by definition of the international foot
KG_PER_M3_PER_SLUG_PER_FT3 = 515.378818393  # 1 slug/ft^3 in kg/m^3
PA_PER_LB_PER_FT2 = 47.8802589804  # 1 lbf/ft^2 in Pa
RANKINE_PER_KELVIN = 1.8

#: Altitude band ``ambiance`` is defined over, converted to feet.  Read from the
#: package's own constants so the two can never drift apart.
MINIMUM_ALTITUDE_FT = CONST.h_min / METERS_PER_FOOT  # ~ -16,417 ft
MAXIMUM_ALTITUDE_FT = CONST.h_max / METERS_PER_FOOT  # ~ 265,814 ft


# --------------------------------------------------------------------------- #
# Atmospheric state
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Standard-atmosphere properties at one geometric altitude, in US units."""

    altitude_ft: float
    speed_of_sound_ft_per_s: float
    density_slug_per_ft3: float
    temperature_rankine: float
    pressure_lb_per_ft2: float

    def dynamic_pressure_lb_per_ft2(self, true_airspeed_ft_per_s: float) -> float:
        """``q = 0.5 * rho * V^2`` at this altitude, in lb/ft^2."""
        return 0.5 * self.density_slug_per_ft3 * float(true_airspeed_ft_per_s) ** 2


@lru_cache(maxsize=256)
def standard_atmosphere(altitude_ft: float) -> AtmosphereState:
    """Return the ICAO standard atmosphere at ``altitude_ft`` (geometric, feet).

    Cached because a single Streamlit click or sensitivity sweep re-solves the model
    dozens of times, almost always at the same handful of altitudes.
    """
    altitude = float(altitude_ft)
    if not isfinite(altitude) or not (MINIMUM_ALTITUDE_FT <= altitude <= MAXIMUM_ALTITUDE_FT):
        raise ValueError(
            f"cruise_altitude_ft must lie in the standard-atmosphere band "
            f"{MINIMUM_ALTITUDE_FT:,.0f} to {MAXIMUM_ALTITUDE_FT:,.0f} ft; got {altitude_ft!r}."
        )

    # ambiance returns a 1-element array per property even for a scalar altitude.
    atmosphere = Atmosphere(altitude * METERS_PER_FOOT)
    return AtmosphereState(
        altitude_ft=altitude,
        speed_of_sound_ft_per_s=float(atmosphere.speed_of_sound[0]) / METERS_PER_FOOT,
        density_slug_per_ft3=float(atmosphere.density[0]) / KG_PER_M3_PER_SLUG_PER_FT3,
        temperature_rankine=float(atmosphere.temperature[0]) * RANKINE_PER_KELVIN,
        pressure_lb_per_ft2=float(atmosphere.pressure[0]) / PA_PER_LB_PER_FT2,
    )
