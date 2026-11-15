# Sponsor analysis — Tieto (14/11/2026)

**Confirmed sponsor**: Tieto (formerly Tietoevry), challenge **"Earned Trust in AI Code"**, Agentic AI track — https://junction2026.com/challenges/tieto-earned-trust-in-ai-code
Question: *"How does AI code review keep pace with AI-written code, while humans stay accountable for every change?"* — principle: *"AI reviews. Humans stay accountable"*, trust based on *"traceable evidence, not AI confidence scores"*.
Exact unit: probably Tieto Indtech (GitHub org `te-industry-tech-office`) — uncertain. Their AI/dev publications come from Tieto Tech Consulting.

## What they do / say
| # | Item | Source | Conf. |
|---|---|---|---|
| 1 | **Agentic DevOps with GitHub Copilot** (Network Products team, critical telecom, brownfield, on-prem): specialised agents epic → stories → plan → code → tests; MCP to GitLab/Jira/Jenkins; PO validates the analysis, engineers validate the plan, same CI/CD, **a human approves the merge**; ×2 productivity (the "−50 % lead time" is NOT in the article: no lead-time figure, no measurement method) | tieto.com/en/insights/2026/agentic-devops-with-github-copilot (23/09/2026) | verified |
| 2 | Microsoft partnership: "agentic transformation and engineering productivity", 5 000 consultants | fintech.global 28/04/2026 | verified (press) |
| 3 | Agent-driven application modernisation, "human-in-the-loop" | fintech.global 08/07/2026 | plausible |
| 4 | "AI isn't one type of tool": assigned accountability, 6 questions, AI Act / ISO 42001 / NIST, "a new Excel hell, only faster" | tieto.com/en/insights/2026/ai-isnt-one-type-of-tool (04/11/2026) | verified |
| 5 | Responsible AI framework: "human oversight remains indispensable" | Tietoevry blog 01/2025 | plausible |
| 6 | SmartGen AI Suite (Azure OpenAI) | blog 02/2025 | plausible |
| 7 | Tietoevry Care: +23 % R&D productivity thanks to GenAI | press release 11/2024 | verified (headline) |

## Close to us
- The AI never approves; a human approves the merge, CI/CD acts as a gate.
- Traceability from the Jira epic ≈ our requirement ID + locked criteria.
- Upstream human validation (analysis, plan) ≈ criteria signed before the code.
- AI-generated tests — for coverage in their case, as **evidence** in ours (base vs branch).
- Named accountability.

## Gaps (not found publicly)
- Code review **by the AI**: their review remains human + CI.
- Evidence **independent** of the agent's claims (mutation, base/branch, replay).
- **Register of the AI's refusals** (even though the challenge asks for it).
- **Review depth according to risk**: "everything goes through a human" → the bottleneck their ×2 creates.
- **Bounded attestation** (verified / not verified / residual risk).
- **Trust metrics**: they publish productivity (×2, with no measurement method), not reverts/incidents.

## Adapting the pitch
1. Their words: "AI reviews. Humans stay accountable", "earned trust", "traceable evidence, not confidence scores", "mission-critical / telecom-grade", "brownfield".
2. **The logical next step after their Agentic DevOps**: they doubled agent throughput → human review becomes the bottleneck → the Passport keeps the ×2 without losing quality; fits into GitLab/Jira/Jenkins and an existing PR.
3. Stick to the judging criteria: trade-offs slide (Clarity), trust metrics (Measurement).
4. Regulation: attestation = documentary artefact aligned with human oversight (AI Act art. 14) and ISO/IEC 42001 — without claiming compliance.
5. Show the 4 branches: different routing depending on risk, 2297 in red with the refusal register.

## Their actual pipeline (article "Agentic DevOps with GitHub Copilot", 23/09/2026, read in full)

1. **epic-analysis agent** → requirements document → validated by PO + engineers.
2. **story-breakdown agent** → stories/sub-tasks → PO review → Jira creation.
3. **code-planning agent** (read-only) → plan in a "standard tracking file" → validated by an engineer.
4. **implementation agent** (controlled write access) → code + unit tests + docs, following the repository instructions.
5. **Jenkins**: build gates, unit tests, integration tests ("same CI/CD checks as human-written code").
6. **conclusion agent** → completion report + GitLab MR (template) → **human approval** → merge + Jira closure.
Tools: on-prem GitLab, Jira, Jenkins; Copilot as "control plane"; in-house MCP; versioned instructions/skills in a central repository. A "review agent" is mentioned without being described.

## Where to gain an edge, step by step

| Their step | What they have | Gap | What we add | How on their side |
|---|---|---|---|---|
| 1-2 Requirements | Requirements doc validated by the PO | Prose, not machine-checkable | **Locked**, executable acceptance criteria | Extract the criteria from the approved doc into REQ.yaml, fingerprint in the Jira story |
| 3 Plan | Plan validated by an engineer | Nothing checks that the code follows the plan | **Hunk → plan/claim traceability**, orphan code flagged | The "tracking file" becomes the list of claims |
| 4 Code + tests | The agent writes its code AND its tests | Self-validating tests (2297: 3/10 changes seen) | **Diff-scoped mutation** + **catching tests** from another agent based on the criteria | 2 Jenkins stages |
| 5 Gates | Build, unit, integration | Same checks as for a human; 2297: 169/169 green but breaks users | Mechanical rule, base/branch comparison, **E2E on a real consumer** (telecom: SS7/Diameter test bench) | Jenkins stages on a worktree of the base |
| 6 Report | Completion report written by the agent | The author summarises their own work | **Passport** produced by the independent factory: claim → evidence, contradicted ones in red | MR comment + passport page |
| 6 Approval | A human approves each MR | Same depth for everything → bottleneck with ×2; no trace of what was checked | **Risk lanes + reading contract + bounded attestation** | Blocking GitLab external status check; CODEOWNERS for sensitive zones |
| "review agent" | Not described | Unknown, probably same family (Copilot) | Reviewer from another family, quotes, closed grid, **refusal register**, verified by the evidence | Read-only MCP agent |
| Instructions | Central repository of instructions/skills | No feedback loop from failures | Every refusal, confirmed finding or catch → proposed PR on their instructions | Weekly digest reviewed by the guardian |
| Measurement | "×2", without method | No trust metric | Reverts/incidents per lane, mutation score, catch precision, share read, replays | Dashboard fed by Jenkins + Jira |

Practical asset: our factory is **on-prem, no SaaS** (Python scripts, git, dotnet) and fits into GitLab/Jenkins/Jira — their exact constraints.
