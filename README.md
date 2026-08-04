# Scientific Computing Methods for Engineering Design Optimization

This repository collects worked examples, reference notes, and interactive aircraft-sizing materials for the course. It ships an installable Python package, `sci-comp-eng-des-opt` (defined in `pyproject.toml`), plus a Streamlit app for the ASW (Anti-Submarine Warfare) fixed-point sizing example.

## Quickstart: run the ASW Streamlit example

Follow these steps to create a Conda environment, install the package into it, and launch the interactive ASW app with sliders for the mission parameters.

### 0. Prerequisites

- [Miniconda or Anaconda](https://docs.conda.io/en/latest/miniconda.html) (provides the `conda` command)
- [Git](https://git-scm.com/)

### 1. Get the code

```bash
git clone https://github.com/<your-account>/sci-comp-eng-des-opt.git
cd sci-comp-eng-des-opt
```

The E-19 electrified-aircraft example (ex_03) references a companion repository tracked as a git submodule. It is **not** required to run the ASW app, but if you want it, fetch it once with:

```bash
git submodule update --init references/ElectricAircraftDesignExample_AIAA2026
```

> Note: `conda`/`pip` do **not** download git submodules — only `git` does, via the command above (or `git clone --recurse-submodules`).

### 2. Create the Conda environment

From the repository root:

```bash
conda env create -f environment.yml --yes
```

`environment.yml` creates an environment named **`eng-des-opt-course`** (Python 3.12) and installs this package in editable mode (`-e .`), so the environment picks up local source edits automatically.

### 3. Activate the environment

```bash
conda activate eng-des-opt-course
```

### 4. Launch the Streamlit app

From the repository root, with the environment active:

```bash
python -m streamlit run apps/streamlit/app.py
```

Streamlit prints a **Local URL** (default <http://localhost:8501>) and usually opens it in your browser automatically. If it doesn't, open that URL yourself. Press `Ctrl+C` in the terminal to stop the server.

### 5. Use the app

The page has a **control sidebar on the left** and **results on the right**. Results recompute only when you click **Recompute** — so you can move several controls, then apply them all at once.

**Sidebar controls** (grouped in expanders):

- **Mission — sliders.** Drag to change the three headline mission parameters: one-way cruise range, mission-equipment weight, and on-station loiter endurance.
- **Propulsion — number fields.** Cruise and loiter TSFC.
- **Aerodynamics — number fields.** Wing aspect ratio and wetted-area ratio S_wet/S_ref. Maximum L/D is *computed* from these (Raymer Eq. 3.12), not entered.
- **Structure — radio.** Switch between **metal** and **composite** (composite scales the empty-weight fraction by 0.95).
- **Solver controls — number fields.** Initial TOGW guess, convergence tolerance, and maximum iterations.
- **One-at-a-time sensitivity sweep.** Pick the swept input — cruise range, mission-equipment weight, aspect ratio, or cruise TSFC — plus the ± span (slider) and number of samples.

Everything else (cruise Mach, altitude, speed of sound, crew weight, prelanding loiter, historical segment ratios, and the fuel/empty-weight allowances) stays fixed at the Raymer 3.6 baseline.

**Buttons:**

- **Recompute** — re-solve using the current sidebar values.
- **Reset baseline** — restore the approved baseline inputs and re-solve.

**Results** (top metrics + four tabs):

- **Metrics row:** Final TOGW, fuel weight, empty weight, and iteration count.
- **Overview:** mission-profile table and the sizing XDSM diagram.
- **Intermediate calculations:** derived cruise/aero quantities, mission segment ratios, mission and fuel fractions, and the final mass breakdown.
- **Convergence:** the fixed-point convergence plot and the iteration-by-iteration table.
- **Sensitivity & sanity checks:** the one-at-a-time TOGW sensitivity plot and table, plus automated sanity checks.

**Try it:** drag the **One-way cruise range** slider up, click **Recompute**, and watch the **Final TOGW** metric rise (a longer cruise burns more fuel, so the sized aircraft gets heavier). Then switch the **Sensitivity** tab's swept input to explore how each assumption drives the final weight. Click **Reset baseline** to return to the defaults.

## Maintaining the environment

If you change package metadata or dependencies, refresh the editable install (with the environment active):

```bash
python -m pip install -e .
```

## Canonical course documents

### Example narratives

- **ex_01 —** [ASW fixed-point sizing narrative](src/aircraft_sizing/examples/ex_01_asw/docs/ex_01_asw_sizing.md) (fuel-based, from Raymer)
- **ex_02 —** [Electrified aircraft — worked examples](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/ex_02_electrified_aircraft.md) (AIAA Short Course), a set of isolated examples:
  - [Range equation](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/01_range_equation.md)
  - [Reference airplane](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/02_reference_airplane.md)
  - [Electric drive train (EDT) SOA energy](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/03_edt_soa_energy.md)
  - [Reduced-order battery sizing](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/04_battery_sizing.md)
- **ex_03 —** [Electrified aircraft (E-19) sizing narrative](src/aircraft_sizing/examples/ex_03_e19_hybrid_electric/docs/ex_03_electrified_aircraft_sizing.md) (hybrid-electric, from de Vries et al., AIAA 2026-4690)

### Course lessons

- [Lesson 1 — Design Structure Matrices (DSM), N2, and XDSM](lessons/lesson_01_dsm/docs/lesson_01_dsm.md)
- [Lesson 2 — Iterative methods: fixed-point vs Newton vs Broyden, gradients vs finite difference](lessons/lesson_02_iterative_methods/docs/lesson_02_iterative_methods.md)

### Reference notes

- [Electrified-aircraft equations](src/aircraft_sizing/examples/ex_02_electrified_aircraft/docs/electrified_aircraft_equations.md)

## Deploying to Streamlit Community Cloud

Set the app entry point to `apps/streamlit/app.py` and keep the repository-root `requirements.txt` as the install source — it installs this package for deployment. Use the app path above as the launch target.
