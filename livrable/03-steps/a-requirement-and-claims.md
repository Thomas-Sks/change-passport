# Step 1 — Requirement, locked criteria, agent claims

A human locks 3–6 short acceptance criteria; the agent declares one-sentence claims; both go into the passport.

## 1.1 Locked acceptance criteria

**What it does.** Before (or right after) the agent is assigned, a human writes 3–6 short acceptance criteria for the requirement, e.g. *"Generated code still compiles for every existing valid user project."* The criteria are stored with a hash; the agent cannot change them. Every later step checks the change **against these criteria**, not against what the agent says.

**Why this choice.**
- Every check needs an **oracle**: something that says what "correct" means. If the oracle comes from the agent (its tests, its summary), the check proves what the agent *believes*, not what was *asked*. LLM-generated test oracles tend to mirror the code's actual behaviour rather than the expected behaviour (arXiv 2410.21136).
- **Validating** a link between a requirement and code is far more reliable than discovering it (98.9% vs 85.5% on automotive requirements, TVR, arXiv 2504.15427). Short criteria written by a human give the machine something to validate against.
- Formal verification work shows agents sometimes **weaken the specification** instead of fixing the code (Vero benchmark, arXiv 2608.13522). Locking the criteria prevents that.

**Why short.** Long specifications do not buy trust: a Spec Kit experience report produced 2,577 lines of markdown for one feature, 3h30 of review instead of 15 minutes, and still missed an obvious bug (Scott Logic, Nov. 2025). We aim for criteria a reviewer can read in one minute.

**Alternatives rejected.**
- *Use the issue text as is* — prose cannot be checked by a machine.
- *Let the agent write the criteria* — the agent would grade its own homework.
- *Full spec-driven development* (Kiro, Spec Kit) — useful upstream, but too verbose to be the review contract.

**Limits.** A badly written criterion gives a passport that is "proven" and still wrong. Criteria cost human time; this is the main price of the concept.

**Generic or per repository?** Generic. Fits existing flows: at Tieto the Product Owner already approves a requirements document before stories are created — the criteria are extracted from it.

## 1.2 Agent claims

**What it does.** The agent declares, one sentence each, what it claims to have done ("All generated formatters carry the attribute", "No behaviour change at runtime") and which criterion each claim serves.

**Why this choice.**
- A claim is something that can be **proven or contradicted**. A free-form summary cannot.
- Claims make **orphan code** visible: code that serves no claim and no criterion is the classic agent drift (unrequested refactors, build tweaks).
- Agents already produce this material: Tieto's planning agent writes a "standard tracking file"; it becomes the claim list.

**Alternatives rejected.** *Trusting the agent's completion report* — the author summarising its own work is self-assessment, exactly what the challenge asks us to avoid.

**Limits.** An agent can write vague claims to "cover" everything. That is why links are checked independently (Step 2) and claims only count when evidence supports them (Step 3).

**Generic or per repository?** Generic; requires the agent prompt/template to emit claims.
