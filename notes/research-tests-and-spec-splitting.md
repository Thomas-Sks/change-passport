# Tests, splitting the code and the code ↔ specs link — what we add, what we fix

> 4 research passes (14/11/2026): big tech & labs, startups / scale-ups, splitting a diff for review, code ↔ requirements traceability.
> Only the items **applicable to our factory** are kept. Cost = effort for the demo.

---

## 1. What the research confirms in what we did

| Our choice | Confirmed by |
|---|---|
| Locked criteria written by a human, used as the oracle | LLM oracles that copy current behaviour (arXiv 2410.21136); link validation far more reliable than discovery (TVR, 98.9 % vs 85.5 %) |
| Base vs branch comparison, "passes before / fails after" | Meta JiTTests (FSE 2026; 60 % true positives, −20 % incidents) |
| Diff-scoped mutation rather than coverage | Google (≈17 M mutants), Meta ACH (277 tests we would have thrown away on coverage alone), Qodo Cover abandoned (06/2025) |
| AI reviewer from another model, triaged before the human | Uber uReview: Claude Sonnet 4 generates, o4-mini-high grades; 75 % useful, 65 % acted on |
| Risk lanes | Meta only runs JiTTest on risky diffs |
| Orphan code flagged | Absent from Kiro and Spec Kit: this is a contribution |
| Deterministic, explainable splitting | CodeRabbit Change Stack and Devin Review group by LLM but publish **no measurement** |

## 2. What the research calls into question (to fix)

| Current weakness | Why it is a problem | Fix |
|---|---|---|
| **No guard against flaky tests** | A test that passes/fails at random becomes a false "catch": our main signal loses its credibility | Re-run each test 3× on base and branch; unstable result = "unstable", never "catch" |
| **Assertion strength not checked** in generated tests | The weak link of LLM tests is the oracle, not coverage (Ernst, ASE 2025) | Reject tests with no assertion, `Assert.NotNull` alone, tautologies; require each test to kill at least one mutant |
| **"Revert a hunk" mutant too coarse** | Removing a whole hunk is easy to detect; it does not simulate a real mistake | Add fine-grained mutants on the changed lines (**Stryker.NET `--since`**, built for C#) and LLM semantic mutants per criterion (Meta ACH) |
| **A file's path ≠ its risk** | Critical logic in an "ordinary" file that feeds the public API slips under the radar | Globs = floor; we **escalate** a hunk if a modified symbol is used by a sensitive zone |
| **Moved code counted as deleted + added** | Inflates the reading contract | `git diff -M --color-moved`; proven refactorings taken out of the contract with the evidence shown |
| **Unordered reading contract** | A defect in the last file is **64 % less likely** to be found (Fregnan, FSE 2022, 106 developers) | Sort by risk then by dependency; sensitive and orphan items first |
| **Possible false assurance** | "42 lines" is worthless if the filter missed a dangerous hunk | Show **what was excluded and why** (rule + evidence) |
| **Keyword-based traceability** | The agent can write its own traceability; false links (`auth` links everything), missed links (synonyms, support code); no precision measurement | See §3, S1 and S2 |
| **Hunk ↔ agent claim link**, not hunk ↔ criterion | The criterion → claim → hunk chain goes through the agent, which is not independent | Direct hunk ↔ criterion link proposed by an independent model |
| **Human review of every catch, one by one** | Does not scale | Meta: human "on-the-loop", aggregated review + filters (−70 % human review); show the **precision** of catches (8 true out of 41 in the JiTTests paper) |

## 3. What we add (ranked by priority)

### Priority 1 — quick, strengthens credibility (low cost)
| # | Addition | Inspired by | Where in the passport |
|---|---|---|---|
| T1 | **Anti-flaky guard**: 3 runs base + branch per test; deterministic filter on catches (failure on an assertion, not on the build; assertion touching a modified symbol) | Meta JiTTests, TestGen-LLM, Trunk | Catching tests, replay |
| T2 | **Assertion strength check** on generated tests and on the agent's tests | Ernst ASE 2025, LLM oracles | Evidence ("test strength") |
| S2 | **Explicit test ↔ criterion link** (`AC-3` in the name or an annotation); "supported" requires a passing linked test; criterion with no test = flagged | ReqToCode (2026), Gherkin | Acceptance criteria |
| D1 | **Moved/renamed code detected** and removed from the contract with the evidence | Devin Review, GitHub, RefactoringMiner | Reading contract |
| D3 | **Contract sorted by risk/dependency** + **list of what is excluded and why** | Fregnan FSE 2022; Rahman 2026 | Reading contract |

### Priority 2 — new evidence (low to medium cost)
| # | Addition | Inspired by | MessagePack application |
|---|---|---|---|
| T3 | **Property-based tests** derived from the criteria (FsCheck/CsCheck), fixed seed, base vs branch | Anthropic (Jan. 2026: 984 reports, 81–86 % valid at the top of the ranking) | `Deserialize(Serialize(x)) == x` on random types → AC-4 |
| T4 | **Fine-grained mutants** (Stryker.NET `--since`) + **a generated test for each surviving mutant** | Meta ACH (73 % of tests accepted) | 7 changes not seen by the agent's tests → 7 tests proposed |
| S1 | **Hunk → criterion links proposed by an independent model** (which does not see the agent's claims), with justification; disagreement with the agent = risk signal; one-click human confirmation | R2Code (F1 0.73), TVR, LinkAnchor | Traceability |
| D2 | **Escalation by impact**: modified symbol used by the public API or the generator core; `linguist-generated`/`@generated` file edited by hand → sensitive | Meta Diff Risk Score, GitHub linguist | Splitting |

### Priority 3 — for the concept and Tieto (to describe, not to demonstrate)
| # | Addition | Inspired by | Why for Tieto |
|---|---|---|---|
| T5 | **Record real traffic then replay it on base and branch**; any differing response not explained by a criterion = risk | Keploy (open source), Speedscale proxymock — run on-site | On-prem SS7/Diameter telecom services |
| S3 | **Provenance**: each link carries an Agent Trace record (range → conversation → model) + criterion ID + Jira story + MR | Agent Trace (Cursor, Jan. 2026), Entire Checkpoints | Jira ↔ MR traceability they already advertise |
| D4 | **Group hunks by intent** (explicit + semantic dependencies) | ColaUntangle (+44 % in C#) | Large agent changes |
| — | Deterministic simulation (Antithesis), assisted fuzzing (CI Fuzz) | — | Horizon for critical software; expensive |

## 4. To avoid
- **Long specs**: Spec Kit produced 2 577 lines of markdown for one feature, 3 h 30 of review instead of 15 min, and an obvious bug went unseen (Scott Logic, 11/2025). Our criteria must stay **short** (4 for 2297).
- **Test selection that skips tests** (CloudBees Smart Tests): contrary to complete evidence; to be used only for ordering.
- **Treating a link as evidence**: a hunk linked to a criterion does not show that the criterion is satisfied; only a passing linked test shows it.

## Main sources
Meta JiTTests: arxiv.org/abs/2601.22832 · engineering.fb.com/2026/10/29/security/catching-bugs-before-they-land-jittestings-human-on-the-loop-approach-at-full-scale · Meta ACH: arxiv.org/abs/2501.12862 · Anthropic PBT: anthropic.com/research/property-based-testing · arxiv.org/abs/2510.09907 · Oracles: arxiv.org/abs/2410.21136 · Google mutation: arxiv.org/abs/2102.11378 · Uber uReview: uber.com/blog/ureview · Uber AutoCover (ICSE 2026) · Keploy: keploy.io · Speedscale proxymock: speedscale.com/proxymock · Stryker.NET · Antithesis Hegel: antithesis.com/blog/2026/hegel · ColaUntangle: arxiv.org/abs/2507.16395 · CodeRabbit Change Stack (13/05/2026) · Devin Review (21/01/2026) · GitHub "giant AI PR → stack" (04/08/2026) · RefactoringMiner: arxiv.org/abs/2403.05939 · Meta DRS (06/08/2025) · Fregnan et al. FSE 2022: arxiv.org/abs/2208.04259 · Rahman et al.: arxiv.org/abs/2609.22610 · R2Code: arxiv.org/abs/2604.22432 · LiSSA (ICSE 2025) · ReqToCode: arxiv.org/abs/2603.13999 · TVR: arxiv.org/abs/2504.15427 · PatchGuru: arxiv.org/abs/2602.05270 · UTBoost: arxiv.org/abs/2506.09289 · Agent Trace: agent-trace.dev · Böckeler (martinfowler.com, 10/2025) · Scott Logic on Spec Kit (26/11/2025)
