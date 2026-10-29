# Quickstart

`wuxing_gua` answers one question about a finite state machine whose transition
table (or a sample of trajectories from it) you already have:

> **Can this symmetry group actually be used — and if not, will the tool say so
> instead of waving it through?**

New to the vocabulary? `docs/glossary.md` defines each core term (symmetry
group, orbit, equivariance, ...) in one sentence.

It combines four things that are usually separate concerns:

- a **group finder** operating on black-box transition data (no model internals
  required);
- a **two-layer, zero-tolerance verifier** for a candidate group (transitions
  and reward profiles must both be exactly preserved);
- an **abstention-aware sample-based verifier** that says "insufficient
  samples" rather than guessing;
- **calibrated self-diagnostics** (a completeness probe and a confidence
  report) that can prove a search underreturned, or tell you how much to trust
  it when it cannot.

Every answer is one of: **pass / reject / insufficient samples** — or a group,
accompanied by exit code 0. The tool never loosens a criterion to produce a
pass.

This page walks through installation, a 60-second tour, and each command with
copy-paste-able commands and their real outputs. All commands assume Python
>= 3.10 (no third-party dependencies) and are shown from the repository root.

**In a hurry?** The fastest first value needs no install and no fixtures:

```bash
python -X utf8 -m wuxing_gua discover --trans examples/ticketfsm_milestones_model.json
```

This judges a real 32-state workflow model and prints the found group in
seconds (exit 0, group order 2, 24 orbits). New to symmetry groups? Start one
rung lower: the 8-state starter cube in `examples/README.md` has a symmetry
you can see on a paper diagram — and a companion group that looks legal but
gets refused. What the fields mean, and what to
do next: `docs/interpreting-output.md`. The tour below uses the sandbox
fixtures, so you can also provoke the refusal paths safely.

## 1. Install (optional — every command also runs without it)

Every command in this page runs directly from the repository root with no
install step: `python -X utf8 -m wuxing_gua <command> ...` works because the
package imports its judge modules from the sibling `src/` tree (a deliberate
layout — see the note at the end of this section and the header note in
`pyproject.toml`). Install only if you want the commands available from other
directories. The verified form — installs the package into an arbitrary target
directory and runs the selftest from there:

```bash
python -m pip install . --target <any-directory> --no-build-isolation
cd <any-directory>
python -X utf8 -m wuxing_gua selftest
```

(`--no-build-isolation` builds with the tooling already installed in your
environment instead of fetching a separate build setup — keeps the install
self-contained.)

Expected: `15/15` branches PASS, exit code 0. (Anchors E24/E40 record the
bundle-era install verification, when the selftest had 13 branches; the
selftest has since grown to 15 branches — see `CHANGELOG.md`.) Alternatively, unpack the source bundle
shipped with the release (104 files) and run the same selftest from the unpacked
directory (anchor E39).

Note on layout: the package imports its judge modules from a sibling `src/`
directory by design; install the project as a whole (as above), not the
`wuxing_gua` package alone.

## 2. 60-second tour

The shipped examples are even faster than the sandbox: a teaching ladder that
starts at an 8-state starter cube (a symmetry you can draw on paper, plus a
refusal you can predict) and tops out at three real systems, each judged in
seconds by a single command whose expected output is documented
(`examples/README.md`). Use the demo below when you want to provoke the
refusal paths yourself; the selftest is a trust step you run once — not a
prerequisite for anything that follows.

Generate the demo fixtures (deterministic — re-running produces byte-identical
files; finishes in seconds):

```bash
python -X utf8 -m wuxing_gua demo --out demo_fixtures
```

This writes seven files: two 64-state environment models (a standard one and a
reward-breaking variant), a renumbered copy of the standard one, a true group
(S6, order 720), a symmetry group that preserves transitions but not rewards,
and two trajectory samples (100 and 10,000 lines).

Then run the end-to-end selftest — 15 branches covering every command, flag and
exit path; takes on the order of two minutes (anchor E41):

```bash
python -X utf8 -m wuxing_gua selftest
```

Expected: all 15 branches PASS, exit code 0 (anchor E24 records the bundle-era 13-branch run).

## 3. Find a group: `discover`

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json
```

The JSON printed on stdout is the found group. On the demo environment:

- `"order": 720`, `"n_orbits": 7`, `"compression": 9.142857142857142` (anchor
  E42) — a *reading*: 64 states fall into 7 orbits under the group;
- `"generators"`: a compact generator list whose closure is exactly
  `"elements"`;
- a `"completeness"` block: the tool's own audit of whether the search may have
  *missed* part of the group.

Every field in this JSON is explained in plain language in
`docs/interpreting-output.md` — typical values, and what to do next.

Exit code 0 means a non-trivial group was found; exit code 1 means only the
trivial group (order 1) was found — an honest "no usable symmetry here", not an
error. The stdout JSON can be redirected to a file and fed straight back to
`check` as the `--group` argument.

`discover` looks only at transitions, never at rewards — always follow it with
`check` (section 4), which enforces both layers.

## 4. Verify a group: `check`

```bash
python -X utf8 -m wuxing_gua check --trans demo_fixtures/model_q6.json --group demo_fixtures/group_true_s6.json
```

Expected: `"verdict": "pass"`, exit code 0 (anchor E43). Both layers are
checked with zero tolerance:

- **transition layer** — every group element (up to 5,000, then certified
  spot-checks) must permute successors exactly (max total-variation 0.0,
  tolerance 1e-9);
- **reward layer** — states in the same orbit must have identical reward
  profiles.

The second demo group shows why both layers exist:

```bash
python -X utf8 -m wuxing_gua check --trans demo_fixtures/model_popcount_q6.json --group demo_fixtures/group_xor_z2n.json
```

Expected: `"verdict": "reject"`, exit code 1 — the transition layer *passes*
(worst TV 0.0) while the reward layer reports 1,586 bad of 2,016 orbit pairs
(anchor E44). A group that preserves transitions but breaks rewards is exactly
the failure mode a transitions-only check would wave through.

## 5. Verify from samples: `check-sample`

When you do not have the full transition table, only logged
`(state, action, next-state, reward)` tuples:

```bash
python -X utf8 -m wuxing_gua check-sample --samples demo_fixtures/samples_10000.jsonl --group demo_fixtures/group_true_s6.json --trans demo_fixtures/model_q6.json
# → "verdict": "pass", exit code 0   (anchor E45)
```

```bash
python -X utf8 -m wuxing_gua check-sample --samples demo_fixtures/samples_100.jsonl --group demo_fixtures/group_true_s6.json --trans demo_fixtures/model_q6.json
# → "verdict": "abstain", exit code 2   (anchor E45)
```

Below an empirically calibrated minimum of 10,000 samples (anchor E22), the
tool abstains — it says *only* "insufficient samples" and never converts silence
into a pass. Three verdicts: `pass` / `reject` (certified violation) /
`abstain`.

The same three verdicts are shipped as committed example files with recorded
expected outputs (`examples/README.md`, rung S: an abstain/pass pair on a
4-state host model) — including an honest boundary demo where the sample layer
refuses a full-table-valid group at any sample size, because the model's
rewards belong to the action, not the landing state. To estimate your own
sample budget, read `diagnostics.thresholds.n_req_total` off the abstaining
output rather than guessing.

## 6. The six discover flags

| Flag | What it does | When to reach for it |
|---|---|---|
| `--canonize` | Canonically renumbers the search graph first, removing state-numbering artifacts from the search | Default searches lose parts of the group on unlucky numberings (up to 40.66% full loss across a 91-instance scan, anchor E25); canonize repairs 85.71% of those — but not all environments (anchor E28) |
| `--multi-label K` | Unions the generators found under K independent random renumberings (fixed seed stream, default 20261025) | A numbering-assumption-free repair path; unions only grow |
| `--extra-candidates` | Adds the environment's own action-permutation maps to the candidate pool (when bijective) | Fixes a blind spot where the action structure itself is symmetric but graph search never proposes it (anchor E30/E32) |
| `--pad-aware` | Adds a quotient-graph arm for unreachable "padding" states, with candidates back-filled and judged identically | Models padded up to a power-of-two state count (anchor E12) |
| `--report-confidence` | Appends a read-only `confidence` block: can the search be *proven* incomplete, and if not, how much does the statistics say to trust it | Always available; see the caveat below |
| `--preset robust` | One-flag form of `--canonize --extra-candidates --multi-label 8` | The recommended entry point; the all-three combination reached the true group on 9/9 calibration environments (anchor E29) |

Flags compose freely; the judging criteria are identical on every path and
never loosened by a flag.

**Caveat on `--report-confidence`:** its statistical layer's thresholds were
calibrated on 115 instances drawn from 9 research environments (AUC 1.0,
anchor E20), and it reported a *false* full-score suspicion on a workflow-shaped
state machine outside that distribution (anchor E19). Treat
`statistical_suspicion` as a hint to investigate — certificates (proof level)
and zero-tolerance check verdicts are the load-bearing outputs; the tool prints
this caveat alongside the verdict itself.

## 7. Exit codes

| Code | Meaning |
|---|---|
| 0 | Group found (non-trivial) / both layers pass |
| 1 | Only the trivial group found / certified violation or illegal group input |
| 2 | `check-sample` only: insufficient samples — nothing else is claimed |
| 3 | Input or internal error |

Usage errors also exit 3 (argparse's usual 2 would collide with "insufficient
samples").

## 8. Where to go next

- `examples/` — a six-rung teaching ladder: an 8-state starter cube
  (`tier1_starter_model.json`, symmetry you can draw on paper), a refusal demo
  (`tier1_xor_goalswap_group.json` — looks legal, gets refused), the real
  32-state workflow with a wrong-candidate control pair, a sample-based rung
  (`samples_tiny_*.jsonl` — abstain/pass pair plus a refuse-at-any-size
  boundary), and the 512 / 16,384-state scale rungs, with commands and
  recorded expected outputs;
- `wuxing_gua/README.md` — the input file formats (model / group / samples)
  and the full flag-by-flag reference;
- `docs/glossary.md` — one-sentence definitions of the core terms;
- `docs/interpreting-output.md` — every field of the JSON output in plain
  language, with the values you will actually see;
- `docs/faq.md` — the questions that come up first: input formats, sample
  sizes, what to do after a refusal, when not to use the tool;
- `docs/boundaries.md` — what works at which scale, and the known limits;
- `docs/negative-results.md` — ten findings that will save you the mistakes
  they cost us;
- `docs/evidence.md` — the source of every number in this documentation.
