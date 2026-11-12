"""Plug in any judge: implement `judge_id` and `judge(case) -> JudgeOutput`.

Here a toy judge says every call offered an escalation. The gate still works:
a rule is judged against whatever your judge actually produced.

    uv run python examples/02_bring_your_own_judge.py
"""

from precedent import Case, JudgeOutput, decide, judge_all, load_pack
from precedent.models import ItemVerdict, PredicateAnswer


class OptimisticJudge:
    judge_id = "example:optimistic"

    def __init__(self, item_ids: list[str], predicate_ids: list[str]) -> None:
        self.items, self.predicates = item_ids, predicate_ids

    def judge(self, case: Case) -> JudgeOutput:
        return JudgeOutput(
            case_id=case.id,
            case_hash=case.hash,
            judge_id=self.judge_id,
            items={i: ItemVerdict(item_id=i, label="pass") for i in self.items},
            predicates={
                p: PredicateAnswer(predicate_id=p, value="unknown") for p in self.predicates
            },
        )


pack = load_pack("collections-conduct")
judge = OptimisticJudge([i.id for i in pack.items], [p.id for p in pack.predicates])
outputs = judge_all(judge, pack.cases)
right = sum(
    decide(pack, outputs[c.id], [])[item].label == label
    for c in pack.cases
    for item, label in c.golden.items()
)
print(f"{judge.judge_id}: {right}/{4 * len(pack.cases)} verdicts agree with the labels")
