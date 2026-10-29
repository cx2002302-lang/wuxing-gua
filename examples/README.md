# Examples

Six worked examples arranged as a ladder. The bottom two rungs are minimal
teaching models you can draw on paper; the top three are finite-state-machine
transition models hand-transcribed from the source code of existing software
systems (with every transcription rule checked against the cited source lines
at extraction time); rung S in between adds sampled trajectory logs — the
input shape the sample-based verifier `check-sample` is built for — on a
4-state host you can also draw on paper. All six are analyzed with the
`wuxing_gua` CLI.

These are static models. Nothing in this repository is a claim about live
production behavior of those systems; what the examples demonstrate is how
the tool behaves on state machines of this shape and scale.

All expected outputs below were produced by running the exact commands shown
against the exact files in this directory. Group-theory terms used below
(symmetry group, orbit, order, generator) are defined in one line each in
`docs/glossary.md`; every field of the JSON output is explained in plain
language in `docs/interpreting-output.md`.

## The ladder

| Rung | Files | States | What it teaches | Exit code |
|---|---|---|---|---|
| 0 — starter | `tier1_starter_model.json` + `tier1_starter_group.json` | 8 | see a symmetry on paper; `discover` finds it, `check` blesses it | 0, 0 |
| R — refusal | `tier1_xor_goalswap_group.json` on the same model | 8 | a candidate that looks legal; read the certified refusal | 1 |
| 1 | `ticketfsm_milestones_model.json` | 32 | `discover` **finding** a group by itself on the smallest real system | 0 |
| S — sampling | `sampling_tiny_model.json` + `sampling_tiny_group.json` + `samples_tiny_*.jsonl` (+ ticketfsm boundary demo) | 4 host (+ 32) | when all you have are logs: abstain below the power requirement, pass at the calibrated budget — and the boundary where the sample layer must refuse at any size | 2, 0, 1 |
| 2 | `gw_chainrot_model.json` + `gw_chainrot_group_h.json` | 512 | `check` carrying the load once a hand-derived candidate exists | 0 |
| 3 | `gw_teambattle_model.json` + `gw_teambattle_group_h.json` | 16,384 | `check` at the scale ceiling where discovery hands over | 0 |

Start at rung 0 if you have never seen a symmetry group before; start at
rung 1 if you only want the tool on a real system. Rung S is for when all you
have are logged `(state, action, next-state, reward)` tuples instead of the
full table. Rungs R, 2 and 3 show
**verification** carrying the load once a candidate group exists — R also
shows what a refusal looks like and how to read it.

## Requirements

- Python >= 3.10 (developed on 3.12), **no third-party dependencies**.
- The `wuxing_gua` package importable, e.g. after `python -m pip install .`
  from the repository root, or by unpacking the source bundle onto `PYTHONPATH`.
- Commands are shown relative to the repository root.

---

## Rung 0 — the starter cube (8 states): see the symmetry first

`tier1_starter_model.json` is a hand-constructed teaching model — generated,
deterministically and byte-identically, by `make_tier1_samples.py` in this
directory (`python -X utf8 examples/make_tier1_samples.py --check` re-verifies
the byte identity). It is *not* transcribed from a real system; its whole
point is that you can hold it in your head:

- 8 states = the 8 corners of a cube, numbered as 3-bit strings;
- 3 actions, action `a` = "flip bit `a`" (deterministic, p = 1.0);
- the corner `111` (state 7) is the goal: absorbing — every action self-loops,
  reward 0;
- reward: +1 for a move up the cube (popcount +1), −1 for a move down.

```
     5(101)──────────7(111) goal: absorbing
    /│              /│
   4(100)──────────6(110)
   │ │             │ │
   │ 1(001)────────│─3(011)
   │/              │/
   0(000) start────2(010)
```

**Step 1 — see the symmetry on paper.** Hold the cube by its long diagonal —
the line through the start corner `000` and the goal corner `111`. You can
spin the cube around that diagonal in 6 ways (all 3! = 6 permutations of the
three axes) and every arrow lands on an arrow, with up still paying +1 and
down −1. Those spins are the symmetry group. The corners it cycles among
themselves are the four shells around that diagonal — 4 orbits:

| Orbit | Corners | Size |
|---|---|---|
| 3 moves from start | `111` (the goal) | 1 |
| 2 moves | `011`, `101`, `110` | 3 |
| 1 move | `001`, `010`, `100` | 3 |
| 0 moves | `000` (the start) | 1 |

Before running anything, that is already a prediction: group order 6, four
orbits, and 8 states collapsing onto 4 orbit representatives — a compression
reading of 8 / 4 = 2.0.

**Step 2 — run the tool.**

```bash
python -X utf8 -m wuxing_gua discover --trans examples/tier1_starter_model.json
python -X utf8 -m wuxing_gua check --trans examples/tier1_starter_model.json --group examples/tier1_starter_group.json
```

The committed `tier1_starter_group.json` is discover's own stdout saved
verbatim — a discover output JSON is itself a valid group file. Re-running
discover reproduces it exactly, except wall-clock timing fields (which drift
by design and are not part of the answer).

**Step 3 — read the output against the record.** Open
`examples/expected/tier1_starter_expected.json` — recorded from a real run of
the two commands above — and tick it line by line:

- `discover`: exit code **0** — `"order": 6`, `"n_orbits": 4`,
  `"compression": 2.0`, `"trivial": false`. The two `"generators"` are read as
  "position s holds the image of state s": `[0,4,1,5,2,6,3,7]` maps corner
  `001` to `100` (it swaps the bit-0 and bit-2 axes) and `[0,1,4,5,2,3,6,7]`
  swaps the bit-1/bit-2 axes — the two visible axis swaps; composing them
  gives all 6 elements. `"orbits"` is exactly the four shells from Step 1.
  `completeness.verdict` is `probe_exhausted_no_certificate` with
  `alert: false` — the tool's own audit found no evidence of missed symmetry.
- `check`: exit code **0** — `"verdict": "pass"`;
  `layer_transition`: 6/6 elements checked, `worst_tv` 0.0 (zero tolerance:
  every element permutes every successor exactly);
  `layer_reward_profile`: `n_bad` 0 of `n_pair` 6 (states in the same shell
  have identical reward profiles — the +1/−1 rule is shell-symmetric).

The tool found, on its own, exactly the group you saw on paper — and refused
to claim anything bigger.

## Rung R — a refusal you can predict: guess first

`tier1_xor_goalswap_group.json` is a 2-element candidate group for the same
starter model. Its non-identity element is XOR-by-001: pair every corner with
its neighbour along the depth axis of the cube above — in particular it
**swaps the goal corner `111` with `110`**. Both elements are honest
permutations, and on the arrow diagram it maps arrows to arrows (it is a
symmetry of the bare cube graph) — nothing about the file is malformed.

**Guess first: does it preserve the machine?** Then run:

```bash
python -X utf8 -m wuxing_gua check --trans examples/tier1_starter_model.json --group examples/tier1_xor_goalswap_group.json
echo $?
```

**The answer: no — and the tool certifies it twice.** Exit code **1**,
`"verdict": "reject"` — both layers fail, each for its own reason (compare
`examples/expected/tier1_xor_goalswap_expected.json`, recorded from a real
run):

- `layer_transition`: 1 of 2 elements fails, `worst_tv` 1.0, `first_bad`
  points at the non-identity element. Where it breaks: `111` is absorbing —
  three self-loop arrows, reward 0. After the swap, its images must look like
  `110`'s behavior, but `110` has three *outgoing* arrows (one of them into
  the goal, paying +1). An absorbing corner swapped with a non-absorbing one
  cannot preserve a transition distribution.
- `layer_reward_profile`: **4 bad of 4 pairs**. Under this group the orbits
  are the four depth-axis pairs `{0,1} {2,3} {4,5} {6,7}`, and every pair
  mixes different reward profiles — e.g. `000` sees three +1 exits while its
  partner `001` sees one −1 and two +1. The `hand_check` block in the
  expected file shows the arithmetic for two of the pairs; the other two are
  four lines each — check them yourself.

This is the tool's contract in miniature: a candidate that looks right on
the diagram is certified wrong in two independent ways; the criterion is
never loosened to admit it; the exit code says so. What each violation field
means, and what to do next, is in `docs/interpreting-output.md` (the
`check` section's "What to do on `reject`"). Further refusal shapes — a
transitions-only group that breaks rewards, and the sample-based abstain —
are one command away in the demo sandbox (`docs/quickstart.md`).

## The three real case studies

Positioned to be non-overlapping with the teaching rungs: 1 shows the tool
**finding** a group by itself on the smallest real system; 2 and 3 show
**verification** carrying the load once a candidate group exists — 2 in the
padding-repair band, 3 at the scale ceiling where discovery hands over to
hand-derived candidates.

## The three models

| # | Model | States (real + padding) | Actions | Command used |
|---|---|---|---|---|
| 1 | `ticketfsm_milestones_model.json` | 32 | 5 | `discover` |
| 2 | `gw_chainrot_model.json` + `gw_chainrot_group_h.json` | 512 (465 + 47) | 7 | `check` |
| 3 | `gw_teambattle_model.json` + `gw_teambattle_group_h.json` | 16,384 (14,415 + 1,969) | 11 | `check` |

The padding states in models 2 and 3 exist because the tool's input contract is
bit-string shaped (`n_states = 2**n_bits`); states that the original system
cannot reach are transcribed as self-loop rows with zero reward. See
`docs/boundaries.md` for what this implies.

## 1. Work-order milestone state machine (32 states)

A ticket-fulfillment workflow encoded as five milestone bits (dispatched /
accepted / en-route / completed / closed), with per-action preconditions
transcribed from the guard clauses of the original code. One command finds the
symmetry group automatically:

```bash
python -X utf8 -m wuxing_gua discover --trans examples/ticketfsm_milestones_model.json
```

**What you'll see:** a JSON with `"order": 2`, `"n_orbits": 24`,
`"trivial": false`, exit code 0.

**What it means:** the search certified exactly one non-trivial symmetry (the
accepted/en-route bit swap) and nothing beyond it — on this workflow, that is
the informative answer, not a weak one.

Expected output (JSON on stdout):

- `"order": 2`, `"n_orbits": 24`, `"compression": 1.3333333333333333`
- `"generators"`: a single generator — the exchange of the "accepted" and
  "en-route" milestone bits (states 2<->4, 3<->5, 10<->12, ...); the other three
  bits are fixed points of the symmetry
- `"completeness": {"verdict": "probe_exhausted_no_certificate", "alert": false, ...}`
- `"trivial": false`

Exit code: **0** (a non-trivial group was found).

The order-2 result matches an independent brute-force enumeration over the
permutations of the 32-state model, which also fixes the true automorphism group
at exactly 2 — the guard structure of the workflow admits this one non-trivial
symmetry and nothing else (`docs/evidence.md`, anchors E4, E5).

Note the reading vs. benefit distinction: 32 states reduce to 24 orbits
(1.33x). For a workflow of this shape the informative output is the *small*
group itself — the tool certifies that no larger exploitable symmetry exists.

### The control pair: the found group vs. a tempting wrong one

Save discover's stdout — it is already a valid group file, committed here as
`ticketfsm_group_found.json` — and judge it against the full table. Then judge a
candidate that looks every bit as legal
(`ticketfsm_wrong_swap_group.json`: the swap of the *dispatched/accepted* bits,
the neighbouring pair next to the found accepted/en-route symmetry):

```bash
python -X utf8 -m wuxing_gua check --trans examples/ticketfsm_milestones_model.json --group examples/ticketfsm_group_found.json
```

**What you'll see:** `"verdict": "pass"`, 2/2 elements at `"worst_tv": 0.0`,
0 bad of 8 reward pairs, exit code 0.

**What it means:** the discovered group preserves the workflow's behavior
exactly — both layers, zero tolerance
(`expected/ticketfsm_check_found_expected.json`).

```bash
python -X utf8 -m wuxing_gua check --trans examples/ticketfsm_milestones_model.json --group examples/ticketfsm_wrong_swap_group.json
```

**What you'll see:** `"verdict": "reject"`, exit code **1** — 1 of 2 elements
fails the transition layer outright (`"worst_tv": 1.0`) and 7 of 8 reward
pairs break.

**What it means:** the guard order of a real workflow (accepted requires
dispatched) is not symmetric under the neighbour swap — the tool certifies
the violation on both layers instead of waving the plausible-looking
candidate through (`expected/ticketfsm_wrong_swap_expected.json`).

## Rung S — when all you have are logs: `check-sample` (4-state host)

The rungs above judge a full transition table. Often all you have is a log of
`(state, action, next-state, reward)` tuples — exactly the input shape
`check-sample` is built for. The host here is `sampling_tiny_model.json`, a
4-state two-switch machine (construction in its meta, hand table below):
its rewards belong to the state you land on (+1 landing on the goal, −0.02
otherwise) — the one premise the sample-based reward layer needs. The
committed `sampling_tiny_group.json` is discover's stdout on the host model
saved verbatim; the visible symmetry is the swap of the two switches
(states 1<->2), order 2, three orbits.

```
state 00 --act0--> 01 (r -0.02)      state 11 is the goal: absorbing,
state 00 --act1--> 10 (r -0.02)      every action self-loops, r 0
state 01 --act0--> 00 (r -0.02)
state 01 --act1--> 11 (r +1.0)       the two switches mirror each other:
state 10 --act0--> 11 (r +1.0)       swapping them maps 01<->10 and
state 10 --act1--> 00 (r -0.02)      leaves 00 and 11 in place
```

The committed trajectory files are generated by `make_samples.py` in this
directory (uniform random policy, seed 20261028 — byte-identical on every
regeneration, and the 100-line file is the prefix of the 10,000-line file):

```bash
python -X utf8 examples/make_samples.py --check
```

**Too few samples first — the tool is allowed to say it does not know:**

```bash
python -X utf8 -m wuxing_gua check-sample --samples examples/samples_tiny_100.jsonl --group examples/sampling_tiny_group.json --trans examples/sampling_tiny_model.json
```

**What you'll see:** `"verdict": "abstain"`, exit code **2** — the reason
names the under-powered orbit, and `diagnostics.thresholds.n_req_total`
reports how many samples the criterion wants (≈ 376 here).

**What it means:** below the power requirement the tool says *only*
"insufficient samples" and draws no other conclusion — observed silence is
never converted into a pass
(`expected/sampling_tiny_100_expected.json`).

**At the calibrated budget — 10,000 samples:**

```bash
python -X utf8 -m wuxing_gua check-sample --samples examples/samples_tiny_10000.jsonl --group examples/sampling_tiny_group.json --trans examples/sampling_tiny_model.json
```

**What you'll see:** `"verdict": "pass"`, exit code **0** — no alarm on
either layer, and the one checkable orbit's power requirement is met.

**What it means:** with enough of the right kind of evidence, the sample
verdict admits the group
(`expected/sampling_tiny_10000_expected.json`) — and the full table says
the same thing:

```bash
python -X utf8 -m wuxing_gua check --trans examples/sampling_tiny_model.json --group examples/sampling_tiny_group.json
```

**What you'll see:** `"verdict": "pass"`, 2/2 elements at `"worst_tv": 0.0`,
0 bad of 1 reward pair, exit code 0
(`expected/sampling_tiny_fulltable_expected.json`).

**What it means:** the log-only path and the full-table path agree on this
model — the admission rests on two independent evidence shapes, not on the
sampled one alone.

**How many samples do *you* need?** Don't guess and don't trust a rule of
thumb: run the command until it stops abstaining and read the requirement off
the output — `diagnostics.thresholds.n_req_total` is the criterion's own
demand for *this* model and sample shape (≈ 376 here; 10,000 is the
empirically calibrated global minimum budget — `docs/faq.md`, question 3).
Two structural exceptions: on models with unreachable padding states the
sample verdict abstains at any sample size (their orbits cannot be sampled —
`docs/boundaries.md`); and on models whose rewards belong to the *action*
rather than the landing state, the sample layer refuses at any sample size —
which is the next command.

**Boundary demo — a valid group the sample layer must refuse:** the ticketfsm
workflow from rung 1, sampled. Generate 50,000 logged trajectories from the
committed model (that is exactly what the committed
`samples_ticketfsm_50000.jsonl` is) and judge the *same, full-table-valid* group:

```bash
python -X utf8 -m wuxing_gua check-sample --samples examples/samples_ticketfsm_50000.jsonl --group examples/ticketfsm_group_found.json --trans examples/ticketfsm_milestones_model.json
```

**What you'll see:** `"verdict": "reject"`, exit code **1** — the reward
layer reports rewards that are not constant on successor orbits (11 of 24
orbit canons bad at this sample size).

**What it means:** ticketfsm's rewards belong to the (state, action) pair (+1 for
a legal advance, −1 for an illegal attempt), not to the landing state, so the
sample layer's cheap reward check — *rewards constant on a successor orbit* —
fires even though the group is valid on the full table (the control pair in
rung 1 passes it). The refusal is honest conservatism, not a verdict about
the group: when your rewards are action-shaped, judge with the full table and
treat the sample interface as built for landing-state-reward logs. Recorded
with the full explanation in
`expected/sampling_ticketfsm_boundary_expected.json`.

One honest footnote on seeds: the committed trajectories use seed 20261028.
`check-sample` is a statistical test at familywise α = 0.05 — regenerating
with a different seed can flip the 10,000-sample run to `reject` (that is the
test's designed error budget, not a malfunction); the full-table verdict is
the load-bearing one.

## 2. Card-engine chain x rotation subsystem (512 states)

The deterministic core math of a card-game engine (a "generation chain"
multiplied by a rotation-field schedule), transcribed onto 9 bits: 465 reachable
states plus 47 padding states, 7 actions. The candidate group here was derived
by hand from the engine rules and is verified, not discovered:

```bash
python -X utf8 -m wuxing_gua check --trans examples/gw_chainrot_model.json --group examples/gw_chainrot_group_h.json
```

**What you'll see:** `"verdict": "pass"`, 5/5 elements at `"worst_tv": 0.0`,
0 bad of 960 reward pairs, exit code 0.

**What it means:** the hand-derived order-5 group preserves this system's
behavior exactly — it is safe to build on (the 4.0x figure describes the
structure; it is not a promised saving).

Expected output (JSON on stdout):

- `"verdict": "pass"`, `"exit_code": 0`
- `"layer_transition"`: 5/5 group elements checked, `"worst_tv": 0.0`
  (tolerance 1e-9), `"passed": true`
- `"layer_reward_profile"`: `"n_bad": 0` out of 960 orbit pairs, `"passed": true`
- `"group"`: `{"order": 5, "n_orbits": 128, "compression": 4.0, ...}`

Exit code: **0** (both zero-tolerance layers pass). Runtime: well under a
second.

For contrast, the abstract system has a 75-element automorphism group, but only
5 of those elements are realizable on the bit-string encoding — an encoding
geometry fact, not a tool failure (`docs/evidence.md`, anchors E8, E9). The
automatic searcher finds the same order-5 group at this size when given the
`--pad-aware` flag (`docs/evidence.md`, anchor E12).

## 3. Two-team extension (16,384 states)

The same rule family extended to two teams with independent generation chains
and a shared rotation field: 31 x 31 x 15 = 14,415 natural states on 14 bits
(plus 1,969 padding states), 11 actions. The hand-derived candidate group is
the direct product of two 5-element cyclic groups, C5 x C5 (25 elements):

```bash
python -X utf8 -m wuxing_gua check --trans examples/gw_teambattle_model.json --group examples/gw_teambattle_group_h.json
```

**What you'll see:** `"verdict": "pass"`, 25/25 elements at `"worst_tv": 0.0`,
0 bad of 176,640 reward pairs, exit code 0.

**What it means:** the same guarantee holds at 16,384 states — verification
stays cheap at this scale; it is automatic discovery, not verification, that
hits the budget wall here (see `docs/boundaries.md`).

Expected output (JSON on stdout):

- `"verdict": "pass"`, `"exit_code": 0`
- `"layer_transition"`: 25/25 group elements checked, `"worst_tv": 0.0`,
  `"passed": true`
- `"layer_reward_profile"`: `"n_bad": 0` out of 176,640 orbit pairs,
  `"passed": true`
- `"group"`: `{"order": 25, "n_orbits": 1024, "compression": 16.0, ...}`

Exit code: **0**. Runtime: seconds-scale on a laptop-class machine (this is the
full transition table, all 25 elements checked element-wise — no sampling).

The 16.0x figure is a reading of `n_states / n_orbits` under this particular
group, not a promised saving. The abstract system's automorphism group contains
375 elements; only 25 survive the encoding — and a 125-element candidate that
additionally moves the rotation-field component is rejected with exit code 1
(100 of its 125 elements violate the transition layer), showing the criterion
is strict about which parts of an abstract symmetry are real on the bit-string
encoding (`docs/evidence.md`, anchors E14, E15, E16).

---

## File sizes

| File | Size |
|---|---|
| `tier1_starter_model.json` | 1.9 KB |
| `tier1_starter_group.json` | 2.4 KB |
| `tier1_xor_goalswap_group.json` | 0.5 KB |
| `make_tier1_samples.py` | 6.3 KB |
| `sampling_tiny_model.json` | 2.1 KB |
| `sampling_tiny_group.json` | 1.9 KB |
| `make_samples.py` | 5.2 KB |
| `samples_tiny_10000.jsonl` | 160.0 KB |
| `samples_tiny_100.jsonl` | 1.6 KB |
| `samples_ticketfsm_50000.jsonl` | 855.3 KB |
| `ticketfsm_group_found.json` | 3.2 KB |
| `ticketfsm_wrong_swap_group.json` | 1.3 KB |
| `expected/tier1_starter_expected.json` | 1.7 KB |
| `expected/tier1_xor_goalswap_expected.json` | 1.6 KB |
| `expected/ticketfsm_check_found_expected.json` | 0.9 KB |
| `expected/ticketfsm_wrong_swap_expected.json` | 1.1 KB |
| `expected/sampling_tiny_fulltable_expected.json` | 1.0 KB |
| `expected/sampling_tiny_100_expected.json` | 1.0 KB |
| `expected/sampling_tiny_10000_expected.json` | 1.0 KB |
| `expected/sampling_ticketfsm_boundary_expected.json` | 1.6 KB |
| `ticketfsm_milestones_model.json` | 9.1 KB |
| `gw_chainrot_model.json` | 190.5 KB |
| `gw_chainrot_group_h.json` | 4.8 KB |
| `gw_teambattle_model.json` | 9.8 MB |
| `gw_teambattle_group_h.json` | 4.2 MB |

Sizes are of the files in this directory as committed (KB = 1000 bytes,
re-measured 2026-10-28 when the teaching rungs were added). The two large
files are committed as-is; both are far below the 50 MB level at which GitHub
begins warning about individual files.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | `discover`: non-trivial group found; `check` / `check-sample`: both layers pass |
| 1 | `discover`: only the trivial group found; `check` / `check-sample`: reject (certified violation or illegal group) |
| 2 | `check-sample` only: abstain — insufficient samples, no other conclusion is drawn |
| 3 | Input or internal error (missing file, malformed JSON, format violation) |

## Where the numbers come from

Every numeric claim about the three real case studies is indexed to a
machine-readable result file in `docs/evidence.md`. The teaching rungs and
the sampling rung carry their machine-readable record directly in
`examples/expected/` (`tier1_starter_expected.json`,
`tier1_xor_goalswap_expected.json`, `ticketfsm_check_found_expected.json`,
`ticketfsm_wrong_swap_expected.json`, `sampling_tiny_fulltable_expected.json`,
`sampling_tiny_100_expected.json`, `sampling_tiny_10000_expected.json`,
`sampling_ticketfsm_boundary_expected.json`; recorded from the real runs of
2026-10-28). All commands in this file are
deterministic and their inputs are the committed files themselves, so every
output is trivially re-runnable by anyone; the committed teaching model and
group files are byte-identical to the generator's output
(`make_tier1_samples.py --check`), and the committed trajectory files are
byte-identical to a regeneration from the committed model files
(`make_samples.py --check`; the sample-based verdicts at α = 0.05 are the one
deliberately statistical exception — see the seed footnote in rung S).

The transcription of model 2 was additionally replayed against the original
engine for 120,000 steps with zero disagreements between the transcription and
the engine's actual behavior (`docs/evidence.md`, anchor E10).
