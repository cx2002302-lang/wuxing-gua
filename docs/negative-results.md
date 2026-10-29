# Negative results worth knowing before you use this tool

A tool that verifies symmetry groups can fail in interesting ways, and the
failures we hit are more transferable than the successes. Below are the ten
findings from this project's research logs with the highest value to an outside
user, one sentence each. **The full list (with trigger conditions, mechanisms
and per-instance data) is in the accompanying paper.** Every claim links to its
machine-readable record via `docs/evidence.md`.

1. **Search-behavior readings on a transition graph are not isomorphism
   invariants**: renumbering the same graph moved a search-cost statistic by
   up to 336.4%, canonical renumbering zeroed that spread, and a "no
   correlation" verdict obtained under natural numbering reversed after
   canonicalization — any cross-instance comparison must canonicalize first,
   or its null results may be numbering noise (anchors E26, E27).

2. **Canonical renumbering is not a universal repair**: on a
   Tower-of-Hanoi-shaped environment it *suppresses* discovery, collapsing the
   true order-6 group to the trivial group — so "always canonicalize" is wrong
   too; union plain and canonical results instead (anchor E28).

3. **Unioning searches over many renumberings has a label-side ceiling**: on
   the 64-state hexagram environment, unions over 13 random renumberings
   plateau at 294,912 elements — the same set every time — while adding the
   environment's own action-permutation maps to the candidate pool reaches the
   full 589,824 (anchors E31, E32).

4. **Randomized-restart search can silently produce nothing on relabeled
   graphs**: 5,000 restarts yielded 296 live restarts on the standard numbering
   but zero completions on each of two relabelings of the same graph — restart
   yield is numbering-sensitive to the point of binary (anchor E33).

5. **A structural exclusion cannot be fixed by budget**: every involution-style
   candidate (29 of them) is fixed-point-free while the target coset contains
   no fixed-point-0 element, so no amount of time, renumbering or restarting
   can reach it — recognize structural impossibility instead of scaling up
   (anchor E34).

6. **"The search finished within budget" does not mean "the budget covered the
   target"**: the first solution in the target coset appeared at search-tree
   node 3,368,887 — about 842x the 4,000-node default budget — while every
   earlier solution was valid and passed every check (anchor E35).

7. **Group-theoretic quantities make seductive but collinear explanations**:
   ten candidate explanatory quantities (shortest-program depth, derived
   length, ...) all collapse once group order is controlled for, leaving no
   independent structural explanation of search cost on 29 graphs (anchor
   E36).

8. **A structural collapse can masquerade as a numbering artifact**: the
   K-family collapse survives canonical renumbering bitwise-identically, i.e.
   canonicalization repairs *readings*, not *structure* — before crediting
   "artifact", check whether the effect survives the artifact fix (anchor
   E37).

9. **A constant-factor speedup decays with scale**: the cheap verifier's
   advantage over full value iteration fell from 1.64x to 1.10x across a
   64x state-count range, with fitted growth below the preregistered
   "widening" line — do not market constant factors as asymptotic wins
   (anchor E38).

10. **A calibrated confidence score can be confidently wrong out of
    distribution**: the confidence layer, perfect on its own 115-instance
    calibration matrix, reported a full-score "suspicion" on a workflow-shaped
    state machine it had never been calibrated on — whose true automorphism group an
    independent brute force fixed at order 2; keep proof-level outputs
    (certificates, zero-tolerance verdicts) strictly above statistical hints
    (anchors E20, E19, E4).

These ten share one lesson: in this problem domain, **the ways a pipeline can
quietly mislead you outnumber the ways it can loudly fail** — which is why the
tool's design center is refusal (exit codes 1/2/3) rather than confidence.
