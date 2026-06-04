"""Pydantic schemas for swarm API and agent contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field


class SwarmAnalyzeRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    case_id: str | None = Field(default=None, description="Optional scenario/case identifier")
    locale: str | None = None
    abstain_when_low_evidence: bool = True
    apply_genes: bool = True


class EvidenceSnippet(BaseModel):
    chunk_id: str
    doc_id: str
    section: str | None = None
    text: str
    score: float | None = None


class ChecklistItem(BaseModel):
    id: str
    status: Literal["pass", "fail", "needs_review"]
    rationale: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    agent_role: str | None = None


class AgentOpinion(BaseModel):
    role: Literal["prosecutor", "defender", "arbiter"]
    checklist: list[ChecklistItem]
    summary: str


class GeneCreatedFrom(BaseModel):
    case_id: str | None = None
    supervisor_override: bool = True
    supervisor_id: str | None = None
    agent_roles: list[str] = Field(default_factory=lambda: ["prosecutor", "defender", "arbiter"])
    chunk_ids: list[str] = Field(default_factory=list)


class GeneEval(BaseModel):
    before: float | None = None
    after: float | None = None
    heldout_cases: int = 0


class PolicyGene(BaseModel):
    id: str
    name: str
    title: str | None = None
    trigger_pattern: str
    action: str
    target_checklist_id: str
    override_status: Literal["pass", "fail", "needs_review"]
    provenance: Literal["human_correction", "swarm_consensus"] = "human_correction"
    eval_score_before: float | None = None
    eval_score_after: float | None = None
    active: bool = True
    created_at: datetime
    source_request_id: str
    rationale: str
    supervisor_id: str | None = None
    created_from: GeneCreatedFrom | None = None
    eval_detail: GeneEval | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gene_id(self) -> str:
        return self.id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status(self) -> Literal["active", "inactive"]:
        return "active" if self.active else "inactive"


class GeneLearnRequest(BaseModel):
    request_id: str
    checklist_id: str
    corrected_status: Literal["pass", "fail", "needs_review"]
    rationale: str
    trigger_pattern: str | None = None
    name: str | None = None
    title: str | None = None
    supervisor_id: str | None = None
    approved: bool = True
    chunk_ids: list[str] = Field(default_factory=list)
    case_id: str | None = None


class SwarmAnalyzeResult(BaseModel):
    request_id: str
    case_id: str | None = None
    abstained: bool
    abstain_reason: str | None = None
    prosecutor: AgentOpinion
    defender: AgentOpinion
    arbiter: AgentOpinion
    checklist: list[ChecklistItem]
    supervisor_summary: str
    coaching_tips: list[str]
    evidence: list[EvidenceSnippet]
    genes_applied: list[str] = Field(default_factory=list)
    evolution_metrics: dict[str, float | int | None] = Field(default_factory=dict)


class SwarmAnalyzeResponse(BaseModel):
    ok: bool
    result: SwarmAnalyzeResult | None = None
    error: str | None = None


class GeneListResponse(BaseModel):
    genes: list[PolicyGene]
    total: int


class HealthResponse(BaseModel):
    ok: bool
    service: str
    version: str


class ServiceProbeRow(BaseModel):
    service: str
    status: str
    endpoint: str | None = None
    details: str
    recommended_next_step: str


class ServicesHealthResponse(BaseModel):
    ok: bool
    retrieval_mode: str
    llm_provider: str
    services: list[ServiceProbeRow]


class ReadyResponse(BaseModel):
    ready: bool
    mode: str
    kb_chunks: int
    active_genes: int


class CaseAuditRecord(BaseModel):
    case_id: str
    request_id: str
    transcript: str
    result: SwarmAnalyzeResult
    recorded_at: datetime


class GeneAuditEvent(BaseModel):
    event_type: Literal["gene_learned", "gene_rollback"]
    gene_id: str
    request_id: str | None = None
    supervisor_id: str | None = None
    checklist_id: str | None = None
    eval_before: float | None = None
    eval_after: float | None = None
    trigger_pattern: str | None = None
    recorded_at: datetime


class EvalRunRequest(BaseModel):
    suite: str = "all"
    apply_genes: bool = True
    gene_store_isolated: bool = True


class EvalCaseResult(BaseModel):
    case_id: str
    passed: bool
    expected: dict[str, str | None]
    actual: dict[str, str | None]
    abstained: bool
    citation_ok: bool
    detail: str | None = None


class EvalRunResponse(BaseModel):
    suite: str
    total: int
    passed: int
    score: float
    citation_coverage: float
    abstain_rate: float
    cases: list[EvalCaseResult]
    gene_learning: dict[str, Any] | None = None


class RollbackResponse(BaseModel):
    gene_id: str
    rolled_back: bool
    message: str
