# Interpreting the output

`wuxing_gua` prints **parseable JSON on stdout** for `discover`, `check` and
`check-sample`; progress and diagnostics go to stderr, and exit codes carry the
headline answer (see the table at the bottom). This page explains every field
you are likely to meet, in plain language, with typical values taken from the
committed fixtures and examples. Everything quoted here was produced by
re-running the exact commands from `docs/quickstart.md` and
`examples/README.md`; where a number also has a research record, it is indexed
in `docs/evidence.md`.

Two reading rules before the field lists:

1. **The load-bearing outputs are proof-level**: a zero-tolerance `check`
   verdict, a `check-sample` verdict backed by enough samples, and a
   completeness *certificate*. Statistical or probe-based fields are hints —
   useful, but never converted into a pass by the tool.
2. **Human-readable strings (the `reason` field, selftest and error messages)
   are currently written in Chinese.** The JSON field names, the verdict
   tokens (`pass` / `reject` / `abstain`, `proved_incomplete` /
   `statistical_suspicion` / `no_evidence_of_missing`) and the exit codes are
   language-independent — parse those, not the prose.

## `discover` output

```bash
python -X utf8 -m wuxing_gua discover --trans examples/ticketfsm_milestones_model.json
```

| Field | What it means | Typical values |
|---|---|---|
| `order` | How many permutations the found group contains. Bigger = more symmetry found. | `2` on the 32-state work-order example; `720` on the demo Q6 fixture |
| `trivial` | `true` when the only "symmetry" found is the do-nothing permutation (order 1). With `trivial: true` the command exits 1 — an honest "no usable symmetry here", not an error. | `false` on both examples above |
| `n_orbits` | The states fall into this many indecomposable classes ("orbits") under the group. States in one orbit are interchangeable as far as the group is concerned. | `24` (ticketfsm), `7` (demo Q6) |
| `compression` | A **reading**: `n_states / n_orbits`. It says how many states collapse into one class *on average under this group* — it is not a promised saving. | `1.3333...` (32/24), `9.142857...` (64/7) |
| `generators` | A short list of permutations from which the whole group can be built by composition. Read this to understand *what* the symmetry is. | On ticketfsm: one generator — the swap of the "accepted"/"en-route" milestone bits |
| `elements` | All `order` permutations, each written as a list where position `s` holds the image of state `s`. This list **is** a valid group file: save the JSON and feed it back to `check` as `--group`. | — |
| `orbits` | The orbits themselves, as lists of state numbers. | ticketfsm: 24 orbits, mostly singletons plus swapped pairs |
| `diagnostics` | Search bookkeeping (candidates tried, how many passed the equivariance judge, sentinel spot-check result). Safe to ignore on a first read. | — |
| `note` | An occasional plain-language hint (e.g. that `elements` can be used directly as a group file). | — |
| `n_bits`, `n_states`, `n_actions` | Echo of the input model's shape. | `5, 32, 5` on ticketfsm |

What to do with the result: exit code 0 and `trivial: false` — take the
`elements` and run `check` on them (discover looks only at transitions, never
at rewards; `check` enforces both layers). Exit code 1 — the model has no
non-trivial symmetry that the search could certify; that is a result, not a
failure.

## The `completeness` block (always present on `discover`)

The tool's own audit of *"might this search have missed part of the group?"*.
Real values from the ticketfsm run:

| Field | What it means | The ticketfsm example |
|---|---|---|
| `verdict` | `proved_incomplete` — a probe found a permutation that passes equivariance but is outside the group: incompleteness is **proven**. `probe_exhausted_no_certificate` — all three probe families ran and found nothing outside the group: evidence, not proof. On models where the probe evaluator is out of its domain (non-bit-string action counts), the whole block is instead `{"skipped": true, "reason": ...}` — an honest skip; the judging criteria are unaffected. | `probe_exhausted_no_certificate` |
| `alert` | `true` = incompleteness was proven (at least one certificate). With the shipped constants the heuristic suspicion score is capped below the alarm line, so `alert` fires only via certificates. | `false` |
| `completeness_score` | 0..1: 1.0 = probes found nothing; heuristic suspicion subtracts up to 0.45 (driven by `wl_gap`); a proof forces 0.0. The alarm line is 0.5, reachable only on the proof path. | `0.75` (= 1 − 0.45 × (6.0−1)/(10−1): mild structural suspicion, no alarm) |
| `n_certificates`, `order_after_union` | If a probe *proved* missing elements: how many, and how large the union grew. | `0` and `null` (nothing proven missing) |
| `n_wl_classes`, `wl_gap` | A coarse structural cross-check: how many classes a label-propagation refinement distinguishes vs. the group's orbits. A large gap records a structural observation; on workflow-shaped models it is expected and can be a false lead (see the confidence block below). | `4` classes vs 24 orbits, `wl_gap` 6.0 |
| `action_probe`, `restart_probe`, `affine_probe` | The three probe families (action-permutations, randomized re-searches, affine maps): how many candidates each tried and how many passed the judge. | ticketfsm: 25 restart candidates, 1 passed the judge and produced no certificate (nothing outside the group) |
| `reasons` | Chinese-language one-line explanations of the verdict. | — |

What to do: `alert: false` → the search found no evidence of missing symmetry;
proceed to `check`. `alert: true` or a certificate → re-run `discover` with the
repair flags (`--preset robust`, or `--pad-aware` for padded models — see
`docs/quickstart.md` section on flags) and compare `order`.

## The optional `confidence` block (`discover --report-confidence`)

A read-only diagnostic answering *"how much should I trust that the group is
complete?"* when no certificate exists. It never changes the exit code. It has
three verdict tokens:

| `verdict` | Meaning | What to do |
|---|---|---|
| `proved_incomplete` | A proof: re-running the same model under other configurations/numberings produced a strictly larger group, so the current one misses elements. | Re-run `discover` with the repair flags and take the larger group. Example from the demo's translated fixture: current `order` 6, but a canonized arm reached 720 (`peers_max`), `proof_miss: true`. |
| `statistical_suspicion` | A calibrated *hint* that the group may be incomplete (statistical layer). Can be a **false positive outside the calibration distribution** — the shipped ticketfsm example is exactly that case: full-score suspicion (`wl_gap` 6.0, `w3d_score` 1.0) while an independent brute-force enumeration proves the true group is order 2. | Investigate (add flags, re-check), but do not treat it as a refusal. Such verdicts carry an explicit `ood_hint` (out-of-distribution hint) field. |
| `no_evidence_of_missing` | No proof and no statistical hint. **Not** a proof of completeness. | Proceed; rely on `check` for the load-bearing verdict. |

Other fields: `order_current` and `arm_orders` / `peers_max` (what each
re-check arm reached — the proof layer compares these), `wl_gap` /
`w3d_score` (the statistical layer's raw reading and its 0..1 score; warning
line 0.5, full line 1.0, derived from `wl_gap` against thresholds 1.5 / 2.0),
`thresholds` (printed inside the block), `basis` / `note` (Chinese-language
explanations), `current_kind` (which flag configuration produced the group).

## `check` output

```bash
python -X utf8 -m wuxing_gua check --trans examples/gw_chainrot_model.json --group examples/gw_chainrot_group_h.json
```

| Field | What it means | Typical values |
|---|---|---|
| `verdict` | `pass` — every group element preserves transitions *and* reward profiles exactly; `reject` — at least one certified violation. Zero tolerance: there is no "close enough". | `pass` on both shipped `check` examples |
| `exit_code` | 0 on pass, 1 on reject. | — |
| `reason` | Chinese-language one-liner saying which layer decided. | — |
| `group.order` / `group.n_orbits` / `group.compression` | The verified group's size and its orbit reading (same meaning as in `discover`). | 5 / 128 / 4.0 (512-state example); 25 / 1,024 / 16.0 (16,384-state example) |
| `layer_transition` | Layer 1: does every element permute successors exactly? `n_checked` elements were each verified (`worst_tv` = worst total-variation distance found; must be ≤ `tol` = 1e-9, i.e. numerical zero). Groups above 5,000 elements switch to certified sentinel spot-checks (`mode` shows which). | 5/5 elements, `worst_tv` 0.0; 25/25 elements, `worst_tv` 0.0 |
| `layer_reward_profile` | Layer 2: do states in the same orbit have identical reward profiles? `n_bad` violations out of `n_pair` same-orbit pairs; must be 0. | 0 bad of 960 pairs; 0 bad of 176,640 pairs |
| `group.input_elements` / `unique_elements` / `duplicates_dropped` / `input_was_closed_group` / `elements_added_by_closure` / `generators_found` | How the input group file was normalized: duplicates removed, closure computed. Useful when you hand-wrote a generator list and want to confirm it closed into the group you intended. | 1 generator in, closure added 4 elements (512-state example) |

What to do on `reject`: read which layer failed. A `layer_transition` failure
means the group does not preserve the dynamics at all — it is simply wrong for
this data. A `layer_reward_profile` failure means the group preserves
transitions but changes the system's reward semantics — the failure mode a
transitions-only check would wave through. The demo's second group shows it:
its transition layer passes (worst TV 0.0) while 1,586 of 2,016 same-orbit
reward pairs disagree, and the verdict is `reject`. In both cases the correct
next step is a different (usually smaller) candidate group — the criterion is
never loosened.

## `check-sample` output

Same three-part shape: `verdict` (`pass` / `reject` / `abstain`), `reason`,
plus:

| Field | What it means | Typical values |
|---|---|---|
| `n_samples` | How many trajectories were read. | `10000` → pass; `100` → abstain (demo fixtures) |
| `abstain_note` | Present only on `abstain`: "insufficient samples — nothing else is claimed". The tool never converts silence into a pass. | — |
| `diagnostics` | Per-orbit detail: which orbits were tested, whether each had enough samples to be meaningful (`powered`), and any certified violations. On `abstain` this tells you *which* orbits were under-sampled. | — |
| `goals_source`, `n_goals` | Where the absorbing-state list came from (model file, group file, or none). Providing `--trans` is recommended whenever the model has absorbing states. | `model` on the demo fixtures |
| `group` | Echo of the group file's shape. | — |

What to do on `abstain`: collect more trajectories — the empirically
calibrated working minimum is 10,000 samples. One structural exception: if the
model contains unreachable padding states, their orbits can never be sampled
and `check-sample` will abstain at **any** sample size — use the full-table
`check` instead.

## Exit codes and the one-line "what next"

| Exit | Meaning | Your next move |
|---|---|---|
| 0 | `check`/`check-sample`: criteria pass. `discover`: non-trivial group found. | Use the group — but run `check` on anything `discover` produced. |
| 1 | Refuse: certified violation, illegal group, or (discover) only the trivial group. | Read `reason` / the failing layer; fix the candidate, or accept the honest negative result. |
| 2 | `check-sample` only: insufficient samples. | Get more samples (≥ 10,000), or switch to a full transition table; padded models abstain structurally. |
| 3 | Input or internal error. | Fix the input file (format below); a traceback on stderr means a bug — please report it. |

Input format in one paragraph: a model file is a JSON object with `n_bits`,
`n_actions` (1..n_bits), a `trans` list of `2**n_bits` rows, each row a list of
`n_actions` action-columns, each column a list of `[probability, next-state,
reward]` triples summing to 1, and optionally `goals` (absorbing states).
States are bit-string numbered (`n_states = 2**n_bits`) and action `a` means
"flip bit `a`" — the tool refuses or returns the trivial group on models that
do not fit this convention, it never silently passes them. A group file holds
`elements` (as printed by `discover`). Sample files are JSONL, one
`[s, a, next-state, reward]` array (or the same as an object) per line.

Still stuck? `docs/faq.md` answers the questions that come up most, and
`docs/boundaries.md` has a decision table for choosing a command and a list of
situations where you should not use the tool at all.
