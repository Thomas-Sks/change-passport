# 7. Decision log

| # | Decision | Reason | Rejected alternative |
|---|---|---|---|
| D1 | Use only 2026 sources (older work only when confirmed in 2026) | Models changed too much; 2024–25 conclusions may be obsolete | Mix all years |
| D2 | Direction: an **evidence-based classifier** with specialised reviewers | Depth of review must follow risk; a single generalist reviewer plateaus at 50–60% F1 | One generalist reviewer |
| D3 | **The AI never approves**, even in the green lane; the owner signs every change | Challenge: "AI review is advice with evidence, never the approval itself" | Auto-approval as at Meta/Vercel |
| D4 | Lanes decided by **explainable rules**; the LLM can only raise risk | "A risk score nobody can explain" is not accepted; Vercel/Rewind practice | LLM risk score alone |
| D5 | **Trust register per zone**, earned from history, withdrawn after an escape | "Trust is earned per area… withdrawn after escapes"; Meta per-recipe autonomy | Global kill switches only |
| D6 | **Bounded attestation**: checked (by whom/what), not checked (why), decisions, residual risk | Challenge "What the owner signs"; avoids the moral crumple zone | An "approve" button |
| D7 | Security kept in two forms: a risk dimension and the security of the factory | Brief asks for frontend, backend **and security** considerations | Concept without security |
| D8 | **Random** counter-review of 10% of green changes | All published baselines are non-randomised | A hand-picked control group |
| D9 | AI reviewer does **not** see the executed evidence | To measure what it finds on its own | Giving it the test results |
| D10 | Policy zones restricted after a false red (doc of an existing diagnostic treated as a new public identifier) | The policy is itself a reviewed, versioned artifact | Keep broad rules |
| D11 | Derived files read through their source | Avoid reading the same logic twice | Read everything |
| D12 | Exclusions from any rule must be **listed and justified** | Otherwise permanent false positives or silent gaps | Ignore silently |
| D13 | **One-click replay** of every executed evidence, base vs branch, editable scenario, logged in the attestation | Trust comes from evidence a person can check themselves | Frozen evidence to believe |
| D14 | **Diff-scoped mutation testing** | Measures test strength instead of assuming it | Line coverage |
| D15 | **Catching tests** from the criteria, base vs branch, never committed; fail-both goes to a human | Meta JiTTests; fail-both may mean an unmet criterion | Discard everything that does not diverge |
| D16 | **End-to-end evidence in a sandbox** for backend, frontend and libraries | Reading tells what code says, running tells what it does (OpenAI Codex, Minitap, Greptile, Devin) | Agent unit tests only |
| D17 | "End-to-end green" proves **only the covered criteria**, and only with criteria signed beforehand | Agent tests were green while users broke | "If E2E passes, the feature is correct" |
| D18 | **Anti-flaky guard**: 3 runs per side | A flaky test creates fake catches | Single run |
| D19 | **Assertion-strength check**; repository verifier helpers count as assertions | The weak link of LLM tests is the oracle | Trust "tests pass" |
| D20 | A criterion is "supported" only if a **linked test passes** | A link is not a proof | Any evidence counts |
| D21 | **Moved code** excluded from reading with proof | Do not inflate the reading contract | Count moves as new code |
| D22 | **Reading contract sorted by risk** + exclusions shown | Position effect on defect detection; avoid false assurance | Alphabetical order, hidden exclusions |
| D23 | Test generator sees **only criteria and the file list** | Observed: a generator reading agent comments inherited the agent's false premise | Give it the full diff with comments |
| D24 | Traceability presented in its **target form** (independent model proposes, human confirms) | Keyword links let the agent write its own traceability | Keyword matching as the final design |
| D25 | **Over-fitted checks removed** from the workflow; only generic principles kept | The deliverable must work for any change | Present the demo-specific checks as steps |
| D26 | Generated files: **regenerate and compare** instead of hand-written line rules | Generic for any generator | Per-change regexes |
| D27 | Nothing published to any public repository; the PR demo runs in **one private repository, one PR** | Team constraint; references to the upstream project must not leak | Public fork with 4 PRs |
| D28 | **The whole chain runs live** on a change; evidence too slow to re-run live is reused from a recorded run and **labelled "reused"** | Show where trust comes from, not a recording of it | Pre-recorded demo only |
| D29 | Rules **not tuned** when a live AI review moved a change from orange to red | The AI may only raise risk; tuning rules to a desired lane is over-fitting | Relax the refusal severity |
| D30 | Signature refused unless: the signer is the named owner, the PR head is the commit the passport covers, every refusal has an answer, and a red change is accepted only after a full read | Accountability must be enforced by the tool, not by goodwill | A free-form "approve" comment |
| D31 | The owner's decision is published as a commit status (`passport/owner-signature`): pending → success (accepted) or failure (sent back / rejected) | Works with any required-check merge gate (GitHub, GitLab) | A bot that merges |
