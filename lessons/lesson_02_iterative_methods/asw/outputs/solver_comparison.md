# Lesson 2 — solver & derivative comparison (generated)

## Nonlinear solvers (analytic JAX gradients)

| Solver | Iterations | Function evals | Derivative evals | Converged TOGW [lb] |
|---|---|---|---|---|
| Fixed point (Gauss-Seidel) | 17 | 85 | 0 | 57615.87 |
| Fixed point + Aitken | 7 | 35 | 0 | 57615.87 |
| Newton | 7 | 110 | 35 | 57615.87 |
| Broyden | 11 | 285 | 20 | 57615.87 |

## Newton: analytic JAX Jacobian vs finite-difference partials

| Derivative source | Iterations | Function evals | Derivative evals | Converged TOGW [lb] |
|---|---|---|---|---|
| JAX (analytic) | 7 | 110 | 35 | 57615.87 |
| Finite difference | 7 | 243 | 0 | 57615.87 |

## Total derivative dW_TO/d(input): analytic JAX vs finite difference

| Input | Analytic (JAX) | Finite difference | Relative difference |
|---|---|---|---|
| `aero.wing_aspect_ratio` | -5.066073e+03 | -5.066073e+03 | 3.17e-08 |
| `prop.tsfc_cruise_per_hr` | 1.114959e+05 | 1.114959e+05 | 2.25e-10 |
| `mission.range_ft` | 6.116739e-03 | 6.116739e-03 | 1.99e-11 |
