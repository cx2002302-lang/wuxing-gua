# -*- coding: utf-8 -*-
"""
make_rung1d_explicit.py -- deterministic generator for the explicit-caliber
teaching sample (rung 1d)

Writes three files next to this script (byte-identical on every re-run;
nothing random, no clock, no locale dependence):

  rung1d_explicit_model.json        the 2x2 walker: 4 real cells on 4 bits
                                    (12 unreachable padding states fill the
                                    table up to 16 = 2**4, the power-of-two
                                    input contract), 4 direction actions,
                                    reward 1.0 for a move / 0.0 for a wall
                                    stay
  rung1d_explicit_group.json        the C4 board-rotation group declaring
                                    semantics "explicit" with per-element
                                    action_maps -- the true group, admitted
                                    by check (exit 0)
  rung1d_explicit_wrong_group.json  the SAME four elements with the direction
                                    keys pinned (semantics "fixed") -- the
                                    refusal control, rejected by check
                                    (exit 1)

The system (first principles, hand-derivable):

  A pawn on a 2x2 board. States 0..3 are the four cells (cell index
  c = 2*y + x, (x, y) = (column, row), x rightward, y downward:
  0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right). Four actions
  bound to board directions (0:up, 1:right, 2:down, 3:left); a move goes one
  cell in that direction, a wall leaves the pawn in place (deterministic
  self-loop). Reward 1.0 for a move that changes the cell, 0.0 for a wall
  stay. States 4..15 are unreachable padding (every action self-loops,
  reward 0); the group acts as the identity on padding.

  The board rotation rot90cw (x, y) -> (1 - y, x) is a symmetry of the
  walker ONLY together with the matching direction-key renaming: rotating
  the board clockwise turns the "up" key into the "right" key. Each group
  element therefore carries its OWN renaming, and no single renaming serves
  all four elements. That is exactly what the "explicit" caliber's
  per-element `action_maps` declaration states (docs/judge-semantics.md),
  and what the legacy single `action_map` field cannot express.

This script DERIVES everything from the transition table, never hardcodes
the answers:

  1. builds the 16x4 transition table from the geometry;
  2. derives the four state permutations from the rotation geometry;
  3. derives each element's action map by exhaustive search over the 24
     permutations of the 4 actions, requiring
        succ(pi(s), rho[a]) == pi(succ(s, a))  for ALL 16 states s, 4 actions a
     and asserts the solution is UNIQUE per element (the renaming is forced);
  4. asserts rho(id) = id and rho(rot90cw) != id;
  5. asserts the homomorphism law rho(pi2 o pi1) = rho2 o rho1 on every
     ordered pair of C4 elements (composition: apply pi1 first, then pi2);
  6. asserts the group closure is exactly the 4 powers of the rot90cw perm
     and computes the orbit structure (one 4-cycle on the real cells +
     12 fixed padding states = 13 orbits, compression 16/13);
  7. asserts the reward profile (multiset of (prob, reward)) is identical
     across the real orbit, so the reward layer alone can NOT refuse the
     pinned-key control -- the refusal comes from the transition layer.

Any assertion failure raises (loud). Writing is byte-stable; `--check`
re-verifies the byte identity of the committed files.

Usage (from the repository root or anywhere):

  python -X utf8 examples/make_rung1d_explicit.py            # write all three
  python -X utf8 examples/make_rung1d_explicit.py --out DIR  # write into DIR
  python -X utf8 examples/make_rung1d_explicit.py --check    # verify bytes
"""
import argparse
import itertools
import json
import os
import sys

N_BITS = 4
N_STATES = 1 << N_BITS          # 16 (4 real cells + 12 padding)
N_ACTIONS = 4
REAL_STATES = 4                 # states 0..3 = board cells
PAD_FIRST = REAL_STATES         # states 4..15 = padding
CELL_XY = [(0, 0), (1, 0), (0, 1), (1, 1)]
XY_CELL = {xy: i for i, xy in enumerate(CELL_XY)}
ACTION_NAMES = ["up", "right", "down", "left"]
VECTOR = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}

REWARD_MOVE = 1.0
REWARD_WALL = 0.0

REGEN = "python -X utf8 examples/make_rung1d_explicit.py"

# ------------------------------------------------------------- the walker
def step(cell, a):
    """One-cell move in direction a from cell; wall -> stay."""
    x, y = CELL_XY[cell]
    vx, vy = VECTOR[a]
    nx, ny = x + vx, y + vy
    if 0 <= nx < 2 and 0 <= ny < 2:
        return XY_CELL[(nx, ny)], True     # moved
    return cell, False                     # wall stay


def build_trans():
    """16 x 4 deterministic rows: [[prob, successor, reward], ...] per (s, a)."""
    trans = []
    for s in range(N_STATES):
        row = []
        for a in range(N_ACTIONS):
            if s >= PAD_FIRST:
                row.append([[1.0, s, 0.0]])          # padding self-loop
            else:
                u, moved = step(s, a)
                row.append([[1.0, u, REWARD_MOVE if moved else REWARD_WALL]])
        trans.append(row)
    return trans


def succ(s, a):
    return build_trans()[s][a][0][1]


# ----------------------------------------------------------- the rotation
def content_map_of(fn):
    """(x,y)->(x',y') board transform -> content map d: the content of cell
    c moves to cell d[c]."""
    return [XY_CELL[fn(x, y)] for (x, y) in CELL_XY]


def state_perm_of(d):
    """Content map d -> state permutation pi on all 16 states (padding fixed):
    the pawn at cell c moves to cell d[c]."""
    pi = list(range(N_STATES))
    for c in range(REAL_STATES):
        pi[c] = d[c]
    return pi


# C4 as (x, y) transforms of the square (rotation subgroup of D4).
C4_TRANSFORMS = [
    ("id",       lambda x, y: (x, y)),
    ("rot90cw",  lambda x, y: (1 - y, x)),
    ("rot180",   lambda x, y: (1 - x, 1 - y)),
    ("rot90ccw", lambda x, y: (y, 1 - x)),
]


def derive_action_map(pi):
    """Exhaustive search over the 24 action permutations for rho with
    succ(pi(s), rho[a]) == pi(succ(s, a)) for ALL 16 states, 4 actions.
    Returns the list of solutions (expected: exactly one)."""
    found = []
    for rho in itertools.permutations(range(N_ACTIONS)):
        ok = True
        for s in range(N_STATES):
            ps = pi[s]
            for a in range(N_ACTIONS):
                if succ(ps, rho[a]) != pi[succ(s, a)]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            found.append(list(rho))
    return found


def compose_perm(p2, p1):
    """Apply p1 first, then p2."""
    return [p2[i] for i in p1]


def compose_maps(rho2, rho1):
    """Same convention on action maps: apply rho1 first, then rho2."""
    return [rho2[a] for a in rho1]


def orbits_of(elements):
    parent = list(range(N_STATES))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in elements:
        for s in range(N_STATES):
            ra, rb = find(s), find(e[s])
            if ra != rb:
                parent[ra] = rb
    return len({find(x) for x in range(N_STATES)})


# ---------------------------------------------------------- certification
def derive():
    """Run the full first-principles derivation with loud asserts.
    Returns (table, elements, n_orbits)."""
    trans = build_trans()
    # model sanity: deterministic, probabilities 1, rewards in {0, 1},
    # padding self-loops everywhere
    for s in range(N_STATES):
        for a in range(N_ACTIONS):
            outs = trans[s][a]
            assert len(outs) == 1 and outs[0][0] == 1.0
            u, r = outs[0][1], outs[0][2]
            assert 0 <= u < N_STATES
            if s >= PAD_FIRST:
                assert u == s and r == 0.0
            else:
                assert r in (REWARD_WALL, REWARD_MOVE)
                assert (u != s) == (r == REWARD_MOVE)

    # per-element state perms from geometry
    table = {}
    for name, fn in C4_TRANSFORMS:
        d = content_map_of(fn)
        pi = state_perm_of(d)
        sols = derive_action_map(pi)
        assert len(sols) == 1, ("action map not unique", name, sols)
        table[name] = {"content_map": d, "state_perm": pi, "action_map": sols[0]}

    assert table["id"]["action_map"] == [0, 1, 2, 3]
    assert table["rot90cw"]["action_map"] != [0, 1, 2, 3]

    # C4 structure: rot180 / rot90ccw are the powers of rot90cw
    rot = table["rot90cw"]["state_perm"]
    assert compose_perm(rot, rot) == table["rot180"]["state_perm"]
    assert compose_perm(compose_perm(rot, rot), rot) == table["rot90ccw"]["state_perm"]

    # homomorphism law on every ordered pair: rho(pi2 o pi1) == rho2 o rho1
    names = [n for n, _ in C4_TRANSFORMS]
    for n1 in names:
        for n2 in names:
            comp = compose_perm(table[n2]["state_perm"], table[n1]["state_perm"])
            sols = derive_action_map(comp)
            assert len(sols) == 1 and sols[0] == \
                compose_maps(table[n2]["action_map"], table[n1]["action_map"]), \
                ("homomorphism broken", n1, n2, sols)

    elements = [table[n]["state_perm"] for n in names]
    assert len({tuple(e) for e in elements}) == 4

    n_orbits = orbits_of(elements)
    # one 4-cycle over the real cells + 12 fixed padding states
    seen = set()
    s = 0
    while s not in seen:
        seen.add(s)
        s = rot[s]
    assert seen == set(range(REAL_STATES)), seen
    assert n_orbits == 1 + (N_STATES - REAL_STATES), n_orbits

    # reward profile (multiset of (p, r)) identical across the real orbit:
    # the reward layer alone cannot refuse the pinned-key control
    def profile(s):
        return sorted((outs[0][0], outs[0][2]) for outs in trans[s])
    prof0 = profile(0)
    for s in range(1, REAL_STATES):
        assert profile(s) == prof0, (s, profile(s), prof0)

    return table, elements, n_orbits


# ---------------------------------------------------------------- files
def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def build_model(table, n_orbits):
    return {
        "n_bits": N_BITS,
        "n_actions": N_ACTIONS,
        "n_states": N_STATES,
        "goals": [],
        "meta": {
            "source_system": ("synthetic teaching model: a pawn on a 2x2 "
                              "board, one-cell moves in four board directions "
                              "(wall = stay), reward 1.0 for a move / 0.0 for "
                              "a wall stay"),
            "variant": "rung1d-explicit-walker",
            "state_encoding": ("states 0..3 = board cells, cell index "
                               "c = 2*y + x (0=top-left, 1=top-right, "
                               "2=bottom-left, 3=bottom-right); states 4..15 "
                               "= unreachable padding (every action self-loops, "
                               "reward 0), present because the model format "
                               "requires n_states = 2**n_bits and four actions "
                               "require n_bits >= 4"),
            "board_symmetry": ("rot90cw generates C4 = {id, rot90cw, rot180, "
                               "rot90ccw} on the four cells; the rotation is a "
                               "symmetry only together with the matching "
                               "direction-key renaming, which is forced per "
                               "element (each element's renaming is derived by "
                               "exhaustive search over the 24 permutations of "
                               "the 4 actions and asserted unique, and the "
                               "homomorphism law is asserted on all 16 ordered "
                               "pairs, by make_rung1d_explicit.py in this "
                               "directory)"),
            "per_element_action_maps": {
                name: {"content_map": table[name]["content_map"],
                       "state_perm": table[name]["state_perm"],
                       "action_map": table[name]["action_map"]}
                for name, _fn in C4_TRANSFORMS
            },
            "orbits_c4": n_orbits,
            "regenerate": REGEN,
        },
        "trans": build_trans(),
    }


def build_true_group(table, elements, n_orbits):
    """The true group: C4 with per-element forced renamings, declared
    explicit."""
    ids = [n for n, _ in C4_TRANSFORMS]
    return {
        "n_states": N_STATES,
        "elements": [list(e) for e in elements],
        "semantics": {
            "action": "explicit",
            "action_maps": [list(table[n]["action_map"]) for n in ids],
        },
        "meta": {
            "claim": ("the C4 board rotation of the rung 1d walker, each "
                      "element carrying its own forced direction-key renaming "
                      "(per-element action_maps, declared semantics explicit)"),
            "construction": ("C4 in order id, rot90cw, rot180, rot90ccw; "
                             "action_maps[i] is the exhaustive-search-derived "
                             "renaming of elements[i] (unique per element; "
                             "homomorphism law asserted on all 16 ordered "
                             "pairs by make_rung1d_explicit.py)"),
            "semantics_note": ("declared explicit: the renaming is part of "
                               "the claim -- rotating the board turns the up "
                               "key into the right key, so no single renaming "
                               "serves all four elements (the legacy single "
                               "action_map field cannot express this group; "
                               "docs/judge-semantics.md)"),
            "expected": ("admitted by check (exit 0); orbits of C4 on the 16 "
                         "states: one 4-cycle over the real cells + 12 fixed "
                         "padding states = %d; compression 16/%d"
                         % (n_orbits, n_orbits)),
            "regenerate": REGEN,
        },
    }


def build_wrong_group(table, elements, n_orbits):
    """The refusal control: the SAME four elements with the direction keys
    pinned (semantics fixed)."""
    return {
        "n_states": N_STATES,
        "elements": [list(e) for e in elements],
        "semantics": {
            "action": "fixed",
        },
        "meta": {
            "claim": ("the SAME four C4 rotation elements with the direction "
                      "keys pinned (declared semantics fixed) -- the refusal "
                      "control for rung 1d"),
            "why_fixed_refused": ("rotating the board turns the up key into "
                                  "the right key; with the key names pinned "
                                  "the rotated arrows do not line up -- e.g. "
                                  "under rot90cw the pawn's right arrow from "
                                  "cell 0 must land on cell 3, but the pinned "
                                  "right key at cell 1 (top-right) is a wall "
                                  "and stays put"),
            "expected": ("rejected by check (exit 1) on the transition layer; "
                         "the reward layer still passes (every cell has the "
                         "same reward profile: two wall stays at 0.0 and two "
                         "moves at 1.0), so the refusal comes from the arrows "
                         "alone; orbits and compression reading are the same "
                         "as the admitted file (%d orbits, 16/%d)"
                         % (n_orbits, n_orbits)),
            "regenerate": REGEN,
        },
    }


def payloads():
    table, elements, n_orbits = derive()
    return {
        "rung1d_explicit_model.json": _dump(build_model(table, n_orbits)),
        "rung1d_explicit_group.json":
            _dump(build_true_group(table, elements, n_orbits)),
        "rung1d_explicit_wrong_group.json":
            _dump(build_wrong_group(table, elements, n_orbits)),
    }


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=here,
                    help="target directory (default: this script's directory)")
    ap.add_argument("--check", action="store_true",
                    help="do not write; verify on-disk files are "
                         "byte-identical to a fresh regeneration")
    args = ap.parse_args(argv)

    ps = payloads()
    if args.check:
        bad = []
        for name, blob in sorted(ps.items()):
            p = os.path.join(args.out, name)
            with open(p, "r", encoding="utf-8", newline="") as f:
                current = f.read()
            if current != blob:
                bad.append(name)
        if bad:
            sys.stderr.write("byte-identity FAILED: %s\n" % ", ".join(bad))
            return 1
        sys.stdout.write("byte-identity OK: %s\n" % ", ".join(sorted(ps)))
        return 0

    for name, blob in sorted(ps.items()):
        p = os.path.join(args.out, name)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(blob)
        sys.stdout.write("wrote %s (%d bytes)\n"
                         % (p, len(blob.encode("utf-8"))))
    table, elements, n_orbits = derive()
    sys.stdout.write("derivation: " + " ".join(
        "%s=%s" % (n, table[n]["action_map"]) for n, _fn in C4_TRANSFORMS) + "\n")
    sys.stdout.write("orbits(C4) = %d, compression = 16/%d\n"
                     % (n_orbits, n_orbits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
