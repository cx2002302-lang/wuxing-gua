# Evidence index

This repository makes quantitative claims (case-study results, calibration
numbers, negative results). This file is the traceability index: **one anchor
per line**, mapping each claim to the machine-readable record it comes from.

Two kinds of sources appear:

1. **JSON result files from the research repository** — the project that
   produced this tool keeps its raw experiment and case-study records as JSON
   files. Those files are the source of truth for every number quoted here.
   Paths are given relative to the root of that research repository (the
   research repository itself is not part of this release; the paths are
   published so that the provenance of each number is unambiguous and
   auditable).
2. **Self-demonstrating commands** — a few numbers (the demo walkthrough in
   `docs/quickstart.md` and the outputs quoted in `examples/README.md`) come
   from deterministic commands over committed files. Anyone re-running the
   command reproduces the exact digits; they were re-run during the preparation
   of this release. Where a research JSON also records the underlying constant,
   it is cited as well.

Timing figures are stated as magnitudes only (single-run wall-clock times
drift between machines and runs); exact measured durations, where they matter,
live in the JSON records cited below.

## Case study 1 — work-order milestone state machine (32 states)

- **E1** | Model is 32 states x 5 actions | `pilot/ticketfsm_run.json` | `extraction_selfcheck.main.n_states`, `.n_actions`
- **E2** | `discover` finds group order 2, 24 orbits, 32/24 = 1.333x | `pilot/ticketfsm_run.json` | `summary.main.group_order`, `.n_orbits`, `.compression_ratio`
- **E3** | `check` on the found group: verdict pass, exit code 0, reward layer 0 bad of 8 orbit pairs | `pilot/ticketfsm_check.json` | `verdict`, `.exit_code`, `.layer_reward_profile.n_pair`, `.n_bad`
- **E4** | An independent brute-force enumeration fixes the true automorphism group at exactly 2 | `pilot/aut_bruteforce.json` | `main.aut_order_dedup_by_pi`
- **E5** | The only non-trivial automorphism swaps the "accepted"/"en-route" milestone bits (2<->4, 3<->5, 10<->12, ...) | `pilot/aut_bruteforce.json` | `main.nontrivial_moves`
- **E6** | The preregistered primary prediction (order 2, this generator, check passes) was hit | `pilot/ticketfsm_run.json` | `summary.main.prereg_judgment`; rule pre-stated in `pilot/prereg_pilot.json` | `meta.preregistered.primary_expectation`
- **E46** | Completeness probe on this model: no certificate, no alert | `pilot/ticketfsm_run.json` | `summary.main.completeness_verdict`, `.completeness_alert`
- **E19** | The confidence layer's statistical verdict was a false positive on this model (full-score suspicion while the true group is order 2) | `pilot/ticketfsm_run.json` | `summary.main.confidence.verdict`, `.wl_gap` (6.0), `.w3d_score` (1.0); true group per anchor E4

## Case study 2 — card-engine chain x rotation subsystem (512 states)

- **E7** | Model is 512 states (465 reachable + 47 padding) x 7 actions | `pilot/gw_chainrot_abstract.json` | `encoding.n_real`, `.n_dummy`; the committed `examples/gw_chainrot_model.json` itself
- **E8** | `check` on the hand-derived 5-element group: verdict pass, exit 0, 5/5 elements worst TV 0.0 (tolerance 1e-9), reward layer 0 bad of 960 orbit pairs, 128 orbits, 4.0x | `pilot/gw_chainrot_check_h.json` | `verdict`, `.exit_code`, `.layer_transition.n_checked`, `.layer_transition.worst_tv`, `.layer_reward_profile.n_pair`, `.n_bad`, `.group.order`, `.group.n_orbits`, `.group.compression`
- **E9** | The abstract (pre-encoding) system has a fully verified 75-element automorphism group (0 violations across all 75 elements); only 5 of them are realizable on the bit-string encoding | `pilot/gw_chainrot_abstract.json` | `abstract.aut_group_checked`, `.abstract.aut_violations`, `.H.order`
- **E10** | Transcription fidelity: 120,000 steps replayed against the original engine, 0 disagreements | `pilot/gw_run.json` | `sampling.n_samples`, `.sampling.fidelity_ok`, `.sampling.fidelity_bad`
- **E11** | Sample-based judgment on 120,000 real engine samples: verdict abstain, exit 2 — 10 orbits uncovered, 56 below the power threshold; structural, because padding-state orbits are unreachable | `pilot/gw_chainrot_checksample.json` | `verdict`, `.exit_code`, `.reason`, `.n_samples`
- **E12** | Automatic discovery at this size needs `--pad-aware`: it finds the order-5 group within the 900 s budget (magnitude: ~277 s wall), all elements within the abstract group, all padding states fixed | `pilot/gw_padaware_run.json` | `stage_main.main_plain.order`, `.returncode`, `.stage_main.main_checks.subset_aut75`, `.pad_all_fixed`, `.meta.wall_main_stage_sec`

## Case study 3 — two-team extension (16,384 states)

- **E13** | Model is 16,384 states (14,415 reachable + 1,969 padding, 12.0%) x 11 actions, 2,325 absorbing goal states | `pilot/gw_teambattle_abstract.json` | `abstract.n_states`, `.abstract.n_actions`, `.model_selfcheck.pad_count`, `.goal_count`
- **E14** | Abstract automorphism group: 375 elements fully verified (0 violations); the bit-string-visible group H has order 25 (C5 x C5) and excludes the rotation-field operator | `pilot/gw_teambattle_abstract.json` | `abstract.aut_group_checked`, `.abstract.aut_violations`, `.H.order`, `.H.sigma_rot_visible`, `.abstract.group_abs`
- **E15** | `check` on H: verdict pass, exit 0, 25/25 elements worst TV 0.0, reward layer 0 bad of 176,640 orbit pairs, 1,024 orbits, 16.0x | `pilot/gw_teambattle_check_hdet.json` | `verdict`, `.exit_code`, `.layer_transition.*`, `.layer_reward_profile.*`, `.group.*`
- **E16** | The 125-element candidate that additionally moves the rotation field is rejected: exit 1, 100 of 125 elements violate the transition layer | `pilot/gw_teambattle_check_hfull_v2.json` | `verdict`, `.exit_code`, `.layer_transition.n_checked`, `.n_failed`; run record `pilot/gw_teambattle_runs.json` | `belt1b_full125_v2.exit_code`, `.n_failed`, `.n_checked`
- **E17** | The preregistered primary-hit rule was satisfied: the rule is stated pre-run in the preregistration, and its two inputs are the passing check (E15) and the discovery branch completing as a clean timeout | rule: `pilot/prereg_teambattle.json` | `meta.preregistered.primary_hit_rules`; input: `pilot/gw_teambattle_runs.json` | `belt2_discover_v2.clean_timeout`, `.belt2_discover_v2.budget_sec`
- **E18** | Automatic discovery at 16,384 states: first run exits 3 (RecursionError — backtracking recursion depth exceeds the interpreter's default limit), and with the limit raised, no output within a 900 s budget; the full recommended configuration likewise none within 1,500 s | `pilot/gw_teambattle_runs.json` | `belt2_discover_v1.returncode`, `.outcome`, `.belt2_discover_v2.clean_timeout`, `.belt2_discover_v2.budget_sec`, `.belt2_robust_appendix.clean_timeout`, `.belt2_robust_appendix.budget_sec`
- **E48** | Automatic discovery at 16,384 states also times out cleanly at a 3,600 s budget — the hard budget boundary at this scale: budget 3,600.0 s, killed at 3,600.2 s, stdout/stderr 0 bytes, no traceback, no exit 3 | `pilot/gw_teambattle_discover_longsight.run.json` | `budget_sec`, `.wall_sec`, `.status`, `.outcome`, `.stdout_json_bytes`, `.stderr_bytes` via `pilot/gw_teambattle_discover_longsight.verdict.json` → `evidence`

## Calibration and correctness of the criteria

- **E20** | Confidence discriminator: AUC 1.0 over its 115-instance calibration matrix (9 environments x 13 state-numberings); 69 true-group vs 46 not-true-group instances, zero errors at both ends, every environment individually correct | `experiments_w3_discriminator.json` | `matrix_summary.auc_main_w3d`, `.n_instances`, `.confusion_2x2`, `.env_level_all_correct`
- **E21** | The same discriminator's challenge set (renumbered instances it was not calibrated on): 31 of 31 arms correct | `experiments_w3_discriminator.json` | `challenge_set.n_correct`, `.n_arms`
- **E22** | Sample-based judgment switches to its pass verdict only at 10,000 samples, an empirically calibrated minimum (4 scenarios x 3 seeds, 100% agreement with the full-table criterion) | `experiments_cheap_sample.json` | `threshold.overall_min_budget`
- **E23** | Reward-profile criterion false-pass audit: 0 false passes in 100 probes | `experiments_p4.json` | `false_pass.n`, `.false`, `.rate`
- **E24** | The tool's own end-to-end selftest: 13 branches, all pass, exit 0 | `dist/install_verification.json` | `bundle.selftest_passed`, `.selftest_total`, `.selftest_exit`

## State-numbering sensitivity and repair paths (background for `docs/boundaries.md`)

- **E25** | Across a 91-instance scan (7 environments x 13 numberings), the plain searcher fully loses the group on 40.66% of instances; canonical renumbering repairs 85.71% (13 residuals remain) | `experiments_discover_labeling.json` | `summary.global.instances_total`, `.plain.completely_lost_rate`, `.canon_repair_rate`, `.canon_residual_count`
- **E26** | Search statistics are not isomorphism invariants: renumbering the same graph moves the measured overhead by up to a 336.4% relative range | `experiments_ovh_relabel.json` | `per_graph_verdict.Heawood.rel_range` (3.3642)
- **E27** | Canonical renumbering zeroes that spread (relative range 0.0 on all three probe graphs) | `experiments_canonical_search.json` | `per_graph.Heawood.rel_range_after`
- **E28** | Canonical renumbering is not a universal repair: on a Tower-of-Hanoi environment (6,561 states) the plain arm finds the true group (order 6) while the canonized arm collapses to the trivial group (order 1) | `experiments_sys4_n8.json` | `n8.env.true_order`, `.n8.plain.auto`, `.n8.canon.auto`
- **E29** | Combining repairs globally (9 environments x 13 numberings), environments reaching the true group: plain 3/9, canonize 6/9, extra-candidates 3/9, extra+multi-label 8/9, canonize+extra 7/9, all three combined 9/9 | `experiments_threefix_global.json` | `judgment.env_count`
- **E30** | On the 64-state hexagram environment the all-three combination reaches the full 589,824-element group | `experiments_fullflags.json` | `environments.gua64.C6_full_flags.order`
- **E31** | Union over 13 random renumberings plateaus at 294,912 — the same element set as the machine group (a label-side ceiling; `same_set` true) | `experiments_multilabel_union.json` | `diagnostics.gua64_union_vs_std_machine_group.union_order_k13`, `.machine_order_std`, `.same_set`
- **E32** | The action-permutation candidate source closes that gap: order 589,824, and an independent zero-tolerance re-check of all 589,824 elements finds 0 failures | `experiments_gua64_gapfix.json` | `fix.gua64.order`, `.full_scan_elements`, `.full_scan_failures`

## Negative results (one-line versions in `docs/negative-results.md`; the full list is in the accompanying paper)

- **E33** | Random-restart search silently produces nothing on relabeled graphs: 5,000 restarts yield 296 alive restarts on the standard numbering but 0 completions on each of two relabeled graphs | `experiments_gua64_gapfix.json` | `diag_exclusions.rr_path_std.alive_restarts`, `.rr_path_relabeled.s01.n_completions`, `.rr_path_relabeled.s03.n_completions`
- **E34** | Involution-style generators were structurally excluded from the target coset: all 29 candidates are fixed-point-free while the coset contains no fixed-point-0 elements — no budget can fix a structural empty intersection | `experiments_gua64_gapfix.json` | `diag_exclusions.involution_path.n_candidates`, `.all_fixed_point_free`, `.mechanism`
- **E35** | "Search finished within budget" does not mean "the budget covered the target": the first solution in the target coset appeared at search-tree node 3,368,887, about 842x the 4,000-node default budget; all earlier solutions were valid and passed every check | `experiments_gua64_gapfix.json` | `diag_exclusions.det_path.ladder[2].first_coset.nodes`, `.ladder[0].node_cap`
- **E36** | Group-theoretic explanatory candidates collapse under collinearity with group order: on 29 graphs, SLP depth has rho = -0.26 (p = 0.17) and partial rho = 0.46, below the preregistered explanation gates (0.7 / 0.5) | `experiments_ovh_residual.json` | `analysis.R1_slp_depth.statistics[0].rho`, `.p_value`, `.partial_rho`
- **E37** | A structural collapse can look like a numbering artifact but is not: the K-family collapse is bitwise identical before and after canonical renumbering (K(4,4) c-range [1.7361, 3.4722] in both calibers; K(5,5) [2.2222, 4.4444]) | `experiments_c_canon.json` | `mechanism` (K44 and K55 rows: `c_natural` vs `c_canon`)
- **E38** | A constant-factor speedup decays with scale: the cheap verifier's speedup over full value iteration falls from 1.64x (n=6) to 1.10x (n=12); fitted growth 0.675, below the preregistered 1.5 "widening" line | `experiments_p4_asymptotic.json` | `fit.growth_A_last_over_first`, `.speedup_vs_n_slope` (-0.08); per-size ratios from `scan` rows (`t_vi_exact_sec` / `t_cheap_exact_sec`)

## Distribution and selftest

- **E39** | Source bundle: 104 files; unpack-and-run selftest 13/13 pass, exit 0 | `dist/install_verification.json` | `bundle.n_files`, `.selftest_passed`, `.selftest_total`, `.selftest_exit`
- **E40** | `pip install` into a scratch target verified: install exit 0, post-install selftest 13/13 | `dist/install_verification.json` | `install.exit`, `.selftest_passed`, `.selftest_total`
- **E41** | Selftest wall-time magnitude: on the order of two minutes on the reference machine (126.7 s from the bundle, 129.4 s post-install) | `dist/install_verification.json` | `bundle.selftest_sec`, `install.selftest_sec`

## Demo walkthrough (`docs/quickstart.md`) — self-demonstrating commands

The walkthrough uses fixtures regenerated by the `demo` command (deterministic,
byte-identical on re-run). The numbers below were reproduced from those fixtures
during release preparation; where a research JSON records the same constant, it
is cited.

- **E42** | Demo environment Q6: `discover` finds order 720, 7 orbits, 64/7 = 9.143x | reproduced by the quickstart command; research record `experiments_p3.json` | `recovery[n=6].auto_order`, `.auto_orbits`
- **E43** | Demo: `check` accepts the true S6 group (exit 0) | reproduced by the quickstart command (deterministic fixtures)
- **E44** | Demo: `check` rejects a transition-preserving but reward-breaking group — transition layer passes (worst TV 0.0) while the reward layer reports 1,586 bad of 2,016 orbit pairs; verdict reject, exit 1 | reproduced by the quickstart command (deterministic fixtures); the selftest asserts the same branch (`wuxing_gua/selftest.py`, popcount-vs-XOR case)
- **E45** | Demo: `check-sample` abstains at 100 samples (exit 2) and passes at 10,000 (exit 0) | reproduced by the quickstart commands (deterministic fixtures); the 10,000 threshold per anchor E22

## Hygiene

- **E47** | Each JSON cited above is a write-once or append-only run record; several embed their own provenance (preregistration timestamps, script hashes before/after the run) in a `meta` block. The research repository additionally maintains an automated consistency audit that re-derives headline numbers from these files; its most recent pass log predates this release.
- **E49** | During release preparation, the `meta.source_system` note inside the three shipped example models was normalized to remove authoring-environment details, and the originating system name of the ticket-dispatch case was anonymized (shipped under the neutral name `ticketfsm`); the model payloads (states, transitions, rewards, goals) are unchanged, and the consistency audit compares payloads excluding that single note field | `examples/ticketfsm_milestones_model.json`, `examples/gw_chainrot_model.json`, `examples/gw_teambattle_model.json` | `meta.source_system` (only divergent field, by release decision)
- **E50** | The completeness alarm's thresholds are fixed constants (ALERT_CERT_MIN = 1, SCORE_ALERT_LINE = 0.5, SUSPICION_CAP = 0.45, WL_GAP_SCALE = 10.0, 3 probe batches, restart-seed base 101), and the alarm was re-verified after the SYS-3 A adjudication on 7 known-true-group calibration environment instances (4 expected-alert positives, 3 expected-silent negatives): 7/7 match their expectation, 0 false alarms on negatives, 0 misses on positives; gua64 has no ground truth and is display-only (excluded from calibration) | `experiments_completeness.json` | `meta.constants`, `calibration_summary.n_positive`, `.n_negative`, `.n_expected_match`, `.false_positives_on_negatives`, `.false_negatives_on_positives`; before/after comparison `experiments_sys3a_recheck.json` | `blindspot_fix`
