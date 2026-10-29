# Glossary

One-sentence definitions of the core terms used across this repository, each
with one example. This page defines vocabulary only — it adds no new claims,
and every number below is the same one documented elsewhere, traceable through
[docs/evidence.md](evidence.md).

## Symmetry group

A set of rearrangements ("permutations") of a system's states that provably
leaves the system's behavior unchanged: relabel the states by any member of
the set, and every transition and every reward stays exactly the same.

- Example: in the 32-state work-order model, swapping the "accepted" and
  "en-route" milestone bits (states 2<->4, 3<->5, 10<->12, ...) preserves all
  behavior — that swap is the model's one non-trivial symmetry (anchor E5).

## Orbit

A maximal set of states that the group's permutations carry into each other;
same-orbit states are behaviorally interchangeable as far as the group is
concerned.

- Example: under the demo environment's true group S6 (order 720), the 64
  states fall into 7 orbits (anchor E42).

## Orbit-based compression

Rewriting the system over orbits instead of single states: because same-orbit
states behave identically, each orbit can be represented once, shrinking the
state space from n_states to n_orbits.

- Example: 16,384 states cover 1,024 orbits under the order-25 group — the
  "compression reading 16.0x" quoted in the README, a description of structure,
  not a promised saving (anchor E15).

## Group order

The number of elements (permutations) the group contains.

- Example: the demo environment's true group S6 has order 720; the work-order
  model's group has order 2 (anchors E42, E2).

## Trivial group

The one-element group that maps every state to itself; it changes nothing, so
"only the trivial group was found" is the tool's honest way of saying "no
usable symmetry here".

- Example: `discover` exits 1 when only the trivial group (order 1) is found —
  a finding, not an error (README §3).

## Generator

A small subset of group elements whose combinations already produce the entire
group; `discover` reports generators so the found group can be inspected and
stored compactly.

- Example: the work-order group needs a single generator — the accepted/
  en-route bit swap (anchor E5).

## Equivariance

The property that applying a permutation before or after taking a transition
gives the same result: the relabeled system and the original system do exactly
the same things.

- Example: a group element passes the transition layer exactly when it is
  equivariant with total variation 0 (tolerance 1e-9); the demo's XOR group is
  equivariant yet still refused — by the reward layer (anchor E44).

  Whether action names may be renamed along with the states is a separate
  caliber question — see "Action semantics" below.

## Action semantics

Which of two kinds your action names are — it decides whether action names
may be renamed along with the states. **Switch/milestone systems**: an action
is bound to a state bit, so renaming a state renames its action with it, and
the default criteria (which allow that renaming) are correct. **Event-driven
machines**: an action name is an external event that must keep its name;
`--strict` (exact action correspondence) is correct there, and the default
would admit business-invalid permutations. The `layer_transition.judge` field
in `check` output records which criterion ran (`bitstring` / `generalized` /
`strict` / `explicit`). The tool cannot infer the kind from data — since
2026-10-29 you **declare** it in the group file (`"semantics":
{"action": "relabel" | "fixed" | "explicit"}`); undeclared groups run
under relabel with a loud `semantics_assumed` warning (README §7; the
comparison table and self-assessment questions:
[docs/judge-semantics.md](judge-semantics.md)).

- Example: in the work-order model "accept" and "en-route" are milestone
  bits — renaming them together with their states is the same instruction, so
  the default criterion is the right one; on an event-driven machine, an
  event like "receive FIN" must keep its name, and only `--strict` judges it
  with the correct reading.

## Total variation (TV)

A standard distance between two probability distributions: 0 means identical,
1 means disjoint; the judge requires max TV ≤ 1e-9 — numerical zero — for
every group element.

- Example: `"worst_tv": 0.0` on all 25 elements of the team-battle check
  (anchor E15).

## Reward profile

The multiset of (probability, reward) pairs reachable from a state; a group
can preserve transitions yet still change rewards, so states in the same orbit
must share an identical reward profile.

- Example: the demo group that keeps transitions (worst TV 0.0) but breaks
  1,586 of 2,016 orbit pairs is refused by the reward layer (anchor E44).

## Admission gate

The tool's contract shape: a decision standing in front of your pipeline with
three outcomes — admit (exit 0), refuse (exit 1), insufficient-data abstain
(exit 2) — plus exit 3 for input or internal errors.

- Example: the exit-code table in README §3 is the authoritative list, and the
  codes are uniform across `discover` / `check` / `check-sample`.

## Abstain

The "insufficient samples" verdict (exit 2): it claims only that the data is
too thin to judge, and never converts silence into a pass.

- Example: `check-sample` abstains on 100 demo samples and passes on 10,000
  (anchor E45).

## Completeness certificate

A machine-checked proof that a `discover` search missed part of the group: a
permutation that itself passes every check yet is not in the returned group.

- Example: when no certificate exists but statistics hint at a gap, the tool
  reports a softer calibrated "suspicion" instead — a hint to investigate,
  never a verdict and never a pass (see `--report-confidence`).

## Padding (dummy) states

Unreachable extra states added because the input contract fixes the state
count to a power of two; they are transcribed as self-loop rows with zero
reward and can never be sampled.

- Example: the 512-state case study has 465 real + 47 padding states; the
  16,384-state one has 14,415 real + 1,969 padding (anchors E7, E13).

## Bit-string convention

The tool's input contract: the state count must be a power of two
(`n_states = 2**n_bits`) and action `a` means "flip bit `a`"; models that do
not fit are refused or yield only the trivial group — never a false pass.

- Example: symmetries not expressible on the bits are out of scope by
  construction — measured as 75 -> 5 and 375 -> 25 in the two case studies
  (anchors E9, E14).

## Preregistration

Writing down each case study's expected outcome and its pass rule before
running it, so the reported verdicts cannot be chosen after seeing the data.

- Example: the work-order case's primary prediction (order 2, that exact
  generator, check passes) was pre-stated and then hit (anchor E6).
