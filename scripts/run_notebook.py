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
    spec = kernel_root / "kernels/milo-final"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "MILO Proyecto Final",
                "language": "python",
            }
        ),
        encoding="utf-8",
    )
    os.environ["JUPYTER_PATH"] = str(kernel_root) + os.pathsep + os.environ.get("JUPYTER_PATH", "")
    path = ROOT / "MILO_Proyecto_Final.ipynb"
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook, timeout=600, kernel_name="milo-final", resources={"metadata": {"path": str(ROOT)}}
    )
    # No conservo salidas antiguas de celdas que quizá no lleguen a ejecutarse.
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    try:
        client.execute()
    finally:
        # Guardo también un fallo real; nunca aparento que terminaron todas las celdas.
        notebook.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
        nbformat.write(notebook, path)
    report = {
        "notebook": path.relative_to(ROOT).as_posix(),
        "executed_code_cells": sum(c.cell_type == "code" for c in notebook.cells),
        "errors": 0,
    }
    print(json.dumps(report))


if __name__ == "__main__":
    main()
