"""Export active Policy Genes as a portable SKILL.md document.

Makes supervisor-approved institutional memory usable by agent runtimes
that consume skill files (Cursor, Claude Code, etc.).
"""

from __future__ import annotations

from pathlib import Path

from conductgene.schemas import PolicyGene


def render_skill_md(genes: list[PolicyGene], *, source_version: str) -> str:
    lines = [
        "---",
        "name: conductgene-policy-genes",
        "description: >",
        "  Supervisor-approved conduct QA rules learned by ConductGene Swarm.",
        "  Apply when reviewing call transcripts for conduct compliance in",
        "  regulated industries (collections, debt servicing, insurance).",
        "---",
        "",
        "# ConductGene Policy Genes",
        "",
        f"Exported from ConductGene Swarm v{source_version}. "
        f"Active genes: {len(genes)}.",
        "",
        "Each rule below was learned from a human supervisor correction, "
        "passed a held-out evaluation, and remains rollbackable in the "
        "source system. Treat them as authoritative conduct review guidance.",
        "",
    ]
    if not genes:
        lines.append("_No active Policy Genes — nothing has been learned yet._")
    for gene in genes:
        title = gene.title or gene.name
        lines.extend(
            [
                f"## {title}",
                "",
                f"- **Gene ID:** `{gene.id}`",
                f"- **Checklist item:** `{gene.target_checklist_id}`",
                f"- **When transcript matches:** `{gene.trigger_pattern}`",
                f"- **Set status to:** `{gene.override_status}`",
                f"- **Provenance:** {gene.provenance}"
                + (f" (supervisor `{gene.supervisor_id}`)" if gene.supervisor_id else ""),
            ]
        )
        if gene.eval_score_before is not None and gene.eval_score_after is not None:
            lines.append(
                f"- **Held-out eval:** {gene.eval_score_before:.2f} → "
                f"{gene.eval_score_after:.2f}"
            )
        lines.extend(["", f"Rationale: {gene.rationale}", ""])
    return "\n".join(lines).rstrip() + "\n"


def export_skill_md(
    genes: list[PolicyGene],
    out_dir: Path,
    *,
    source_version: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "SKILL.md"
    path.write_text(render_skill_md(genes, source_version=source_version), encoding="utf-8")
    return path
