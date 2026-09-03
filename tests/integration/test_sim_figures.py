"""Sim figure artifact verification."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "tools" / "feasibility" / "run_cfi_sim.py"
VERIFY = ROOT / "scripts" / "ci" / "verify_figures.py"


def test_all_section9_figures_generated() -> None:
    result = subprocess.run([sys.executable, str(SIM)], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    fig_result = subprocess.run([sys.executable, str(VERIFY)], cwd=ROOT, capture_output=True, text=True)
    assert fig_result.returncode == 0, fig_result.stderr
    assert "Figure verification OK" in fig_result.stdout

    meta = json.loads((ROOT / "tools" / "feasibility" / "output" / "study_meta.json").read_text(encoding="utf-8"))
    assert meta["seed"] == 421337
    for stem in [
        "fig1_lodo_f1",
        "fig5_dp",
        "fig8_threat_model",
    ]:
        assert (ROOT / "tools" / "feasibility" / "output" / "figures" / f"{stem}.png").exists()
