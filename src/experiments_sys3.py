# -*- coding: utf-8 -*-
"""
experiments_sys3.py —— SYS-3：鲁棒性 / 负向控制场景（自动发现会不会"谎报对称"）

为什么需要第三个场景：
  阶段 1 验收要 ≥3 个真实场景。SYS-1(D_n)、SYS-2(S_n) 都是"有对称"的正例。
  但计划里反复强调的诚实红线是：真实系统可能根本没有非平凡对称，
  框架必须敢说"没有 / 不许压"，否则压缩会引入错误。

本实验用同一套自动发现 + 廉价校验，在两类"非满对称"构造上验证：
  A 负向控制：目标 = 单个具体状态（打破所有对称）
               ⇒ 期望发现平凡群（阶 1，零压缩）；过大的群(D_n)喂给校验应被拒答
  B 部分对称：目标 = {位0=位1=1}（理论对称 = 自由位上的 S_{n-2} × 交换(0,1)）
               ⇒ 看自动发现能否恢复（完整性）；若不恢复，定位原因

并复用奖励剖面校验 + 等变检验做判真：
  · 把"发现的群"喂给 cheap_check ⇒ 应通过（真对称）
  · 把"过大的群"(D_n) 喂给 cheap_check ⇒ 应拒答（防止误用满对称）
  · 诊断：在 B 上统计搜索候选数 / 通过等变检验数 / 最差 equiv_error，
         确认"漏掉的是真对称、但伪自同构被拒"这一机制

运行：python src/experiments_sys3.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import build_model_n, orbits_of, group_dn  # noqa: E402
from experiments_p3 import (discover, backbone_adj, wl_refine,        # noqa: E402
                            equiv_error, graph_automorphisms,
                            graph_automorphisms_rr, closure_perms)
from experiments_p4 import cheap_check                               # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def swap_gen(NS, i, j):
    """坐标对换 (i<->j) 作为状态置换表"""
    pi = list(range(NS))
    for s in range(NS):
        a, b = (s >> i) & 1, (s >> j) & 1
        if a == 0 and b == 1:
            pi[s] = (s | (1 << i)) & ~(1 << j)
        elif a == 1 and b == 0:
            pi[s] = (s | (1 << j)) & ~(1 << i)
    return pi


def free_sym_gens(n):
    """
    目标={位0=位1=1} 时的**真对称群**生成元。

    2026-10-16 修正：此前只返回坐标置换生成元（S_{n-2} x S_2，阶 2*(n-2)!），
    **漏了一整类对称 —— 自由位上的 XOR 平移**。

    成因：`build_model_n` 的扰动是对所有位均匀翻转的
        for j in range(n): u = tt ^ (1 << j)
    使转移分布在「异或一个常数」下形状不变（(s^c)^(1<<a) = (s^(1<<a))^c）；
    而目标集 {位0=位1=1} 在**只翻自由位**的 XOR 下不变，奖励结构也随之不变。

    ⇒ 真群 = S_2 x S_{n-2} x (Z_2)^{n-2}，阶 2*(n-2)!*2^(n-2)
        n=6 → 768      n=8 → 92160
    有向骨干图丢失了 XOR 这一类对称，正是 SYS-3 B 搜不到东西的根因；
    `backbone_adj` 已于同日无向化，n=6 上完全恢复真群。
    """
    NS = 1 << n
    gens = [swap_gen(NS, 2, k) for k in range(3, n)]
    gens.append(swap_gen(NS, 0, 1))
    for j in range(2, n):                       # 自由位上的 XOR 平移
        gens.append([s ^ (1 << j) for s in range(NS)])
    return gens


def main():
    print("=" * 96)
    print("SYS-3 · 鲁棒性/负向控制：自动发现会不会在非满对称系统上谎报对称")
    print("=" * 96)
    out = {}

    for n in (6, 8):
        NS = 1 << n
        print("\n  ===== n = %d (NS=%d) =====" % (n, NS))

        # ---------- A 负向控制：单个具体状态 ⇒ 打破所有对称 ----------
        g_single = 0b101010 if n == 6 else 0b10101010
        goal_single = {g_single}
        tr_a = build_model_n(n, goal_single)
        Ga, _ = discover(tr_a, n, verbose=False)
        oa_a = orbits_of(Ga, NS)
        ok_a, _ = cheap_check(tr_a, goal_single, oa_a, n)
        Gdn = group_dn(n)
        odn = orbits_of(Gdn, NS)
        ok_dn, _ = cheap_check(tr_a, goal_single, odn, n)
        print("[A] 负向控制  目标=单状态 %s" % bin(g_single))
        print("    发现群阶=%d（期望 1）｜ 轨道=%d（期望 %d）" % (len(Ga), len(oa_a), NS))
        print("    奖励剖面校验·发现群：放行=%s（期望 T）｜ 过大 D_n：放行=%s（期望 F）"
              % (ok_a, ok_dn))
        out.setdefault("A", {})[n] = {"order": len(Ga), "orbits": len(oa_a),
                                      "check_found_pass": ok_a, "check_Dn_pass": ok_dn}

        # ---------- B 部分对称：{位0=位1=1} ⇒ 理论 S_{n-2}×S_2 ----------
        goal_partial = set(s for s in range(NS) if (s & 3) == 3)
        tr_b = build_model_n(n, goal_partial)
        Gb, _ = discover(tr_b, n, verbose=False)
        ob_b = orbits_of(Gb, NS)
        ok_b, _ = cheap_check(tr_b, goal_partial, ob_b, n)
        sg = free_sym_gens(n)
        sg_pass = all(equiv_error(tr_b, g, n)[0] <= 1e-9 for g in sg)
        Gexp = closure_perms(sg, NS)
        adj = backbone_adj(tr_b, n)
        color = wl_refine(adj)
        cands = (graph_automorphisms(adj, color, max_gens=48)
                 + graph_automorphisms_rr(adj, color, n_restarts=40, seed=7))

        # 候选的 equiv 分布：只看 worst 会被 inf 淹没，必须同时看 best / inf 占比
        errs = []
        n_inf = 0
        for g in cands:
            e, _ = equiv_error(tr_b, g, n)
            if e == float("inf"):
                n_inf += 1
            else:
                errs.append(e)
        errs.sort()
        n_pass = sum(1 for v in errs if v <= 1e-9)
        best_out = errs[0] if errs else None
        worst_out = errs[-1] if errs else None

        # 理论群元素是否真的落在搜索候选中（区分"没找到" vs "不在这空间里"）
        cand_set = set(tuple(g) for g in cands)
        n_hit_theory = sum(1 for g in Gexp if tuple(g) in cand_set)

        # ⚠️ 轨道数修正（2026-10-14 审计）：群作用非自由 ⇒ |X/G| ≠ NS/|G|。
        # 原写法 NS//expect_b 在 n=6 打印 1、n=8 打印 0，而真值是 15 / 21
        # （Burnside 交叉验算一致）。改用真轨道，并用 Burnside 交叉复核。
        expect_b = len(Gexp)
        ob_exp = orbits_of(Gexp, NS)
        burn = sum(1 for g in Gexp for x in range(NS) if g[x] == x) / len(Gexp)
        assert abs(burn - len(ob_exp)) < 1e-9, "轨道数与 Burnside 不一致"

        print("[B] 部分对称  目标={位0=位1=1}")
        print("    发现群阶=%d（期望 %d = S_2×S_{n-2}×(Z_2)^{n-2}）｜ 轨道=%d（真实期望 %d，Burnside 交叉 %.1f）"
              % (len(Gb), expect_b, len(ob_b), len(ob_exp), burn))
        print("    理论对称存在且过等变=%s（闭包阶 %d）｜ 搜索候选=%d｜ 通过等变=%d｜ 最差 equiv=%.3g"
              % (sg_pass, expect_b, len(cands), n_pass,
                 (errs[-1] if errs else float("inf"))))
        if errs:
            print("    候选分布：非坐标置换(inf)=%d ／ 有限误差=%d（最优 %.3g ～ 最差 %.3g）｜ 命中理论群 %d/%d"
                  % (n_inf, len(errs), best_out, worst_out, n_hit_theory, expect_b))
        else:
            print("    候选分布：**全部**为非坐标置换(inf)=%d ／ 有限误差 0 个"
                  "（即候选连''由坐标置换诱导''都不满足）｜ 命中理论群 %d/%d"
                  % (n_inf, n_hit_theory, expect_b))
        print("    奖励剖面校验·发现群：放行=%s（期望 T；保守不谎报）" % ok_b)
        out.setdefault("B", {})[n] = {"order_found": len(Gb), "expected_order": expect_b,
                                      "expected_orbits": len(ob_exp),
                                      "theory_sym_exists_pass": sg_pass,
                                      "n_candidates": len(cands), "n_pass_equiv": n_pass,
                                      "n_not_coord_perm": n_inf,
                                      "n_finite_err": len(errs),
                                      "best_equiv": best_out, "worst_equiv": worst_out,
                                      "n_hit_theory_in_cands": n_hit_theory,
                                      "check_found_pass": ok_b}

    with open(os.path.join(ROOT, "experiments_sys3.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_sys3.json")


if __name__ == "__main__":
    main()
