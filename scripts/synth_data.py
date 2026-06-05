#!/usr/bin/env python3
"""Generate synthetic policy KB documents and optional scenario stubs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

KB_DOCS: dict[str, str] = {
    "collections_fintech_en.md": """## Fintech collections — fair treatment (EN)

Agents must identify the company and purpose of call within the first 30 seconds.
Debtors requesting hardship review must be offered supervisor callback within policy SLA (default 24h).
Threatening criminal prosecution without legal basis is prohibited.
Repayment plans and partial payments are acceptable escalation paths when supervisor is mentioned.
""",
    "insurance_outbound_en.md": """## Insurance outbound conduct (EN)

Recording disclosure is required before collecting sensitive health or payment data.
Agents must state that the call may be recorded for quality and compliance.
Escalation to licensed supervisor is mandatory when customer disputes policy terms.
""",
    "escalation_sla_en.md": """## Escalation SLA policy (EN)

Supervisor callback must be offered when debtor expresses inability to pay in full.
Implicit escalation phrases: "speak with a supervisor", "transfer to manager", "escalation team".
Offering repayment path plus supervisor connection satisfies escalation-offer requirements.
""",
    "harassment_limits_en.md": """## Harassment and contact limits (EN)

Repeated calls under minimum interval constitute undue pressure.
Agents must not use arrest, jail, or police language unless legally authorized.
Coercive soft language ("serious consequences") requires supervisor review.
""",
    "disclosures_th_extended.md": """## การเปิดเผยข้อมูล — ภาษาไทย (TH/EN mix)

Agent ต้องแจ้งชื่อบริษัทและวัตถุประสงค์ของการโทร / Company and purpose disclosure required.
การบันทึกเสียงต้องได้รับการแจ้งให้ทราบก่อน / Recording must be disclosed before capture.
เสนอการติดต่อหัวหน้างานเมื่อลูกค้าขอ / Offer supervisor when customer requests escalation.
""",
    "recording_compliance_en.md": """## Recording compliance (EN)

If call recording is active, agent must inform debtor before substantive discussion.
Failure to disclose recording when recording is mentioned triggers needs_review.
""",
    "payment_plan_policy_en.md": """## Payment plan policy (EN)

Structured repayment and payment-over-time options are compliant when paired with supervisor offer.
Agents should document agreed callback window for supervisor follow-up.
""",
    "company_identification_en.md": """## Company identification (EN)

Opening script must include company name and call purpose.
Phrases like "calling from", "this is", "regarding your account" satisfy company_disclosure when clear.
""",
    "supervisor_transfer_en.md": """## Supervisor transfer policy (EN)

Warm transfer to supervisor is preferred over cold callback promises.
Manager transfer and escalation team routing count as escalation_offered.
""",
    "adversarial_handling_en.md": """## Adversarial caller handling (EN)

Remain professional; do not mirror hostile language.
Escalation must still be offered when debtor is distressed or disputes balance.
""",
    "regulatory_fair_debt_en.md": """## Fair debt collection principles (EN)

No false representation of legal authority.
Document all repayment arrangements in CRM within same business day.
""",
    "bilingual_scripts_th_en.md": """## Bilingual scripts TH/EN

สำหรับลูกค้าที่ขอภาษาไทย ให้สรุปนโยบาย escalation และ recording ในภาษาที่ลูกค้าเข้าใจ.
English summary must still meet company_disclosure and escalation requirements.
""",
}

EXTRA_SCENARIOS: list[dict] = [
    {
        "id": "CASE-017",
        "persona": "strict_compliance",
        "transcript": (
            "Agent: Good morning, this is Horizon Insurance calling about your policy renewal.\n"
            "Agent: This call may be recorded for quality assurance.\n"
            "Customer: I want to speak to someone about my coverage.\n"
            "Agent: I can transfer you to a licensed supervisor now."
        ),
        "golden": {
            "recording_disclosure": "pass",
            "escalation_offered": "pass",
            "company_disclosure": "pass",
            "abstain": False,
        },
        "tags": ["insurance", "synth"],
    },
    {
        "id": "CASE-018",
        "persona": "adversarial_caller",
        "transcript": (
            "Agent: This is Nova Fintech collections regarding your overdue balance.\n"
            "Customer: Stop calling me!\n"
            "Agent: I understand your frustration. I can arrange a payment plan "
            "or connect you with a supervisor."
        ),
        "golden": {
            "threat_language": "pass",
            "escalation_offered": "pass",
            "company_disclosure": "pass",
            "abstain": False,
        },
        "tags": ["fintech", "synth"],
    },
]


def write_kb(kb_dir: Path, *, force: bool) -> int:
    kb_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for name, body in KB_DOCS.items():
        path = kb_dir / name
        if path.exists() and not force:
            continue
        path.write_text(body.strip() + "\n", encoding="utf-8")
        written += 1
    return written


def write_scenarios(scenarios_dir: Path, *, force: bool) -> int:
    coll = scenarios_dir / "collections"
    coll.mkdir(parents=True, exist_ok=True)
    written = 0
    for sc in EXTRA_SCENARIOS:
        path = coll / f"{sc['id'].lower().replace('-', '_')}.json"
        if path.exists() and not force:
            continue
        path.write_text(json.dumps(sc, indent=2) + "\n", encoding="utf-8")
        written += 1
    return written


def update_manifest(manifest_path: Path) -> None:
    if not manifest_path.exists():
        return
    import yaml

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    existing_ids = {c["id"] for c in cases}
    for sc in EXTRA_SCENARIOS:
        if sc["id"] in existing_ids:
            continue
        cases.append(
            {
                "id": sc["id"],
                "file": f"collections/{sc['id'].lower().replace('-', '_')}.json",
                "suite": "synth",
            }
        )
    data["cases"] = cases
    manifest_path.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic KB and scenarios")
    parser.add_argument("--kb-only", action="store_true")
    parser.add_argument("--scenarios-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    kb_dir = ROOT / "data" / "synthetic" / "kb"
    scenarios_dir = ROOT / "data" / "scenarios"
    manifest = scenarios_dir / "manifest.yaml"

    kb_count = 0
    sc_count = 0
    if not args.scenarios_only:
        kb_count = write_kb(kb_dir, force=args.force)
        print(f"KB: wrote {kb_count} new documents ({len(list(kb_dir.glob('*.md')))} total)")
    if not args.kb_only:
        sc_count = write_scenarios(scenarios_dir, force=args.force)
        update_manifest(manifest)
        print(f"Scenarios: wrote {sc_count} new cases")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
