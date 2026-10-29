# -*- coding: utf-8 -*-
"""
experiments_p4.py —— 拒答能力：廉价的在线合法性校验器

前序模块攒的能力全是「怎么压缩」。但报告里最有价值的那行字是：**求解率从 100% 掉到 46.1%**。
一个只会说"可以"的工具会害人；一个敢说"这个不许用"的工具才值钱。

本模块把「不许」做成可计算的：不跑全 VI，只用**采样**估 V* 极差的上界并给置信区间。

**判据（事前定死）**
  ① 误通过率：100 个随机 MDP 上，不该用却放行的比例 < 1%
  ② 拒答代价：拒答带来的收益损失 ≤ 总收益的 10%
  ③ kill：在线校验成本与全 VI 同阶 ⇒ 无实用价值，降级为离线工具

**方法**
  全 VI 要 O(|S|²|A|)，在 2¹⁶ 状态上跑不动。这里用两个廉价代理：

  代理 A「同轨道回报差」：从每个轨道抽 k 个代表状态，各跑 m 条长度为 L 的
    随机策略 rollout，比较平均回报。若差异显著 ⇒ 该群在此奖励下不等变。
    （随机策略下 V^π 的差是 V* 差的上界代理：V* 差 ≤ 2·max|V^π 差| 之类，
     此处不依赖具体常数，只要求「V* 差 = 0 ⇒ V^π 差 = 0」这个方向。）

  代理 B「转移支撑差异」：对同轨道的 (s,t)，比较它们在各动作下的
    后继集合的 Jaccard 相似度。自同构要求支撑集在 π 下一一对应。

  两者都通过 ⇒ 放行；任一不通过 ⇒ 拒答，并给出理由。

  成本：O(轨道数 × k × m × L)，与 |S| 线性，远低于全 VI 的 O(|S|²)。

运行：python src/experiments_p4.py
"""
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import (tables, group_dn, orbits_of,   # noqa: E402
                            build_model_n, vi_n, expected_steps,
                            abstraction_loss, canonical_and_perm_n, qlearn_n)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

K_REP = 3          # 每轨道抽几个代表状态
M_ROLL = 40        # 每个代表跑几条 rollout
L_ROLL = 60        # rollout 长度
ALPHA = 0.05       # 显著性水平
N_RANDOM_MDP = 100 # 随机 MDP 个数（误通过率测试）


def cheap_check(trans, goals, orbits, n, seed=777, alpha=ALPHA):
    """
    廉价合法性校验：**奖励/转移在群下是否等变**（不跑 VI）。

    前两版的代理都失败过，记录在此以防再犯：
      · 代理「后继支撑 Jaccard」：用原始后继集比 —— 无分辨力。
        同轨道状态的后继集当然不同（它们是不同状态）；必须先用 canon 映射到
        轨道空间再比。而映射后两个环境都是 1.0000，因为 D_n 的**转移结构**
        本来就等变，与奖励无关。
      · 代理「随机策略回报差 + Welch t」：精确环境 t=3.26 也超阈值 ——
        rollout 方差太大，把信号淹了。
      · 本版代理「**奖励剖面**」：对每个状态 s，把 (概率, 奖励) 多重集按
        canon(u) 聚合，得到该状态的「奖励剖面」。群等变 ⟺ 同轨道状态的
        奖励剖面全同。实测：精确环境 178/178 全同；有损环境 173/178。
        ⚠️ 注意：这个代理需要已知 trans（不是纯采样数据），
        适用边界是「有模型、但跑不起全 VI」的场景。

    返回 (放行?, 诊断 dict)。
    """
    t0 = time.time()
    NS = len(trans)
    canon = {}
    for ob in orbits:
        for s in ob:
            canon[s] = min(ob)

    def profile(s):
        prof = []
        for a in range(n):
            agg = {}
            for (p, u, r) in trans[s][a]:
                k = canon.get(u, u)
                if k not in agg:
                    agg[k] = [0.0, set()]
                agg[k][0] += p
                agg[k][1].add(round(r, 9))
            prof.append(tuple(sorted((k, round(v[0], 9), tuple(sorted(v[1])))
                                     for k, v in agg.items())))
        return tuple(sorted(prof))

    prof = {s: profile(s) for s in range(NS)}
    n_bad = 0
    n_pair = 0
    for ob in orbits:
        for i in range(len(ob)):
            for j in range(i + 1, len(ob)):
                n_pair += 1
                if prof[ob[i]] != prof[ob[j]]:
                    n_bad += 1
    ok = (n_bad == 0)
    return ok, {"n_pair": n_pair, "n_bad": n_bad,
                "sec": time.time() - t0}


def main():
    print("=" * 96)
    print("廉价在线合法性校验器（不跑全 VI，只用采样）")
    print("  奖励剖面代理：按 canon 把 (概率, 奖励) 多重集聚合到轨道空间，"
          "群等变 ⟺ 同轨道奖励剖面全同")
    print("=" * 96)

    out = {}

    # ---------- ① 在已知答案的环境上验证方向 ----------
    print("\n  [1] 方向验证：已知「精确」与「有损」的环境，校验器应分别放行/拒答")
    cases = []
    for n in (6, 8):
        NS = 1 << n
        G = group_dn(n)
        od = orbits_of(G, NS)
        # 精确环境：目标全阳（D_n 等变）
        tr_ok = build_model_n(n, {NS - 1})
        # 有损环境：目标为非不动点
        tr_bad = build_model_n(n, {0b000111} if n == 6 else {0b000111})
        for (name, tr, expect) in (("精确（应放行）", tr_ok, True),
                                   ("有损（应拒答）", tr_bad, False)):
            t0 = time.time()
            V, _ = vi_n(tr, n, NS)
            l = abstraction_loss(V, od, NS)
            t_vi = time.time() - t0
            ok, diag = cheap_check(tr, {NS - 1} if expect else {0b000111},
                                   od, n)
            right = (ok == expect)
            cases.append({"n": n, "case": name, "expect": expect,
                          "vi_loss": l[0], "vi_sec": t_vi,
                          "cheap_ok": ok, "correct": right,
                          "cheap_diag": diag})
            print("      n=%d %-14s V*极差=%.6f（%s，VI %.2fs）｜ "
                  "廉价校验=%s（%s：剖面不同 %d/%d 对，%.2fs）"
                  % (n, name, l[0], "精确" if l[0] < 1e-9 else "有损", t_vi,
                     "放行 ✓" if ok else "拒答",
                     "✓判对" if right else "✗判错",
                     diag["n_bad"], diag["n_pair"], diag["sec"]))
    out["direction"] = cases

    # ---------- ② 误通过率：随机 MDP ----------
    print("\n  [2] 误通过率测试：%d 个随机 MDP（随机奖励 => 绝大多数应拒答）" % N_RANDOM_MDP)
    n = 6
    NS = 1 << n
    G = group_dn(n)
    od = orbits_of(G, NS)
    rng = random.Random(4242)
    n_pass, n_should_pass, false_pass = 0, 0, 0
    for i in range(N_RANDOM_MDP):
        # 随机奖励：给每个非目标状态一个随机 r（破坏对称性 => 应拒答）
        rmap = {s: rng.gauss(0, 1) for s in range(NS) if s != NS - 1}
        goals = {NS - 1}
        tr = build_model_n(n, goals)
        # 把奖励换成随机的（改 trans 里的 r）
        tr2 = [[None] * n for _ in range(NS)]
        for s in range(NS):
            if s in goals:
                tr2[s] = [[(1.0, s, 0.0)] for _ in range(n)]
                continue
            for a in range(n):
                lst = []
                for (p, u, _r) in tr[s][a]:
                    rr = 0.0 if u in goals else rmap.get(u, 0.0)
                    lst.append((p, u, rr))
                tr2[s][a] = lst
        V, _ = vi_n(tr2, n, NS)
        l = abstraction_loss(V, od, NS)
        should = (l[0] < 1e-9)          # 全 VI 的真值
        ok, diag = cheap_check(tr2, goals, od, n)
        n_pass += 1 if ok else 0
        n_should_pass += 1 if should else 0
        if ok and not should:
            false_pass += 1
    fp_rate = false_pass / max(1, N_RANDOM_MDP - n_should_pass)
    print("      应放行 %d / %d；实际放行 %d；**误通过 %d（占不该放行的 %.1f%%）**"
          % (n_should_pass, N_RANDOM_MDP, n_pass, false_pass, fp_rate * 100))
    print("      验收线 <1%%：%s" % ("✓ 达标" if fp_rate < 0.01 else "✗ 未达标"))
    out["false_pass"] = {"n": N_RANDOM_MDP, "should": n_should_pass,
                         "pass": n_pass, "false": false_pass,
                         "rate": fp_rate}

    with open(os.path.join(ROOT, "experiments_p4.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_p4.json")


if __name__ == "__main__":
    main()
