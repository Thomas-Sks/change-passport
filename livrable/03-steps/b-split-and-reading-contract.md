# Step 2 — Split the change and build the reading contract

The diff is sorted by a versioned policy; generated files are regenerated and compared; moved code is detected; each hunk is linked to a criterion. What remains becomes the **reading contract**, sorted by risk, with the list of what is excluded and why.

## 2.1 Policy zones

**What it does.** A versioned policy file (owned by the policy guardian, protected like CODEOWNERS) classifies every changed file: *mechanical* (generated), *ordinary*, *sensitive* (public API, build/CI, agent instruction files, security, data migrations), *tests*, *docs*. Sensitive zones have a severity (minor/major).

**Why this choice.**
- Every company that auto-approves part of its PRs starts with **hard rules the AI cannot override**: CODEOWNERS paths, size limits, never-auto-approve zones (Vercel, Rewind, Ona, Meta RADAR — 2026 engineering blogs).
- A rule is **explainable**: "this file is in the public-API zone" is a reason anyone can check. The challenge explicitly rejects "a risk score nobody can explain".
- **The LLM may raise a zone's risk, never lower it** (Vercel, Rewind).

**Limits found by research.** A path is not a risk: critical logic in an "ordinary" file that feeds the public API slips through. Target improvement: **raise a hunk's level when a changed symbol is used by a sensitive zone** (call graph or symbol search, as Meta's Diff Risk Score uses change features).

**Generic or per repository?** Mechanism generic; **zone content is per repository** (like CODEOWNERS).

## 2.2 Generated and derived files

**What it does.** Files produced by a tool (snapshots, generated code, lockfiles) are **regenerated in the sandbox from their sources and compared** with the committed version. If they match, they are proven without being read. Any difference not reproduced by regeneration goes to the reading contract. Derived files (e.g. code produced from a template) are read through their source.

**Why this choice.** Agent changes are often dominated by generated output (one challenge branch: 222 of 237 files). Reading them is wasted attention; trusting them blindly is dangerous, because an agent can regenerate snapshots to make a wrong behaviour "green". Regeneration turns them into evidence.

**Alternative rejected.** *Collapsing generated files* (GitHub `linguist-generated`) — hides them without proving them.

**Generic or per repository?** Generic; the regeneration command is per repository.

## 2.3 Moved code

**What it does.** A block deleted in one place and added identically elsewhere in the same diff is a move, not new logic. It is excluded from reading, with the proof (source location) shown.

**Why.** Moves otherwise count twice (deleted + added) and inflate the reading contract; Devin Review and GitHub's stacked-PR guidance treat moved code separately (2026).

## 2.4 Links between code and criteria

**What it does (target form).** An **independent model**, which does *not* see the agent's claims, proposes for each changed hunk the criterion it serves, with a one-line justification. The proposal is compared with the agent's claims:
- agreement → linked;
- disagreement → risk signal shown to the owner;
- no criterion → **orphan code**, always in the reading contract.
The owner confirms or rejects links in one click.

**Why this choice.**
- Keyword matching lets the agent write its own traceability (a broad keyword links everything) and misses synonyms.
- LLM traceability recovery has improved (R2Code, F1 0.73, arXiv 2604.22432) but **is still a proposal, not a proof** — hence human confirmation.
- Linking hunk → *criterion* (not hunk → *claim*) removes the agent from the chain.

**Limit.** In our reference implementation, links are still made by keyword patterns per claim. We present the target form and state this gap.

## 2.5 The reading contract

**What it does.** The list of hunks the owner must read, **sorted by risk** (orphan code and files breaking a rule first, then weak tests, then sensitive zones), plus a table of **what is excluded and why** (rule, proof).

**Why this choice.**
- **Order matters**: a defect placed in the last file of a review has 64% lower odds of being found (controlled experiment with 106 developers, Fregnan et al., FSE 2022); defect rates rise with file position across 330,000 PRs (Rahman et al., 2026).
- **Showing exclusions prevents false assurance**: "read 46 lines" means nothing if the filter silently dropped a dangerous hunk.

**Generic or per repository?** Generic.
