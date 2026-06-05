#!/usr/bin/env python3
"""Benchmark LLM providers on synthetic scenario subset."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from conductgene.config import Settings
from conductgene.eval.metrics import citation_ok
from conductgene.eval.scenarios import load_all_scenarios
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.logutil import setup_logging
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.providers.llm import resolve_llm_config
from conductgene.schemas import SwarmAnalyzeRequest

OUTPUT_DIR = ROOT / "outputs" / "benchmarks"

# Rough USD per 1M tokens (dev estimates for cost cap display)
COST_PER_1M = {
    "openai/gpt-4.1-mini": 0.15,
    "anthropic/claude-sonnet-4": 3.0,
    "google/gemini-2.5-flash-preview": 0.10,
}


async def bench_model(
    settings: Settings,
    model: str,
    case_ids: list[str],
) -> dict:
    kb = MemoryKnowledgeBase(settings.kb_dir)
    gene_path = Path(tempfile.mkdtemp()) / "bench_genes.jsonl"
    genes = GeneStore(gene_path)
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}

    if settings.llm_provider == "openrouter":
        cfg_settings = settings.model_copy(update={"openrouter_models": model, "mode": "live"})
    elif settings.llm_provider == "lmstudio":
        cfg_settings = settings.model_copy(update={"lmstudio_model": model, "mode": "live"})
    else:
        cfg_settings = settings.model_copy(update={"llm_model": model, "mode": "live"})
    resolve_llm_config(cfg_settings, model_override=model)

    latencies: list[float] = []
    passed = 0
    citations = 0
    abstains = 0

    for cid in case_ids:
        sc = scenarios[cid]
        t0 = time.perf_counter()
        result = await swarm_analyze(
            settings=cfg_settings,
            kb=kb,
            gene_store=genes,
            request=SwarmAnalyzeRequest(
                transcript=sc.transcript,
                case_id=sc.id,
                apply_genes=False,
            ),
        )
        latencies.append(time.perf_counter() - t0)
        if result.abstained:
            abstains += 1
        if citation_ok(result):
            citations += 1
        golden_dict = sc.golden.model_dump()
        ok = True
        if sc.golden.abstain != result.abstained:
            ok = False
        for key in (
            "threat_language",
            "escalation_offered",
            "company_disclosure",
            "recording_disclosure",
        ):
            expected = golden_dict.get(key)
            if expected is None:
                continue
            actual = next((c.status for c in result.checklist if c.id == key), None)
            if actual != expected:
                ok = False
        if ok:
            passed += 1

    n = len(case_ids)
    cost_rate = COST_PER_1M.get(model, 1.0)
    est_tokens = n * 3 * 1500
    return {
        "model": model,
        "cases": n,
        "pass_rate": passed / n if n else 0,
        "citation_coverage": citations / n if n else 0,
        "abstain_rate": abstains / n if n else 0,
        "latency_p50_s": sorted(latencies)[len(latencies) // 2] if latencies else 0,
        "latency_p95_s": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
        "cost_estimate_usd": round(est_tokens / 1_000_000 * cost_rate, 4),
    }


async def run(args: argparse.Namespace) -> int:
    setup_logging()
    settings = Settings()
    settings.resolve_paths(ROOT)
    settings = settings.model_copy(
        update={
            "mode": "live",
            "llm_provider": args.provider,
        }
    )

    if args.provider == "openrouter":
        models = args.models or settings.openrouter_model_list()
    elif args.provider == "lmstudio":
        if not settings.lmstudio_model and not args.models:
            print("Set CONDUCTGENE_LMSTUDIO_MODEL or pass --models", file=sys.stderr)
            return 1
        models = args.models or [settings.lmstudio_model]
    else:
        models = args.models or [settings.llm_model]

    all_scenarios = load_all_scenarios(settings.scenarios_dir)
    case_ids = [s.id for s in all_scenarios]
    if args.limit:
        case_ids = case_ids[: args.limit]

    results = []
    for model in models:
        print(f"Benchmarking {model} on {len(case_ids)} cases...")
        try:
            row = await bench_model(settings, model, case_ids)
            results.append(row)
            print(json.dumps(row, indent=2))
        except Exception as exc:
            print(f"FAILED {model}: {exc}", file=sys.stderr)
            results.append({"model": model, "error": str(exc)})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"bench_{ts}.json"
    csv_path = OUTPUT_DIR / f"bench_{ts}.csv"
    md_path = OUTPUT_DIR / f"bench_{ts}.md"

    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    ok_rows = [r for r in results if "error" not in r]
    if ok_rows:
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ok_rows[0].keys())
            writer.writeheader()
            writer.writerows(ok_rows)

    md_lines = [
        f"# Benchmark {ts}",
        "",
        f"Provider: {args.provider} | Cases: {len(case_ids)}",
        "",
        "| model | pass_rate | citation | abstain | p50_s | cost_est |",
        "|-------|-----------|----------|---------|-------|----------|",
    ]
    for r in ok_rows:
        md_lines.append(
            f"| {r['model']} | {r['pass_rate']:.0%} | {r['citation_coverage']:.0%} | "
            f"{r['abstain_rate']:.0%} | {r['latency_p50_s']:.1f} | ${r['cost_estimate_usd']} |"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {json_path}, {csv_path}, {md_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark LLM models on scenarios")
    parser.add_argument("--provider", default="openrouter", choices=["openrouter", "lmstudio", "instruct"])
    parser.add_argument("--models", nargs="*", help="Model ids to benchmark")
    parser.add_argument("--limit", type=int, default=4, help="Max scenarios (cost cap)")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
