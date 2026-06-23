"""Create a timestamped experiment run folder from a config file."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--experiments-dir", default=Path("experiments"), type=Path)
    args = parser.parse_args()

    run_dir = args.experiments_dir / args.run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    config = json.loads(args.config.read_text(encoding="utf-8"))
    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (run_dir / "notes.md").write_text(
        f"# {args.run_id}\n\nCreated: {datetime.now().isoformat()}\n\n## Notes\n\n",
        encoding="utf-8",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
