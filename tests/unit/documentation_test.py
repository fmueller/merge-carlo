from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "docs").is_dir():
    ROOT = ROOT.parent


@pytest.mark.unit
def test_release_status_distinguishes_completed_limited_unsupported_and_remaining_work() -> None:
    status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")

    assert "| M1 |" in status and "| Complete |" in status
    assert "## Verification evidence" in status
    assert "## Limited or unverified" in status
    assert "## Unsupported in v0.1.0" in status
    assert "## Remaining v0.1.0 work" in status
    assert "Live GitHub integration has not been run" in status
    assert "mise run check" in status


@pytest.mark.unit
def test_release_docs_cover_console_contract_and_report_limitations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    limitations = (ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")
    report = (ROOT / "src" / "merge_carlo" / "reporting.py").read_text(encoding="utf-8")

    for code in ("`0`", "`2`", "`3`", "`4`"):
        assert code in readme
    assert "--json" in readme
    assert "Live GitHub integration has not been run" in readme
    assert "active review effort" in limitations
    assert "defect_escape_rate: null" in report
    assert "Historical fit is not causal validation" in report
