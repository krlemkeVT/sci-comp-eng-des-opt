# Electrified Aircraft — Worked Examples

A set of short, self-contained worked examples that build intuition for **electrified
aircraft sizing** one idea at a time. They are drawn from the **AIAA Short Course on
Electrified Aircraft Sizing** (Dr. Brian J. German, June 2018; showcase calculations by
Marty K. Bradley; drivetrain and battery worksheets by J. Lents).

Unlike the full end-to-end sizing loop of the [E-19 hybrid-electric example](../../ex_03_e19_hybrid_electric/docs/ex_03_electrified_aircraft_sizing.md),
each example here isolates a **single concept** so it can be checked by hand. Read them in
order — each builds on the equations of the one before.

## Sub-examples (recommended reading order)

1. **[Range equation](01_range_equation.md)** — the electrified-aircraft range equation,
   worked from the battery-mass-fraction form to a numeric answer (≈231 km), with careful
   unit resolution. The starting point for everything else.

2. **[Reference airplane](02_reference_airplane.md)** — apply the range equation to a
   reference airplane (Dr. German's *"instructive example"*) and watch the ideal Breguet
   range get **progressively eroded** by installation weight, takeoff/climb overhead,
   reserves, the usable SOC window, and end-of-life degradation — through seven showcases,
   ending with a VTOL variant whose mission does not even close.

3. **[Electric drive train (EDT) energy — SOA components](03_edt_soa_energy.md)** — compare
   the mission energy of **five powertrain architectures** (conventional, turboelectric with
   and without battery, and two parallel hybrids) on a common mission, including the payload
   penalty of the added drivetrain and battery weight.

4. **[Reduced-order battery sizing](04_battery_sizing.md)** — size a battery pack from a
   required **energy** and **peak power** using a purely feed-forward model. The `max()` in
   the capacity equation is the whole lesson: a pack is either energy-limited or
   power-limited, and two worked cases land on opposite sides of that crossover.

## Reference note

- **[Equations for electrified aircraft](electrified_aircraft_equations.md)** — the range
  and total-mass equations used above, with the derivation of the mass equation from the
  range equation.
