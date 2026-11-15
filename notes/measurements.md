# Measurements — what the demo proves, and what it does not prove

> All the values below come from running `factory/` on the 4 challenge branches (14/11/2026). Public challenge data, synthetic people.

## 1. Share routed to humans and reading avoided

| Branch | Lane | Files to read | Lines to read | Why |
|---|---|---|---|---|
| **2297** (with full evidence chain) | **Red** | **11 / 237** | **56 / 1 392 (4 %)** | 2 criteria contradicted by executed evidence; 1 major refusal |
| 2283 (no claims or evidence) | Orange | 4 / 4 | 228 / 228 | No declared claim → everything is orphan |
| 2234 (no claims or evidence) | Orange | 4 / 4 | 266 / 266 | Same |
| 2129 (no claims or evidence) | Red | 26 / 28 | 1 035 / 1 043 | New public API + new diagnostic identifiers |

**Reading:** the passport reduces reading **only where there is evidence**. Without structured claims from the agent or evidence, it only routes — this is intentional (no trust without evidence). 0 green lanes out of 4: no zone has a trust history yet.

## 2. Are the AI findings real?

AI reviewer (read-only, full context, without seeing our evidence) checked against the executed evidence:

| | Value |
|---|---|
| Findings issued | 4 |
| Confirmed by evidence | **4 / 4 (precision 100 %)** |
| Severity misjudged | 1 (CS0579: rated *low*, confidence 0.4 → compilation regression confirmed) |
| Known real issues | 5 (netstandard guard, CS0579, user code excluded, orphan change, weak test) |
| Found by the AI | 4 / 5 (**recall 80 %**) |
| Missed | User code excluded from coverage — the AI claimed the opposite ("on a partial class is fine") |
| Minor factual error | Attribute located in mscorlib instead of System.dll (net472) |
| Refusals issued by the AI | 3, of which 1 later settled by the mechanical rule (AI-R3) |

⚠️ A single change: order of magnitude, not statistics.

## 3. What does the chain miss? — seeded bugs (deterministic layer only)

8 typical agent defects seeded on **local** branches on top of 2297 (`factory/seed_bugs.py`):

| # | Seeded defect | Result | Caught by |
|---|---|---|---|
| S1 | Behaviour changed in a regenerated snapshot | ✅ flagged | mechanical rule |
| S2 | Template forgotten + snapshots regenerated consistently | ✅ flagged | coverage rule (AC-1) |
| S3 | Unrequested change to the runtime | ✅ flagged | orphan |
| S4 | Assertion removed from an existing test | ✅ flagged | "weakened test" rule |
| S5 | Silent addition to the public API | ✅ flagged | major zone → red |
| S6 | Build change slipped in | ✅ flagged | orphan + sensitive zone |
| S7 | Logic changed in a template | ✅ flagged | orphan |
| S8 | The agent weakens **its own new** test | ❌ **missed** | — |

**7 / 8 flagged, 1 missed** (v1) → **8 / 8 after priority 1** (tautology check). ⚠️ Bias: we knew the rules when writing the bugs → this recall is optimistic. S8 shows the limit: the strength of a *new* test is only measured by analysis (E7) or mutation testing, not by a rule.

## 4. Would the agent's human reviewer have been enough?

The agent's tests: 169 / 169 green, and its 2 new tests "fail before, pass after". **According to its own evidence, the change was perfect.** Our 2 independent acceptance tests (written from the criteria, not from the code) reveal 2 regressions. This is the demonstration of principle 3 (independence of evidence).

## 3 bis. After priority 1 (anti-flaky guard, assertion strength, test ↔ criterion link, moved code, sorted contract)

| Measure | Before | After |
|---|---|---|
| Seeded bugs flagged | 7 / 8 | **8 / 8** (S8 caught by the tautology check) |
| "Moved code" control (S9) | — | excluded from reading, with the evidence of the original block |
| Unstable catching tests over 3 runs | not measured | 0 / 8 |
| 2297 criteria "supported" by a passing linked test | — | 0 / 4: AC-1 and AC-4 are "supported without a passing linked test", AC-2 and AC-3 contradicted |
| Agent tests linked to a criterion | — | 0 / 2; 1 "text only" test |
| Lines to read on 2297 | 42 | **56** (+14: the agent's weak test) then **46** once the rules tailored for 2297 were removed (generated files proven by regeneration) |

## 4 bis. End-to-end evidence in a sandbox (E8)

Real consumer project built with the branch's generator, for two targets, then inspected by reflection (`factory/e2e/`):

| Target | Generated types excluded | User-written code (`AppResolver.UserBusinessRule`) |
|---|---|---|
| net8.0 | 5 / 5 ✅ | **excluded ❌** (should remain measured) |
| netstandard2.0 | **0 / 5 ❌** (feature missing even though the attribute exists) | measured ✅ |

The E2E confirms in real conditions 2 of the 3 issues found by the acceptance tests, **and gives the most readable evidence for the owner** (a table, not code).

## 4 ter. Test strength (mutation) and catching tests

**"Revert a hunk" mutation testing** (10 mutants, one per agent change in the compiled code):

| Test set | Mutants killed |
|---|---|
| Tests delivered by the agent | **3 / 10** |
| Full suite (snapshots included) | 10 / 10 |

The snapshots notice any output change but do not say whether it is correct; the agent's tests, for their part, only see 3 changes out of 10.

**Catching tests** (8 scenarios generated from the criteria by a separate process, run on base/branch, ~100 s):

| Class | Count | Example |
|---|---|---|
| Catch (passes before, fails after) | 1 | C5: CS0579 regression — **rediscovered without seeing our tests** |
| Fails on both sides → human | 4 | C1–C3: nested class excluded only via its parent (new question); C8: invalid test |
| No difference | 3 | — |

**One-click replay**: each piece of evidence E2, E3, E4, E8, E10, E11 can be replayed on base and branch in 10 to 25 s (`factory/server.py`).

## 5. What the demo does not measure (and how we would measure it in production)

| Judges' question | In production | In the demo |
|---|---|---|
| Reverts/incidents when review decreases | Reverts and incidents **per lane and per zone**, linked to the originating passport; counter-review of 10 % of greens drawn at random | Not measurable (no production history) |
| AI findings accepted | % confirmed ("Incorrect?"), % followed by a change | 4/4 confirmed |
| Time to merge | p50/p75 per lane; signature time measured | To be timed during the live demo |
| Share routed to humans | Green/orange/red split; lines read / lines changed | 0 % green; 4 % of lines to read on 2297 |
| Recall | Canary bugs seeded continuously | 7/8 (deterministic layer); AI 4/5 |

**Circuit breakers**: zone suspended at the first linked revert; green lane suspended if counter-review agreement < 90 % or if a canary goes green.
