# 4. Principles and trade-offs

## How the design balances the five forces of the challenge

| Force | Risk if ignored | How the passport handles it |
|---|---|---|
| **Risk** | Same attention for a typo and a public-API change → rubber stamp | Policy zones + lanes + trust per zone; depth of human review follows risk |
| **Hallucination** | AI invents bugs (noise) or denies real ones (false reassurance) | Findings must quote the diff, survive a refuter and be confirmed by execution; unconfirmed = "opinion"; an empty AI review is never a green light |
| **Transparency** | Nobody can explain why a change was routed or accepted | Deterministic verdict engine with written reasons; reading contract lists what is excluded and why; every proof replayable |
| **Confidence** | Trust in a score or in the AI's tone | No confidence score is shown; only evidence statuses (proven / contradicted / not tested); trust is earned per zone from outcomes |
| **Quality** | Green tests, broken users | Evidence independent of the agent: criteria as oracle, base-vs-branch execution, end-to-end runs, mutation, assertion checks |

## The eight principles and the reasoning behind each

| Principle | Reasoning | What would break without it |
|---|---|---|
| 1. Requirement first | Every check needs an oracle; the agent cannot be its own oracle | Checks prove what the agent believes |
| 2. Evidence, not confidence | AI reviewers reach 50–60% F1; explanations raise confidence, not correctness | "The AI said it was fine" |
| 3. Independence | Same-family judging and self-correction are biased; 80% of agent tests have weak oracles | Agent tests green, users broken |
| 4. Rules decide the lane | Explainable, testable, auditable; the AI can only add risk | Opaque risk scores, silent downgrades |
| 5. Depth follows risk | Human attention is the scarce resource; uniform review becomes a stamp | Either everything is read (no scale) or nothing is (no trust) |
| 6. Refusing is normal | Architecture, product intent, compatibility are human decisions | The AI quietly decides product questions |
| 7. Trust per zone | Autonomy must be earned and revocable (Meta per-recipe history) | One bad zone poisons trust everywhere, or nothing ever gets lighter |
| 8. The factory secures itself | The reviewer reads hostile input | A hijacked reviewer approves or leaks secrets |

## Explicit trade-offs

| Decision | What we gain | What we give up |
|---|---|---|
| Human signs even green changes | Named accountability for every change (challenge requirement) | 1–2 minutes per change; less speed than Meta/Vercel auto-approval |
| Criteria written by humans | An independent oracle | Human time upfront; quality depends on the criteria |
| Lean to orange when in doubt | Fewer escaped defects | More reviews early on, until zones earn trust |
| Execution-based evidence | Proof instead of opinion | One harness per repository/product type; compute cost |
| Mutation only in orange/red | Bounded cost | Green changes rely on other evidence |
| Questions before the AI view | Less automation bias | Friction; users rate such interfaces lower (Buçinca 2021) |
| Precision over recall in AI findings | Owners keep reading them | Some real issues are not raised by the AI — hence execution evidence |
| No AI approval at all | Accountability by construction | We do not reach the 40–75% "no human" rates published by some companies |
