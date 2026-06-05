"""Streamlit UI — 5-panel ConductGene demo."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import streamlit as st

from conductgene.audit.gene_events import GeneAuditStore
from conductgene.audit.store import AuditStore
from conductgene.config import Settings
from conductgene.eval.harness import compute_learn_eval_delta, run_eval_suite
from conductgene.eval.scenarios import load_all_scenarios
from conductgene.evolution.genes import GeneStore
from conductgene.kb.memory import MemoryKnowledgeBase
from conductgene.pipeline.swarm import swarm_analyze
from conductgene.schemas import GeneLearnRequest, SwarmAnalyzeRequest, SwarmAnalyzeResult


def _root() -> Path:
    return Path.cwd()


def _api_client(settings: Settings):
    from conductgene.ui.client import ConductGeneClient

    return ConductGeneClient(base_url=settings.api_base_url)


def _result_from_api(payload: dict) -> SwarmAnalyzeResult | None:
    if not payload.get("ok") or not payload.get("result"):
        return None
    return SwarmAnalyzeResult.model_validate(payload["result"])


def _init_state() -> tuple[Settings, MemoryKnowledgeBase, GeneStore, AuditStore, GeneAuditStore]:
    settings = Settings()
    settings.resolve_paths(_root())
    kb = MemoryKnowledgeBase(settings.kb_dir)
    genes = GeneStore(settings.gene_store_path)
    audit = AuditStore(settings.audit_store_path)
    gene_audit = GeneAuditStore(settings.gene_audit_store_path)
    return settings, kb, genes, audit, gene_audit


def main() -> None:
    st.set_page_config(page_title="ConductGene Swarm", layout="wide")
    st.title("ConductGene Swarm")
    st.caption("Human-approved AI conduct QA that remembers supervisor corrections safely.")

    settings, kb, genes, audit, gene_audit = _init_state()
    scenarios = load_all_scenarios(settings.scenarios_dir)
    scenario_map = {s.id: s for s in scenarios}

    with st.sidebar:
        st.subheader("Model Jury")
        provider = st.selectbox(
            "LLM provider",
            ["mock", "openrouter", "lmstudio", "instruct"],
            index=["mock", "openrouter", "lmstudio", "instruct"].index(settings.llm_provider),
        )
        mode = st.selectbox("Mode", ["mock", "live"], index=0 if settings.mode == "mock" else 1)
        retrieval = st.selectbox(
            "Retrieval",
            ["memory", "qdrant", "qdrant_rerank"],
            index=["memory", "qdrant", "qdrant_rerank"].index(settings.retrieval_mode),
        )
        model_name = st.text_input("Model override (optional)", value="")
        settings = settings.model_copy(
            update={
                "llm_provider": provider,  # type: ignore[arg-type]
                "mode": mode,  # type: ignore[arg-type]
                "retrieval_mode": retrieval,  # type: ignore[arg-type]
            }
        )
        if model_name.strip():
            if provider == "openrouter":
                settings = settings.model_copy(update={"openrouter_models": model_name.strip()})
            elif provider == "lmstudio":
                settings = settings.model_copy(update={"lmstudio_model": model_name.strip()})
            else:
                settings = settings.model_copy(update={"llm_model": model_name.strip()})

        if st.button("Probe services"):
            from conductgene.services.discovery import discover_services, format_service_table

            probes = discover_services(settings)
            st.code(format_service_table(probes))

    mode_label = "Deterministic Demo Mode" if settings.mode == "mock" else "Live Mode"
    backend = "REST API" if settings.ui_use_api else "in-process"
    llm_note = (
        f" | LLM: **{settings.llm_provider}**"
        if settings.llm_provider != "mock"
        else ""
    )
    retrieval_note = f" | Retrieval: **{settings.retrieval_mode}**"
    st.info(f"**{mode_label}** ({backend}){llm_note}{retrieval_note}")
    if settings.retrieval_mode != "memory" and settings.retrieval_fallback_to_memory:
        st.caption("Degraded retrieval falls back to memory with logged warning.")
    if settings.ui_use_api:
        st.caption(f"API backend: `{settings.api_base_url}` — start with `uv run conductgene-serve`")

    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_transcript" not in st.session_state:
        st.session_state.last_transcript = ""

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Transcript")
        pick = st.selectbox(
            "Load scenario",
            ["(custom)"] + list(scenario_map.keys()),
            format_func=lambda x: x if x != "(custom)" else "Custom transcript",
        )
        default_text = scenario_map[pick].transcript if pick in scenario_map else ""
        transcript = st.text_area("Call transcript", value=default_text, height=200)
        case_id = pick if pick in scenario_map else None
        run = st.button("Run swarm analyze", type="primary")

    with col2:
        st.subheader("2. Evidence pool")
        if st.session_state.last_result and st.session_state.last_result.evidence:
            for ev in st.session_state.last_result.evidence:
                st.markdown(f"**{ev.chunk_id}** (score={ev.score:.2f}) — {ev.doc_id}")
                st.write(ev.text[:200])
        else:
            st.info("Run analyze to retrieve policy evidence.")

    if run and transcript.strip():
        if settings.ui_use_api:
            client = _api_client(settings)
            payload = client.analyze(
                SwarmAnalyzeRequest(
                    transcript=transcript,
                    case_id=case_id,
                    apply_genes=True,
                )
            )
            result = _result_from_api(payload)
            if result is None:
                st.error(payload.get("error") or "Analyze failed")
            else:
                st.session_state.last_result = result
                st.session_state.last_transcript = transcript
        else:
            result = asyncio.run(
                swarm_analyze(
                    settings=settings,
                    kb=kb,
                    gene_store=genes,
                    audit_store=audit,
                    request=SwarmAnalyzeRequest(
                        transcript=transcript,
                        case_id=case_id,
                        apply_genes=True,
                    ),
                )
            )
            st.session_state.last_result = result
            st.session_state.last_transcript = transcript

    result = st.session_state.last_result

    st.subheader("3. Agent swarm")
    if result:
        t1, t2, t3 = st.tabs(["Prosecutor", "Defender", "Arbiter"])
        for tab, opinion in zip([t1, t2, t3], [result.prosecutor, result.defender, result.arbiter]):
            with tab:
                st.write(opinion.summary)
                st.json([c.model_dump() for c in opinion.checklist])
        if result.abstained:
            st.warning(result.abstain_reason)
    else:
        st.info("No analysis yet.")

    st.subheader("4. Supervisor override")
    if result and not result.abstained:
        with st.form("learn_form"):
            checklist_id = st.selectbox(
                "Checklist item",
                [c.id for c in result.checklist] or ["escalation_offered"],
            )
            corrected = st.selectbox("Approved status", ["pass", "fail", "needs_review"])
            rationale = st.text_area(
                "Supervisor rationale",
                "Supervisor-approved pattern for institutional memory.",
            )
            trigger = st.text_input("Trigger pattern", "repayment")
            supervisor_id = st.text_input("Supervisor ID", "supervisor-001")
            submitted = st.form_submit_button("Approve Policy Gene")
            if submitted:
                learn_req = GeneLearnRequest(
                    request_id=result.request_id,
                    checklist_id=checklist_id,
                    corrected_status=corrected,  # type: ignore[arg-type]
                    rationale=rationale,
                    trigger_pattern=trigger,
                    title="Supervisor-approved conduct pattern",
                    supervisor_id=supervisor_id,
                    case_id=result.case_id,
                    chunk_ids=[e.chunk_id for e in result.evidence[:3]],
                )
                if settings.ui_use_api:
                    client = _api_client(settings)
                    gene_body = client.learn_gene(learn_req)
                    before = gene_body.get("eval_score_before")
                    after = gene_body.get("eval_score_after")
                    st.success(
                        f"Policy Gene stored via API: {gene_body['id']} "
                        f"(held-out eval {before} → {after})"
                    )
                else:
                    before, after, heldout = asyncio.run(
                        compute_learn_eval_delta(
                            settings=settings,
                            kb=kb,
                            scenarios_dir=settings.scenarios_dir,
                            request=learn_req,
                        )
                    )
                    gene = genes.learn_from_correction(
                        learn_req,
                        eval_before=before,
                        eval_after=after,
                        heldout_cases=heldout,
                    )
                    gene_audit.append_learned(gene, learn_req, eval_before=before, eval_after=after)
                    st.success(
                        f"Policy Gene stored: {gene.id} "
                        f"(held-out eval {before:.2f} → {after:.2f})"
                    )
    else:
        st.info("Complete an analysis to approve a Policy Gene.")

    st.subheader("5. Policy Genes + audit")
    m1, m2, m3 = st.columns(3)
    active = genes.list_active()
    m1.metric("Active genes", len(active))
    metrics = genes.compute_evolution_metrics()
    m2.metric("Avg eval delta", metrics.get("avg_eval_delta") or "—")
    m3.metric("Last case", result.case_id if result else "—")

    if active:
        st.dataframe(
            [
                {
                    "gene_id": g.id,
                    "title": g.title or g.name,
                    "status": g.status,
                    "eval_before": g.eval_score_before,
                    "eval_after": g.eval_score_after,
                }
                for g in active
            ],
            use_container_width=True,
        )
        rollback_id = st.selectbox("Rollback gene", [g.id for g in active])
        if st.button("Rollback selected gene"):
            genes.rollback(rollback_id)
            gene_audit.append_rollback(rollback_id)
            st.warning(f"Rolled back {rollback_id}")

    if st.button("Run eval suite"):
        eval_resp = asyncio.run(
            run_eval_suite(
                settings=settings,
                kb=kb,
                gene_store=genes,
                scenarios_dir=settings.scenarios_dir,
            )
        )
        st.json(json.loads(eval_resp.model_dump_json()))

    gene_events = gene_audit.export_all()
    if gene_events:
        with st.expander("Gene audit events"):
            st.json(gene_events)

    if result and result.case_id:
        rec = audit.get(result.case_id)
        if rec:
            with st.expander("Case audit trail"):
                st.json(json.loads(rec.model_dump_json()))


if __name__ == "__main__":
    main()
