"""Ejecuta el notebook con el Python actual; kernel temporal dentro de storage/."""

import json
import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    kernel_root = ROOT / "storage/jupyter"
    spec = kernel_root / "kernels/milo-sprint1"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "MILO Sprint 1",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    os.environ["JUPYTER_PATH"] = str(kernel_root) + os.pathsep + os.environ.get("JUPYTER_PATH", "")
    path = ROOT / "notebooks/00_sprint1_validation.ipynb"
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook, timeout=90, kernel_name="milo-sprint1", resources={"metadata": {"path": str(ROOT)}}
    )
    client.execute()
    # El archivo compartido no depende del nombre del kernel temporal local.
    notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nbformat.write(notebook, path)
    report = {
        "notebook": path.relative_to(ROOT).as_posix(),
        "executed_code_cells": sum(c.cell_type == "code" for c in notebook.cells),
        "errors": 0,
    }
    (ROOT / "evaluation/results/notebook_execution.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
