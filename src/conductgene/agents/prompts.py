"""Prompt templates for live LLM agents."""

from __future__ import annotations

import json

from conductgene.schemas import AgentOpinion, EvidenceSnippet, PolicyGene

CHECKLIST_IDS = (
    "threat_language",
    "escalation_offered",
    "company_disclosure",
    "recording_disclosure",
)

AGENT_OPINION_JSON_HINT = json.dumps(
    {
        "role": "prosecutor|defender|arbiter",
        "checklist": [
            {
                "id": "threat_language",
                "status": "pass|fail|needs_review",
                "rationale": "evidence-grounded explanation",
                "cited_chunk_ids": ["chunk-id-from-evidence"],
            }
        ],
        "summary": "one paragraph synthesis",
    },
    indent=2,
)

_BASE_RULES = """You are a conduct QA agent for regulated debt-collection call review.
Rules:
- Ground every checklist rationale in the provided evidence snippets only.
- cited_chunk_ids MUST reference chunk_id values from the evidence pool (never invent IDs).
- status must be one of: pass, fail, needs_review.
- Only evaluate checklist items relevant to your role and the transcript.
- Do not hallucinate policy; if evidence is insufficient, use needs_review.
- Respond with valid JSON matching the schema exactly. No markdown fences."""


def _format_evidence(evidence: list[EvidenceSnippet]) -> str:
    if not evidence:
        return "(no evidence retrieved — use needs_review where policy grounding is required)"
    lines = []
    for ev in evidence:
        score = f" score={ev.score:.3f}" if ev.score is not None else ""
        lines.append(f"- chunk_id={ev.chunk_id} doc={ev.doc_id}{score}: {ev.text[:500]}")
    return "\n".join(lines)


def prosecutor_messages(transcript: str, evidence: list[EvidenceSnippet]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                f"{_BASE_RULES}\n"
                "Role: PROSECUTOR — flag violations, coercive tone, missing disclosures.\n"
                f"Focus checklist ids: threat_language, recording_disclosure.\n"
                f"JSON schema:\n{AGENT_OPINION_JSON_HINT}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Transcript:\n{transcript}\n\n"
                f"Evidence pool:\n{_format_evidence(evidence)}\n\n"
                'Return JSON with role="prosecutor".'
            ),
        },
    ]


def defender_messages(transcript: str, evidence: list[EvidenceSnippet]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                f"{_BASE_RULES}\n"
                "Role: DEFENDER — identify mitigating compliance signals.\n"
                f"Focus checklist ids: escalation_offered, company_disclosure.\n"
                f"JSON schema:\n{AGENT_OPINION_JSON_HINT}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Transcript:\n{transcript}\n\n"
                f"Evidence pool:\n{_format_evidence(evidence)}\n\n"
                'Return JSON with role="defender".'
            ),
        },
    ]


def arbiter_messages(
    transcript: str,
    prosecutor: AgentOpinion,
    defender: AgentOpinion,
    evidence: list[EvidenceSnippet],
    genes: list[PolicyGene],
) -> list[dict[str, str]]:
    gene_block = "No active Policy Genes."
    if genes:
        gene_lines = [
            f"- {g.id}: trigger={g.trigger_pattern!r} -> {g.target_checklist_id}={g.override_status}"
            for g in genes
            if g.active
        ]
        if gene_lines:
            gene_block = "Active Policy Genes (supervisor-approved):\n" + "\n".join(gene_lines)

    return [
        {
            "role": "system",
            "content": (
                f"{_BASE_RULES}\n"
                "Role: ARBITER — synthesize prosecutor and defender into final checklist.\n"
                "On disagreement between agents, prefer needs_review.\n"
                f"Valid checklist ids: {', '.join(CHECKLIST_IDS)}.\n"
                f"JSON schema:\n{AGENT_OPINION_JSON_HINT}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Transcript:\n{transcript}\n\n"
                f"Evidence pool:\n{_format_evidence(evidence)}\n\n"
                f"Prosecutor opinion:\n{prosecutor.model_dump_json()}\n\n"
                f"Defender opinion:\n{defender.model_dump_json()}\n\n"
                f"{gene_block}\n\n"
                'Return JSON with role="arbiter".'
            ),
        },
    ]
