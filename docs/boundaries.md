# Boundaries: what works, at which scale, and what does not

This page states the tool's operating envelope as measured, not as marketed.
Every number is traceable through `docs/evidence.md`; terms are defined in one
line each in `docs/glossary.md`.

## What the tool decides

`wuxing_gua` decides whether a **symmetry group of a finite state machine can
be used**, judged on black-box transition data (a full transition table, or a
sample of `(state, action, next-state, reward)` trajectories), **before** any
symmetry-based compression is applied, and it can refuse to answer. It is a
gate in front of orbit-based compression — not a compression algorithm itself,
and not a general model auditor.

The judge requires the **bit-string convention**: `n_states = 2**n_bits` and
action `a` = "flip bit `a`". Models that do not fit this convention are not
silently passed — the transition layer rejects them or `discover` only finds
the trivial group (limitation 1 below).

## Verified scale bands

Behavior on the three case-study models (`examples/`), all measured on the
committed files:

| Scale | `check` (full table) | `discover` (automatic search) | `check-sample` |
|---|---|---|---|
| **32 states** (case study 1) | passes/fails in well under a second | finds the order-2 group in seconds, no flags needed | needs >= 10,000 samples (anchor E22) |
| **512 states, 47 padding states** (case study 2) | order-5 group verified, sub-second (anchor E8) | plain/older flag paths crash or stall on this shape; `--pad-aware` finds the order-5 group within a 900 s budget — magnitude of several minutes (anchor E12) | structurally abstains: padding-state orbits are unreachable by construction, so no sample count helps (anchor E11) |
| **16,384 states, 1,969 padding states** (case study 3) | order-25 group verified, 25/25 elements, seconds-scale (anchor E15) | **two hard walls**: the backtracking search exceeds the interpreter's default recursion limit (exit 3), and with the limit raised, no output within 900 s (nor 1,500 s for the full configuration) — see limitation 8 (anchor E18) | not exercised at this scale; the padding-orbit abstention above is expected to apply a fortiori |

Reading of the table: **verification is cheap and scales well** (no search
involved — cost is roughly states x group elements); **automatic discovery is
the expensive part** and currently has a practical ceiling somewhere between
512 and 16,384 states for padded models. Where discovery does not converge,
the intended workflow is: derive candidate groups by hand or by independent
means, then `check` them — the case studies show that workflow working at both
512 and 16,384 states.

Between the case-study points, the completeness and confidence blocks on
`discover` output are the tool's own way of flagging when a search has likely
underreturned; neither converts into a pass.

## A user decision table

The same envelope, restated as "given your system, which command?". What the
output fields mean is covered in `docs/interpreting-output.md`; the most
common practical questions in `docs/faq.md`.

| Your situation | Recommended path | Why |
|---|---|---|
| You have a full transition table **and** a candidate group (hand-derived, from a domain expert, or from another tool) | `check` | No search involved — the load-bearing verdict, cheap at every shipped scale (sub-second at 512 states, seconds at 16,384 states). |
| You have a full table, no candidate, model up to the ~512-state band | `discover`; if `completeness.alert` fires or the result looks thin, re-run with `--preset robust` (add `--pad-aware` if the model has padding states) | The measured convergence band of automatic discovery; the repair flags recover groups the plain search loses on unlucky numberings. |
| Only logged `(s, a, s', r)` trajectories, no full table, and no unreachable states | `check-sample` with ≥ 10,000 samples | The sample-based criterion agreed with the full-table criterion from that budget on (anchor E22); below it you get an honest abstain, not a guess. |
| Model padded to a power of two with unreachable self-loop rows | `check` freely; `discover --pad-aware`; do not use `check-sample` | Padding orbits can never be sampled, so the sample verdict abstains structurally at any sample size (anchor E11); the pad-aware arm is what recovers the group at 512 states (anchor E12). |
| Unsure about the input shape or its state numbering | Start from `--preset robust` | The all-three combination reached the true group on 9/9 calibration environments (anchor E29); single-flag arms use the stricter bit-string judge and may honestly refuse or error on such models. |
| Large model (thousands of states and up), no candidate group | Derive a candidate by hand or by independent means, then `check` it | Discovery hits two recorded walls at 16,384 states — the recursion limit (exit 3), then no output within recorded budgets of 900 s / 1,500 s (anchor E18), nor at 3,600 s (anchor E48) — while verification stays cheap because it involves no search. This is exactly the shipped 16,384-state example's workflow. |

**Do not use this tool — or expect an honest refusal — when:**

- Your system cannot be encoded as `n_states = 2**n_bits` with bit-flip
  actions (continuous state spaces, hidden-state settings, string-keyed states
  you cannot re-encode): out of scope; the tool refuses or returns only the
  trivial group rather than pass silently.
- The symmetry you care about is invisible on the bit-string encoding: the
  judge only sees the visible group (75 → 5 and 375 → 25 in the shipped
  cases, anchors E9, E14).
- You need guaranteed savings or a speedup: compression figures are readings,
  not benefit claims, and the tool does no compression itself.
- You need a mathematical guarantee from the confidence block: its statistics
  are calibrated hints, with a documented false positive on workflow-shaped
  models; only certificates and zero-tolerance verdicts are proof-level.
- You need sample-based verification on a model with unreachable states: it
  abstains structurally, at any sample size, by design (anchor E11).

## Known limitations

1. **Bit-string convention is mandatory.** The judge requires
   `n_states = 2**n_bits` and action `a` = "flip bit `a`". Non-conforming
   models are rejected or yield only the trivial group — never a false pass.
   Consequence: symmetry that is invisible on the bit-string encoding is
   out of scope. The case studies make this concrete: abstract automorphism
   groups of 75 and 375 elements shrink to 5 and 25 on the encoding
   (anchors E9, E14).
   Since 2026-10-29 one more shape exists: models with `n_actions > n_bits`
   (event-driven machines) run `check` under the generalized judge, while
   `discover` refuses them at the entry gate — its candidate search is built
   on the bit-string action convention. Declare the action reading in the
   group file (`semantics`: `relabel` / `fixed`); see
   [judge-semantics.md](judge-semantics.md) and rung 1c in `examples/`.
2. **The trivial group always passes `check`.** `check` answers "is this group
   legal", not "is it useful"; an order-1 group is vacuously legal. Use
   `discover` to find groups, `check` to verify them.
3. **`discover` looks only at transitions, not rewards.** A group it finds can
   still fail `check`'s reward layer. This is by design — discovery and
   verification are deliberately separate — but it means you should always run
   `check` on whatever `discover` outputs.
4. **The 10,000-sample threshold is empirical.** It is the smallest budget at
   which the sample-based criterion agreed with the full-table criterion on the
   calibration scenarios (anchor E22), not a theorem; the detectable-effect
   size is anchored to the calibration environments' single-step randomness and
   must be re-derived for very different environments.
5. **`check-sample` needs `goals` for models with absorbing states** (via
   `--trans` or the group file), otherwise the reward layer can misread
   absorbing self-loops as unstable rewards. It errs toward flagging, not
   passing, but the conclusion would be wrong.
6. **Performance is unoptimized pure Python.** Demo-scale commands are
   seconds-scale; costs grow with states x group elements. Above 5,000 group
   elements the transition layer switches to certified spot-checks rather than
   exhaustive element-wise checking (sound by closure of equivariance).
7. **The package imports judge modules from a sibling `src/` tree at import
   time** and pins the module search path accordingly. Install the whole
   project (as in the quickstart), not the `wuxing_gua` package alone.
8. **Discovery has two walls at large scale.** First, the graph-automorphism
   backtracking recurses once per vertex, so graphs of more than ~1,000
   vertices hit Python's default recursion limit (exit 3; raising the limit in
   the surrounding process is the current workaround, as done for the
   16,384-state case study). Second, past that wall, search cost on padded
   16k-state models exceeded 900-1,500 s budgets without producing output
   (anchor E18). Neither wall is fixed in this release; both are recorded
   honestly as scale-boundary data, and a timeout is never reported as a
   result.
9. **Padding states make sample-based verification structurally abstain.**
   Unreachable padding states form orbits that can never be sampled; the tool
   correctly abstains forever rather than ignoring them silently. A
   reachable-states-only judge is a design option not implemented in this
   release (anchor E11).
10. **The confidence statistics are calibrated, not universal.** Thresholds
    were calibrated on 115 instances from 9 research environments (AUC 1.0,
    anchor E20) and produced a false full-score suspicion on a workflow-shaped
    state machine outside that distribution (anchor E19). The tool prints an
    explicit out-of-distribution caveat with such verdicts; treat them as
    hints, and treat proof-level outputs (certificates, zero-tolerance
    verdicts) as the authoritative ones.
11. **No third-party reproduction yet.** Every number here comes from the
    authors' own runs, recorded in machine-readable JSON with preregistration
    and provenance metadata, and re-verified by an internal consistency audit;
    but no external party has independently reproduced the results yet.
    `docs/evidence.md` publishes the source of every claim so that this can
    change.
12. **Single-machine timings.** All duration statements are magnitudes from
    runs on one reference machine; the JSON records hold exact values where
    they matter.

## What this tool is not

- **Not a compressor.** Compression ratios quoted anywhere in this repository
  (1.33x, 4.0x, 16.0x) are readings of `n_states / n_orbits` under a given
  group — descriptions of structure, not promised savings.
- **Not a replacement for domain review.** A passing `check` says a group
  exactly preserves this transition data's two layers. Whether the implied
  abstraction is *appropriate* for your use remains a human decision.
- **Not production-hardened.** The tool has been exercised on research
  environments and on three extracted case-study models; see limitation 11.
