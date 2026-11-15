# Lessons log & decision log

## Decision log

| # | Date | Decision | Why | Alternative rejected |
|---|---|---|---|---|
| D1 | 14 Nov | Keep only 2026 sources (earlier foundations only if confirmed in 2026) | Models have changed too much | Mix all years |
| D2 | 14 Nov | Direction: **evidence-based classifier** + specialised reviewers | Review depth according to risk; a single generalist reviewer plateaus at 50–60 % F1 | Single generalist reviewer |
| D3 | 14 Nov | **The AI never approves**, even in the green lane; the named owner always signs | Brief: "AI review is advice with evidence, never the approval itself" | Meta/Vercel-style self-approval |
| D4 | 14 Nov | The lane is decided by **explainable rules**; the LLM can only raise the risk | "A risk score nobody can explain" rejected; Vercel/Rewind practice | LLM risk score alone |
| D5 | 14 Nov | **Trust register per area** | "Trust is earned per area… withdrawn after escapes" | Global circuit breakers only |
| D6 | 14 Nov | Attestation: verified (by whom/what), not verified (why), decisions, residual risk | Brief "What the owner signs" | "Approve" button |
| D7 | 14 Nov | Security excluded then **reinstated** | The brief asks for "frontend, backend and security" | Concept without security |
| D8 | 14 Nov | Counter-review **drawn at random** (10 % of greens) | Published control groups not randomised | Chosen control group |
| D9 | 14 Nov | Main sample: **ju26-issue-2297** | 237 files including 222 snapshots: best demonstrates "accept without reading everything" | 2129 |
| D10 | 14 Nov | The AI reviewer does **not** see our executed evidence | To measure what it finds on its own (precision/recall) | Give it the tests |
| D11 | 14 Nov | Policy v2: the "diagnostics" zone no longer covers the docs of an existing diagnostic | False red observed on 2283 (see F3) | Keep the broad rule |
| D12 | 14 Nov | The T4-generated `*Template.cs` are not read: we read the `.tt`, and the behaviour is proven by the snapshots | Avoids reading the same thing twice | Read everything |
| D13 | 14 Nov | Exclusions from the coverage rule **listed and justified** in the requirement (3 dead fixtures) | Otherwise permanent false positives | Silently ignore |
| D15 | 14 Nov | Addition of **E2E evidence in a sandbox** (frontend: driven journeys; backend: service + ephemeral database; library: consumer project per target) | Reading tells what the code says, running tells what it does; practice of OpenAI Codex, Minitap, Greptile TREX, Devin | Limit ourselves to the agent's unit tests |
| D16 | 14 Nov | "Green E2E" = evidence for the **covered criteria** only, and only if the scenarios come from criteria signed beforehand | The agent's tests were green and the change broke users | "If the E2E passes, the feature is good" |
| D17 | 14 Nov | **One-click replay** of each piece of evidence, base and branch side by side, editable scenario, replay recorded in the attestation | Trust comes from evidence the person can check themselves | Frozen evidence, to be taken on faith |
| D18 | 14 Nov | **"Revert a hunk" mutation testing** on the compiled code of the diff | Measures test strength instead of assuming it (closes the S8 gap) | Line coverage |
| D19 | 14 Nov | **Catching tests** generated from the criteria by a separate process, run on base/branch, never committed; failures on both sides go to a human instead of being discarded | Meta JiTTests; a failure on both sides can be an unmet criterion | Discard everything that does not diverge |
| D20 | 14 Nov | **Anti-flakiness guard**: each test (catching, replay) runs 3× per side; a result that changes = "flaky", never evidence | Main signal not credible without it (Meta JiTTests, TestGen-LLM, Trunk) | A single run |
| D21 | 14 Nov | **Static assertion check** (no assertion, trivial, tautology, text only); the repository's internal verifiers count as assertions | The weak link of LLM tests is the oracle | Rely on "the tests pass" |
| D22 | 14 Nov | **A criterion is only "supported" if a test that cites it (AC-n) passes on the branch** | A link is not evidence; only a linked execution is (ReqToCode, UTBoost) | Support by any evidence |
| D23 | 14 Nov | **Moved code** (identical block deleted elsewhere in the diff) excluded from reading, with the evidence | Do not inflate the reading contract (Devin Review, GitHub) | Count everything as new |
| D24 | 14 Nov | **Reading contract sorted by risk** + table "what does not need reading, and why" | Position effect measured (Fregnan, −64 %); avoid false assurance | Alphabetical order, invisible exclusions |
| D14 | 14 Nov | Nothing is pushed or published to a remote repository; injected-bug branches are local | Explicit request | — |

## Observed failure modes

| # | Where | What we observed | What the chain did | Lesson / rule |
|---|---|---|---|---|
| F1 | 2297 — agent | **False premise written into the code, the docs and the test**: "the attribute does not exist in netstandard2.0/.NET Framework" → feature removed for those consumers | Contradicted by E5 (inspection of the refs); also found by the AI (F1) | An agent's claim about the environment is a claim to be proven |
| F2 | 2297 — agent | **Green tests, broken change**: 169/169 + the agent's tests "fail before / pass after", but CS0579 regression | Revealed by an **independent** acceptance test (E3) | The agent's tests prove what the agent believes, not what is asked |
| F3 | 2297 — agent | **Test that freezes the error**: the test checks for the presence of the wrong guard | Flagged (E7, finding F3) | Measure a test's strength and intent, not its presence |
| F4 | 2297 — agent | **Undeclared change** (TransformUtilities) — necessary but not announced | Orphan + 2 snapshots outside the rule, linked to the same cause | Tracing also reveals *justified* changes that still need explaining |
| F5 | 2297 — AI | **False and confident claim**: "[ExcludeFromCodeCoverage] on a partial class is fine" → the AI missed the exclusion of user code | Caught by E4 | An AI opinion without evidence must never close a question |
| F6 | 2297 — AI | **Underestimated severity**: CS0579 rated *low*, confidence 0.4 | Confirmed and re-rated by E3 | The AI's stated confidence is not calibrated; evidence sets the severity |
| F7 | Factory | **False red** on 2283: the docs of an existing diagnostic treated as an identifier assignment | Policy corrected (D11) | The policy is itself an artefact to review and version |
| F8 | Factory | **Parsing bug**: paths with spaces misclassified (20 snapshots in the "tests" zone) | Fixed; detected because the counts did not add up (202 ≠ 222) | Check the factory's own totals |
| F9 | Factory | **Detection gap**: the agent weakening *its own new* test (S8) got through | Fixed by the tautology check (D21): S8 now flagged | Mutation testing or independent tests are needed; a rule is not enough |
| F10 | Factory | **Without structured claims, no reading avoided** (2283, 2234, 2129: 100 % to read) | Routing only | Requiring traceable claims from the agent is the condition for the gain |
| F12 | Factory | **Compiler version**: the generator (Roslyn 4.12) did not run with the installed SDK (4.11) → "green" E2E build with no generated code at all | Detected because the inspection found no generated type; fixed by pinning the compiler | A green E2E may have tested nothing: always check that the feature was actually exercised |
| F13 | Factory — catching | **The oracle inherits the agent's error**: the first generator, which read the diff, wrote a scenario "netstandard2.0 does not have the attribute" (the agent's false premise) | Spotted when reading the scenarios | The generator must see only the criteria and the *list* of touched files, not the agent's comments |
| F14 | Factory — catching | **Bug in our harness**: the `using` cleanup also removed those of the scenarios' user code → 8 failures on both sides, false | Detected because 8/8 failed everywhere | A uniform result is suspect: check the tool before concluding |
| F15 | Factory — catching | **Invalid generated test** (C8: wrong expected bytes) | Also fails on the base → classified "to examine", discarded | A generated test is a hypothesis; the base serves as the control |
| F16 | 2297 — new | **Question nobody had seen**: the wrapper class generated for the namespace is only excluded via its parent class | Raised by C1/C2/C3, turned into a refusal | Tests generated from the criteria raise questions, not only verdicts |
| F17 | 2297 — measured | **Agent's tests weak, quantified**: they notice only 3 of its 10 changes | Mutation testing (E9) | "Green tests" says nothing without a mutation score |
| F18 | Factory | **Catch filter too strict**: the real C5 detection reclassified "to examine" because its message did not contain "Assert" | Inverted: only a crash (exception) is discarded | A false-positive filter creates false negatives; test it on a real catch |
| F19 | Factory | **False positives of the assertion check**: helper that asserts (C3), repository verifiers (`VerifyCS…RunDefaultAsync`, 2283) | Helpers followed; verifiers declared in the policy | A static check must know the repository's conventions |
| F20 | Factory | **Double counting**: 2283 showed 678 lines to read for 228 modified | Lines of the same file counted only once | Always check that "to read ≤ modified" |
| F21 | Test bench | **Our injection stripped the BOM** from files: part of the "detections" came from this artefact | Injection fixed (BOM kept), bench rerun: still 8/8, S2 detected for the right reason | The test bench must itself be verified |
| F11 | Repository | **Dead fixtures** (3 InterfaceUnion snapshots referenced by no test) | Justified exclusion (D13) | Pre-existing noise must be traced, not ignored |

## Lessons learned

- **L1** — "Before" human review is not a gold standard: at Vercel, >50 % of PRs approved without a comment.
- **L2** — Published self-approval figures are self-reported and biased; cite them as "reported by".
- **L3** — The Vercel post was taken down 48 h after publication; check sources before citing them.
- **L4** — No actor publishes who answers for an auto-approved change that breaks: that is the gap the attestation fills.
- **L5** — On 2297, **the agent was right on the essentials (C1) and wrong on two points that break users**: neither its tests nor a quick read would have shown it; two tests written from the criteria showed it in a few minutes.
- **L6** — The AI reviewer was **precise (4/4) but not complete (4/5)**, and was confidently wrong on the missed point: it directs attention, it does not replace it.
- **L7** — The reading gain (56 lines out of 1,392) comes from the **mechanical rule derived from the requirement**, not from the AI.
- **L8** — The acceptance criteria were written by us **after** seeing the change (hackathon constraint); in production they must be written before.
