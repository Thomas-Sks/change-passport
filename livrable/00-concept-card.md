# The Change Passport: concept card

*Tieto challenge "Earned Trust in AI Code", Junction 2026*

## Recommendation

Don't ask reviewers to read agent code faster: **change what they review.** Every agent-written change ships with a **passport** that states what was asked, what the agent claims, an **executed proof** for each claim (before vs after, in a sandbox), what the AI **refused to decide**, and **how much a human must read**. A **named owner** reads only what the risk requires and signs a **bounded attestation**. The AI advises with evidence. It never approves.

> **The LLM proposes, execution proves, rules decide, a named human signs.**

**Change** (code + requirement ID + agent claims) → **Sort** (zones, traceability, orphan code) → **Prove** (sandbox, base vs branch, 3 runs) → **AI review** (blind to proofs, then verified against them) → **Lane** (green / orange / red, explicit rules) → **Owner signs** (bound to the commit)

## Principles

1. **Requirement first:** short acceptance criteria locked by a human before review.
2. **Evidence, not confidence:** a claim counts only if an executed proof supports it.
3. **Independence from the agent:** the agent's own tests are the weakest evidence.
4. **Rules decide the lane:** the AI can raise risk, never lower it.
5. **Review depth follows risk:** a human signs in every lane, even green.
6. **Refusing is a normal output:** API, user-visible behaviour, compatibility and risk acceptance go to a person.
7. **Trust is earned per zone:** it is lightened by track record and suspended after an escape.
8. **The factory secures itself:** PR content is untrusted input, and no AI has merge rights.

## How it balances the five tensions

| Tension | Our answer |
|---|---|
| **Risk** | Explainable rules route attention: green 1–2 min, orange reads a listed part, red goes back to the agent |
| **Hallucination** | Every AI finding must quote code and is checked against proofs: *confirmed*, *rejected*, or *opinion — proofs disagree* |
| **Transparency** | The passport says what was **not** checked and why; every proof replays with one command |
| **Confidence** | No model-stated confidence is used. Evidence sets severity |
| **Quality** | Mutation testing measures the agent's tests; catching tests come from the criteria, not from the agent |

## What the owner signs

**Checked** (by whom or what) · **Not checked** (why) · a decision on **each AI refusal** · **residual risk accepted** · bound to the **commit** and the passport fingerprint. The signing step itself refuses the wrong signer, a newer commit, unanswered refusals, and a red change accepted without a full read.

## Shown on REQ-2297 (agent-written, 237 files)

The agent's 169 tests were green, yet execution against the criteria found **2 user-breaking regressions**. The owner had to read **46 of 1,392 lines**. The AI reviewer made 4 findings, all confirmed by proofs, **missed 1** and **refused 6 decisions**. Lane **red**: Camille Durand (synthetic) signed "send back" on the real PR, bound to commit `a0aa5ab2`. On two bug fixes the issue's reproduction **crashes before and works after**, with 39 and 36 lines to read.

## How trust is measured

Reverts and incidents **per lane and zone** · **random counter-review** of 10% of green changes · **canary bugs** injected continuously · share of AI findings confirmed by evidence · time to merge per lane · share routed to humans. **Circuit breakers** are set in advance: an escape suspends its zone, and a canary passing green suspends the green lane.

## Trade-offs and limits

- **Cost:** humans write 3–6 criteria per change, and each repository needs one end-to-end harness per product type.
- **Friction:** a signature even in green. *A false orange costs a review; a false green costs an incident.*
- **Bounded by the criteria:** a wrong criterion gives a passport that is proven and wrong.
- **Not judged:** architecture and product intent. They become refusals, that is, human decisions.
- **Without agent claims and harnesses,** the passport still routes and records accountability, but the owner reads everything.

## The judges' questions

- **Who owns the decision?** The named CODEOWNER signs and merges. The policy guardian owns the rules. The AI owns nothing.
- **What would make us distrust our own output?** A canary passing green, a revert linked to a green passport, counter-review agreement dropping, or signatures faster than the required reading.
- **How does it scale?** Reading grows with **risk**, not diff size (3–17% of lines on our samples). Proofs run in parallel on existing CI runners, and the chain takes minutes per change.
