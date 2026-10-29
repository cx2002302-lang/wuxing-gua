# -*- coding: utf-8 -*-
"""
make_dualchannel_samples.py -- deterministic generator for the rung-1a samples

Writes four files next to this script (byte-identical on every re-run; nothing
random, no clock, no locale dependence):

  dualchannel_model.json         16-state model, NO business constraint
  dualchannel_guarded_model.json 16-state model, WITH the business constraint
  dualchannel_guarded_group.json order-2 group: swap channel A <-> B  (admitted)
  dualchannel_wrong_group.json   order-2 group: swap collect<->reconcile
                                 inside one channel             (refused)

This is a hand-constructed teaching model, NOT a transcription of a real
system. The construction rule is fully stated here and in examples/README.md.

Business shape: one order goes through two payment channels A and B at once.
Each channel has two steps -- collect, then reconcile. Four bits:

  bit0 = A collected   bit1 = A reconciled
  bit2 = B collected   bit3 = B reconciled

Four actions set bit a. Reward: +1 on a successful set; -1 (self-loop) on a
repeat or when the prerequisite is unmet; the goal state 1111 self-loops at 0.

The two variants differ by ONE constraint, and that is the point:

  unguarded  -> any of the four stages may swap      -> order 24 (4!), 5 orbits
  guarded    -> reconcile needs its own collect first -> order 2, 10 orbits

Usage (from the repository root or anywhere):

  python -X utf8 examples/make_dualchannel_samples.py            # write files
  python -X utf8 examples/make_dualchannel_samples.py --out DIR  # write into DIR
  python -X utf8 examples/make_dualchannel_samples.py --check    # verify bytes
"""
import argparse
import json
import os
import sys

N_BITS = 4
N_ACTIONS = 4
N_STATES = 1 << N_BITS          # 16
GOAL = N_STATES - 1             # 1111, absorbing

# action a -> the bit of the prerequisite step (None = no prerequisite)
PREREQ = {0: None, 1: 0, 2: None, 3: 2}    # reconcile(1) needs collect(0); same for B


def _build(guarded):
    """Both variants. `guarded=False` drops the prerequisite (degenerate model)."""
    trans = []
    for s in range(N_STATES):
        row = []
        for a in range(N_ACTIONS):
            pre = PREREQ[a]
            ready = (pre is None) or ((s >> pre) & 1)
            if s == GOAL:
                row.append([[1.0, GOAL, 0.0]])
            elif guarded and not ready:
                row.append([[1.0, s, -1.0]])       # prerequisite unmet
            elif (s >> a) & 1:
                row.append([[1.0, s, -1.0]])       # already done
            else:
                row.append([[1.0, s | (1 << a), 1.0]])
        trans.append(row)

    if guarded:
        meta = {
            "source_system": ("rung-1a teaching model: two-channel reconciliation "
                              "(hand-constructed for this repository, not "
                              "transcribed from a real system)"),
            "variant": "dual-channel-reconcile-guarded",
            "bit_names": ["A collected", "A reconciled", "B collected", "B reconciled"],
            "action_names": ["collect A", "reconcile A", "collect B", "reconcile B"],
            "constraint": ("reconcile requires collect within the same channel; "
                           "channels do not interact"),
            "visible_symmetry": ("swap the two channels: bit0<->bit2, bit1<->bit3 "
                                 "(order 2, 10 orbits)"),
            "reward_rule": ("successful set +1 / unmet prerequisite or repeat "
                            "self-loop -1 / goal self-loop 0; deterministic p=1.0"),
            "regenerate": "python -X utf8 examples/make_dualchannel_samples.py",
        }
    else:
        meta = {
            "source_system": ("rung-1a teaching model: two-channel reconciliation, "
                              "constraint deliberately omitted (hand-constructed "
                              "for this repository, not transcribed from a real system)"),
            "variant": "dual-channel-reconcile-unguarded",
            "bit_names": ["A collected", "A reconciled", "B collected", "B reconciled"],
            "action_names": ["collect A", "reconcile A", "collect B", "reconcile B"],
            "constraint": "none -- the four bits are independent (contrast model)",
            "visible_symmetry": ("every permutation of the four bits: order 24 "
                                 "(4!), 5 orbits"),
            "reward_rule": ("successful set +1 / repeat self-loop -1 / "
                            "goal self-loop 0; deterministic p=1.0"),
            "regenerate": "python -X utf8 examples/make_dualchannel_samples.py",
        }

    return {
        "n_bits": N_BITS,
        "n_actions": N_ACTIONS,
        "n_states": N_STATES,
        "goals": [GOAL],
        "meta": meta,
        "trans": trans,
    }


def _swap_channels(s):
    b0, b1, b2, b3 = [(s >> i) & 1 for i in range(4)]
    return b2 | (b3 << 1) | (b0 << 2) | (b1 << 3)


def _swap_within_a(s):
    b0, b1, b2, b3 = [(s >> i) & 1 for i in range(4)]
    return b1 | (b0 << 1) | (b2 << 2) | (b3 << 3)


def _order2(fn):
    return [list(range(N_STATES)), [fn(s) for s in range(N_STATES)]]


def build_guarded_group():
    """
    Swap channel A with channel B. The two channels are structurally identical,
    so this is a true symmetry of the guarded model -- admitted (exit 0).
    """
    return {
        "n_states": N_STATES,
        "elements": _order2(_swap_channels),
        "semantics": {"action": "relabel"},
        "meta": {
            "construction": ("order-2 group generated by swapping the two channels "
                             "(bit0<->bit2, bit1<->bit3); a true symmetry of the "
                             "guarded model, expected to be ADMITTED by check"),
            "semantics_note": ("declared relabel: channel bits are switch-class "
                               "(setting bit a IS the action), so action names "
                               "travel with the state renaming "
                               "(docs/judge-semantics.md)"),
            "regenerate": "python -X utf8 examples/make_dualchannel_samples.py",
        },
    }


def build_wrong_group():
    """
    Swap collect with reconcile inside channel A. Looks like two adjacent steps
    of one flow, but the prerequisite is directional: after the swap, "reconcile
    before collect" becomes reachable while "collect then no reconcile" turns
    illegal -- check certifies this on the transition layer (exit 1).
    Note the reward layer passes this candidate; only the transition layer
    catches it, which is exactly why both layers exist.
    """
    return {
        "n_states": N_STATES,
        "elements": _order2(_swap_within_a),
        "semantics": {"action": "relabel"},
        "meta": {
            "construction": ("order-2 group swapping collect<->reconcile inside "
                             "channel A; the tempting 'adjacent steps' candidate, "
                             "expected to be REFUSED by check (transition layer)"),
            "why_it_looks_legal": ("reconcile and collect are adjacent steps of the "
                                   "same channel and each element is a valid "
                                   "permutation"),
            "semantics_note": ("declared relabel: the refusal below is certified "
                               "under the switch-class reading, the right one for "
                               "this model (docs/judge-semantics.md)"),
            "regenerate": "python -X utf8 examples/make_dualchannel_samples.py",
        },
    }


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=here,
                    help="target directory (default: this script's directory)")
    ap.add_argument("--check", action="store_true",
                    help="do not write; verify the committed files are byte-identical")
    args = ap.parse_args(argv)

    payloads = {
        "dualchannel_model.json": _dump(_build(guarded=False)),
        "dualchannel_guarded_model.json": _dump(_build(guarded=True)),
        "dualchannel_guarded_group.json": _dump(build_guarded_group()),
        "dualchannel_wrong_group.json": _dump(build_wrong_group()),
    }

    if args.check:
        bad = []
        for name, blob in payloads.items():
            p = os.path.join(here, name)
            if not os.path.exists(p):
                bad.append(name + " (missing)")
                continue
            with open(p, "r", encoding="utf-8", newline="") as f:
                if f.read() != blob:
                    bad.append(name)
        if bad:
            sys.stderr.write("byte-identity FAILED: %s\n" % ", ".join(bad))
            return 1
        sys.stdout.write("byte-identity OK: %s\n" % ", ".join(sorted(payloads)))
        return 0

    os.makedirs(args.out, exist_ok=True)
    for name, blob in payloads.items():
        p = os.path.join(args.out, name)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(blob)
        sys.stdout.write("wrote %s (%d bytes)\n" % (p, len(blob.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
