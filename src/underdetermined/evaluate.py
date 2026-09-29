"""
Score a real model on the committed benchmark.

Reads labels from disk rather than recomputing them, so evaluating an agent
does not require the rules engine — only the labels it produced.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import AgentConfig, run_agent
from .benchmark import Verdict, score
from .determinability import (
    Case, Determinability, DeterminabilityResult, Household,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> list[DeterminabilityResult]:
    """Rebuild labelled results from the committed benchmark."""
    out = []
    for row in json.loads(path.read_text()):
        # The household is not reconstructed: evaluation needs the description
        # the agent sees and the label, not the underlying record.
        r = DeterminabilityResult(
            case=Case(Household(), tuple(row["withheld"])),
            label=Determinability(row["label"]),
            truth=Verdict(row["truth"]),
            spread=row["spread"],
            flips_eligibility=row.get("flips_eligibility", False),
        )
        r.case.describe = lambda d=row["description"]: d   # type: ignore[method-assign]
        out.append(r)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="underdetermined.evaluate")
    ap.add_argument("--benchmark", default=str(ROOT / "evidence" / "benchmark.json"))
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "evidence" / "agent.json"))
    args = ap.parse_args(argv)

    results = load(Path(args.benchmark))
    if args.limit:
        results = results[:args.limit]

    print(f"scoring {args.model} on {len(results)} cases...", flush=True)
    verdicts = run_agent(results, AgentConfig(model=args.model), progress=True)
    s = score(results, verdicts)

    Path(args.out).write_text(json.dumps(
        {"model": args.model, **s.as_dict(), "detail": s.detail}, indent=2))
    print()
    print(s.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
