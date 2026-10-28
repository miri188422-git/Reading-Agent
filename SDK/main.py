"""Entry point for the Claude Agent SDK reading agent.
# replaces: API/main.py
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claude_agent_sdk import __version__ as sdk_version

from SDK.agent import Agent, MODEL, EFFORT
from shared.loc import count_dir
from shared.scenario import run_scenario


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description="Run the SDK reading-agent scenario"
    )
    parser.add_argument(
        "--scenario", default=str(ROOT / "scenario.json")
    )
    parser.add_argument(
        "--out", default=str(ROOT / "results" / "sdk.json")
    )
    args = parser.parse_args()

    scenario_path = Path(args.scenario).resolve()
    out_path = Path(args.out).resolve()

    meta = {
        "harness": "SDK",
        "model": MODEL,
        "effort": EFFORT,
        "sdk_version": sdk_version,
        "loc": count_dir(ROOT / "SDK")["total"],
    }

    result = run_scenario(
        scenario_path=scenario_path,
        make_agent=lambda session_id: Agent(session_id),
        out_path=out_path,
        label="sdk",
        meta=meta,
        data_root=ROOT / "data",
    )

    print("\nSDK run complete.")
    print(json.dumps(result.get("totals", {}), indent=2))


if __name__ == "__main__":
    main()
