"""Agent role implementations — mock (rule-based) and live (LLM) modes."""

from __future__ import annotations

import re

from conductgene.schemas import AgentOpinion, ChecklistItem, EvidenceSnippet, PolicyGene


def _transcript_lower(transcript: str) -> str:
    return transcript.lower()


def _find_cited_chunks(keywords: list[str], evidence: list[EvidenceSnippet]) -> list[str]:
    cited: list[str] = []
    for ev in evidence:
        text_lower = ev.text.lower()
        if any(kw in text_lower for kw in keywords):
            cited.append(ev.chunk_id)
    return cited[:3] or ([evidence[0].chunk_id] if evidence else [])


def run_prosecutor(transcript: str, evidence: list[EvidenceSnippet]) -> AgentOpinion:
    t = _transcript_lower(transcript)
    checklist: list[ChecklistItem] = []

    threat_words = ["jail", "arrest", "prison", "police will"]
    coercive_soft = [
        "serious consequences",
        "consequences for your account",
        "may create serious",
    ]
    if any(w in t for w in threat_words):
        checklist.append(
            ChecklistItem(
                id="threat_language",
                status="fail",
                rationale="Prohibited threat language detected (arrest/jail).",
                cited_chunk_ids=_find_cited_chunks(["threat", "arrest", "jail"], evidence),
                agent_role="prosecutor",
            )
        )
    elif any(w in t for w in coercive_soft):
        checklist.append(
            ChecklistItem(
                id="threat_language",
                status="needs_review",
                rationale="Coercive tone flagged — supervisor review recommended.",
                cited_chunk_ids=_find_cited_chunks(["threat", "harassment"], evidence),
                agent_role="prosecutor",
            )
        )
    else:
        checklist.append(
            ChecklistItem(
                id="threat_language",
                status="pass",
                rationale="No prohibited threat language detected.",
                cited_chunk_ids=_find_cited_chunks(["threat"], evidence),
                agent_role="prosecutor",
            )
        )

    if "record" in t and "disclos" not in t and "inform" not in t:
        checklist.append(
            ChecklistItem(
                id="recording_disclosure",
                status="needs_review",
                rationale="Recording mentioned without clear disclosure language.",
                cited_chunk_ids=_find_cited_chunks(["recording", "disclosure"], evidence),
                agent_role="prosecutor",
            )
        )

    summary = "Prosecutor review complete."
    if any(c.status == "fail" for c in checklist):
        summary = "Prosecutor flagged potential conduct violations requiring review."
    return AgentOpinion(role="prosecutor", checklist=checklist, summary=summary)


def run_defender(transcript: str, evidence: list[EvidenceSnippet]) -> AgentOpinion:
    t = _transcript_lower(transcript)
    checklist: list[ChecklistItem] = []

    escalation_phrases = ["supervisor", "escalation", "transfer", "manager", "speak with"]
    repayment_phrases = ["repayment", "payment plan", "payment option", "pay over time"]
    if any(p in t for p in escalation_phrases):
        checklist.append(
            ChecklistItem(
                id="escalation_offered",
                status="pass",
                rationale="Agent offered escalation path to debtor.",
                cited_chunk_ids=_find_cited_chunks(["escalation", "supervisor"], evidence),
                agent_role="defender",
            )
        )
    elif any(p in t for p in repayment_phrases):
        checklist.append(
            ChecklistItem(
                id="escalation_offered",
                status="needs_review",
                rationale="Repayment path offered — verify escalation policy compliance.",
                cited_chunk_ids=_find_cited_chunks(["escalation", "supervisor"], evidence),
                agent_role="defender",
            )
        )
    else:
        checklist.append(
            ChecklistItem(
                id="escalation_offered",
                status="needs_review",
                rationale="No explicit escalation offer detected in transcript.",
                cited_chunk_ids=_find_cited_chunks(["escalation"], evidence),
                agent_role="defender",
            )
        )

    company_intro = ["this is", "calling from", "company", "purpose of"]
    if any(p in t for p in company_intro):
        checklist.append(
            ChecklistItem(
                id="company_disclosure",
                status="pass",
                rationale="Company identification or call purpose present.",
                cited_chunk_ids=_find_cited_chunks(["company", "purpose"], evidence),
                agent_role="defender",
            )
        )

    return AgentOpinion(
        role="defender",
        checklist=checklist,
        summary="Defender identified mitigating compliance signals.",
    )


def run_arbiter(
    prosecutor: AgentOpinion,
    defender: AgentOpinion,
    evidence: list[EvidenceSnippet],
) -> AgentOpinion:
    merged: dict[str, ChecklistItem] = {}

    for item in prosecutor.checklist + defender.checklist:
        existing = merged.get(item.id)
        if existing is None:
            merged[item.id] = item.model_copy(update={"agent_role": "arbiter"})
            continue
        if existing.status != item.status:
            merged[item.id] = ChecklistItem(
                id=item.id,
                status="needs_review",
                rationale=f"Agent disagreement: prosecutor={existing.status}, defender={item.status}.",
                cited_chunk_ids=list(set(existing.cited_chunk_ids + item.cited_chunk_ids)),
                agent_role="arbiter",
            )

    checklist = list(merged.values())
    summary = "Arbiter synthesized prosecutor and defender opinions."
    if any(c.status == "fail" for c in checklist):
        summary = "Arbiter: violations or conflicts require supervisor attention."
    return AgentOpinion(role="arbiter", checklist=checklist, summary=summary)


def apply_genes_to_checklist(
    checklist: list[ChecklistItem],
    genes: list[PolicyGene],
    transcript: str,
) -> tuple[list[ChecklistItem], list[str]]:
    """Apply active PolicyGenes when trigger matches transcript."""
    t = _transcript_lower(transcript)
    applied: list[str] = []
    updated = [c.model_copy() for c in checklist]

    for gene in genes:
        if not gene.active:
            continue
        pattern = gene.trigger_pattern.lower()
        if pattern not in t and not re.search(re.escape(pattern), t):
            continue
        for i, item in enumerate(updated):
            if item.id == gene.target_checklist_id:
                updated[i] = ChecklistItem(
                    id=item.id,
                    status=gene.override_status,
                    rationale=f"[Supervisor-approved gene: {gene.title or gene.name}] {gene.rationale}",
                    cited_chunk_ids=item.cited_chunk_ids,
                    agent_role="arbiter",
                )
                applied.append(gene.id)
                break

    return updated, applied
