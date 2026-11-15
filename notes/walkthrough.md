# Live walkthrough — "where trust comes from" (≈ 8 minutes)

Material: `factory/out/REQ-2297.html` open in the browser, `measurements.md` and `concept.md` (concept card) at hand.

## 0. Hook (30 s)
"An agent wrote 237 files for issue #2297. Its 169 tests are green. Its own tests fail before and pass after. Would you sign? — We wouldn't, and with 56 lines read we'll show you why."

## 1. The problem (45 s)
- Agents produce more than humans read; review was already a rubber stamp (Vercel: >50 % of PRs approved without a comment).
- AI reviewers plateau at 50–60 % F1; 80 % of agent tests are weak.
- Those who self-approve (Meta, Vercel) do not say **who answers** when it breaks.

## 2. The concept in one sentence (30 s) — concept card
"We no longer review the code, we check a passport. The AI advises with evidence, it never approves. A named human signs what they checked."

## 3. Demo of passport 2297 (4 min)
1. **Header**: named owner (Camille Durand (synthetic)), lane **Red**, action "do not sign as is". Figures: **11/237 files, 56/1,392 lines**.
2. **Questions before the AI**: the page refuses to show the AI opinion until the questions have been answered → countermeasure against over-trust.
3. **Locked criteria**: AC-1 supported, **AC-2 and AC-3 contradicted** — by evidence, not by an opinion.
4. **Evidence** (where trust comes from):
   - mechanical rule: 220 snapshots proven without being read; 2 flagged → lead back to the orphan change;
   - E2: the agent's tests fail before / pass after (the agent's evidence);
   - **E3**: an independent test → CS0579, a user's code no longer compiles;
   - **E4**: hand-written code in a partial resolver is excluded from coverage;
   - **E5**: the attribute exists in netstandard2.0 and .NET Framework → the agent's premise is wrong.
   - **E8 (E2E sandbox)**: a real user project, two targets → on net8.0 the user's business rule is excluded from coverage; on netstandard2.0 nothing is excluded. "The agent's tests were green; real execution against our criteria is not."
5. **What the AI found**: 4 findings, diff quotes, all confirmed by evidence; CS0579 underestimated (low, 0.4). **What it missed**: the exclusion of user code — it even asserted it was "fine".
6. **What the AI refused to decide**: 4 refusals, with reason and decision-maker — example R1, product decision.
7. **Why Red**: deterministic verdict engine, every reason is readable.
8. **Reading contract**: 13 hunks to tick. Signing impossible while a refusal is unsettled or a hunk unticked.
9. **Attestation**: verified/by whom, not verified/why, decisions, residual risk → signed JSON (show `attestation-REQ-2297.json`: sent back to the agent with E3/E4/E5).

## 4. Measurement (1 min 30) — `measurements.md`
- The 4 branches: 2297 → 4 % of lines to read; 2283/2234/2129 → 100 %: **without claims or evidence, no free trust**.
- AI: precision 4/4, recall 4/5.
- Injected bugs: 7/8 flagged; **S8 missed** (the agent weakens its own new test) — we say so.
- In production: reverts/incidents per lane and per area, random counter-review of 10 % of greens, canaries, circuit breakers.

## 5. Answers to jury questions (30 s, keep ready)
- **What would make you not believe your own result?** A canary in green, a revert linked to a green passport, counter-review agreement < 90 %, signatures faster than the imposed reading time, an AI that never refuses anything.
- **Who owns the decision?** The area's CODEOWNER owner; they merge; the AI has no approval rights.
- **How does it scale?** AI cost bounded per lane; human reading proportional to risk; trust earned area by area; constant 10 % counter-review.

## Video plan (if recorded)
1. Title screen + concept sentence (10 s) · 2. Concept card (30 s) · 3. Screen capture of the passport page, narrated scroll (3 min) · 4. `measurements.md` table (1 min) · 5. Failure modes (`lessons-log.md`, 3 examples: F2, F5, F9) (1 min) · 6. Conclusion "AI reviews, humans stay accountable" (15 s).
