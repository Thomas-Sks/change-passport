# Passport factory — reference implementation

> Illustrates the concept (`../livrable/README.md`). **This is not a product.** Everything runs locally; the only remote is one private demo PR (`pr_flow.py`).

## Contents

| File | Role |
|---|---|
| `review-policy.yaml` | Versioned policy: zones, severity, refusal catalogue, lane rules (v2) |
| `trust.yaml` | Per-zone trust registry |
| `requirements/REQ-*.yaml` | Requirement: **locked** criteria, agent claims, mechanical rule, coverage rule |
| `evidence/<n>.json` | Executed evidence per change (2297: dotnet test, independent acceptance tests, ref inspection; 2283 and 2234: end-to-end reproduction of the issue, base vs branch, plus the agent tests) |
| `acceptance-tests/PassportAcceptanceTests.cs` | Our tests, independent of the agent (E3, E4) |
| `ai/2297-review.json` | AI review (read-only, mandatory quotes, closed grid, refusals) |
| `ai/2297-verification.json` | Each AI finding checked against the evidence; what the AI missed |
| `passport.py` | Partitioning, mechanical rule, traceability, coverage, weakened tests, refusals, **deterministic verdict engine**, reading contract, attestation draft |
| `render.py` | Owner's page (questions before the AI opinion, refusals to settle, reading contract, signature) |
| `seed_bugs.py` | Test bench: 8 bugs injected on local branches |
| `repro-REQ-*.yaml`, `sandbox.yaml`, `scenarios/` | How to replay each piece of evidence (editable scenarios) and where the isolated worktrees are |
| `replay.py` | Replays one piece of evidence on base and branch, side by side |
| `server.py` | Local server (127.0.0.1): passport page + “Replay” button |
| `mutate.py` | “Revert one hunk” mutation testing on the diff's code |
| `catching.py` | Catching tests generated from the criteria, run on base/branch |
| `pipeline.py` | **Live end-to-end chain** on one change: sort → prove (replays) → evidence → blind AI review (`claude -p`, read-only) → verification against proofs → passport. Status in `out/live/<REQ>/status.json` |
| `build_demo.py`, `demo/demo.template.html` | Builds `out/demo.html`, the jury demo page (all passports, recorded replays and measurements embedded); `--record REQ:ID …` re-records replay fallbacks |
| `pr_flow.py` | Puts the passport in a real pull request: posts it as a PR comment, sets `passport/lane` and `passport/owner-signature` commit statuses, and signs (bound to the commit, refused for the wrong signer, a stale commit, unanswered refusals, or a red change accepted without `--full-read`) |
| `out/` | JSON/HTML passports for the 4 branches, live run of REQ-2283 (`*.live.*`, `live/`), recorded replays, signed attestations (`attestation-REQ-2297.json` from the owner page, `signatures/` from the PR flow), seeded-bug, mutation and catching results |

## Run

```bash
python3 passport.py --repo ../upstream-repo --req requirements/REQ-2297.yaml \
  --evidence evidence/2297.json --ai ai/2297-review.json --verif ai/2297-verification.json \
  --tests scenarios/PassportAcceptanceTests.cs scenarios/CatchingTests.cs --catching out/catching-REQ-2297.json --out out
python3 render.py out/REQ-2297.passport.json        # → out/REQ-2297.html
python3 seed_bugs.py --worktree <2297 worktree> --out out
python3 replay.py E3                                 # base / branch replay on the command line
python3 server.py   # then http://127.0.0.1:8765/REQ-2297.html → “Replay” button
python3 mutate.py --req requirements/REQ-2297.yaml --agent-filter "FullyQualifiedName~CodeCoverageExclusionTests" --out out
python3 catching.py --req requirements/REQ-2297.yaml --out out

# live chain and demo page
python3 pipeline.py --req REQ-2283 [--skip-review]     # → out/REQ-2283.live.html
python3 build_demo.py                                  # → out/demo.html
python3 server.py 8765                                 # http://127.0.0.1:8765/ : live replays (POST /replay/REQ/ID) and live pipeline (POST /pipeline/REQ)

# pull-request flow (gh CLI, one private repository)
python3 pr_flow.py publish --repo OWNER/NAME REQ-2297
python3 pr_flow.py sign --repo OWNER/NAME REQ-2297 --by "Camille Durand (synthetic)" --decision send-back \
  --risk "..." --answer R1=accept --answer R2=reject ...
```

Executed evidence: .NET SDK 8.0.402 in an isolated worktree (`dotnet test tests/MessagePack.SourceGenerator.Tests`), then `PassportAcceptanceTests.cs` copied into the test project, on the branch and on base `32258fdb`.
