# -*- coding: utf-8 -*-
"""
experiments_e1.py —— 研究报告 §7.2 的 E1 追加对照：n 位上的轨道抽象

  原报告 Exp B 只在 n=6（64 态）上验证。E1 回答两个问题：
    Q1  状态压缩比随 n 线性增长（8x -> 14.2x -> 23.3x -> 33.6x）之后，
        样本效率增益是否随之增长，还是早早就饱和 / 倒转？
    Q2  §5.2 的核心规则「先用 V* 极差校验抽象合法性，非法就别用」在高维是否仍成立？

  环境：Q_n 超立方体。动作集 = 翻转一位（共 n 个，与 Exp B「仅爻变」口径一致），
        目标 = {2^n - 1}（全阳 / "乾"），
        扰动与 Exp B 完全相同：动作失效 10% + 随机爻动 12%，gamma = 0.95。
        奖励参数 R_GOAL / R_STEP / GAMMA 亦与 Exp B 一致，因此 n=6 一行应能复现原结果。

  运行：python src/experiments_e1.py smoke   # 秒级冒烟，验证正确性
        python src/experiments_e1.py std     # n=6/8/10 正式对照
        python src/experiments_e1.py big     # 追加 n=12
"""
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import closure   # compose / closure 已是 N 通用  # noqa: E402

# ---- 与 Exp B 严格一致的环境参数 -------------------------------------------
P_NOOP = 0.10        # 动作失效概率
P_PERT = 0.12        # 每步随机翻转一位的扰动概率
R_GOAL = 1.0
R_STEP = -0.02
GAMMA = 0.95
BETA_CB = 0.05

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ===========================================================================
# 1. n 位通用的位运算表
# ===========================================================================

_TAB = {}


def tables(n):
    """返回 (NS, mask, rot, rev, cmp)：
       rot = 循环左移 1 位；rev = 位倒序（综）；cmp = 逐位取反（错）"""
    if n in _TAB:
        return _TAB[n]
    NS = 1 << n
    mask = NS - 1
    rot = tuple((((s << 1) | (s >> (n - 1))) & mask) for s in range(NS))
    rev = []
    for s in range(NS):
        r = 0
        for j in range(n):
            if (s >> j) & 1:
                r |= 1 << (n - 1 - j)
        rev.append(r)
    cmp_ = tuple(s ^ mask for s in range(NS))
    t = (NS, mask, rot, tuple(rev), cmp_)
    _TAB[n] = t
    return t


def group_dn(n):
    """D_n = <循环移位, 倒序>，阶 2n（对角体旋转群作用在 n 个位上）"""
    NS, mask, rot, rev, cmp_ = tables(n)
    return closure([rot, rev])


def group_dnz2(n):
    """D_n x Z2 = <循环移位, 倒序, 取反>，阶 4n"""
    NS, mask, rot, rev, cmp_ = tables(n)
    return closure([rot, rev, cmp_])


def orbits_of(group, NS):
    """轨道划分（N 通用版）"""
    parent = list(range(NS))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for g in group:
        for x in range(NS):
            ra, rb = find(x), find(g[x])
            if ra != rb:
                parent[ra] = rb
    buckets = {}
    for x in range(NS):
        buckets.setdefault(find(x), []).append(x)
    return list(buckets.values())


def burnside(group, NS):
    return sum(1 for g in group for x in range(NS) if g[x] == x) / len(group)


def canonical_and_perm_n(group, n, NS):
    """
    对每个状态 s 返回 (canonical, invmap)：
      canonical = min{ g(s) : g in G }
      invmap    = 位置映射的逆，invmap[posmap[j]] = j
    与原报告 canonical_and_perm 语义一致，仅去掉 6 位硬编码。
    """
    gl = list(group)
    out = [None] * NS
    for s in range(NS):
        best, bg = None, None
        for g in gl:
            v = g[s]
            if best is None or v < best:
                best, bg = v, g
        base = bg[0]
        inv = [0] * n
        for j in range(n):
            inv[(bg[1 << j] ^ base).bit_length() - 1] = j
        out[s] = (best, inv)
    return out


# ===========================================================================
# 2. Q_n MDP 与规划
# ===========================================================================

def build_model_n(n, goals):
    """动作 0..n-1 = 翻转第 j 位。先判失效，再叠随机扰动。"""
    NS, mask, rot, rev, cmp_ = tables(n)
    trans = [[None] * n for _ in range(NS)]
    for s in range(NS):
        if s in goals:
            trans[s] = [[(1.0, s, 0.0)] for _ in range(n)]
            continue
        for a in range(n):
            t = s ^ (1 << a)
            lst = []
            for (pt, tt) in ((P_NOOP, s), (1 - P_NOOP, t)):
                r0 = R_GOAL if tt in goals else R_STEP
                for j in range(n):
                    u = tt ^ (1 << j)
                    lst.append((pt * P_PERT / n, u, R_GOAL if u in goals else R_STEP))
                lst.append((pt * (1 - P_PERT), tt, r0))
            trans[s][a] = lst
    return trans


def vi_n(trans, n, NS, gamma=GAMMA, iters=4000, tol=1e-10):
    V = [0.0] * NS
    for _ in range(iters):
        delta = 0.0
        newV = V[:]
        for s in range(NS):
            best = -1e18
            for lst in trans[s]:
                q = 0.0
                for (p, ns_, r) in lst:
                    q += p * (r + gamma * V[ns_])
                if q > best:
                    best = q
            newV[s] = best
            d = abs(newV[s] - V[s])
            if d > delta:
                delta = d
        V = newV
        if delta < tol:
            break
    pi = [max(range(n), key=lambda a: sum(p * (r + gamma * V[ns_])
                                         for (p, ns_, r) in trans[s][a]))
          for s in range(NS)]
    return V, pi


def expected_steps(trans, pi, goals, NS, iters=4000, tol=1e-10):
    V = [0.0] * NS
    for _ in range(iters):
        delta = 0.0
        newV = V[:]
        for s in range(NS):
            if s in goals:
                newV[s] = 0.0
                continue
            newV[s] = 1 + sum(p * V[ns_] for (p, ns_, _) in trans[s][pi[s]])
            d = abs(newV[s] - V[s])
            if d > delta:
                delta = d
        V = newV
        if delta < tol:
            break
    non = [s for s in range(NS) if s not in goals]
    return sum(V[s] for s in non) / len(non)


def abstraction_loss(V, orbits, NS):
    """同轨道内 V* 的极差。max=0 视为精确同态（可对商空间做无损 Q 学习）"""
    worst, tot = 0.0, 0.0
    for ob in orbits:
        vs = [V[s] for s in ob]
        d = max(vs) - min(vs)
        if d > worst:
            worst = d
        tot += d * len(ob)
    return worst, tot / NS


# ===========================================================================
# 3. Q 学习（抽象 / 非抽象）
# ===========================================================================

def qlearn_n(n, NS, goals, mode, group_info, seed, episodes=1200,
             horizon=40, eval_every=25, target_steps=None, eval_all=True,
             eval_seeds=(99991,), reward_fn=None, n_eval_starts=256):
    """
    mode: 'base'  | 'orbit'(D_n 抽象) | 'orbitZ2'(D_n x Z2 抽象) | 'count'
    抽象模式下 Q 表按轨道索引（Q 行 = 典型元），动作仍是 n 个抽象位，
    执行时通过逆位置映射还原为具体动作。
    """
    rng = random.Random(seed)
    rf = reward_fn
    na = n
    is_orbit = mode.startswith("orbit")
    gi = group_info if is_orbit else None
    Q = [[0.0] * na for _ in range(NS)]
    N = [[0] * na for _ in range(NS)]
    n_abs = len({v[0] for v in gi}) if is_orbit else NS

    def key(s):
        return gi[s][0] if is_orbit else s

    def concrete(s, aa):
        return gi[s][1][aa] if is_orbit else aa

    def step(s, aa, rr=None):
        rr = rr or rng
        if rr.random() < P_NOOP:
            t = s
        else:
            t = s ^ (1 << concrete(s, aa))
        if rr.random() < P_PERT:
            t = t ^ (1 << rr.randrange(n))
        r = rf(t) if rf else (R_GOAL if t in goals else R_STEP)
        return t, r, t in goals

    def greedy_steps(es=99991):
        """评估用给定的评估种子：不同方法用同一批评估流 => 可进行配对比较"""
        rr = random.Random(es)
        tot, ok, m = 0.0, 0, 0
        starts = range(NS) if eval_all else rng_eval_starts
        for s0 in starts:
            if s0 in goals:
                continue
            m += 1
            s, cnt = s0, 0
            while s not in goals and cnt < 200:
                k = key(s)
                aa = max(range(na), key=lambda j: Q[k][j])
                s, _, _ = step(s, aa, rr)
                cnt += 1
            tot += cnt
            if s in goals:
                ok += 1
        return tot / m, ok / m

    if not eval_all:
        # 必须无重复抽样：n_eval_starts > NS 时 randrange 会重复，
        # 使"平均步数"变成有偏加权（早期版本在 n=10 上真实踩到）
        rng_eval_starts = random.Random(7777).sample(
            range(NS), min(n_eval_starts, NS))

    first_ok = None
    curve = []
    for ep in range(episodes):
        eps = max(0.05, 0.5 * (0.998 ** ep))
        s = rng.randrange(NS)
        while s in goals:
            s = rng.randrange(NS)
        for _ in range(horizon):
            k = key(s)
            aa = rng.randrange(na) if rng.random() < eps else \
                max(range(na), key=lambda j: Q[k][j])
            ns_, r, done = step(s, aa)
            nk = key(ns_)
            bonus = BETA_CB / math.sqrt(N[k][aa] + 1) if mode == "count" else 0.0
            N[k][aa] += 1
            Q[k][aa] += 0.15 * (r + bonus + GAMMA * (0.0 if done else max(Q[nk]))
                                - Q[k][aa])
            s = ns_
            if done:
                break
        if (ep + 1) % eval_every == 0:
            st, sr = greedy_steps()
            curve.append((ep + 1, st, sr))
            if first_ok is None and target_steps is not None and st <= target_steps:
                first_ok = ep + 1
    st, sr = greedy_steps(eval_seeds[0])
    return {"n_abs": n_abs, "first_ok": first_ok if first_ok else episodes,
            "avg_steps": st, "solve_rate": sr, "curve": curve,
            "by_eseed": [greedy_steps(es)[0] for es in eval_seeds]}


# ===========================================================================
# 4. E1 主流程
# ===========================================================================

PLAN = {
    "smoke": [dict(n=6, seeds=1, episodes=200, eval_every=50,
                   methods=("base", "orbit", "orbitZ2", "count"))],
    "std": [dict(n=6, seeds=20, episodes=1200, eval_every=25,
                 methods=("base", "orbit", "orbitZ2", "count")),
            dict(n=8, seeds=10, episodes=2500, eval_every=50,
                 methods=("base", "orbit", "orbitZ2")),
            dict(n=10, seeds=10, episodes=5000, eval_every=100,
                 methods=("base", "orbit", "orbitZ2"))],
    # n=10 上 base 在 5000 ep 内未达标 -> 补跑长预算，去掉右删失
    "extend10": [dict(n=10, seeds=10, episodes=20000, eval_every=100,
                      methods=("base",))],
    "big": [dict(n=12, seeds=5, episodes=9000, eval_every=200, eval_all=False,
                 methods=("orbit",))],
}


def run_one(n, seeds, episodes, eval_every, eval_all=True, methods=("base",)):
    NS, mask, rot, rev, cmp_ = tables(n)
    goals = {mask}
    t0 = time.time()

    print("\n" + "=" * 88)
    print("E1 · n = %d   (|S| = 2^%d = %d)" % (n, n, NS))
    print("=" * 88)

    # ---- (1) 群与轨道：压缩比 ----------------------------------------------
    Gd = group_dn(n)
    Gd2 = group_dnz2(n)
    od = orbits_of(Gd, NS)
    od2 = orbits_of(Gd2, NS)
    bd, bd2 = burnside(Gd, NS), burnside(Gd2, NS)
    assert bd == len(od) and bd2 == len(od2), "Burnside 校验不通过"
    print("  [1] 群与压缩比")
    print("      %-12s %-8s %-10s %-12s" % ("群", "|G|", "轨道数", "压缩比"))
    print("      %-12s %-8d %-10d %.2fx" % ("D_%d" % n, len(Gd), len(od), NS / len(od)))
    print("      %-12s %-8d %-10d %.2fx" % ("D_%d x Z2" % n, len(Gd2), len(od2),
                                            NS / len(od2)))

    # ---- (2) 规划：V* 与抽象合法性（核心前置校验）---------------------------
    tr = build_model_n(n, goals)
    V, pi = vi_n(tr, n, NS)
    opt = expected_steps(tr, pi, goals, NS)
    ld = abstraction_loss(V, od, NS)
    ld2 = abstraction_loss(V, od2, NS)
    print("  [2] 抽象有效性前置校验（同轨道内 V* 极差）")
    print("      D_%d       max=%.6f  %s   mean=%.6f"
          % (n, ld[0], "精确 ✓" if ld[0] < 1e-9 else "有损 ✗", ld[1]))
    print("      D_%d x Z2  max=%.6f  %s   mean=%.6f"
          % (n, ld2[0], "精确 ✓" if ld2[0] < 1e-9 else "有损 ✗", ld2[1]))
    print("      最优策略期望步数 = %.3f" % opt)

    # ---- (3) 学习对照 -------------------------------------------------------
    info_d = canonical_and_perm_n(Gd, n, NS)
    info_d2 = canonical_and_perm_n(Gd2, n, NS)
    target = opt + 0.5
    print("  [3] 样本效率对照（target <= %.3f 步；%d seeds x %d ep）"
          % (target, seeds, episodes))
    print("      %-14s %-10s %-12s %-11s %-11s %-10s" %
          ("方法", "抽象状态数", "达标ep", "AUC步数", "最终步数", "求解率"))
    print("      %-14s %-10s %-12s %-11s %-11s %-10s" %
          ("(参考) 理论最优", "-", "-", "-", "%.3f" % opt, "-"))
    sub = {}
    for m in ["base", "orbit", "orbitZ2", "count"]:
        if m not in methods:
            continue
        if n >= 8 and m == "count":
            continue      # 无结构探索基线已在 n=6 处垫底，高维省算力
        f, aucs, sts, srs, ts = [], [], [], [], []
        for sd in range(seeds):
            t1 = time.time()
            r = qlearn_n(n, NS, goals, m, info_d2 if m == "orbitZ2" else info_d,
                         seed=2000 + sd, episodes=episodes, eval_every=eval_every,
                         target_steps=target, eval_all=eval_all)
            ts.append(time.time() - t1)
            f.append(r["first_ok"])
            sts.append(r["avg_steps"])
            srs.append(r["solve_rate"])
            cv = r["curve"]
            aucs.append(sum(x[1] for x in cv) / len(cv))
        sub[m] = {"n_abs": {"base": NS, "count": NS,
                            "orbit": len(od), "orbitZ2": len(od2)}[m],
                  "first": sum(f) / seeds, "auc": sum(aucs) / seeds,
                  "steps": sum(sts) / seeds, "solve": sum(srs) / seeds,
                  "sec": sum(ts) / seeds}
        print("      %-14s %-10d %-12.0f %-11.3f %-11.3f %-10.3f"
              % (m, sub[m]["n_abs"], sub[m]["first"], sub[m]["auc"],
                 sub[m]["steps"], sub[m]["solve"]))

    # 结论行
    if "orbit" in methods and "base" in methods:
        print("  [4] 小结：压缩 %.2fx -> 达标加速 %.2fx（耗时 %.1fs）"
              % (NS / len(od), sub["base"]["first"] / sub["orbit"]["first"],
                 time.time() - t0))
    else:
        print("  [4] 单方法补跑完成（耗时 %.1fs）" % (time.time() - t0))

    return {"n": n, "NS": NS, "group_order": [len(Gd), len(Gd2)],
            "orbits": [len(od), len(od2)],
            "loss": {"D": ld, "DZ2": ld2}, "opt": opt,
            "methods": sub, "seeds": seeds, "episodes": episodes,
            "sec": time.time() - t0}


EVAL_SEEDS = tuple(1000 + k for k in range(20))


def run_paired(n, seeds, episodes, eval_every=100):
    """
    配对检验：同一批遗传 rng 种子 x 同一批评估随机流下，
    比较 base 与 orbit 学到的策略质量差 (base 步数 - orbit 步数)。
    不配对时评估噪声 (std 0.12 @ n=6) 与效应量同阶，配对后可把噪声消掉。
    """
    import statistics
    NS, mask, _r, _v, _c = tables(n)
    goals = {mask}
    tr = build_model_n(n, goals)
    V, pi = vi_n(tr, n, NS)
    opt = expected_steps(tr, pi, goals, NS)
    info = canonical_and_perm_n(group_dn(n), n, NS)
    got = {}
    for m in ("base", "orbit"):
        cols = []
        for sd in range(seeds):
            r = qlearn_n(n, NS, goals, m, info, seed=2000 + sd, episodes=episodes,
                         eval_every=eval_every, eval_seeds=EVAL_SEEDS)
            cols.append(r["by_eseed"])
        got[m] = cols
    diffs = [got["base"][i][j] - got["orbit"][i][j]
             for i in range(seeds) for j in range(len(EVAL_SEEDS))]
    mean = statistics.mean(diffs)
    sd_ = statistics.stdev(diffs)
    se = sd_ / math.sqrt(len(diffs))
    print("\n" + "=" * 88)
    print("配对检验 · n = %d（%d 训练种子 x %d 评估流 = %d 个配对样本）"
          % (n, seeds, len(EVAL_SEEDS), len(diffs)))
    print("  理论最优 %.4f | base 均值 %.4f | orbit 均值 %.4f"
          % (opt, statistics.mean(got["base"][i][j]
                                  for i in range(seeds) for j in range(len(EVAL_SEEDS))),
             statistics.mean(got["orbit"][i][j]
                            for i in range(seeds) for j in range(len(EVAL_SEEDS)))))
    print("  配对差 (base - orbit) = %+.4f ± %.4f (SE)  t = %.2f  orbit 占优率 %.1f%%"
          % (mean, se, mean / se, 100.0 * sum(1 for d in diffs if d > 0) / len(diffs)))
    return {"n": n, "opt": opt, "diff": mean, "se": se, "t": mean / se,
            "win": sum(1 for d in diffs if d > 0) / len(diffs),
            "base": statistics.mean(got["base"][i][j] for i in range(seeds)
                                    for j in range(len(EVAL_SEEDS))),
            "orbit": statistics.mean(got["orbit"][i][j] for i in range(seeds)
                                     for j in range(len(EVAL_SEEDS)))}


def measure_eval_noise(n, n_streams=40):
    """
    评估噪声底：同一策略换 n_streams 条评估随机流，看"步数"读数抖多少。
    回答的是"最终步数"这一列到底有多大分辨率。
    """
    import statistics
    NS, mask, _r, _v, _c = tables(n)
    goals = {mask}
    tr = build_model_n(n, goals)
    V, pi = vi_n(tr, n, NS)
    opt = expected_steps(tr, pi, goals, NS)

    def roll(pi_, es):
        rr = random.Random(es)
        tot, m = 0.0, 0
        for s0 in range(NS):
            if s0 in goals:
                continue
            m += 1
            s, c = s0, 0
            while s not in goals and c < 200:
                t = s if rr.random() < P_NOOP else (s ^ (1 << pi_[s]))
                if rr.random() < P_PERT:
                    t = t ^ (1 << rr.randrange(n))
                s = t
                c += 1
            tot += c
        return tot / m

    fixed = roll(pi, 99991)
    many = [roll(pi, 1000 + k) for k in range(n_streams)]
    print("  n=%-3d 理论期望 opt=%.4f | 固定种子 99991=%.4f | %d 条流均值=%.4f | "
          "单次 std=%.4f"
          % (n, opt, fixed, n_streams, statistics.mean(many), statistics.stdev(many)))
    return {"n": n, "opt": round(opt, 4), "fixed": round(fixed, 4),
            "mean": round(statistics.mean(many), 4),
            "std": round(statistics.stdev(many), 4), "streams": n_streams}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"
    if mode == "noise":
        out = {"n6": measure_eval_noise(6), "n8": measure_eval_noise(8),
               "n10": measure_eval_noise(10)}
        with open(os.path.join(ROOT, "experiments_e1_noise.json"), "w",
                  encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("\n评估噪声底已写入 experiments_e1_noise.json")
        return
    if mode == "paired":
        out = {"n6": run_paired(6, 20, 1200, 25),
               "n8": run_paired(8, 10, 2500, 50),
               "n10": run_paired(10, 10, 5000, 100)}
        with open(os.path.join(ROOT, "experiments_e1_paired.json"), "w",
                  encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("\n配对检验结果已写入 experiments_e1_paired.json")
        return
    plan = PLAN.get(mode, PLAN["std"])
    results = {}
    t0 = time.time()
    print("\n" + "#" * 88)
    print("# E1 —— n 位轨道抽象的可扩展性对照（报告 §7.2 E1）")
    print("# 环境 Q_n 超立方体 / 动作=翻转一位 / 目标=全阳 / 扰动=失效10%+爻动12%")
    print("#" * 88)
    for cfg in plan:
        r = run_one(**cfg)
        results["n%d" % cfg["n"]] = r
        with open(os.path.join(ROOT, "experiments_e1_%s.json" % mode), "w",
                  encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
    print("\n总计耗时 %.1fs，结果已写入 experiments_e1_%s.json" % (time.time() - t0, mode))


if __name__ == "__main__":
    main()
