# Audit: which steps are generic, which are tailored to our case?

Three levels:
- **Generic**: the mechanism works for any change, any repository.
- **Repository adapter**: the mechanism is generic, but it has to be configured once per repository (like CODEOWNERS or a CI pipeline).
- **Overfit**: written for 2297; to be reformulated or removed from the concept.

| # | Step | Level | What is specific | Generic version to present |
|---|---|---|---|---|
| 1 | Requirement + locked criteria | Generic | — | A human writes 3–6 short criteria before the agent works |
| 2 | Agent claims | Generic (concept) / handmade (demo) | We extracted them from the agent's README | The agent **must** declare them (at Tieto: the plan's "tracking file") |
| 3 | Split into zones | Repository adapter | `templates-compiles` (T4), `snapshots` zones: specific to MessagePack | Policy per repository, like CODEOWNERS; sensitive zones = public API, build/CI, security, data |
| 4 | Mechanical rule on snapshots (regex of the 3 allowed lines) | **Overfit** | Regex handwritten for 2297 | **Regenerate** the generated files in the sandbox and compare with the committed ones; any non-reproduced difference = to read |
| 5 | Coverage rule (each type carries the attribute) | **Overfit** | Invariant specific to requirement 2297 | It is not a step: it is an acceptance criterion turned into a test (step 7) |
| 6 | Hunk → claim traceability by keywords | Generic but **naive** | Patterns written by us | Hunk → criterion link proposed by an independent model, confirmed by the human (not built) |
| 7 | Acceptance tests from the criteria | Generic | Written by me, already suspecting the bugs (bias) | Generated from the criteria (step 10) + completed by a human |
| 8 | End-to-end test | Generic / adapter | .NET harness (consumer project, reflection) | Run the real product: library → consumer project; service → start + calls; UI → browser. One harness per product type |
| 9 | "Revert a hunk" mutation | Generic | — | Any language with tests; cost N × suite → reserved for orange/red lanes |
| 10 | Catching tests (base vs branch) | Generic / adapter | The prompt contains the repository's Roslyn harness | One harness template per repository; the principle does not change |
| 11 | Assertion check | Generic / adapter | C#/xUnit regex, `VerifyCS` | One analyser per language/test framework |
| 12 | AI reviewer | Generic | — | — |
| 13 | Refusal register | Generic (catalogue) / **overfit (code)** | Two refusals **hard-coded** for 2297 in `passport.py` (user code excluded, netstandard scope) | Refusals produced only by: policy zones, evidence, AI reviewer — with a generic catalogue |
| 14 | Lanes and verdict engine | Generic | — | — |
| 15 | Reading contract | Generic / adapter | Exclusion of `*Template.cs` (T4) | Files derived from a source are read via their source: policy rule |
| 16 | One-click replay | Generic | — | — |
| 17 | Attestation | Generic / **overfit (code)** | "Not verified" list hard-coded for 2297 in `passport.py` | Built from what has no evidence |
| 18 | Trust register per area | Generic | Never exercised (no history) | — |
| 19 | Injected bugs | **Overfit** | 8 bugs written for 2297, knowing the rules | Canary bugs injected continuously, drawn from a library of typical agent defects |
| 20 | Verification of .NET references (E5) | **Overfit** | One-off investigation, not a step | Generic principle: **an agent's claim about the environment is a claim to be proven** |

## What 2283 brings
With the generic steps alone (criteria written from the issue, end-to-end test reproducing the issue, base/branch replay), the chain showed the crash on the base and the fix on the branch, without any rule tailored to this case.

## To fix in the reference code
- Remove the refusals and "not verified" entries hard-coded for 2297 in `passport.py`.
- Replace the snapshot regex rule with "regenerate and compare" (or present it as a declared policy rule, not as a mechanism).
