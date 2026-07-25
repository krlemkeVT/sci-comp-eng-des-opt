from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


DIAGRAM_BASENAME = "asw_sizing_xdsm"
SOURCE_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = SOURCE_DIR.parents[1]  # .../examples/ex_05_asw


def _find_repo_root() -> Path:
    for candidate in (SOURCE_DIR, *SOURCE_DIR.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(f"Could not locate repository root from {SOURCE_DIR}.")


REPO_ROOT = _find_repo_root()
PNG_OUTPUT_DIR = EXAMPLE_DIR / "docs" / "assets" / "images"
PDF_OUTPUT_DIR = EXAMPLE_DIR / "docs" / "assets" / "reference"
SCRIPT_COMMAND = f"python {Path(__file__).resolve().relative_to(REPO_ROOT)}"


class MissingPrerequisiteError(RuntimeError):
    """Raised when rendering prerequisites are unavailable."""


def _pyxdsm_api():
    try:
        from pyxdsm.XDSM import FUNC, RIGHT, SOLVER, XDSM
    except ModuleNotFoundError as exc:
        raise MissingPrerequisiteError(
            "Missing prerequisite: Python package 'pyXDSM' is not installed in the active "
            f"environment. Install it, then rerun `{SCRIPT_COMMAND}` from the repository root."
        ) from exc

    return XDSM, SOLVER, FUNC, RIGHT


def _require_executable(name: str, purpose: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise MissingPrerequisiteError(
            f"Missing prerequisite: executable '{name}' is required for {purpose}. "
            f"After installing it, rerun `{SCRIPT_COMMAND}`."
        )
    return executable


def build_xdsm():
    """Build the fixed-point ASW sizing XDSM described in ex_05_asw_sizing.md."""
    XDSM, SOLVER, FUNC, RIGHT = _pyxdsm_api()

    xdsm = XDSM(use_sfmath=False)

    xdsm.add_system("solver", SOLVER, (r"\text{Fixed-point}", r"\text{solver}"))
    xdsm.add_system("fuel", FUNC, (r"\text{Mission fuel-}", r"\text{fraction analysis}"))
    xdsm.add_system("empty", FUNC, (r"\text{Empty-weight}", r"\text{fraction analysis}"))
    xdsm.add_system("update", FUNC, (r"\text{TOGW}", r"\text{update}"))

    xdsm.add_input("solver", (r"W_{TO}^{(0)}", r"\varepsilon_{\text{conv}}"))
    xdsm.add_input(
        "fuel",
        (
            r"\text{mission data}",
            r"M, R, E",
            r"L/D, \mathrm{sfc}",
            r"\text{fuel allowances}",
        ),
    )
    xdsm.add_input("empty", r"0.93\,W_{TO}^{-0.07}")
    xdsm.add_input("update", r"W_{\text{fixed}} = 10{,}800~\mathrm{lb}")

    xdsm.connect("solver", "empty", r"W_{TO}^{(k)}")
    xdsm.connect("fuel", "update", r"W_f / W_{TO}")
    xdsm.connect("empty", "update", r"W_e / W_{TO}")
    xdsm.connect("update", "solver", r"W_{TO}^{(k+1)}")

    xdsm.add_output("solver", r"W_{TO}^{*}", side=RIGHT)

    xdsm.add_process(["output_fuel", "fuel", "update"], arrow=True)
    xdsm.add_process(["output_solver", "solver", "empty", "update", "solver"], arrow=True)

    return xdsm


def _cleanup_latex_artifacts(stem: Path) -> None:
    for suffix in (".aux", ".fdb_latexmk", ".fls", ".log"):
        artifact = stem.with_suffix(suffix)
        if artifact.exists():
            artifact.unlink()


def _copy_output(source_path: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_path = destination_dir / source_path.name
    shutil.copy2(source_path, destination_path)
    return destination_path


def _render_pdf(tex_path: Path) -> Path:
    _require_executable("pdflatex", "pyXDSM PDF rendering")

    subprocess.run(
        [
            "pdflatex",
            "-halt-on-error",
            "-interaction=nonstopmode",
            tex_path.name,
        ],
        cwd=tex_path.parent,
        check=True,
    )

    pdf_path = _copy_output(tex_path.with_suffix(".pdf"), PDF_OUTPUT_DIR)
    source_pdf_path = tex_path.with_suffix(".pdf")
    if source_pdf_path.exists():
        source_pdf_path.unlink()
    _cleanup_latex_artifacts(tex_path.with_suffix(""))
    return pdf_path


def _render_png(pdf_path: Path) -> Path | None:
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        return None

    PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    png_prefix = PNG_OUTPUT_DIR / pdf_path.with_suffix("").name
    subprocess.run(
        [pdftoppm, "-png", "-singlefile", str(pdf_path), str(png_prefix)],
        check=True,
    )
    return png_prefix.with_suffix(".png")


def render() -> list[Path]:
    """Render the diagram assets into the approved source and documentation paths."""
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    xdsm = build_xdsm()
    xdsm.write(DIAGRAM_BASENAME, build=False, cleanup=True, outdir=str(SOURCE_DIR))

    tex_path = SOURCE_DIR / f"{DIAGRAM_BASENAME}.tex"
    tikz_path = SOURCE_DIR / f"{DIAGRAM_BASENAME}.tikz"
    pdf_path = _render_pdf(tex_path)
    png_path = _render_png(pdf_path)

    outputs = [tikz_path, tex_path, pdf_path]
    if png_path is not None:
        outputs.append(png_path)

    return outputs


def _format_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        outputs = render()
    except MissingPrerequisiteError as exc:
        print(exc, file=sys.stderr)
        print(f"Render command: {SCRIPT_COMMAND}", file=sys.stderr)
        return 1

    print("Rendered:", ", ".join(_format_relative(path) for path in outputs))

    png_path = PNG_OUTPUT_DIR / f"{DIAGRAM_BASENAME}.png"
    if png_path.exists():
        print(f"Markdown embed: ![ASW sizing XDSM]({_format_relative(png_path)})")
    else:
        pdf_path = PDF_OUTPUT_DIR / f"{DIAGRAM_BASENAME}.pdf"
        print(f"Markdown link: [ASW sizing XDSM]({_format_relative(pdf_path)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
