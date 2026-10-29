# FAQ

Practical answers to the questions that come up when you first point
`wuxing_gua` at your own system. Every number is the same one documented in
`docs/evidence.md`; for field-by-field output help see
`docs/interpreting-output.md`, and for the "should I use this at all" decision
table see `docs/boundaries.md`.

## 1. My system is not a bit-string state machine — can I still use this?

The judging core requires the bit-string convention: `n_states = 2**n_bits`
states, numbered `0..2**n_bits - 1`, and action `a` means "flip bit `a`". If
your system has, say, 100 named states and string actions, you have two
options: re-encode it onto a power-of-two state count with bit-flip actions
(this is exactly what the shipped examples do — a 32-state workflow encoded as
5 milestone bits, and game engines padded with unreachable self-loop "padding"
states up to 512 / 16,384), or accept that the tool is not applicable. It will
never silently pass a non-conforming model: the transition layer rejects it,
or `discover` returns only the trivial group. One caveat when re-encoding:
symmetry that is invisible on the bit-string encoding is out of scope — in the
shipped cases the abstract symmetry groups had 75 and 375 elements, of which
only 5 and 25 are visible on the encoding.

## 2. What input formats does the tool accept?

Three file kinds (see `docs/interpreting-output.md` for a full paragraph):

- **Model** (JSON): `n_bits`, `n_actions`, a `trans` table with one row per
  state and one column per action, each cell a list of
  `[probability, next-state, reward]` triples summing to 1, and optionally
  `goals` (absorbing states). This is the full-transition-table input for
  `discover` and `check`.
- **Group** (JSON): `elements` — the list of permutations; the exact format
  `discover` prints, so its stdout can be saved and fed straight back.
- **Samples** (JSONL): one `[state, action, next-state, reward]` array (or an
  object with those four keys) per line, for `check-sample`.

## 3. How many samples do I need for `check-sample`?

10,000 trajectories is the empirically calibrated minimum: below it the tool
returns `abstain` (exit 2) — "insufficient samples", nothing else. The
threshold comes from calibration scenarios where the sample-based criterion
first agreed with the full-table criterion; it is not a theorem, and for very
different environments you should re-derive it. Structural exception: if the
model has unreachable padding states, their orbits can never be sampled and
`check-sample` abstains at any sample size — use the full-table `check`
instead.

## 4. `discover` exited 1 — is that an error?

No. Exit 1 from `discover` means it could only certify the trivial group
(order 1, the do-nothing permutation): an honest "no usable symmetry found",
not a failure. Verify your input is what you intended, optionally retry with
the repair flags (`--preset robust` is the recommended entry point; add
`--pad-aware` for padded models), and if it still returns trivial, that is a
result worth having — it says the search could not certify any non-trivial
symmetry on this data.

## 5. `check` said `reject` — what is my next step?

Read which layer failed in the output. A `layer_transition` failure means the
candidate group does not preserve the dynamics — it is simply wrong for this
data. A `layer_reward_profile` failure means the group preserves transitions
but changes reward semantics (states lumped together that earn different
rewards) — the failure mode a transitions-only check would wave through; the
demo's second group reproduces exactly this (transition layer passes, reward
layer reports 1,586 bad of 2,016 same-orbit pairs). In both cases the criterion
will not be loosened: derive a different — usually smaller — candidate and
check that, or accept the refusal as the answer.

## 6. The confidence block says `statistical_suspicion` — is my group wrong?

Not necessarily — treat it as a hint to investigate, never as a verdict. The
statistical layer's thresholds were calibrated on research-shaped environments
and are not a mathematical guarantee; the shipped ticketfsm example is a documented
false positive: the block reports full-score suspicion (`wl_gap` 6.0,
`w3d_score` 1.0) while an independent brute-force enumeration proves the true
group has order 2 and the found group is complete. That is why such verdicts
carry an explicit out-of-distribution hint field, and why the block is
read-only — it never changes the exit code. The load-bearing outputs are the
zero-tolerance `check` verdict and completeness certificates; only
`proved_incomplete` from the confidence block is a proof (it names a strictly
larger group found by re-running the same model under other configurations).

## 7. Will this speed up my training / planning?

No — and that is stated up front rather than implied. `wuxing_gua` is not a
compression algorithm and not a fast solver; it is an admission gate that runs
*before* you invest in symmetry-based reduction, answering "is this group safe
to use on this data". The compression numbers it prints (for example 1.333x,
4.0x, 16.0x) are readings of `n_states / n_orbits` — descriptions of
structure, not promised savings. If your goal is wall-clock speedup from
symmetry, this tool tells you whether the symmetry you are about to exploit is
real; the exploitation itself is your pipeline's job.

## 8. My model has unreachable "padding" states — what should I expect?

Nothing silently goes wrong; three concrete behaviors: `check` is unaffected
(padding rows are judged like any other row); `discover` needs `--pad-aware`
— plain search paths miss cross-padding symmetry elements on such models,
while the pad-aware arm recovered the true order-5 group on the 512-state
shipped example; and `check-sample` will abstain **structurally** — padding
orbits cannot be sampled, so no sample count helps.

## 9. `discover` is taking forever on my large model — what do I do?

Check the measured scale bands first (`docs/boundaries.md`): automatic
discovery's verified band is around 512-state padded models (minutes with
`--pad-aware`); at 16,384 states it hits two recorded walls — the backtracking
search exceeds Python's default recursion limit (exit 3), and with the limit
raised it produced no output within recorded budgets up to 3,600 s, ending in
a clean timeout. A timeout is never reported as a result. The intended workflow
above that band is the one the shipped 16,384-state example itself uses: derive
a candidate group by hand or by independent means, then `check` it —
verification is cheap (seconds at 16,384 states) precisely because there is no
search.

## 10. Why are some messages in Chinese, and is that a problem for scripting?

The tool's authors worked in Chinese, and the human-readable strings (the
`reason` field, selftest progress, error messages) are still in that language.
For scripting this does not matter: stdout is parseable JSON with stable
English field names and verdict tokens (`pass` / `reject` / `abstain`,
`proved_incomplete` / `statistical_suspicion` / `no_evidence_of_missing`), and
the exit codes (0 pass / 1 refuse / 2 insufficient samples / 3 error) are the
contract — branch on those, never on scraping prose. The JSON structure is
exactly what `docs/interpreting-output.md` documents.
