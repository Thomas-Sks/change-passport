# 6. Limits and failure modes

## What is generic, what must be configured per repository

| Component | Generic | Per repository | Per requirement |
|---|---|---|---|
| Locked criteria, agent claims | ✓ | | criteria text |
| Policy zones, lanes, verdict engine | ✓ (mechanism) | zone list (like CODEOWNERS) | |
| Regenerate & compare generated files | ✓ | regeneration command | |
| End-to-end sandbox | ✓ (principle) | **one harness per product type** | scenarios derived from criteria |
| Catching tests, mutation, replay | ✓ | test runner + harness template | |
| Assertion-strength check | ✓ (principle) | per language / test framework | |
| AI review, refusal register, signature, trust per zone | ✓ | | |

**Honest cost statement:** the concept saves reading time only where a repository has invested in harnesses and where agents declare claims. Without them, the passport still routes and records accountability, but the owner reads everything.

## What we removed from the workflow because it was over-fitted

While building the reference implementation we wrote some checks for one specific change. We removed them from the concept and kept only their generic principle:

| Over-fitted check | Generic principle kept |
|---|---|
| A regex listing the exact lines allowed in generated snapshots | Regenerate generated files and compare |
| A check that every generated type carries one specific attribute | It is just an acceptance criterion turned into a test |
| Refusals and "not checked" items written for one change | Refusals come only from policy, evidence and the AI reviewer |
| Inspecting .NET reference assemblies to disprove one agent statement | Agent claims about the environment are claims to prove |
| A bench of 8 bugs written for one change | Continuous canary bugs from a library of typical agent defects |

## Limits of the concept

- **Criteria quality** bounds everything: a wrong criterion yields a passport that is proven and wrong.
- **Architecture, cross-system effects, product intent** are not judged — they become refusals.
- **Traceability** is a proposal: LLM link recovery is still imperfect (state of the art F1 ≈ 0.73), so links need human confirmation; our reference implementation still links by keywords.
- **End-to-end evidence proves only what it covers**; untested scenarios stay "not tested".
- **Same model family risk**: if author and reviewer share a family, bias returns; the family of the author is not always known.
- **Industry numbers we cite are mostly self-reported** and selection-biased; we rely on random counter-review for our own measurement.

## Failure modes we observed (in agent code and in our own factory)

| # | Failure mode | Where seen | Countermeasure in the concept |
|---|---|---|---|
| 1 | **Green tests, broken users** | Agent change: all tests green, users' builds broken | Evidence independent of the agent; execution against criteria |
| 2 | **A false premise written into code, docs and tests at once** | Agent stated a platform limitation that does not exist | Environment claims must be proven |
| 3 | **A test that freezes the error** | Agent test asserted its own wrong assumption | Assertion check + test ↔ criterion link |
| 4 | **Undeclared change** (necessary but not announced) | Agent touched shared code without a claim | Orphan code always in the reading contract |
| 5 | **AI reviewer confidently wrong** | Reviewer stated a risky pattern was "fine" | Findings never close a question without evidence |
| 6 | **AI severity miscalibrated** | A compile break rated "low, 0.4 confidence" | Severity set by evidence, not by the model |
| 7 | **Generator inherits the agent's error** | Test generator that read the agent's comments repeated its false premise | Generator sees only criteria and file list |
| 8 | **Over-strict false-positive filter creates false negatives** | Our catch filter dropped a real catch | Filters are tested against known catches |
| 9 | **Static checks ignoring repository conventions** | Tests using the repo's verifier flagged "no assertion" | Repository conventions declared in the policy |
| 10 | **Counting errors in the factory** | More lines "to read" than changed | Invariant: to-read ≤ changed, checked automatically |
| 11 | **A test bench that creates its own signals** | Our bug injector changed file encodings | The bench itself is verified |
| 12 | **A "green" end-to-end run that exercised nothing** | Toolchain mismatch: build passed, generator never ran | Evidence must show the feature was actually exercised |
| 13 | **Over-fitting the factory to one example** | See table above | Generic / per-repository / per-requirement separation |
| 14 | **The AI review is not reproducible** | Two live runs on the same change gave different refusals and different lanes | AI output is advisory; refusals can only raise the lane; findings are verified against proofs |
| 15 | **An AI blind to the evidence asserts a test is missing** | Live run: "no round-trip test exists" while the executed proof runs one | Each finding is checked against the proofs and labelled "opinion — proofs disagree" |
| 16 | **The issue text itself is inaccurate** | Bug report said the analyzer "does not work"; the run showed it crashed | The issue is not evidence; the reproduction run is |
| 17 | **A signature without a gate is only a record** | Our demo PR: the pending status is visible but does not block the merge (no branch protection on the demo repo) | In production the status is a required check; the owner, not a bot, merges |
