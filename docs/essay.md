# Your reviewers are already writing policy. Nobody is reviewing it.

*Why Precedent treats a human correction to an AI judge as a code change.*

Every LLM that makes decisions in production is supervised by people. A QA
analyst listens to a sample of calls the model scored. A customs broker checks
the tariff codes it proposed. A claims handler reopens the cases it closed. These
people disagree with the model often, and each disagreement carries something
the model did not have: a reading of the policy, a piece of context, a judgment
call that the organisation stands behind.

What happens to that disagreement decides whether the system improves or decays.
In most teams it meets one of three fates.

## Three fates of a correction

**It is lost.** The reviewer fixes the one decision in front of them and moves on.
Next week the model makes the same mistake on a similar case, and someone fixes
it again. The organisation pays for the same insight every time it recurs.

**It is pasted into the prompt.** Someone adds a sentence: "a callback from a team
lead counts as an escalation offer". That edit applies to every future case,
including thousands nobody looked at. Nobody can say which past decisions it
would have changed, whether it contradicts a sentence added last month, or who
agreed to it. When the model behaves differently on Tuesday than on Monday, the
prompt history, if anyone kept one, is the only explanation.

**It is learned as a pattern.** This is the sophisticated version, and the most
dangerous. The system notices what the corrected case had in common with others
and generalises. The first version of this project did exactly that, and it is
the reason the second version exists.

## How a learning system learned the wrong thing

A supervisor corrected a call where the agent had offered "a supervisor to
discuss a repayment path". The system stored the lesson as a rule triggered by
the word *repayment*. On the next similar call, one that offered a repayment path
and **no** supervisor, the rule fired and passed a call that should have gone to
review. The held-out score dropped from 1.0 to 0.67. The evaluation said
`improved: True`, because it measured whether the answer *changed* in the
direction of the correction, not whether it got *closer to the truth*.

The word "repayment" was a correlate of the correction, not its reason. The
reason was "a supervisor was offered". A human who wrote the rule down would
probably have caught that. A system that infers rules from surface features will
not, and a system that grades itself on its own intent will report success.

## Software already solved this problem

We do not let engineers change production behaviour by editing a live file and
hoping. A change is a diff. It states its intent. Tests run against everything
that used to work. Someone else reviews it. It can be reverted. The history is
append-only and anyone can read it.

A correction to an AI judge is a change to production behaviour. Precedent gives
it the same treatment:

| software | Precedent |
|---|---|
| issue | a correction: this decision was wrong, here is the right label and why |
| diff | a rule: `when <conditions> then <item> = <label>` |
| tests | every labelled case, every past correction, a frozen held-out set |
| failing test that must stay failing | counter-examples: cases the rule must not touch |
| CI | the gate: blocks on any case that goes from right to wrong |
| code review | approval by someone other than the author |
| revert | one event; the rule stops applying |
| git log | an append-only event log with a hash chain |

The mapping is not decoration; it decides the details. Because a rule must list
counter-examples, the reviewer has to think about where it should **not** apply,
which is exactly the thought the keyword rule skipped. Because the gate counts
broken cases one by one, a rule that fixes two cases and breaks one cannot hide
behind a better average.

## Perception and decision, separated

For a rule to be testable, its effect must be deterministic. A sentence added to
a prompt is not: you cannot know what it does without running the model on
everything, and even then the next run may differ.

So Precedent splits the work. The model **perceives**: in one call per case it
labels each rubric item and answers a library of narrow yes/no questions about
the case ("did the agent offer contact with a supervisor?", "is this part of
general use?"). Every "yes" must come with a quote that exists word for word in
the case; claims that cannot be quoted are downgraded. Code **decides**: rules
read those answers, never the raw text, so applying a rule is a lookup, and
re-checking every rule against every case after any change takes milliseconds.

The predicates are also the vocabulary in which a reviewer states a reason. "This
should pass because the customer was offered a callback from a team lead" becomes
`supervisor_contact_offered = yes`. Writing the reason down in that vocabulary is
most of the value: it separates the cause from the coincidence.

## What a small experiment already showed

On a deliberately small pack of 28 calls, two judges, a keyword baseline and
Gemma 4 running locally, agreed with the labels equally often, 107 of 112
verdicts, and failed in completely different places. The keyword judge missed
callbacks phrased as "my team lead can call you back"; Gemma got those right and
instead gave a confident verdict on a hotel booking call that had nothing to do
with debt collection.

Then the same keyword rule from version one was run through the gate on top of
each judge. On the keyword judge it broke three verdicts. On Gemma it broke five:
the model reads "can we agree on a payment date?" as an offer of a repayment plan,
so the rule fires more often and does more damage. **A rule is only safe relative
to the judge it was tested on.** That is why every gate result records the judge,
and why the next step is to re-run the gate on every active rule whenever the
model is upgraded. Model upgrades are when silent regressions happen.

## Where this goes

Nothing here is specific to call centres. The same machinery fits wherever an AI
makes many similar judgments, experts correct some of them, and someone outside
the team will eventually ask why: tariff classification, claims triage, alert
review, content moderation, the house rules a coding agent should follow. Only the
pack changes: the rubric, the predicates, the policy, the labelled cases.

What is not known yet matters as much. The packs are small and labelled by one
person, so there is no ceiling to measure against. The cheapest serious
competitor, "put the corrections into the prompt as examples", has not been
beaten on a public benchmark yet; that comparison, on public customs rulings, is
next. If it loses, the gate and the log still stand, but the predicate rules
would need to justify themselves differently. We would rather publish that
result than not run the test.

---

*Aleksandr Mordvinov, [Scanovich](https://scanovich.ai). Precedent is open source:
[github.com/FUYOH666/precedent](https://github.com/FUYOH666/precedent).*
