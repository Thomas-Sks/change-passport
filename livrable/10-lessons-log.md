# 10. Lessons log

What we learned while building the reference implementation and running it on the four agent-written changes. Decisions are in the [decision log](07-decision-log.md); failure modes in [limits and failure modes](06-limits-and-failure-modes.md).

## About the problem

| # | Lesson |
|---|---|
| L1 | **Human review "before AI" is not a gold standard.** At Vercel, over half of PRs were approved without a comment. Comparing the passport with an idealised human review would flatter the human. |
| L2 | **Published auto-approval numbers are self-reported and selection-biased.** We cite them as "reported by" and rely on random counter-review for our own measurement. |
| L3 | **Check sources before citing them.** One vendor blog post we relied on was taken down 48 hours after publication. |
| L4 | **No vendor says who answers when an auto-approved change breaks.** That gap is exactly what the bounded attestation fills. |

## About agent-written code

| # | Lesson |
|---|---|
| L5 | On the 237-file change, **the agent was right on the core claim and wrong on two points that break users.** Neither its 169 green tests nor a quick read showed it; two tests written from the acceptance criteria showed it in minutes. |
| L6 | **An agent's environment claims must be proven.** The agent wrote a false platform limitation into code, docs and its own test at once. |
| L7 | **Green agent tests measure the agent's belief.** Under mutation, its tests noticed 3 of its 10 changes. |
| L8 | **The issue text is not evidence either.** On one bug fix, the reproduction showed the analyzer crashed, while the issue said it "did not work". |

## About the AI reviewer

| # | Lesson |
|---|---|
| L9 | **Precise but not complete.** On the large change the AI reviewer found 4 issues, all confirmed, missed 1, and was confidently wrong about the one it missed. It directs attention; it does not replace it. |
| L10 | **Blind review is useful because it can be checked.** Kept away from the evidence, the AI stated in a live run that "no round-trip test exists" while our proof runs one. The verification step caught it; a reviewer that had seen the proofs would have hidden that weakness. |
| L11 | **The AI review is not reproducible, so it must never decide.** Two live runs on the same change gave different refusals; one moved the lane from orange to red. Because refusals can only raise the lane, the variance costs a review, never an escape. |
| L12 | **Severity and confidence stated by the AI are not calibrated.** A compile break was rated "low, confidence 0.4". Severity comes from evidence. |

## About the factory itself

| # | Lesson |
|---|---|
| L13 | **The reading gain comes from rules derived from the requirement, not from the AI.** 46 of 1,392 lines on the large change; 39 of 228 and 36 of 266 on the bug fixes. Without traceable claims from the agent, the passport still routes and records, but the owner reads everything. |
| L14 | **Verify the factory's own numbers.** A path-parsing bug, double-counted lines, a bug injector that changed file encodings and a "green" end-to-end run that exercised nothing were all caught because totals did not add up. |
| L15 | **A uniform result is suspicious.** 8 of 8 scenarios failing on both sides was our harness, not the code. |
| L16 | **A filter against false positives creates false negatives.** Test every filter against a known real catch. |
| L17 | **Accountability must be enforced by the tool.** Writing "the owner signs" is not enough; the signing step itself refuses the wrong signer, a stale commit, unanswered refusals and a red change accepted without a full read. |
| L18 | **Our acceptance criteria were written after seeing the changes** (hackathon constraint). In production they must be locked before the agent starts, or the passport proves what was delivered rather than what was asked. |
