"""Compruebo el proyecto sin generar informes duplicados; --live consume API."""

import argparse
import subprocess
import sys

from milo.config import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Incluye Gemini real y ejecuta el notebook")
    args = parser.parse_args()
    commands = [
        [sys.executable, "-m", "pytest", "-q", *(["--live"] if args.live else [])],
        [sys.executable, "-m", "ruff", "check", "src", "scripts", "tests"],
        [sys.executable, "-m", "pip", "check"],
    ]
    if args.live:
        commands.append([sys.executable, "scripts/run_notebook.py"])
    for command in commands:
        print("python " + " ".join(command[1:]), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
