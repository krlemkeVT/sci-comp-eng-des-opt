from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


DIAGRAM_BASENAME = "asw_sizing_xdsm"
SOURCE_DIR = Path(__file__).resolve().parent
EXAMPLE_DIR = SOURCE_DIR.parents[1]  # .../examples/ex_01_asw


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
    """Build the ASW multidisciplinary sizing XDSM described in ex_01_asw_sizing.md.

    Five disciplines wired the way the OpenMDAO group is: aerodynamics and
    propulsion feed the mission-fuel analysis (feed-forward), which feeds the
    sizing residual. The only feedback edge is Sizing -> Structures via W_TO, and
    that loop is what the nonlinear solver drives.
    """
    XDSM, SOLVER, FUNC, RIGHT = _pyxdsm_api()

    xdsm = XDSM(use_sfmath=False)

    # Diagonal order chosen so the single feedback edge (sizing -> solver) is the
    # only entry below the diagonal.
    xdsm.add_system("aero", FUNC, (r"\text{Aerodynamics}",))
    xdsm.add_system("prop", FUNC, (r"\text{Propulsion}",))
    xdsm.add_system("mission", FUNC, (r"\text{Mission fuel}",))
    xdsm.add_system("solver", SOLVER, (r"\text{Nonlinear}", r"\text{solver}"))
    xdsm.add_system("struct", FUNC, (r"\text{Structures}",))
    xdsm.add_system("sizing", FUNC, (r"\text{Sizing}", r"\text{residual}"))

    xdsm.add_input("aero", r"AR,\ S_{wet}/S_{ref}")
    xdsm.add_input("prop", r"M,\ a,\ \mathrm{sfc}")
    xdsm.add_input("mission", r"R,\ E")
    xdsm.add_input("solver", (r"W_{TO}^{(0)}", r"\varepsilon_{\text{conv}}"))
    xdsm.add_input("sizing", r"W_{\text{fixed}}")

    # Feed-forward couplings (upper triangle).
    xdsm.connect("aero", "mission", r"L/D")
    xdsm.connect("prop", "mission", r"V,\ \mathrm{sfc}")
    xdsm.connect("mission", "sizing", r"W_f / W_{TO}")

    # The solver-driven feedback loop between Structures and the Sizing residual.
    xdsm.connect("solver", "struct", r"W_{TO}^{(k)}")
    xdsm.connect("struct", "sizing", r"W_e / W_{TO}")
    xdsm.connect("sizing", "solver", r"\mathcal{R}(W_{TO})")

    xdsm.add_output("solver", r"W_{TO}^{*}", side=RIGHT)

    xdsm.add_process(["aero", "mission", "sizing"], arrow=True)
    xdsm.add_process(["prop", "mission"], arrow=True)
    xdsm.add_process(["solver", "struct", "sizing", "solver"], arrow=True)

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
