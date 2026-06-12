"""CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from conductgene.audit.gene_events import GeneAuditStore
from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.harness import compute_learn_eval_delta, run_eval_suite
from conductgene.eval.scenarios import load_all_scenarios, load_scenario
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import GeneLearnRequest, SwarmAnalyzeRequest


def _root() -> Path:
    return Path.cwd()


def cli_main() -> None:
    parser = argparse.ArgumentParser(
        description="ConductGene Swarm — supervisor-approved conduct QA",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Run swarm analyze")
    analyze_p.add_argument("transcript", nargs="?", help="Transcript or @file")
    analyze_p.add_argument("--file", "-f", type=Path, help="Scenario JSON or transcript file")
    analyze_p.add_argument("--case-id", default=None)
    analyze_p.add_argument(
        "--provider",
        choices=["mock", "openrouter", "lmstudio", "instruct"],
        default=None,
        help="Override CONDUCTGENE_LLM_PROVIDER",
    )
    analyze_p.add_argument("--model", default=None, help="Override LLM model name")
    analyze_p.add_argument(
        "--mode",
        choices=["mock", "live"],
        default=None,
        help="Override CONDUCTGENE_MODE",
    )

    learn_p = sub.add_parser("learn", help="Store supervisor-approved Policy Gene")
    learn_p.add_argument("--request-id", required=True)
    learn_p.add_argument("--checklist-id", required=True)
    learn_p.add_argument("--status", required=True, choices=["pass", "fail", "needs_review"])
    learn_p.add_argument("--rationale", required=True)
    learn_p.add_argument("--trigger", default="repayment")
    learn_p.add_argument("--supervisor-id", default="supervisor-001")

    genes_p = sub.add_parser("genes", help="List or export active Policy Genes")
    genes_sub = genes_p.add_subparsers(dest="genes_command")
    export_skill_p = genes_sub.add_parser(
        "export-skill", help="Export active genes as portable SKILL.md"
    )
    export_skill_p.add_argument(
        "--out", type=Path, default=Path("reports/skill"), help="Output directory"
    )
    sub.add_parser("demo", help="Demo: CASE-002 → learn → CASE-005")
    eval_p = sub.add_parser("eval", help="Run synthetic scenario eval suite")
    eval_p.add_argument("--suite", default="all")
    eval_p.add_argument("--out", type=Path, default=Path("reports/eval_latest.json"))

    audit_p = sub.add_parser("audit", help="Audit trail operations")
    audit_sub = audit_p.add_subparsers(dest="audit_command", required=True)
    export_p = audit_sub.add_parser("export", help="Export case + gene audit JSON")
    export_p.add_argument("--out", type=Path, default=Path("reports/audit_export.json"))

    args = parser.parse_args()
    asyncio.run(_dispatch(args))


def _apply_cli_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    overrides: dict = {}
    if getattr(args, "provider", None):
        overrides["llm_provider"] = args.provider
    if getattr(args, "mode", None):
        overrides["mode"] = args.mode
    provider = overrides.get("llm_provider", settings.llm_provider)
    if getattr(args, "model", None):
        if provider == "openrouter":
            overrides["openrouter_models"] = args.model
        elif provider == "lmstudio":
            overrides["lmstudio_model"] = args.model
        else:
            overrides["llm_model"] = args.model
    if overrides:
        return settings.model_copy(update=overrides)
    return settings


async def _dispatch(args: argparse.Namespace) -> None:
    settings = Settings()
    settings.resolve_paths(_root())
    if args.command == "analyze":
        settings = _apply_cli_overrides(settings, args)
    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)

    if args.command == "analyze":
        text, case_id = _read_input(args)
        from conductgene.providers.llm import resolve_llm_config

        model_override = getattr(args, "model", None)
        if settings.llm_provider != "mock" and settings.mode == "live":
            resolve_llm_config(settings, model_override=model_override)
        result = await swarm_analyze(
            settings=settings,
            kb=kb,
            gene_store=genes,
            request=SwarmAnalyzeRequest(
                transcript=text,
                case_id=case_id or args.case_id,
            ),
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))

    elif args.command == "learn":
        learn_req = GeneLearnRequest(
            request_id=args.request_id,
            checklist_id=args.checklist_id,
            corrected_status=args.status,
            rationale=args.rationale,
            trigger_pattern=args.trigger,
            supervisor_id=args.supervisor_id,
            title="Supervisor-approved conduct pattern",
        )
        before, after, heldout = await compute_learn_eval_delta(
            settings=settings,
            kb=kb,
            scenarios_dir=settings.scenarios_dir,
            request=learn_req,
        )
        gene = genes.learn_from_correction(
            learn_req,
            eval_before=before,
            eval_after=after,
            heldout_cases=heldout,
        )
        print(json.dumps(gene.model_dump(mode="json"), indent=2))

    elif args.command == "genes":
        if getattr(args, "genes_command", None) == "export-skill":
            from conductgene import __version__
            from conductgene.evolution.skill_export import export_skill_md

            path = export_skill_md(
                genes.list_active(), args.out, source_version=__version__
            )
            print(f"Wrote {path}")
        else:
            print(json.dumps([g.model_dump(mode="json") for g in genes.list_active()], indent=2))

    elif args.command == "demo":
        await _run_demo(settings, kb, genes)

    elif args.command == "eval":
        resp = await run_eval_suite(
            settings=settings,
            kb=kb,
            gene_store=genes,
            scenarios_dir=settings.scenarios_dir,
            suite=args.suite,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(resp.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps(json.loads(resp.model_dump_json()), indent=2))
        if resp.score < 1.0:
            failed = [c.case_id for c in resp.cases if not c.passed]
            print(f"Eval score {resp.score:.2%} — failed: {failed}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "audit" and args.audit_command == "export":
        audit = AuditStore(settings.audit_store_path)
        gene_audit = GeneAuditStore(settings.gene_audit_store_path)
        payload = {
            "cases": audit.export_all(),
            "gene_events": gene_audit.export_all(),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))


def _read_input(args: argparse.Namespace) -> tuple[str, str | None]:
    if args.file:
        raw = args.file.read_text(encoding="utf-8")
        if args.file.suffix == ".json":
            sc = load_scenario(args.file)
            return sc.transcript, sc.id
        return raw, None
    if args.transcript:
        if args.transcript.startswith("@"):
            p = Path(args.transcript[1:])
            if p.suffix == ".json":
                sc = load_scenario(p)
                return sc.transcript, sc.id
            return p.read_text(encoding="utf-8"), None
        return args.transcript, None
    print("Provide transcript or --file", file=sys.stderr)
    sys.exit(1)


async def _run_demo(settings: Settings, kb: MemoryKnowledgeBase, genes: GeneStore) -> None:
    scenarios = {s.id: s for s in load_all_scenarios(settings.scenarios_dir)}
    case2 = scenarios["CASE-002"]
    case5 = scenarios["CASE-005"]

    print("=== Step 1: CASE-002 swarm analyze ===")
    r1 = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=genes,
        request=SwarmAnalyzeRequest(transcript=case2.transcript, case_id=case2.id, apply_genes=False),
    )
    print(f"Case: {r1.case_id} | threat: {_status(r1, 'threat_language')} | escalation: {_status(r1, 'escalation_offered')}")

    gl = case2.gene_learning
    assert gl is not None
    print("\n=== Step 2: Supervisor approves Policy Gene ===")
    learn_req = GeneLearnRequest(
        request_id=r1.request_id,
        checklist_id=gl.checklist_id,
        corrected_status=gl.corrected_status,
        rationale=gl.rationale,
        trigger_pattern=gl.trigger_pattern,
        name="implicit_repayment_escalation",
        title="Implicit repayment escalation detection",
        supervisor_id="demo-supervisor",
        case_id=case2.id,
    )
    before, after, heldout = await compute_learn_eval_delta(
        settings=settings,
        kb=kb,
        scenarios_dir=settings.scenarios_dir,
        request=learn_req,
    )
    gene = genes.learn_from_correction(
        learn_req,
        eval_before=before,
        eval_after=after,
        heldout_cases=heldout,
    )
    print(f"Stored: {gene.id} ({gene.title}) [held-out eval {before:.2f} → {after:.2f}]")

    print("\n=== Step 3: CASE-005 held-out (genes applied) ===")
    r2 = await swarm_analyze(
        settings=settings,
        kb=kb,
        gene_store=genes,
        request=SwarmAnalyzeRequest(transcript=case5.transcript, case_id=case5.id, apply_genes=True),
    )
    print(f"Genes applied: {r2.genes_applied}")
    print(f"Escalation: {_status(r2, 'escalation_offered')} (target: pass via gene)")
    print(f"Metrics: {r2.evolution_metrics}")


def _status(result, checklist_id: str) -> str:
    for c in result.checklist:
        if c.id == checklist_id:
            return c.status
    return "n/a"


if __name__ == "__main__":
    cli_main()
