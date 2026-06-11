from unittest.mock import patch

from backend.services import fabrication


def test_missing_kicad_cli_reports_install_hint(tmp_path):
    sch = tmp_path / "board.kicad_sch"
    sch.write_text("(kicad_sch)")
    with patch("backend.services.fabrication.shutil.which", return_value=None):
        res = fabrication.run_native_erc(sch)
    assert not res.ok
    assert "kicad-cli not found" in res.message

    with patch("backend.services.fabrication.shutil.which", return_value=None):
        res = fabrication.export_schematic_artifacts(sch)
    assert not res.ok
    assert "kicad-cli not found" in res.message


def test_native_erc_reads_report(tmp_path):
    sch = tmp_path / "board.kicad_sch"
    sch.write_text("(kicad_sch)")
    report = tmp_path / "board.erc.rpt"

    def fake_run(args, capture_output, text, timeout):
        report.write_text("ERC report: 2 warnings")

        class P:
            returncode = 5  # kicad-cli exits non-zero when violations exist
            stdout = ""
            stderr = ""

        return P()

    with patch("backend.services.fabrication.shutil.which", return_value="/usr/bin/kicad-cli"):
        with patch("backend.services.fabrication.subprocess.run", side_effect=fake_run):
            res = fabrication.run_native_erc(sch)

    assert res.ok
    assert "2 warnings" in res.message
    assert res.outputs == [str(report)]


def test_export_artifacts_collects_outputs_and_failures(tmp_path):
    sch = tmp_path / "board.kicad_sch"
    sch.write_text("(kicad_sch)")

    def fake_run(args, capture_output, text, timeout):
        out_idx = args.index("--output") + 1
        out_path = args[out_idx]

        class P:
            returncode = 0
            stdout = ""
            stderr = ""

        if out_path.endswith(".pdf"):
            P.returncode = 1
            P.stderr = "pdf renderer unavailable"
        else:
            open(out_path, "w").write("x")
        return P()

    with patch("backend.services.fabrication.shutil.which", return_value="/usr/bin/kicad-cli"):
        with patch("backend.services.fabrication.subprocess.run", side_effect=fake_run):
            res = fabrication.export_schematic_artifacts(sch)

    assert res.ok
    assert len(res.outputs) == 2  # netlist + bom; pdf failed
    assert "pdf renderer unavailable" in res.message


def test_gerber_export_requires_existing_pcb(tmp_path):
    with patch("backend.services.fabrication.shutil.which", return_value="/usr/bin/kicad-cli"):
        res = fabrication.export_pcb_gerbers(tmp_path / "board.kicad_pcb")
    assert not res.ok
    assert "Route the board in KiCad first" in res.message
