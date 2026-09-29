"""
Label a benchmark. Slow, because the rules engine is.

Run once and commit the result: labelling is deterministic given a seed, so
re-running it in CI would burn minutes to reproduce a file already in the
repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import (
    abstain_if_anything_missing, always_abstain, always_answer,
    build_benchmark, label_benchmark, oracle_policy, score,
)
from .determinability import Oracle

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="underdetermined.build")
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--material-spread", type=float, default=50.0)
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    oracle = Oracle()
    cases = build_benchmark(args.n, seed=args.seed)
    print(f"labelling {len(cases)} cases against the rules engine...", flush=True)
    results = label_benchmark(cases, oracle,
                              material_spread=args.material_spread,
                              progress=True)

    det = sum(1 for r in results if r.label.value == "determinable")
    print(f"  {det} determinable, {len(results) - det} underdetermined")
    print(f"  {len(oracle._cache)} distinct engine evaluations")

    (out / "benchmark.json").write_text(
        json.dumps([r.as_dict() for r in results], indent=2))

    rows = []
    for name, fn in [("always answer", always_answer),
                     ("always abstain", always_abstain),
                     ("abstain if anything missing", abstain_if_anything_missing),
                     ("oracle (ceiling)", oracle_policy)]:
        s = score(results, fn(results))
        rows.append({"policy": name, **s.as_dict()})
    (out / "baselines.json").write_text(json.dumps(rows, indent=2))

    print()
    print(f"  {'policy':30s} {'unsafe':>8s} {'coverage':>9s}")
    for r in rows:
        print(f"  {r['policy']:30s} {r['unsafe_rate']:>7.1%} {r['coverage']:>9.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
