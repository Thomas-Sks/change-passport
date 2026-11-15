# 1. The problem

## What changed

Agents now write a large share of the code. In 2026 the bottleneck is no longer writing code, it is **verifying** it.

| Observation | Source |
|---|---|
| Review time ×5, incidents per PR +243%, 31% more PRs merged with no review at all, in teams adopting AI heavily | Faros AI, *Acceleration Whiplash* (2026, 22,000 developers, vendor data) |
| AI-written code receives 1.9× more blocking review threads | Google, 3.5 M C++ changes (arXiv 2608.06640, 2026) |
| Most agent-written PRs receive **no human review at all**; when reviewed, it is mostly by other agents | AIDev study (EASE 2026, arXiv 2605.02273) |
| Tieto's own Agentic DevOps doubled delivery productivity, with a human approving every merge | Tieto, *Agentic DevOps with GitHub Copilot* (Sept. 2026) |

**Doubling the output of agents doubles the review load.** Human review becomes the constraint.

## Why line-by-line review is not the answer

1. **It does not scale.** Detection collapses beyond roughly 150–400 changed lines per review; agent changes routinely exceed that (one of the challenge branches changes 237 files).
2. **It was already weaker than we think.** Before automation, Vercel found that more than half of its PRs were approved without a single comment and 18% in under 5 minutes. A human click is often a rubber stamp.
3. **Reading is not checking.** A reviewer reading complex code labelled "AI" accepts *more* incorrect changes (controlled study, 385 reviewers, FSE 2026).

## Why "let the AI approve" is not the answer either

1. **AI reviewers miss a lot.** The best tools reach 50–60% F1 on real pull requests (Martian Code Review Bench, 2026), and almost nothing beyond ~150 changed lines (arXiv 2606.15689).
2. **They are confidently wrong.** Explanations raise human confidence without raising correctness (arXiv 2607.08885, 2026).
3. **A model judges its own family favourably** (+3 to +8 points, arXiv 2609.17857) and corrects its own errors far less than others' (arXiv 2606.05976).
4. **The agent's own tests prove little.** 80% of tests written by agents have weak or no oracles (*All Smoke, No Alarm*, arXiv 2606.18168); about 1 in 5 "resolved" benchmark patches is actually wrong (SWE-ABS, arXiv 2603.00520).
5. **Accountability disappears.** Companies that auto-approve low-risk changes (Meta RADAR, Vercel, Intercom) publish speed and revert numbers, but none states **who answers when an auto-approved change breaks** — the person nearest to the failure ends up blamed for something they did not control (the "moral crumple zone").

## The design goal

> A **named human** can accept an agent-written change **without reading all of it**, because **evidence traceable to the requirement** shows what was checked, and the system says plainly **what was not checked** and **what the AI refused to decide**.

Three questions every change must answer:

1. **Does it do what was asked?** (requirement)
2. **What could break?** (risk)
3. **Who answers for it?** (accountability)
