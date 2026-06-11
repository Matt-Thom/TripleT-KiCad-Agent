"""Native KiCad exports via `kicad-cli`, when it is installed.

The agent's compiled artifacts are plain files, so anything beyond schematic
generation (KiCad's own ERC, netlist for the PCB editor, BOM CSV, printable
PDF) needs the real KiCad toolchain. This wrapper degrades gracefully: every
entry point first checks for `kicad-cli` and reports how to install it.

Gerber/drill export works the same way but needs a routed `.kicad_pcb`, which
the user produces in KiCad — see `export_pcb_gerbers`.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

_INSTALL_HINT = (
    "kicad-cli not found. Install KiCad 9 (https://www.kicad.org/download/) "
    "and ensure `kicad-cli` is on the PATH to run native KiCad exports."
)

_TIMEOUT_S = 120


@dataclass
class FabResult:
    ok: bool
    message: str
    outputs: list[str] = field(default_factory=list)


def kicad_cli_path() -> str | None:
    return shutil.which("kicad-cli")


def _run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args, capture_output=True, text=True, timeout=_TIMEOUT_S
    )
    detail = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, detail.strip()


def run_native_erc(sch_path: str | Path) -> FabResult:
    """Run KiCad's own ERC on a schematic, returning the report text."""
    cli = kicad_cli_path()
    if cli is None:
        return FabResult(ok=False, message=_INSTALL_HINT)
    sch = Path(sch_path)
    report = sch.with_suffix(".erc.rpt")
    code, detail = _run(
        [cli, "sch", "erc", "--output", str(report), "--severity-all", str(sch)]
    )
    report_text = report.read_text() if report.exists() else ""
    # kicad-cli exits non-zero when violations exist; that is still a
    # successful check from our point of view.
    if not report_text and code != 0:
        return FabResult(ok=False, message=f"kicad-cli sch erc failed: {detail}")
    return FabResult(
        ok=True,
        message=report_text or "ERC completed with no report output.",
        outputs=[str(report)] if report.exists() else [],
    )


def export_schematic_artifacts(sch_path: str | Path) -> FabResult:
    """Export netlist, BOM CSV, and PDF for a compiled schematic."""
    cli = kicad_cli_path()
    if cli is None:
        return FabResult(ok=False, message=_INSTALL_HINT)
    sch = Path(sch_path)
    jobs = [
        ("netlist", sch.with_suffix(".net"), ["sch", "export", "netlist"]),
        ("BOM", sch.with_suffix(".bom.csv"), ["sch", "export", "bom"]),
        ("PDF", sch.with_suffix(".pdf"), ["sch", "export", "pdf"]),
    ]
    outputs: list[str] = []
    failures: list[str] = []
    for label, out_path, cmd in jobs:
        code, detail = _run([cli, *cmd, "--output", str(out_path), str(sch)])
        if code == 0 and out_path.exists():
            outputs.append(str(out_path))
        else:
            failures.append(f"{label}: {detail or f'exit code {code}'}")
    if not outputs:
        return FabResult(ok=False, message="; ".join(failures) or "No artifacts produced.")
    message = f"Exported {len(outputs)} artifact(s)."
    if failures:
        message += " Failed: " + "; ".join(failures)
    return FabResult(ok=True, message=message, outputs=outputs)


def export_pcb_gerbers(pcb_path: str | Path, out_dir: str | Path | None = None) -> FabResult:
    """Export Gerbers + drill files for a routed board (.kicad_pcb)."""
    cli = kicad_cli_path()
    if cli is None:
        return FabResult(ok=False, message=_INSTALL_HINT)
    pcb = Path(pcb_path)
    if not pcb.exists():
        return FabResult(
            ok=False,
            message=(
                f"{pcb} does not exist. Route the board in KiCad first "
                "(open the project, Update PCB from Schematic, place and route)."
            ),
        )
    target = Path(out_dir) if out_dir else pcb.parent / f"{pcb.stem}_gerbers"
    target.mkdir(parents=True, exist_ok=True)
    code, detail = _run([cli, "pcb", "export", "gerbers", "--output", str(target), str(pcb)])
    if code != 0:
        return FabResult(ok=False, message=f"Gerber export failed: {detail}")
    code, detail = _run([cli, "pcb", "export", "drill", "--output", str(target), str(pcb)])
    if code != 0:
        return FabResult(ok=False, message=f"Drill export failed: {detail}")
    produced = sorted(str(p) for p in target.iterdir())
    return FabResult(ok=True, message=f"Gerbers and drill files in {target}.", outputs=produced)
