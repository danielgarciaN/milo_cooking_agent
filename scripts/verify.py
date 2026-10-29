"""Guarda evidencia real de tests, dependencias, estilo, importación y notebook."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    commands = [
        [sys.executable, "-m", "pytest", "-q", "--junitxml=evaluation/results/pytest.xml"],
        [sys.executable, "-m", "ruff", "check", "src", "scripts", "tests"],
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "scripts/run_notebook.py"],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(
            command,
            check=False,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        label = "python " + " ".join(command[1:])
        results.append(
            {
                "command": label,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        print(label, "->", completed.returncode, flush=True)
    xml = ROOT / "evaluation/results/pytest.xml"
    suites = ET.parse(xml).getroot().findall("testsuite") if xml.exists() else []
    counts = {
        key: sum(int(s.get(key, "0")) for s in suites) for key in ["tests", "failures", "errors", "skipped"]
    }
    report = {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "python_version": sys.version.split()[0],
        "success": all(r["exit_code"] == 0 for r in results),
        "pytest": counts,
        "checks": results,
    }
    (ROOT / "evaluation/results/verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"success": report["success"], "pytest": counts}))
    if not report["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
