# Scientific Computing Methods for Engineering Design Optimization

This repository collects worked examples, reference notes, and interactive aircraft-sizing materials for the course.

## Installable aircraft-sizing package

The repository now ships an installable Python package, `sci-comp-eng-des-opt-aircraft-sizing`, defined in `pyproject.toml`.

### Conda environment (recommended for local work)

Create the separate Conda environment from the repository root:

```bash
conda env create -f environment.yml --yes
conda activate aircraft-sizing
```

On this Windows machine, if global Conda ToS or libmamba configuration interferes with the normal command, use this verified PowerShell fallback instead:

```powershell
$env:CONDA_NO_PLUGINS='true'; conda env create -f environment.yml --yes --solver classic; Remove-Item Env:CONDA_NO_PLUGINS -ErrorAction SilentlyContinue
```

`environment.yml` defines the `aircraft-sizing` environment, uses the `conda-forge` and `nodefaults` channels, and installs the package in editable mode (`-e .`), so the environment picks up local source edits without duplicating dependency lists here.

## Canonical course documents

### Example narratives

- [Range equation worked example](src/aircraft_sizing/examples/ex_01_range/docs/ex_01_range_calculation.md)
- [Reference-airplane worked example](src/aircraft_sizing/examples/ex_02_reference_airplane/docs/ex_02_reference_airplane.md)
- [Electric drive train SOA energy example](src/aircraft_sizing/examples/ex_03_edt_soa/docs/ex_03_edt_soa_example.md)
- [ASW fixed-point sizing narrative](src/aircraft_sizing/examples/ex_05_asw/docs/ex_05_asw_sizing.md)
- [Electrified aircraft (E-19) sizing narrative](src/aircraft_sizing/examples/ex_06_e19_hybrid_electric/docs/ex_06_electrified_aircraft_sizing.md)

### Reference notes

- [Electrified-aircraft equations](src/aircraft_sizing/examples/ex_01_range/docs/electrified_aircraft_equations.md)

## ASW interactive app

### Local launch

From the repository root:

```bash
python -m streamlit run apps/streamlit/app.py
```

### Editable reinstall / update

If you need to refresh the editable install after updating package metadata, rerun:

```bash
python -m pip install -e .
```

### Streamlit Community Cloud

For Streamlit Community Cloud, set the app entry point to `apps/streamlit/app.py` and keep the repository-root `requirements.txt` as the install source. That file installs the repository package for deployment; use the app path above as the launch target.
