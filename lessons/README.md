# Course lessons

Hands-on lessons in scientific-computing methods for engineering design
optimization. Every lesson uses the same shared model — the OpenMDAO + JAX ASW
conceptual-sizing example in
[`src/aircraft_sizing/examples/ex_01_asw`](../src/aircraft_sizing/examples/ex_01_asw) —
so the ideas build on one concrete artifact instead of a new toy each time.

Run all commands from the repository root with the `aircraft-sizing` environment
active (`conda activate aircraft-sizing`; see the top-level [README](../README.md)).

## Lessons

1. **[Design Structure Matrices (DSM), N2, and XDSM](lesson_01_dsm/docs/lesson_01_dsm.md)**
   — read a model's coupling structure; generate OpenMDAO's automatic N2 and a
   hand-authored pyXDSM.
   ```bash
   python lessons/lesson_01_dsm/generate_n2.py     # -> outputs/asw_n2.html
   python lessons/lesson_01_dsm/generate_xdsm.py   # -> outputs/asw_xdsm.pdf/.png
   ```

2. **[Iterative methods](lesson_02_iterative_methods/docs/lesson_02_iterative_methods.md)**
   — fixed point vs Newton vs Broyden, counting iterations and
   function/derivative evaluations; analytic (JAX) gradients vs finite difference.
   ```bash
   python lessons/lesson_02_iterative_methods/compare_solvers.py
   # -> outputs/solver_comparison.md, outputs/convergence.png
   ```

Each lesson has a `docs/` narrative, runnable scripts, and committed `outputs/` so
the figures render on GitHub without re-running anything. Rendering the XDSM to
PDF/PNG additionally needs `pdflatex` and `pdftoppm` on PATH.
