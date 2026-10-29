# -*- coding: utf-8 -*-
"""
experiments_restart_scan6.py —— 第六例 Heawood 图（真群 PGL(2,7)，阶 336）：非可解群的独立前瞻检验

与第五例（K_{n,n}，可解群 (S_n×S_n)⋊Z_2）及老族（可解群 S_k×S_{n-k}×(Z_2)^{n-k}）的区别：
  第六例换到**非可解群**——Heawood 图（Fano 平面点-线关联图）的自同构群
  Aut = PGL(2,7)，阶 q(q²−1) = 7·48 = 336，内含单群 PSL(2,7)（阶 168，指数 2）。
  它既不是 S_m（336 非阶乘），也不是 S_k×(Z_2)^m（336 = 2^m·k! 无解且非可解），
  也不是 (S_n×S_n)⋊Z_2（2(n!)² = 336 ⇒ (n!)² = 168 非平方）。

先验预测（运行前已锁定于预注册文档）：
  · 真群阶 336；点稳定子 S_4 阶 24；数据陷阱阶（§9.6 口径）= 保二分部子群
    PSL(2,7) = GL(3,2)，阶 168（指数 2，K_{n,n} 式「最后的坑」）
  · 168 ≤ 1,440 < T* ⇒ 判据预测【平台】；辅助预测逃逸 node_cap ∈ (5.5×10³, 1.2×10⁵]
    （168 × c，c ∈ [33, 694] 老族五例）；10^6 仍卡 168/24 ⇒ 判据上界被打破

实例选择说明：候选池的可行性判断（Petersen = S_5 违规否掉、环面真群不干净否掉、
Clebsch 双覆盖搜索病态否掉）与一次只验证「群阶一致性 + 单档耗时」的可行性探针，
均如实记录于预注册与可行性记录；预测数字不来自探针。

运行：python src/experiments_restart_scan6.py     # 产出 experiments_restart_scan6.json
"""
import itertools
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_p3 import (backbone_adj, closure_perms,  # noqa: E402
                            dist_of, graph_automorphisms,
                            graph_automorphisms_rr, tvd, wl_refine)
from experiments_restart_scan2 import closure_order  # noqa: E402
from experiments_restart_scan3 import (NO_CAP, first_branch_class,  # noqa: E402
                                       scan, trap_analysis)
from experiments_restart_scan5 import (abelianization_index,  # noqa: E402
                                       equiv_error_knn, fact,
                                       group_center, perm_inv,
                                       perm_sign, top_succ)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUT = os.path.join(ROOT, "experiments_restart_scan6.json")

P_PERT = 0.05
NS = 14                       # 7 个 Fano 点 + 7 条线
N_ACT = 3                     # 每个顶点 3 条关联边
CAPS = (100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000,
        64000, 128000, 256000, 1000000)          # 13 档，跨度 10^4 倍
T_START = time.time()

PTS = list(range(1, 8))       # F_2^3 的非零向量（Fano 平面的 7 个点）


# 运行前锁定的预测（预注册逐字在案，运行后不改）
PREDICTION = {
    "source": "预注册（先验预测，事前锁定）",
    "locked_before_run": True,
    "criterion": "硬顶 ⟺ 陷阱阶 ≥ T*，T* ∈ (1440, 5040]（10^6 预算刻度）",
    "instance": "Heawood 图 MDP（14 状态 / 3 动作），真群 PGL(2,7)",
    "true_order_formula": "|PGL(2,7)| = q(q²−1) = 7·48 = 336",
    "true_order": 336,
    "point_stabilizer_formula": "S_4，336/14 = 24",
    "point_stabilizer_order": 24,
    "trap_order_formula": "保二分部子群 PSL(2,7) = GL(3,2)，指数 2 ⇒ 168",
    "trap_order": 168,
    "verdict_label": "平台",
    "escape_cap_band": [5544, 116592],              # 168 × c，c ∈ [33, 694]
    "escape_cap_band_interval": "(5.5×10³, 1.2×10⁵]",
    "falsification_cap": 1000000,
    "falsification_note": ("若 10^6 档仍卡在 168（或 24）⇒ 硬顶且陷阱阶 ≤ 1,440 "
                            "⇒ 判据上界被打破（§9.6 证伪条件 2）"),
    "verbatim": (
        "预注册第六例 Heawood 图（真群 PGL(2,7) 阶 336，非可解；点稳定子 S_4 阶 24；"
        "数据陷阱阶预测 = 指数 2 的保二分部子群 PSL(2,7) 阶 168，K_{n,n} 式「最后的坑」）："
        "168 ≤ 1,440 ⇒ 判据预测【平台】，逃逸 node_cap ∈ (5.5×10³, 1.2×10⁵]；"
        "若 10^6 档仍卡在 168/24 ⇒ 硬顶且陷阱阶 ≤ 1,440 ⇒ 判据上界被打破。"),
}


# ---------------------------------------------------------------- Fano / Heawood 建模
def fano_lines():
    """Fano 平面 = PG(2,2)：点为 F_2^3 非零向量，线 = {w : v·w = 0}（法向量 v）"""
    def line_of(v):
        return tuple(sorted(w for w in PTS if bin(v & w).count("1") % 2 == 0))
    lines = [line_of(v) for v in PTS]
    assert len(set(lines)) == 7 and all(len(L) == 3 for L in lines), "Fano 线异常"
    return lines


def heawood_neighbors():
    """Heawood 图：点顶点 0..6，线顶点 7..13；返回每顶点 3 个邻居（有序）"""
    lines = fano_lines()
    idx = {p: i for i, p in enumerate(PTS)}
    nbrs = [[] for _ in range(NS)]
    for li, L in enumerate(lines):
        for p in L:
            nbrs[idx[p]].append(7 + li)
            nbrs[7 + li].append(idx[p])
    assert all(len(n) == 3 for n in nbrs), "Heawood 必须 3-正则"
    return nbrs, lines, idx


def build_heawood(p_pert=P_PERT):
    """Heawood 图上的 MDP：3 个动作 = 「沿第 a 条关联边跳到对侧顶点」

    P(目标) = (1−p) + p/3，其余两个邻点各 p/3。骨干图（每 (s,a) 取最大概率后继）
    恰为 Heawood 图。Aut(Heawood) 下等变（每顶点 3 邻点的扰动结构对称）。
    """
    nbrs, _lines, _idx = heawood_neighbors()
    trans = []
    for s in range(NS):
        row = []
        nb = nbrs[s]
        for a in range(N_ACT):
            d = [((1.0 - p_pert) + p_pert / N_ACT, nb[a], 1.0)]
            for b in range(N_ACT):
                if b != a:
                    d.append((p_pert / N_ACT, nb[b], 1.0))
            row.append(d)
        trans.append(row)
    return trans


# ---------------------------------------------------------------- F_2 上 3x3 矩阵工具
def vec_apply(M, v):
    r = 0
    for i in range(3):
        if (v >> i) & 1:
            for j in range(3):
                if M[i][j]:
                    r ^= (1 << j)
    return r


def mat_transpose(M):
    return [[M[j][i] for j in range(3)] for i in range(3)]


def mat_inv(M):
    """F_2 上高斯消元求逆"""
    A = [row[:] + [1 if i == j else 0 for j in range(3)] for i, row in enumerate(M)]
    for c in range(3):
        p = next(r for r in range(c, 3) if A[r][c])
        A[c], A[p] = A[p], A[c]
        for r in range(3):
            if r != c and A[r][c]:
                A[r] = [(A[r][k] + A[c][k]) % 2 for k in range(6)]
    return [row[3:] for row in A]


def gl32_gens():
    """GL(3,2) 的两个生成元：3-循环置换矩阵（阶 3）+ 对换（阶 2）"""
    cyc = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
    tr = [[1, 1, 0], [0, 1, 0], [0, 0, 1]]
    return [cyc, tr]


def lift(M, idx):
    """M ∈ GL(3,2) → Heawood 14 点置换：点 v ↦ Mv；线 L_v（法向量 v）↦ L_{M^{-T}v}"""
    MT = mat_transpose(mat_inv(M))
    g = list(range(NS))
    for p in PTS:
        g[idx[p]] = idx[vec_apply(M, p)]
    for v in PTS:
        g[7 + PTS.index(v)] = 7 + PTS.index(vec_apply(MT, v))
    return g


def duality(idx):
    """极性（对偶）：点 v ↔ 线 L_v，保关联 ⇒ 骨干图自同构，生成 Z_2"""
    g = list(range(NS))
    for v in PTS:
        g[idx[v]] = 7 + PTS.index(v)
        g[7 + PTS.index(v)] = idx[v]
    return g


def true_gens_heawood():
    _nbrs, _lines, idx = heawood_neighbors()
    return [lift(M, idx) for M in gl32_gens()] + [duality(idx)]


# ---------------------------------------------------------------- 结构判别工具
def commutator(a, b, NS):
    ia, ib = perm_inv(a), perm_inv(b)
    return [a[b[ia[ib[x]]]] for x in range(NS)]


def commutator_subgroup(gens, NS):
    """[⟨gens⟩, ⟨gens⟩] = 原始交换子在群中的**正规闭包**

    ⚠️ 方法论坑（本例实测）：只对生成元两两求交换子再闭包**不等于**换位子群——
    [x,y]（x,y 为任意群元素）是原始交换子的共轭之积，漏掉共轭会欠估。
    Heawood 生成元集上：原始交换子闭包仅 24，正规闭包 168（= 真换位子群 PSL(2,7)）。
    scan5 在 K_{n,n} 上用原始交换子恰好得真值 288（该生成元集上两者相等），
    但该方法不通用，故本例一律用正规闭包修正版。
    """
    comms = [commutator(gens[i], gens[j], NS)
             for i in range(len(gens)) for j in range(i + 1, len(gens))]
    seeds = list(comms)
    for s in gens:                                  # 用生成元共轭即覆盖全部共轭
        si = perm_inv(s)
        for c in comms:
            seeds.append([s[c[si[x]]] for x in range(NS)])
    return closure_perms(seeds, NS), seeds


def derived_series(gens, NS, max_steps=6):
    """导序列 [G,G], [[G,G],[G,G]], ... 的阶；不到 1 即非可解"""
    orders, cur = [], list(gens)
    for _ in range(max_steps):
        G = closure_perms(cur, NS)
        orders.append(len(G))
        if len(G) == 1:
            break
        H, seeds = commutator_subgroup(cur, NS)
        orders.append(len(H))
        if len(H) == len(G) or len(H) == 1:
            break
        cur = seeds
    return orders


def bruteforce_fano_auts():
    """暴力枚举 7! 个点置换，数保线系统的（= |Aut(Fano)| = |GL(3,2)| = 168）"""
    lines = set(fano_lines())
    cnt = 0
    for perm in itertools.permutations(range(7)):
        m = {PTS[i]: PTS[perm[i]] for i in range(7)}
        if all(tuple(sorted(m[w] for w in L)) in lines for L in lines):
            cnt += 1
    return cnt


def structure_evidence(trans, true_gens):
    """「不是 S_m / S_k×(Z_2)^m / (S_n×S_n)⋊Z_2」的可复算证据"""
    adj = backbone_adj(trans, N_ACT)
    color = wl_refine(adj)
    G = closure_perms(true_gens, NS)
    Gset = set(map(tuple, G))
    order = len(Gset)

    # (a) 阶不是阶乘
    lo_m, hi_m = None, None
    m = 1
    while fact(m) < order:
        m += 1
    hi_m, lo_m = m, m - 1

    # (b) 非本原：保持二分块系统 {点, 线}（2 块 × 7）
    blocks = [set(range(7)), set(range(7, NS))]
    preserves = all({g[s] for s in blocks[0]} in (blocks[0], blocks[1])
                    and {g[s] for s in blocks[1]} in (blocks[0], blocks[1])
                    for g in true_gens)

    # (c) 换位子群（正规闭包修正版）/ 阿贝尔化 / 中心
    comm_sub, _seeds = commutator_subgroup(true_gens, NS)
    comm_sub_set = set(map(tuple, comm_sub))
    ab_raw = abelianization_index(true_gens, NS)      # scan5 式原始交换子（对照用）

    # (d) 无固定点元素（老族 XOR 平移非单位元全无固定点；本例不构成子群）
    derangements = sum(1 for g in G if all(g[s] != s for s in range(NS)))

    # (e) 非可解：导序列
    der = derived_series(true_gens, NS)

    # (f) 两个 GL(3,2) 生成元单独即生成保二分部子群（阶 168）
    idx = {p: i for i, p in enumerate(PTS)}
    gl_only, _k = closure_order([lift(M, idx) for M in gl32_gens()], NS)

    # (g) 保二分部子群 / 点稳定子（从真群集合直接取，不猜）
    part_pres = [g for g in G if all(g[s] < 7 for s in range(7))]
    point_stab = [g for g in G if g[0] == 0]
    pp_set = set(map(tuple, part_pres))

    # (h) 等变检验（生成元全过 ⇒ 闭包必然全过，复合封闭；哨兵抽样防实现错误）
    top = top_succ(trans, N_ACT)
    worst = 0.0
    for g in true_gens:
        e, _c = equiv_error_knn(trans, g, N_ACT, top)
        worst = max(worst, e)
    sample = G[:64] + (G[len(G) // 2:len(G) // 2 + 64] if len(G) > 192 else [])
    worst2 = 0.0
    for g in sample:
        e, _c = equiv_error_knn(trans, g, N_ACT, top)
        worst2 = max(worst2, e)

    return {
        "NS": NS, "n_actions": N_ACT,
        "graph": "Heawood（Fano 点-线关联图，3-正则二部，21 边）",
        "order": order,
        "order_formula": "|PGL(2,7)| = q(q²−1) = 7·48 = %d" % order,
        "closure_matches_formula": order == 336,
        "not_factorial": {
            "order": order,
            "bracket": "%d! = %d < %d < %d = %d!"
                      % (lo_m, fact(lo_m), order, fact(hi_m), hi_m),
            "is_factorial": any(fact(k) == order for k in range(1, 25)),
        },
        "imprimitive": {
            "block_system": "2 块 × 7（Fano 点侧 / 线侧）",
            "generators_preserve_bipartition": preserves,
            "n_classes_wl": len(set(color.values())),
            "note": "S_14 在 14 点上本原；本群保持非平凡块系统 ⇒ 非对称群型",
        },
        "not_Sk_times_Z2m": {
            "order_has_no_2m_factorial_form": not any(
                order == (1 << mm) * fact(k)
                for mm in range(0, 12) for k in range(1, 12)),
            "non_solvable": der[-1] != 1,
            "derived_series_orders": der,
            "note": ("336 = 2^m·k! 无整数解；且导序列终止于 168（完满，= PSL(2,7)）不到 1 "
                     "⇒ 非可解，而 S_k×(Z_2)^m 可解 ⟺ k ≤ 4 且阶为 2^m·k!"),
        },
        "not_Sn_x_Sn_semidirect_Z2": {
            "equation": "2(n!)² = %d ⇒ (n!)² = %.1f" % (order, order / 2.0),
            "is_perfect_square": (lambda x: int(x) ** 2 == x)(order / 2.0),
            "note": "(n!)² 非完全平方 ⇒ 无整数 n",
        },
        "abelianization": {
            "corrected": {
                "commutator_subgroup_order": len(comm_sub_set),
                "equals_part_preserving_subgroup": comm_sub_set == pp_set,
                "abelianization_order": order // len(comm_sub_set),
                "abelianization_is_Z2": order // len(comm_sub_set) == 2,
            },
            "raw_commutators_only_scan5_style": {
                "commutator_subgroup_order": ab_raw["commutator_subgroup_order"],
                "abelianization_order": ab_raw["abelianization_order"],
                "note": ("scan5 式「生成元两两交换子直接闭包」在本生成元集上欠估"
                         "（24 ⊊ 真换位子群 168，漏共轭）；scan5 的 K_{n,n} 上两者"
                         "恰好相等（均 288 = 真换位子群），故 scan5 数字不受影响，"
                         "但该方法不通用，本例以正规闭包修正版为准"),
            },
            "note": ("|G^ab| = 2 ⇒ 若 G ≅ S_k×(Z_2)^m 则 2^{m+1} = 2 ⇒ m = 0 "
                     "⇒ G ≅ S_k ⇒ 阶应为阶乘，与 336 矛盾"),
        },
        "center_order": group_center(true_gens, NS),
        "no_xor_translation": {
            "fixed_point_free_elements": derangements,
            "contains_identity": False,
            "is_power_of_two": (derangements & (derangements - 1)) == 0,
            "note": ("老族 (Z_2)^{n-k} 直积因子的非单位元在 2^n 个状态上全部无固定点"
                     "（半正则、正规、个数为 2 的幂）；本群无固定点元素集合不含单位元，"
                     "不构成子群，且中心平凡 ⇒ 无 XOR 平移成分"),
        },
        "gl32_two_gens_closure_order": gl_only,
        "part_preserving_subgroup_order": len(part_pres),
        "point_stabilizer_order": len(point_stab),
        "bruteforce_fano_point_auts": bruteforce_fano_auts(),
        "bruteforce_graph_aut": ("NS=14 > 8，14! 过大未暴力；改用 Fano 点置换暴力 "
                                 "（7! = 5040）+ 二部双覆盖式分解："
                                 "保二分部 = Aut(Fano) = 168，换部陪集 = 168（极性非空）"
                                 " ⇒ |Aut| = 336"),
        "generators_pass_equivariance": (worst <= 1e-9),
        "sentinel_pass_equivariance": (worst2 <= 1e-9),
        "sentinel_n": len(sample),
        "worst_equivariance_error": max(worst, worst2),
    }


# ---------------------------------------------------------------- 等变 / 重启（Heawood 版）
def equiv_error_heawood(trans, pi, top=None):
    """与 p3.equiv_error 同语义，但不假设状态是超立方体（用骨干映射推动作像）

    与 scan5.equiv_error_knn 同构；scan5 版写死 NS = 2n（K_{n,n} 专用），
    Heawood 是 14 状态 / 3 动作，故本文件另写一份，只替换规模假设。
    """
    n = N_ACT
    if top is None:
        top = top_succ(trans, n)
    worst, checked = 0.0, 0
    for s in range(NS):
        ps = pi[s]
        for a in range(n):
            tgt = pi[top[s][a]]
            pa = None
            for b in range(n):
                if top[ps][b] == tgt:
                    pa = b
                    break
            if pa is None:
                return float("inf"), checked
            p1 = {pi[u]: v for u, v in dist_of(trans, s, a).items()}
            p2 = dist_of(trans, ps, pa)
            worst = max(worst, tvd(p1, p2))
            checked += 1
    return worst, checked


def discover_heawood(trans, tol=1e-9, seed=7):
    """Heawood 版 discover：确定性 + 随机重启 + 等变过滤 + 闭包 + 哨兵复检

    原版 p3.discover 的 equiv_error 用 s^(1<<a) 推动作像，只对 n 位翻转 MDP
    （状态 = 2^n）有意义；scan5.discover_knn 写死 NS = 2n。两者在本实例
    （14 状态 / 3 动作）均不适用，故另写同构流程，仅替换等变检验与规模假设。
    """
    adj = backbone_adj(trans, N_ACT)
    color = wl_refine(adj)
    top = top_succ(trans, N_ACT)
    gens = graph_automorphisms(adj, color, max_gens=48)
    n_det = len(gens)
    gens_rr = graph_automorphisms_rr(adj, color, n_restarts=40, seed=seed)
    gens = gens + gens_rr
    good, worst = [], 0.0
    for g in gens:
        e, _c = equiv_error_heawood(trans, g, top)
        worst = max(worst, e)
        if e <= tol:
            good.append(g)
    if not good:
        return [list(range(NS))], {"n_gens": len(gens), "n_pass": 0,
                                   "n_det": n_det, "n_rr": len(gens_rr),
                                   "worst_equiv": worst, "sentinel_ok": None}
    G = closure_perms(good, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _c = equiv_error_heawood(trans, g, top)
        worst2 = max(worst2, e)
    return G, {"n_gens": len(gens), "n_pass": len(good), "order": len(G),
               "n_det": n_det, "n_rr": len(gens_rr), "worst_equiv": worst2,
               "sentinel_ok": worst2 <= tol, "sentinel_n": len(sample)}


# ---------------------------------------------------------------- 受控扫描
def run_instance(caps=CAPS, run_discover=True):
    trans = build_heawood()
    true_gens = true_gens_heawood()
    true_order, kept_true = closure_order(true_gens, NS)

    s_true = set(map(tuple, closure_perms(kept_true, NS)))
    s_ps = set(g for g in s_true if g[0] == 0)                          # 点稳定子 24
    s_pp = set(g for g in s_true if all(g[s] < 7 for s in range(7)))    # 保二分部 168

    print("\n" + "=" * 96)
    print("[Heawood] NS=%d / %d 动作 ｜ 真群 Aut(Heawood) = PGL(2,7) ｜ 阶 %d"
          "（公式 q(q²−1) = 7·48）" % (NS, N_ACT, true_order))
    print("           点稳定子 S_4 阶 %d ｜ 保二分部子群 PSL(2,7)=GL(3,2) 阶 %d（指数 2）"
          % (len(s_ps), len(s_pp)))
    print("=" * 96)

    rows, adj, color, kepts = scan(trans, N_ACT, NS, caps)
    print("  %-10s %-9s %-12s %-9s %s" % ("node_cap", "生成元", "闭包阶", "耗时s", "较上一档"))
    prev = None
    for row in rows:
        if prev is None:
            change = "（基线）"
        elif row["closure_order"] > prev:
            change = "↑继续上升"
        else:
            change = "＝已停滞"
        print("  %-10d %-9d %-12d %-9.2f %s"
              % (row["node_cap"], row["n_gens"], row["closure_order"], row["sec"], change))
        prev = row["closure_order"]
    ck = [r for r in rows if "pruning_consistent" in r]
    if ck:
        print("  交叉校验（原版 closure_perms vs 剪枝版 closure_order）：%d 档，全部一致 = %s"
              % (len(ck), all(r["pruning_consistent"] for r in ck)))

    identities = []
    ps_caps, pp_caps = [], []
    for row, kept in zip(rows, kepts):
        obs = set(map(tuple, closure_perms(kept, NS)))
        info = {"node_cap": row["node_cap"], "order": len(obs),
                "equals_point_stabilizer": obs == s_ps,
                "equals_part_preserving": obs == s_pp,
                "equals_true_group": obs == s_true,
                "inside_true_group": len(obs & s_true),
                "inside_part_preserving": len(obs & s_pp),
                "index_in_true_group": (true_order // len(obs)
                                        if obs and true_order % len(obs) == 0 else None)}
        identities.append(info)
        if info["equals_point_stabilizer"]:
            ps_caps.append(info["node_cap"])
        if info["equals_part_preserving"]:
            pp_caps.append(info["node_cap"])
        print("  档 %-9d 阶 %-6d ==点稳定子(%d)? %s ｜ ==保二分部(%d)? %s ｜ ==真群(%d)? %s"
              % (info["node_cap"], info["order"], len(s_ps),
                 info["equals_point_stabilizer"], len(s_pp),
                 info["equals_part_preserving"], true_order,
                 info["equals_true_group"]))
    print("  点稳定子 %d 实际出现的档：%s" % (len(s_ps), ps_caps if ps_caps else "未出现"))
    print("  保二分部 %d 实际出现的档：%s" % (len(s_pp), pp_caps if pp_caps else "未出现"))

    ta = trap_analysis(rows, true_order)
    trap_rows = [r for r in rows if r["closure_order"] == ta.get("trap_order")]
    if len(trap_rows) >= 2:
        stall = {"from_cap": trap_rows[0]["node_cap"], "to_cap": trap_rows[-1]["node_cap"],
                 "cap_ratio": trap_rows[-1]["node_cap"] / trap_rows[0]["node_cap"],
                 "order_at_stall": ta["trap_order"],
                 "gens_from": trap_rows[0]["n_gens"], "gens_to": trap_rows[-1]["n_gens"],
                 "gens_still_grew": trap_rows[-1]["n_gens"] > trap_rows[0]["n_gens"]}
    else:
        stall = None

    top = rows[-1]["closure_order"]
    if ta.get("escaped"):
        verdict, label = "NOT_CAPPED", "平台"
        reason = ("陷阱阶 %d 形成平台后于 node_cap=%d 档逃逸到完整群 %d；未观察到硬顶"
                  % (ta["trap_order"], ta["escape_cap"], true_order))
        if stall:
            reason = ("陷阱阶 %d 在 node_cap %d → %d 间形成平台（生成元 %d → %d 虚增），"
                      "随后在 %d 档到达真群阶 %d；纯预算跨过平台，未形成硬顶。"
                      % (ta["trap_order"], stall["from_cap"], stall["to_cap"],
                         stall["gens_from"], stall["gens_to"], ta["escape_cap"],
                         true_order))
    elif rows[-1]["node_cap"] >= 1000000 and top < true_order:
        verdict, label = "CAPPED", "硬顶"
        reason = ("至 10^6 档仍停在 %d < 真群 %d" % (top, true_order))
        if stall:
            reason = ("预算 %d → %d（放大 %.1f 倍）闭包阶恒为 %d，同期生成元 %d → %d 虚增，"
                      "10^6 档仍未突破 ⇒ 硬顶在阶 %d 的真子群"
                      % (stall["from_cap"], stall["to_cap"], stall["cap_ratio"],
                         ta["trap_order"], stall["gens_from"], stall["gens_to"],
                         ta["trap_order"]))
    else:
        verdict, label = "INSUFFICIENT_DATA", "未观察"
        reason = ("顶档 %d 未达真群 %d 且未扫到 10^6 证伪档，数据不足"
                  % (rows[-1]["node_cap"], true_order))
        if top >= true_order:
            verdict, label = "NOT_CAPPED", "平台"
            reason = "顶档已到真群阶 %d，未观察到封顶" % true_order

    struct = first_branch_class(adj, color, NS)
    print("  陷阱阶 = %s ｜ 逃逸窗口 = (%s, %s] ｜ c = %s"
          % (ta.get("trap_order"), ta.get("trap_last_cap"), ta.get("escape_cap"),
             ta.get("c_band")))
    print("  首分支色类：大小 %s ｜ 内部边 %s ｜ 恒等分支固定节点 %s ｜ 色类总数 %s"
          % (struct["class_size"], struct["intra_edges"], struct["first_node"],
             struct["n_classes"]))

    restart = None
    if run_discover:
        print("  [对照] 确定性 + 随机重启（discover_heawood，同实例同数据）")
        t0 = time.time()
        G, diag = discover_heawood(trans)
        el = time.time() - t0
        restart = {"closure_order": len(G), "sec": round(el, 3),
                   "full": len(G) == true_order, "diag": dict(diag)}
        print("    闭包阶 = %d（真群 %d）｜ %.2fs" % (len(G), true_order, el))

    print("  [结论] %s（%s）：%s" % (verdict, label, reason))
    return {"instance": "Heawood 图（PGL(2,7)）", "NS": NS, "n_actions": N_ACT,
            "true_group": "Aut(Heawood) = PGL(2,7)",
            "true_order": true_order,
            "true_order_formula": "q(q²−1) = 7·48 = %d" % true_order,
            "point_stabilizer": "S_4", "point_stabilizer_order": len(s_ps),
            "part_preserving_subgroup": "PSL(2,7) = GL(3,2)（指数 2）",
            "part_preserving_order": len(s_pp),
            "caps": list(caps), "max_gens": NO_CAP,
            "point_stabilizer_plateau_caps": ps_caps,
            "part_preserving_plateau_caps": pp_caps,
            "scan": rows, "identities": identities, "stall_point": stall,
            "trap_analysis": ta, "first_branch_class": struct, "restart": restart,
            "verdict": verdict, "verdict_label": label, "verdict_reason": reason}


def compare(inst):
    """逐条对照预注册预测与实测（只读预测，不回写）"""
    p = PREDICTION
    ta = inst["trap_analysis"]
    trap = ta.get("trap_order")
    label = inst["verdict_label"]
    items = {
        "true_order": {"prediction": p["true_order"], "observed": inst["true_order"],
                       "hit": p["true_order"] == inst["true_order"]},
        "trap_order_data_defined": {
            "prediction": p["trap_order"],
            "observed": trap,
            "note": "§9.6 口径 max{闭包阶 < 真群阶}；预注册判其为指数 2 保二分部子群",
            "hit": p["trap_order"] == trap},
        "hard_cap_or_plateau": {"prediction": p["verdict_label"], "observed": label,
                                "hit": p["verdict_label"] == label},
    }
    lo, hi = p["escape_cap_band"]
    esc = ta.get("escape_cap")
    items["escape_cap_band"] = {
        "prediction": p["escape_cap_band_interval"], "observed_first_full_cap": esc,
        "observed_window": [ta.get("trap_last_cap"), esc],
        "hit": esc is not None and lo < esc <= hi}
    items["point_stabilizer_observed"] = {
        "prediction": "点稳定子阶 %d 会作为早期平台出现" % p["point_stabilizer_order"],
        "observed_caps": inst["point_stabilizer_plateau_caps"],
        "hit": bool(inst["point_stabilizer_plateau_caps"])}
    items["trap_identity_is_part_preserving"] = {
        "prediction": "数据陷阱 = 保二分部子群 PSL(2,7)（阶 168，指数 2），非点稳定子",
        "observed_caps": inst["part_preserving_plateau_caps"],
        "hit": bool(inst["part_preserving_plateau_caps"])
                and ta.get("trap_order") == inst["part_preserving_order"]}
    return items


def main():
    assert len(CAPS) >= 8
    assert CAPS[-1] / CAPS[0] >= 100
    assert 1000000 in CAPS

    print("=" * 96)
    print("第六例预注册验证：Heawood 图，真群 Aut(Heawood) = PGL(2,7)，阶 336（非可解）")
    print("预测已在运行前锁定：陷阱阶 168（指数 2 保二分部子群）≤ 1,440 ⇒ 平台")
    print("=" * 96)

    out = {"source": "src/experiments_restart_scan6.py",
           "purpose": "换结构族且换群种（非可解群 PGL(2,7)）独立检验 §9.6 的 T* 判据",
           "preregistration": PREDICTION,
           "scan_design": {"n_caps": len(CAPS), "min_cap": min(CAPS), "max_cap": max(CAPS),
                           "span_ratio": max(CAPS) / min(CAPS), "covers_1e6": True},
           "instance_selection_probe": {
               "used": True,
               "purpose": "只验证「公式 vs 构造闭包」一致性与单档耗时，不参与预测数字设定",
               "rejected_candidates": {
                   "Petersen 图": "Aut = S_5，违反「非 S_n」约束",
                   "环面 C_m×C_n": "真群阶对 (m,n) 敏感，双确认不干净",
                   "Clebsch 图二部双覆盖（阶 3840）":
                       "确定性搜索病态：node_cap 20 万仅 1 个生成元（A 部 16 点独立集剪枝极弱），"
                       "预算曲线退化，无法检验判据",
               },
               "note": "探针的 5 档曲线（1,000→24；10,000→168；100,000→336）与 §12.1 "
                       "预注册的结构预测一致，但预注册数字来自判据与 K_{n,n} 机制类比",
           },
           "instances": {}, "structure_evidence": {}, "comparison": {}}

    # ---------- 第 1 步：建模验证（真群阶闭包双确认 + 结构判别） ----------
    print("\n[1] 建模验证：真群阶 = |PGL(2,7)| = 336，且不是 S_m / S_k×(Z_2)^m / (S_n×S_n)⋊Z_2")
    trans = build_heawood()
    gens = true_gens_heawood()
    ev = structure_evidence(trans, gens)
    out["structure_evidence"]["heawood"] = ev
    print("  骨干图：%s ｜ 闭包阶 %d ｜ 公式 %s ｜ 一致 = %s"
          % (ev["graph"], ev["order"], ev["order_formula"], ev["closure_matches_formula"]))
    print("  非阶乘：%s" % ev["not_factorial"]["bracket"])
    print("  非本原：块系统 %s，生成元保持二分 = %s，WL 色类数 %s"
          % (ev["imprimitive"]["block_system"],
             ev["imprimitive"]["generators_preserve_bipartition"],
             ev["imprimitive"]["n_classes_wl"]))
    print("  非 S_k×(Z_2)^m：2^m·k! 形式无解 = %s ｜ 导序列 %s（非可解 = %s）"
          % (ev["not_Sk_times_Z2m"]["order_has_no_2m_factorial_form"],
             ev["not_Sk_times_Z2m"]["derived_series_orders"],
             ev["not_Sk_times_Z2m"]["non_solvable"]))
    print("  非 (S_n×S_n)⋊Z_2：%s ｜ 完全平方 = %s"
          % (ev["not_Sn_x_Sn_semidirect_Z2"]["equation"],
             ev["not_Sn_x_Sn_semidirect_Z2"]["is_perfect_square"]))
    print("  阿贝尔化 |G^ab| = %d（[G,G] 阶 %d = 保二分部子群? %s；原始交换子欠估至 %d）｜ |Z(G)| = %d"
          % (ev["abelianization"]["corrected"]["abelianization_order"],
             ev["abelianization"]["corrected"]["commutator_subgroup_order"],
             ev["abelianization"]["corrected"]["equals_part_preserving_subgroup"],
             ev["abelianization"]["raw_commutators_only_scan5_style"]["commutator_subgroup_order"],
             ev["center_order"]))
    print("  无固定点元素 %d 个（2 的幂? %s，含单位元? %s）"
          % (ev["no_xor_translation"]["fixed_point_free_elements"],
             ev["no_xor_translation"]["is_power_of_two"],
             ev["no_xor_translation"]["contains_identity"]))
    print("  GL(3,2) 两生成元单独闭包 = %d（预期 168）｜ 保二分部子群 = %d ｜ 点稳定子 = %d"
          % (ev["gl32_two_gens_closure_order"],
             ev["part_preserving_subgroup_order"], ev["point_stabilizer_order"]))
    print("  Fano 点置换暴力计数 = %d（预期 168）" % ev["bruteforce_fano_point_auts"])
    print("  生成元 %d 个 + 哨兵抽样 %d 个过等变检验：%s / %s（最大 TV 误差 %.2e）"
          % (len(gens), ev["sentinel_n"], ev["generators_pass_equivariance"],
             ev["sentinel_pass_equivariance"], ev["worst_equivariance_error"]))

    # ---------- 第 3 步：扫描 ----------
    print("\n[3] 受控扫描：max_gens 放开，只扫 node_cap")
    inst = run_instance(CAPS, run_discover=True)
    out["instances"]["heawood"] = inst
    out["comparison"]["heawood"] = compare(inst)

    # ---------- 原版 p3.discover 是否可用（如实记录） ----------
    try:
        from experiments_p3 import discover
        _G, _d = discover(trans, N_ACT)
        if len(_G) <= 1:
            out["legacy_discover"] = {
                "usable": False, "order": len(_G),
                "reason": ("未抛异常，但只返回平凡群（阶 1）：equiv_error 用 s^(1<<a) "
                           "推动作像，只对 n 位翻转 MDP（状态 = 2^n）有意义；"
                           "Heawood 是 14 状态 / 3 动作，位翻转推出的动作像无意义，"
                           "全部候选被等变检验判为 inf ⇒ 一个真对称都找不到。"
                           "scan5.discover_knn 又写死 NS = 2n。"
                           "本文件改用 discover_heawood（仅替换等变检验与规模假设，"
                           "其余流程：骨干图→WL→确定性→随机重启→等变过滤→闭包→哨兵复检，同构）。")}
        else:
            out["legacy_discover"] = {"usable": True, "order": len(_G)}
    except Exception as exc:
        out["legacy_discover"] = {
            "usable": False,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "reason": ("p3.discover 的 equiv_error 用 s^(1<<a) 推动作像，只对 n 位翻转 MDP "
                       "（状态 = 2^n）有意义；本实例状态空间不适用。"
                       "本文件改用 discover_heawood（仅替换等变检验，其余流程同构）。")}
    print("\n  原版 p3.discover 可用性：%s（返回阶 %s）"
          % (out["legacy_discover"].get("usable"), out["legacy_discover"].get("order")))

    # ---------- 总体结论（三选一，判定规则运行前即定） ----------
    hits = []
    for k, items in out["comparison"].items():
        hits += [v["hit"] for v in items.values()]
    n_hit = sum(1 for h in hits if h)
    label_pairs = {k: (PREDICTION["verdict_label"],
                       out["instances"][k]["verdict_label"])
                   for k in out["comparison"]}
    label_misses = [k for k, (p, o) in label_pairs.items() if p != o]
    if label_misses:
        result = "不成立"
        correction = ("判据的核心二分输出「硬顶/平台」被推翻（预测 %s，实测 %s）。"
                      % (label_pairs[label_misses[0]][0],
                         label_pairs[label_misses[0]][1]))
        if out["instances"]["heawood"]["verdict_label"] == "硬顶":
            correction += ("出现「陷阱阶 ≤ 1,440 却呈硬顶」的反例 ⇒ T* 的上界被打破"
                           "（§9.6 证伪条件 2）：该实例上 c 大了一个量级，"
                           "T* ∈ (1,440, 5,040] 不能跨族外推。")
        else:
            correction += "T* ∈ (1,440, 5,040] 不能跨族外推，必须纳入实例相关的 c 或结构变量。"
    elif n_hit == len(hits):
        result, correction = "成立", ("硬顶/平台标签与全部定量条目命中；"
                                      "T* ∈ (1,440, 5,040] 在非可解群族上再次成立"
                                      "（与 K_{n,n} 的推翻并存：判据的失效目前只见于"
                                      "K_{n,n} 一族，不是普遍现象）。")
    else:
        result, correction = ("部分成立",
                              "硬顶/平台标签命中，但陷阱阶 / 逃逸窗口的定量预测未中；"
                              "保留 T* 但须纳入结构变量（群型 / 块系统 / 状态数）。")
    out["overall"] = {"n_items": len(hits), "n_hit": n_hit, "result": result,
                      "label_predictions": label_pairs,
                      "correction_direction": correction}

    print("\n" + "=" * 96)
    print("逐条对照")
    print("=" * 96)
    for k, items in out["comparison"].items():
        print("  %s：" % k)
        for name, item in items.items():
            obs = item.get("observed", item.get("observed_first_full_cap",
                                                item.get("observed_caps")))
            print("    %-30s 命中=%s ｜ 预测=%s ｜ 实测=%s"
                  % (name, item["hit"], item["prediction"], obs))
    print("  判据：%s（%d/%d 命中）" % (result, n_hit, len(hits)))
    print("  修正方向：%s" % correction)
    print("  总耗时 %.1fs" % (time.time() - T_START))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_restart_scan6.json")


if __name__ == "__main__":
    main()
