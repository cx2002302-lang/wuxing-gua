# -*- coding: utf-8 -*-
"""
make_eventfsm_samples.py -- deterministic generator for the event-driven sample
(rung 1c)

Writes four files next to this script (byte-identical on every re-run; nothing
random, no clock, no locale dependence):

  eventfsm_model.json              the 4-reachable-state event-labeled teaching
                                   model, padded to 8 states (power-of-two
                                   input contract, same transcription rule as
                                   the 512/16,384-state real cases)
  eventfsm_group_pads.json         order-2 candidate: swap of two padding
                                   states -- genuinely symmetric with event
                                   names pinned (declares semantics "fixed")
  eventfsm_group_swap_fixed.json   order-2 candidate: swap of the two
                                   structurally identical wait states -- NOT a
                                   symmetry once event names are pinned
                                   (declares semantics "fixed"; refused)
  eventfsm_group_swap_relabel.json the SAME elements as the previous file, but
                                   declaring semantics "relabel": admitted by
                                   the default reading -- the two readings of
                                   one candidate, side by side

This is a hand-constructed teaching model, NOT a transcription of a real
system. It is the minimal shape of the ambiguity described in
docs/judge-semantics.md (and observed against an external standard in the
project's review notes): two states that are structurally interchangeable but
whose outgoing events differ. Here:

  states (4 reachable, 4 padding)      events (external, protocol-named)
    0 open (ESTABLISHED-like)           0 rcv FIN
    1 wait-fin (our FIN is out;         1 rcv ACK of FIN
       waiting for the peer's FIN)      2 snd FIN
    2 closing (both FINs out;           3 rcv RST
       waiting for the peer's ACK)
    4 time-wait (goal, absorbing)     padding states 3, 5, 6, 7: unreachable,
                                      every event self-loops with reward 0

The two wait states 1 and 2 are structurally identical: each has exactly one
outgoing edge into the goal state and otherwise only penalized self-loops.
But the events on those edges differ -- "the peer's FIN arrived" (state 1)
versus "the peer acknowledged our FIN" (state 2). Whether swapping them is a
symmetry depends entirely on whether event names may travel with the states:

  - semantics "relabel" (actions may be renamed along with states): the swap
    is equivariant -- the judge simply renames rcv FIN into rcv ACK of FIN.
  - semantics "fixed" (event names pinned): TV = 1.0 on the completion edges
    -- merging "peer sent FIN" with "peer acknowledged" is a protocol error.

The padding-state swap, by contrast, is a symmetry under BOTH readings: the
padding rows reference no event at all. That is the declared "fixed" positive
control.

Usage (from the repository root or anywhere):

  python -X utf8 examples/make_eventfsm_samples.py            # write all four
  python -X utf8 examples/make_eventfsm_samples.py --out DIR  # write into DIR
  python -X utf8 examples/make_eventfsm_samples.py --check    # verify bytes

`--check` regenerates all four files in memory and compares against the
committed copies, exiting 0 when byte-identical (used when editing the
samples).
"""
import argparse
import json
import os
import sys

N_BITS = 3
N_ACTIONS = 4                     # rcv FIN / rcv ACK of FIN / snd FIN / rcv RST
N_STATES = 1 << N_BITS            # 8 = 4 reachable + 4 padding
GOAL = 4                          # 100 = time-wait, absorbing
OPEN, WAIT_FIN, CLOSING = 0, 1, 2
PADS = (3, 5, 6, 7)

R_OK, R_BAD, R_FINISH, R_RESET = 0.0, -1.0, 1.0, -1.0


def build_model():
    """Event-labeled close-fragment model in the wuxing_gua model.json format."""
    trans = []
    for s in range(N_STATES):
        row = []
        for a in range(N_ACTIONS):
            if s == GOAL or s in PADS:
                row.append([[1.0, s, 0.0]])
            elif s == OPEN:
                # a0 rcv FIN: peer closes first -> both FINs outstanding -> closing
                # a1 rcv ACK of FIN: nothing outstanding to acknowledge -> illegal
                # a2 snd FIN: peer may or may not have sent theirs; the fragment
                #    transcribes the normal branch (wait-fin). (Transcription rule
                #    declared in meta; the simultaneous branch is state 2's entry.)
                # a3 rcv RST: abnormal teardown -> time-wait-equivalent terminal
                tgt = {0: CLOSING, 1: OPEN, 2: WAIT_FIN, 3: GOAL}[a]
                rew = {0: R_OK, 1: R_BAD, 2: R_OK, 3: R_RESET}[a]
                row.append([[1.0, tgt, rew]])
            elif s == WAIT_FIN:
                # a0 rcv FIN completes the close (+1); everything else illegal
                tgt = {0: GOAL, 1: WAIT_FIN, 2: WAIT_FIN, 3: GOAL}[a]
                rew = {0: R_FINISH, 1: R_BAD, 2: R_BAD, 3: R_RESET}[a]
                row.append([[1.0, tgt, rew]])
            else:  # CLOSING
                # a1 rcv ACK of FIN completes the close (+1); everything else illegal
                tgt = {0: CLOSING, 1: GOAL, 2: CLOSING, 3: GOAL}[a]
                rew = {0: R_BAD, 1: R_FINISH, 2: R_BAD, 3: R_RESET}[a]
                row.append([[1.0, tgt, rew]])
        trans.append(row)
    return {
        "n_bits": N_BITS,
        "n_actions": N_ACTIONS,
        "n_states": N_STATES,
        "goals": [GOAL],
        "meta": {
            "source_system": ("event-driven teaching fragment: a close handshake "
                              "with event-labeled edges (hand-constructed minimal "
                              "example for this repository, not transcribed from "
                              "a real system; shaped after the lesson of an "
                              "external RFC 9293 spot-check)"),
            "variant": "eventfsm",
            "encoding": ("states 0/1/2/4 = open / wait-fin / closing / time-wait; "
                         "states 3, 5, 6, 7 = unreachable padding (power-of-two "
                         "input contract, same rule as the 512 / 16,384-state "
                         "real cases): every event self-loops, reward 0"),
            "event_names": ["rcv FIN", "rcv ACK of FIN", "snd FIN", "rcv RST"],
            "semantics_class": ("event: the four actions are external events "
                                "named by the protocol; their names are part of "
                                "the behavior and do not follow state renamings "
                                "-> declare semantics \"fixed\" "
                                "(docs/judge-semantics.md)"),
            "transcription_rules": ("fragment merges the normal-close wait states "
                                    "into one state 1 and the simultaneous-close "
                                    "branch into state 2; rcv FIN while open "
                                    "enters state 2 (both FINs then outstanding); "
                                    "rcv RST tears down to the terminal state 4 "
                                    "with a penalty; repeating an event whose "
                                    "precondition is gone is an illegal self-loop "
                                    "at -1"),
            "reward_rule": ("+1 when the close completes (the state's own "
                            "completion event arrives); -1 for illegal attempts "
                            "and resets; 0 in the terminal state and padding"),
            "structural_fact": ("states 1 and 2 are structurally identical (one "
                                "outgoing edge into the goal each, otherwise "
                                "only penalized self-loops) but their completion "
                                "events differ: rcv FIN vs rcv ACK of FIN"),
            "regenerate": "python -X utf8 examples/make_eventfsm_samples.py",
        },
        "trans": trans,
    }


def _swap(a, b):
    perm = list(range(N_STATES))
    perm[a], perm[b] = perm[b], perm[a]
    return perm


def build_group_pads():
    """
    The "fixed" positive control: swap of two padding states (3 <-> 5).

    Padding rows reference no event (every event self-loops, reward 0), so the
    swap is a symmetry under BOTH readings -- genuinely symmetric with event
    names pinned. Declares semantics "fixed"; check admits it (exit 0).
    """
    return {
        "n_states": N_STATES,
        "elements": [list(range(N_STATES)), _swap(3, 5)],
        "semantics": {"action": "fixed"},
        "meta": {
            "construction": ("order-2 group swapping the two unreachable padding "
                             "states 3 and 5: a genuine symmetry under both "
                             "readings because padding rows reference no event"),
            "why_fixed_passes": ("with event names pinned the swap still maps "
                                 "every event-labeled arrow to itself: padding "
                                 "states have no arrows that name an event"),
            "regenerate": "python -X utf8 examples/make_eventfsm_samples.py",
        },
    }


def build_group_swap():
    """Shared body of the two wait-state-swap candidates (same elements)."""
    return {
        "n_states": N_STATES,
        "elements": [list(range(N_STATES)), _swap(WAIT_FIN, CLOSING)],
        "meta": {
            "construction": ("order-2 group swapping the two structurally "
                             "identical wait states 1 (wait-fin) and 2 "
                             "(closing)"),
            "why_it_looks_legal": ("the two states have the same shape: one "
                                   "outgoing edge into the goal, otherwise only "
                                   "penalized self-loops -- on the unlabeled "
                                   "graph the swap maps arrows to arrows"),
            "why_it_is_not_a_symmetry": ("the completion events differ: state 1 "
                                         "waits for rcv FIN, state 2 waits for "
                                         "rcv ACK of FIN. With event names "
                                         "pinned the swap reads 'the peer's FIN "
                                         "arrived' as 'the peer acknowledged' -- "
                                         "a protocol error (TV 1.0 on the "
                                         "completion edges)"),
            "regenerate": "python -X utf8 examples/make_eventfsm_samples.py",
        },
    }


def build_group_swap_fixed():
    """The wait-state swap declaring semantics "fixed": refused (exit 1)."""
    g = build_group_swap()
    g["semantics"] = {"action": "fixed"}
    return g


def build_group_swap_relabel():
    """
    The SAME elements declaring semantics "relabel": admitted (exit 0).

    The default reading lets action names travel with the states, so the
    judge renames rcv FIN into rcv ACK of FIN and the swap passes. Side by
    side with the "fixed" file this is the two-readings table of
    docs/judge-semantics.md, made runnable.
    """
    g = build_group_swap()
    g["semantics"] = {"action": "relabel"}
    return g


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=here, help="target directory (default: this script's directory)")
    ap.add_argument("--check", action="store_true",
                    help="do not write; verify the committed files are byte-identical")
    args = ap.parse_args(argv)

    payloads = {
        "eventfsm_model.json": _dump(build_model()),
        "eventfsm_group_pads.json": _dump(build_group_pads()),
        "eventfsm_group_swap_fixed.json": _dump(build_group_swap_fixed()),
        "eventfsm_group_swap_relabel.json": _dump(build_group_swap_relabel()),
    }
    if args.check:
        bad = []
        for name, blob in payloads.items():
            p = os.path.join(here, name)
            with open(p, "r", encoding="utf-8", newline="") as f:
                current = f.read()
            if current != blob:
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
