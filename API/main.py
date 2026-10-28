"""API version entry point.

    python API/main.py --scenario scenario.json --out results/api.json

Needs ANTHROPIC_API_KEY in the terminal environment (never in code or git).
"""
import argparse
import os
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import truststore  # noqa: E402

truststore.inject_into_ssl()  # use the OS certificate store (needed behind a TLS-inspecting filter)

from API.agent import make_agent  # noqa: E402
from API.harness.loop import EFFORT, MODEL  # noqa: E402
from shared.loc import count_dir  # noqa: E402
from shared.scenario import run_scenario  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the reading-list scenario on the raw Messages API harness.")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Set it in this terminal only: "
                 '$env:ANTHROPIC_API_KEY = "<your key>"')

    meta = {
        "harness": "API",
        "model": MODEL,
        "effort": EFFORT,
        "libraries": {"anthropic": version("anthropic")},
        "harness_loc": count_dir(ROOT / "API" / "harness"),
    }
    run_scenario(args.scenario, make_agent, args.out, label="api", meta=meta, data_root=ROOT / "data")


if __name__ == "__main__":
    main()