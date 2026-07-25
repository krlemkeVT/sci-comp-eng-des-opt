"""Pure-JAX physics for the notional ASW conceptual-sizing example.

Every function here is written with ``jax.numpy`` so that OpenMDAO can obtain
*exact* partial derivatives by automatic differentiation (see ``components.py``,
where each component fills ``compute_partials`` with a visible ``jax.jacobian``
call).  Keeping the physics in one dependency-light module also lets the model run
on a GPU later without code changes -- JAX dispatches these same functions to
whatever device ``jaxlib`` was built for.

The equations follow Raymer, *Aircraft Design: A Conceptual Approach* (7e),
Section 3.6.  ``jax_enable_x64`` is turned on because the tutorial baselines are
checked to ~1e-4 and JAX defaults to float32.
"""

from __future__ import annotations

import jax

jax.config.update("jax_enable_x64", True)

import jax.numpy as jnp  # noqa: E402  (import after enabling x64 on purpose)

FEET_PER_NAUTICAL_MILE = 6076.0
SECONDS_PER_HOUR = 3600.0
SECONDS_PER_MINUTE = 60.0


# --------------------------------------------------------------------------- #
# Aerodynamics
# --------------------------------------------------------------------------- #
def aerodynamics(wing_aspect_ratio, wetted_area_ratio, k_ld, cruise_ld_factor):
    """Return ``(L/D_max, L/D_cruise, L/D_loiter)``.

    Raymer 7e Eq. 3.12 / Fig. 3.6:  ``(L/D)_max = K_LD * sqrt(wetted AR)`` with
    ``wetted AR = AR / (S_wet / S_ref)``.  Cruise runs at a fraction of the best
    L/D; loiter is flown at the best L/D.
    """
    wetted_aspect_ratio = wing_aspect_ratio / wetted_area_ratio
    lift_to_drag_max = k_ld * jnp.sqrt(wetted_aspect_ratio)
    cruise_lift_to_drag = cruise_ld_factor * lift_to_drag_max
    loiter_lift_to_drag = lift_to_drag_max
    return lift_to_drag_max, cruise_lift_to_drag, loiter_lift_to_drag


# --------------------------------------------------------------------------- #
# Propulsion
# --------------------------------------------------------------------------- #
def propulsion(mach, speed_of_sound, tsfc_cruise_per_hr, tsfc_loiter_per_hr):
    """Return ``(cruise_speed_ft_per_s, sfc_cruise_per_s, sfc_loiter_per_s)``.

    Cruise true airspeed is ``M * a``; the thrust-specific fuel consumptions are
    converted from per-hour to per-second for the Breguet equations.
    """
    cruise_speed = mach * speed_of_sound
    sfc_cruise = tsfc_cruise_per_hr / SECONDS_PER_HOUR
    sfc_loiter = tsfc_loiter_per_hr / SECONDS_PER_HOUR
    return cruise_speed, sfc_cruise, sfc_loiter


# --------------------------------------------------------------------------- #
# Mission fuel weight
# --------------------------------------------------------------------------- #
def breguet_range_ratio(range_ft, sfc_per_s, speed_ft_per_s, lift_to_drag):
    """Cruise-segment weight ratio from the Breguet range equation."""
    return jnp.exp(-(range_ft * sfc_per_s) / (speed_ft_per_s * lift_to_drag))


def breguet_endurance_ratio(endurance_s, sfc_per_s, lift_to_drag):
    """Loiter-segment weight ratio from the Breguet endurance equation."""
    return jnp.exp(-(endurance_s * sfc_per_s) / lift_to_drag)


def mission_segment_ratios(
    cruise_lift_to_drag,
    loiter_lift_to_drag,
    cruise_speed,
    sfc_cruise,
    sfc_loiter,
    range_ft,
    station_endurance_s,
    preland_endurance_s,
    warmup,
    climb,
    landing,
):
    """Return the seven mission-segment weight ratios (W2/W1 ... W8/W7)."""
    cruise_ratio = breguet_range_ratio(range_ft, sfc_cruise, cruise_speed, cruise_lift_to_drag)
    station_ratio = breguet_endurance_ratio(station_endurance_s, sfc_loiter, loiter_lift_to_drag)
    preland_ratio = breguet_endurance_ratio(preland_endurance_s, sfc_loiter, loiter_lift_to_drag)
    # Outbound and return cruise legs are identical, so cruise_ratio appears twice.
    return warmup, climb, cruise_ratio, station_ratio, cruise_ratio, preland_ratio, landing


def fuel_weight_fraction(
    cruise_lift_to_drag,
    loiter_lift_to_drag,
    cruise_speed,
    sfc_cruise,
    sfc_loiter,
    range_ft,
    station_endurance_s,
    preland_endurance_s,
    warmup,
    climb,
    landing,
    reserve,
    trapped,
):
    """Fuel weight fraction ``W_fuel / W_TO`` (with reserve + trapped allowances)."""
    ratios = mission_segment_ratios(
        cruise_lift_to_drag,
        loiter_lift_to_drag,
        cruise_speed,
        sfc_cruise,
        sfc_loiter,
        range_ft,
        station_endurance_s,
        preland_endurance_s,
        warmup,
        climb,
        landing,
    )
    mission_weight_fraction = jnp.prod(jnp.stack(ratios))  # W8 / W1
    mission_fuel = 1.0 - mission_weight_fraction
    return (1.0 + reserve + trapped) * mission_fuel


# --------------------------------------------------------------------------- #
# Structures (empty-weight fraction)
# --------------------------------------------------------------------------- #
def empty_weight_fraction(takeoff_gross_weight, coefficient, exponent, material_factor):
    """Raymer statistical empty-weight fraction ``We/WTO = a * WTO^b * K_mat``."""
    return coefficient * takeoff_gross_weight ** exponent * material_factor


# --------------------------------------------------------------------------- #
# Sizing residual (closes the loop)
# --------------------------------------------------------------------------- #
def sizing_residual(
    takeoff_gross_weight, fuel_weight_fraction_value, empty_weight_fraction_value, fixed_weight
):
    """Residual of the sizing identity ``WTO*(1 - Wf/WTO - We/WTO) - W_fixed = 0``.

    Driving this to zero is equivalent to the Raymer fixed point
    ``WTO = W_fixed / (1 - Wf/WTO - We/WTO)``.
    """
    return (
        takeoff_gross_weight
        * (1.0 - fuel_weight_fraction_value - empty_weight_fraction_value)
        - fixed_weight
    )
