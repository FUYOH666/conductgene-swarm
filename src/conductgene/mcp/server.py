"""Policy Gene MCP stub server (stdio transport).

Exposes supervisor-approved Policy Genes to MCP-capable agent runtimes:

    uv sync --extra mcp
    uv run conductgene-mcp

Tools:
- ``list_genes`` — active genes with provenance and eval scores
- ``export_skill`` — render active genes into a portable SKILL.md
"""

from __future__ import annotations

from pathlib import Path

from conductgene import __version__
from conductgene.config import Settings
from conductgene.evolution.genes import GeneStore
from conductgene.evolution.skill_export import export_skill_md


def _store() -> GeneStore:
    settings = Settings()
    settings.resolve_paths(Path.cwd())
    return GeneStore(settings.gene_store_path)


def list_genes_payload(store: GeneStore) -> list[dict]:
    """Active Policy Genes as JSON-serializable dicts."""
    return [g.model_dump(mode="json") for g in store.list_active()]


def export_skill_payload(store: GeneStore, out_dir: str) -> dict:
    """Write SKILL.md for active genes; return path and gene count."""
    path = export_skill_md(
        store.list_active(), Path(out_dir), source_version=__version__
    )
    return {"path": str(path), "active_genes": store.count_active()}


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "mcp SDK not installed; run: uv sync --extra mcp"
        ) from exc

    server = FastMCP("conductgene-policy-genes")

    @server.tool()
    def list_genes() -> list[dict]:
        """List active supervisor-approved Policy Genes with provenance and eval scores."""
        return list_genes_payload(_store())

    @server.tool()
    def export_skill(out_dir: str = "reports/skill") -> dict:
        """Export active Policy Genes as a portable SKILL.md file for agent runtimes."""
        return export_skill_payload(_store(), out_dir)

    server.run()  # stdio transport


if __name__ == "__main__":
    main()
