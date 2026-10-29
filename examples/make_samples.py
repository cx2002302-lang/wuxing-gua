# -*- coding: utf-8 -*-
"""
make_samples.py -- deterministic trajectory generator for rung S, the
check-sample example in examples/README.md.

Simulates the black-box situation `check-sample` is built for: you do NOT have
the full transition table, only logged (state, action, next-state, reward)
tuples. The generator replays a committed model file through a uniform random
policy and writes one JSON array [s, a, u, r] per line.

Generation protocol (fully stated so every committed file can be re-derived):

  state     s : uniform over 0..n_states-1, drawn fresh for every step
  action    a : uniform over 0..n_actions-1
  successor u : sampled from trans[s][a]'s cumulative probabilities
                (every model in this directory is deterministic, so u is the
                row's successor; the protocol makes no use of that fact)
  reward    r : the reward attached to the sampled (s, a, u) transition
  RNG           random.Random(SEED), SEED = 20261028, consumed in exactly one
                order: per step -- s, then a, then the successor draw.

Deterministic: same seed + same n + same model = byte-identical file; no
clock, no locale. The committed 100-line file is the first 100 lines of the
10,000-line file (same seed, same stream: --n 100 reproduces it exactly).

The committed files (regenerate and compare with --check):

  samples_tiny_10000.jsonl   from sampling_tiny_model.json   (n=10000)
  samples_tiny_100.jsonl     from sampling_tiny_model.json   (n=100, its prefix)
  samples_ticketfsm_50000.jsonl   from ticketfsm_milestones_model.json (n=50000)

Usage (from the repository root):

  python -X utf8 examples/make_samples.py --n 10000 \
      --trans examples/sampling_tiny_model.json --out examples/samples_tiny_10000.jsonl
  python -X utf8 examples/make_samples.py --check   # verify all three committed files
"""
import argparse
import json
import os
import random
import sys

SEED_DEFAULT = 20261028
HERE = os.path.dirname(os.path.abspath(__file__))

# name -> (n_samples, model file, seed) for --check; all committed, all
# reproducible from the committed model files alone.
COMMITTED = {
    "samples_tiny_10000.jsonl": (10000, "sampling_tiny_model.json", SEED_DEFAULT),
    "samples_tiny_100.jsonl": (100, "sampling_tiny_model.json", SEED_DEFAULT),
    "samples_ticketfsm_50000.jsonl": (50000, "ticketfsm_milestones_model.json", SEED_DEFAULT),
}


def generate(trans, n_actions, n_samples, seed):
    """Uniform-random-policy replay; returns [(s, a, u, r), ...]."""
    rng = random.Random(seed)
    n_states = len(trans)
    out = []
    for _ in range(n_samples):
        s = rng.randrange(n_states)
        a = rng.randrange(n_actions)
        x = rng.random()
        u, r = trans[s][a][-1][1], trans[s][a][-1][2]
        for (p, uu, rr) in trans[s][a]:
            x -= p
            if x <= 0.0:
                u, r = uu, rr
                break
        out.append((s, a, u, r))
    return out


def render(samples):
    return "".join(json.dumps(list(t)) + "\n" for t in samples)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="deterministic trajectory generator for the check-sample example")
    ap.add_argument("--trans", default=os.path.join(HERE, "sampling_tiny_model.json"),
                    help="model.json to replay (default: the rung-S host model)")
    ap.add_argument("--n", type=int, default=None,
                    help="number of trajectory steps to generate")
    ap.add_argument("--seed", type=int, default=SEED_DEFAULT,
                    help="RNG seed (default %d)" % SEED_DEFAULT)
    ap.add_argument("--out", default=None, help="output .jsonl path")
    ap.add_argument("--check", action="store_true",
                    help="do not write; verify the three committed sample files "
                         "are byte-identical to a regeneration from the committed "
                         "model files")
    args = ap.parse_args(argv)

    if args.check:
        bad = []
        for name, (n, model_rel, seed) in sorted(COMMITTED.items()):
            with open(os.path.join(HERE, model_rel), encoding="utf-8") as f:
                model = json.load(f)
            blob = render(generate(model["trans"], model["n_actions"], n, seed))
            path = os.path.join(HERE, name)
            with open(path, "r", encoding="utf-8", newline="") as f:
                if f.read() != blob:
                    bad.append(name)
        if bad:
            sys.stderr.write("byte-identity FAILED: %s\n" % ", ".join(bad))
            return 1
        sys.stdout.write("byte-identity OK: %s\n" % ", ".join(sorted(COMMITTED)))
        return 0

    if args.n is None or args.out is None:
        ap.error("--n and --out are required unless --check is given")
    with open(args.trans, encoding="utf-8") as f:
        model = json.load(f)
    blob = render(generate(model["trans"], model["n_actions"], args.n, args.seed))
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        f.write(blob)
    sys.stdout.write("wrote %s (%d samples, seed %d)\n"
                     % (args.out, args.n, args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
