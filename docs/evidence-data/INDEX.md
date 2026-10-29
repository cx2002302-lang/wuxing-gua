# Evidence data — in-repo excerpts

Every number quoted in the README and indexed by `docs/evidence.md`
comes from a JSON record kept in the **research repository**, which is
not part of this release. This directory holds **verbatim excerpts of
exactly the cited fields** of each record, so the numbers can be
checked from the public repository alone. Each file states the mother
path (`excerpt_of`) and the field paths it covers; values are copied
without rounding or edits. Excerpted on 2026-10-29.

The live index that maps each claim to its excerpt lives in
[docs/evidence.md](../evidence.md) — every E anchor now points here
first, with the mother path kept as an annotation.

## Files

| Excerpt file | Mother path (research repo) | Anchors | Fields excerpted |
|---|---|---|---|
| [`pilot_ticketfsm_run.json`](pilot_ticketfsm_run.json) | `pilot/ticketfsm_run.json` | E1, E2, E6, E19, E46 | 12 |
| [`pilot_ticketfsm_check.json`](pilot_ticketfsm_check.json) | `pilot/ticketfsm_check.json` | E3 | 4 |
| [`pilot_aut_bruteforce.json`](pilot_aut_bruteforce.json) | `pilot/aut_bruteforce.json` | E4, E5 | 2 |
| [`pilot_prereg_pilot.json`](pilot_prereg_pilot.json) | `pilot/prereg_pilot.json` | E6 | 3 |
| [`pilot_gw_chainrot_abstract.json`](pilot_gw_chainrot_abstract.json) | `pilot/gw_chainrot_abstract.json` | E7, E9 | 5 |
| [`pilot_gw_chainrot_check_h.json`](pilot_gw_chainrot_check_h.json) | `pilot/gw_chainrot_check_h.json` | E8 | 9 |
| [`pilot_gw_run.json`](pilot_gw_run.json) | `pilot/gw_run.json` | E10 | 3 |
| [`pilot_gw_chainrot_checksample.json`](pilot_gw_chainrot_checksample.json) | `pilot/gw_chainrot_checksample.json` | E11 | 4 |
| [`pilot_gw_padaware_run.json`](pilot_gw_padaware_run.json) | `pilot/gw_padaware_run.json` | E12 | 5 |
| [`pilot_gw_teambattle_abstract.json`](pilot_gw_teambattle_abstract.json) | `pilot/gw_teambattle_abstract.json` | E13, E14 | 9 |
| [`pilot_gw_teambattle_check_hdet.json`](pilot_gw_teambattle_check_hdet.json) | `pilot/gw_teambattle_check_hdet.json` | E15 | 9 |
| [`pilot_gw_teambattle_check_hfull_v2.json`](pilot_gw_teambattle_check_hfull_v2.json) | `pilot/gw_teambattle_check_hfull_v2.json` | E16 | 4 |
| [`pilot_gw_teambattle_runs.json`](pilot_gw_teambattle_runs.json) | `pilot/gw_teambattle_runs.json` | E16, E17, E18 | 9 |
| [`pilot_prereg_teambattle.json`](pilot_prereg_teambattle.json) | `pilot/prereg_teambattle.json` | E17 | 3 |
| [`pilot_gw_teambattle_discover_longsight.run.json`](pilot_gw_teambattle_discover_longsight.run.json) | `pilot/gw_teambattle_discover_longsight.run.json` | E48 | 5 |
| [`pilot_gw_teambattle_discover_longsight.verdict.json`](pilot_gw_teambattle_discover_longsight.verdict.json) | `pilot/gw_teambattle_discover_longsight.verdict.json` | E48 | 1 |
| [`experiments_w3_discriminator.json`](experiments_w3_discriminator.json) | `experiments_w3_discriminator.json` | E20, E21 | 6 |
| [`experiments_w3_discriminator_v2.json`](experiments_w3_discriminator_v2.json) | `experiments_w3_discriminator_v2.json` | README-115 | 4 |
| [`experiments_cheap_sample.json`](experiments_cheap_sample.json) | `experiments_cheap_sample.json` | E22 | 1 |
| [`experiments_p4.json`](experiments_p4.json) | `experiments_p4.json` | E23 | 3 |
| [`dist_install_verification.json`](dist_install_verification.json) | `dist/install_verification.json` | E24, E39, E40, E41 | 9 |
| [`experiments_p3.json`](experiments_p3.json) | `experiments_p3.json` | E42, README-flagship | 10 |
| [`experiments_discover_labeling.json`](experiments_discover_labeling.json) | `experiments_discover_labeling.json` | E25, E51 | 8 |
| [`experiments_fullflags.json`](experiments_fullflags.json) | `experiments_fullflags.json` | E30 | 2 |
| [`experiments_threefix_global.json`](experiments_threefix_global.json) | `experiments_threefix_global.json` | E29 | 1 |
| [`experiments_ovh_relabel.json`](experiments_ovh_relabel.json) | `experiments_ovh_relabel.json` | E26 | 1 |
| [`experiments_canonical_search.json`](experiments_canonical_search.json) | `experiments_canonical_search.json` | E27 | 1 |
| [`experiments_sys4_n8.json`](experiments_sys4_n8.json) | `experiments_sys4_n8.json` | E28 | 3 |
| [`experiments_multilabel_union.json`](experiments_multilabel_union.json) | `experiments_multilabel_union.json` | E31 | 3 |
| [`experiments_gua64_gapfix.json`](experiments_gua64_gapfix.json) | `experiments_gua64_gapfix.json` | E32, E33, E34, E35 | 10 |
| [`experiments_ovh_residual.json`](experiments_ovh_residual.json) | `experiments_ovh_residual.json` | E36 | 3 |
| [`experiments_c_canon.json`](experiments_c_canon.json) | `experiments_c_canon.json` | E37 | 6 |
| [`experiments_p4_asymptotic.json`](experiments_p4_asymptotic.json) | `experiments_p4_asymptotic.json` | E38 | 2 |
| [`experiments_completeness.json`](experiments_completeness.json) | `experiments_completeness.json` | E50 | 6 |
| [`experiments_sys3a_recheck.json`](experiments_sys3a_recheck.json) | `experiments_sys3a_recheck.json` | E50 | 1 |

## Corrections applied to `docs/evidence.md`

Two anchor lines cited field paths that do not exist in the research
records; corrected against the actual files:

- E6: field `meta.preregistered.primary_expectation` → actual
  `meta.preregistered.preregistered_expectations.primary_hypothesis`.
- E17: field `meta.preregistered.primary_hit_rules` → actual
  `meta.preregistered.judgment.belt1_primary.expectation`.

Naming convention: the ticket-dispatch case's record paths are written
under their release alias `pilot/ticketfsm_*.json`, per the release
naming decision recorded in anchor E49 (the research files themselves
carry the pre-anonymization internal name). Field paths and values are
verbatim.

## README quick map (claims without an E anchor)

| README claim | Excerpt | Fields |
|---|---|---|
| §2 flagship number 40320 vs 16 (2520x) | [`experiments_p3.json`](experiments_p3.json) | `recovery[1].auto_order` vs `.manual_order` |
| §5 115-instance AUC 1.0 | [`experiments_w3_discriminator_v2.json`](experiments_w3_discriminator_v2.json) | `matrix_summary.auc_main_w3d`, `.n_instances`, `.confusion_2x2` |
| §5 0/100 adversarial false admission | [`experiments_p4.json`](experiments_p4.json) | `false_pass.n`, `.false`, `.rate` |
| §3/§6 ticketfsm order 2 / 24 orbits / 1.33x | [`pilot_ticketfsm_run.json`](pilot_ticketfsm_run.json) | `summary.main.group_order`, `.n_orbits`, `.compression_ratio` |
| §5 512 = 465 + 47 | [`pilot_gw_chainrot_abstract.json`](pilot_gw_chainrot_abstract.json) | `encoding.n_real`, `.n_dummy` |
| §5 16,384 = 14,415 + 1,969 (12.0% pad) | [`pilot_gw_teambattle_abstract.json`](pilot_gw_teambattle_abstract.json) | `abstract.n_states`, `model_selfcheck.pad_count` |
| §5 120,000-step replay, 100.000% | [`pilot_gw_run.json`](pilot_gw_run.json) | `sampling.n_samples`, `.fidelity_ok`, `.fidelity_bad` |
| §5 900/1500/3600 s timeouts | [`pilot_gw_teambattle_runs.json`](pilot_gw_teambattle_runs.json) + [`pilot_gw_teambattle_discover_longsight.run.json`](pilot_gw_teambattle_discover_longsight.run.json) | `belt2_*` blocks, `budget_sec`/`wall_sec` |
| §7 75 → 5 / 375 → 25 | [`pilot_gw_chainrot_abstract.json`](pilot_gw_chainrot_abstract.json) / [`pilot_gw_teambattle_abstract.json`](pilot_gw_teambattle_abstract.json) | `abstract.aut_group_checked`, `H.order` |
| selftest 13/13 | [`dist_install_verification.json`](dist_install_verification.json) | `bundle.selftest_passed`, `.selftest_total` |
