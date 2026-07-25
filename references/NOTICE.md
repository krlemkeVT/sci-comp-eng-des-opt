# Third-Party References

## ElectricAircraftDesignExample_AIAA2026 (git submodule)

- **What:** Open-source companion code (Jupyter notebook + Python modules) for the paper
  *"Conceptual Design of Electrified Aircraft: A Practical Guide for Engineering Students
  and Practitioners"* (de Vries et al., **AIAA 2026-4690**, AIAA AVIATION 2026).
- **Upstream:** <https://github.com/EAT-AD-TC/ElectricAircraftDesignExample_AIAA2026>
- **Pinned to:** tag `v1.0` (commit `b3af7f2`).
- **Provenance:** A non-profit initiative of the AIAA Electrified Aircraft Technologies (EAT)
  and Aircraft Design (AD) Technical Committees. © 2026 the paper's authors.
- **Why it's here:** Referenced by
  [`ex_06_electrified_aircraft_sizing.md`](../src/aircraft_sizing/examples/ex_06_e19_hybrid_electric/docs/ex_06_electrified_aircraft_sizing.md)
  for equation-to-code cross-references and to let students run the E-19 worked example.

### How it is included

It is a **git submodule** — this repository stores only a *pointer* (commit SHA in
`.gitmodules` + a gitlink), **not** a copy of the upstream source. To fetch it:

```bash
git submodule update --init references/ElectricAircraftDesignExample_AIAA2026
```

### ⚠ License status

The upstream repository ships **no `LICENSE` file**, so formal reuse terms are not granted.
It is included here **by reference only** (submodule pointer) for non-commercial educational
use, with attribution. Before redistributing the code, vendoring a copy into this repo's
history, or publishing derivatives, **confirm reuse terms with the authors / AIAA EAT-TC**.

The accompanying course document restates equations and factual data from the paper in our
own words with citation; it does not reproduce the paper's prose or figures.
