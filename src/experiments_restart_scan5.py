# -*- coding: utf-8 -*-
"""
experiments_restart_scan5.py —— 第五例 K_{n,n}：换结构族的前瞻预注册检验

与前四例的区别（本例存在的全部理由）：
  前四例（Q_8 / SYS-3 B / (7,3) / Q_7）全部来自同一族 —— n 位翻转 MDP 的 (n,k) 目标集，
  真群形如 S_k × S_{n-k} × (Z_2)^{n-k}（含 XOR 平移成分）。§9.6 的判据
  「硬顶 ⟺ 陷阱阶 ≥ T*，T* ∈ (1,440, 5,040]」可能只是这一族的性质。
  本例换到完全二分图 K_{n,n}：真群 Aut(K_{n,n}) = (S_n × S_n) ⋊ Z_2，阶 2·(n!)²，
  **既不是 S_m，也没有 (Z_2)^m 平移直积因子**（判别证据见 structure_evidence 一节实测）。

先验预测（运行前已锁定于预注册文档）：
  · n=4：真群 2·(4!)² = 1,152；陷阱 = 点稳定子 (4-1)!·4! = 144 ≤ 1,440 ⇒ 预测【平台】
  · n=5：真群 2·(5!)² = 28,800；陷阱 = 4!·5! = 2,880 ∈ (1,440, 5,040] ⇒ 预测【硬顶】

运行：python src/experiments_restart_scan5.py
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_p3 import (backbone_adj, closure_perms, discover,  # noqa: E402
                            dist_of, graph_automorphisms,
                            graph_automorphisms_rr, tvd, wl_refine)
from experiments_restart_scan2 import closure_order  # noqa: E402
from experiments_restart_scan3 import (NO_CAP, first_branch_class,  # noqa: E402
                                       trap_analysis)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTPUT = os.path.join(ROOT, "experiments_restart_scan5.json")

P_PERT = 0.05
CAPS = (100, 250, 500, 1000, 2000, 4000, 8000, 16000, 64000, 250000, 1000000)
N6_CAPS = (1000, 8000, 64000)
T_START = time.time()
N6_TIME_GATE = 900.0      # 已耗时超过此值（秒）就砍掉 n=6
TOTAL_BUDGET = 1500.0     # 单任务 25 分钟硬上限

# 运行前锁定的预测（预注册逐字在案，运行后不改）
PREDICTION = {
    "source": "预注册（先验预测，事前锁定）",
    "locked_before_run": True,
    "criterion": "硬顶 ⟺ 陷阱阶 ≥ T*，T* ∈ (1440, 5040]（10^6 预算刻度）",
    "instances": {
        "n=4": {
            "true_order_formula": "2·(4!)² = 1152",
            "true_order": 1152,
            "trap_order_formula": "(4-1)!·4! = 144",
            "trap_order": 144,
            "verdict_label": "平台",
            "escape_cap_band": [4752, 99936],          # 144 × c，c ∈ [33, 694]
            "escape_cap_band_interval": "(4.8×10³, 1.0×10⁵]",
            "falsification_cap": 1000000,
        },
        "n=5": {
            "true_order_formula": "2·(5!)² = 28800",
            "true_order": 28800,
            "trap_order_formula": "4!·5! = 2880",
            "trap_order": 2880,
            "verdict_label": "硬顶",
            "escape_cap_band": None,
            "escape_cap_band_interval": "不适用（预测不逃逸）",
            "falsification_cap": 1000000,
            "falsification_note": "若 10^6 档已到达 28,800 ⇒ 出现「陷阱阶 ∈(1440,5040] 却呈平台」"
                                  " ⇒ 判据上界被打破。",
        },
    },
    "verbatim": (
        "预注册第五例 K_{n,n}（真群 Aut(K_{n,n}) = (S_n × S_n) ⋊ Z_2，阶 2·(n!)²，"
        "点稳定子阶 (n-1)!·n!）：n=4 陷阱 144 ≤ 1,440，预测平台，逃逸 node_cap ∈ "
        "(4.8×10³, 1.0×10⁵]；n=5 陷阱 2,880 ∈ (1,440, 5,040]，预测硬顶，"
        "若 10^6 档仍卡在 2,880 则判据再得一个正例，若已逃逸则判据上界被打破。"
    ),
}


# ---------------------------------------------------------------- MDP 建模
def build_knn(n, p_pert=P_PERT):
    """K_{n,n} 上的 MDP：状态 s = side*n + idx（共 2n 个）

    动作 a = j：「跳到对侧第 j 个点」。
      P((1-side)*n + j | s, j) = (1 - P_PERT) + P_PERT/n
      P((1-side)*n + j' | s, j) = P_PERT/n            (j' ≠ j)
    骨干图（每个 (s,a) 取概率最大的后继）恰好是完全二分图 K_{n,n}：
    每个点连到对侧全部 n 个点，同侧 0 条边、无自环。
    """
    NS = 2 * n
    trans = []
    for s in range(NS):
        side, _idx = divmod(s, n)
        row = []
        for j in range(n):
            d = [((1.0 - p_pert) + p_pert / n, (1 - side) * n + j, 1.0)]
            for jp in range(n):
                if jp != j:
                    d.append((p_pert / n, (1 - side) * n + jp, 1.0))
            row.append(d)
        trans.append(row)
    return trans


def top_succ(trans, n):
    """骨干映射 f(s,a) = argmax P(·|s,a)"""
    NS = len(trans)
    return [[max(trans[s][a], key=lambda x: x[0])[1] for a in range(n)]
            for s in range(NS)]


def swap_states(NS, i, j):
    g = list(range(NS))
    g[i], g[j] = g[j], g[i]
    return g


def true_gens_knn(n):
    """Aut(K_{n,n}) = (S_n × S_n) ⋊ Z_2 的生成元

    同侧相邻对换 ×2（各 n-1 个，生成 S_n × S_n）+ 侧交换（1 个，生成 Z_2）。
    """
    NS = 2 * n
    gens = [swap_states(NS, i, i + 1) for i in range(0, n - 1)]        # 侧 0 内 S_n
    gens += [swap_states(NS, n + i, n + i + 1) for i in range(n - 1)]  # 侧 1 内 S_n
    gens += [[(s + n) % NS for s in range(NS)]]                        # 侧交换 (side,idx)->(1-side,idx)
    return gens


def trap_gens_knn(n):
    """点稳定子（固定状态 0 = 侧 0 的第 0 个点）= S_{n-1} × S_n，阶 (n-1)!·n!"""
    NS = 2 * n
    gens = [swap_states(NS, i, i + 1) for i in range(1, n - 1)]        # 侧 0 内固定 0：S_{n-1}
    gens += [swap_states(NS, n + i, n + i + 1) for i in range(n - 1)]  # 侧 1 内 S_n
    return gens


def fact(m):
    r = 1
    for i in range(2, m + 1):
        r *= i
    return r


# ---------------------------------------------------------------- 等变检验（K_{n,n} 版）
def equiv_error_knn(trans, pi, n, top=None):
    """与 p3.equiv_error 同语义的检验，但不假设状态是超立方体 / 动作是位翻转

    p3 原版用 `pi[s ^ (1<<a)] ^ pi[s]` 推动作像，只对 n 位翻转 MDP 有意义；
    K_{n,n} 的状态是 2n 个点的二部图，必须用骨干映射 f 推：
    要求 π(f(s,a)) = f(π(s), a')，a' 即动作 a 在 π 下的像（允许随 s 变，与原版一致）。
    """
    NS = len(pi)
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


def discover_knn(trans, n, tol=1e-9, seed=7):
    """K_{n,n} 版的 discover：确定性 + 随机重启 + 等变过滤 + 闭包 + 哨兵复检

    原版 p3.discover 直接调 equiv_error，在 2n 状态空间上会越界（s^(1<<a) ≥ 2n），
    故本文件另写一份，仅替换等变检验，其余（骨干图→WL→确定性→重启→闭包→哨兵）同构。
    """
    NS = 2 * n
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)
    top = top_succ(trans, n)
    gens = graph_automorphisms(adj, color, max_gens=48)
    n_det = len(gens)
    gens_rr = graph_automorphisms_rr(adj, color, n_restarts=40, seed=seed)
    gens = gens + gens_rr
    good, worst = [], 0.0
    for g in gens:
        e, _c = equiv_error_knn(trans, g, n, top)
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
        e, _c = equiv_error_knn(trans, g, n, top)
        worst2 = max(worst2, e)
    return G, {"n_gens": len(gens), "n_pass": len(good), "order": len(G),
               "n_det": n_det, "n_rr": len(gens_rr), "worst_equiv": worst2,
               "sentinel_ok": worst2 <= tol, "sentinel_n": len(sample)}


# ---------------------------------------------------------------- 结构判别：为什么不是 S_m / S_k×(Z_2)^m
def perm_sign(g):
    NS = len(g)
    seen = [False] * NS
    s = 0
    for i in range(NS):
        if not seen[i]:
            L = 0
            j = i
            while not seen[j]:
                seen[j] = True
                j = g[j]
                L += 1
            s += L - 1
    return -1 if (s % 2) else 1


def perm_inv(g):
    inv = [0] * len(g)
    for i, x in enumerate(g):
        inv[x] = i
    return inv


def abelianization_index(gens, NS):
    """G^{ab} 的阶 = |G| / |[G,G]|

    做法：取生成元两两交换子，闭包得 H ⊆ [G,G]；若 H 恰好等于 G 中全体偶置换
    （[G,G] ⊆ G∩A_NS 恒成立），则 [G,G] = G∩A_NS，指数即 |G^{ab}|。
    """
    G = closure_perms(gens, NS)
    Gset = set(map(tuple, G))
    comms = []
    for i in range(len(gens)):
        for j in range(i + 1, len(gens)):
            a, b = gens[i], gens[j]
            ia, ib = perm_inv(a), perm_inv(b)
            comms.append([a[b[ia[ib[x]]]] for x in range(NS)])
    H = closure_perms(comms, NS)
    Hset = set(map(tuple, H))
    even = sum(1 for t in Gset if perm_sign(list(t)) == 1)
    return {"group_order": len(Gset),
            "commutator_subgroup_order": len(Hset),
            "even_elements_in_G": even,
            "commutator_equals_even_subgroup": (Hset == set(
                t for t in Gset if perm_sign(list(t)) == 1)),
            "abelianization_order": len(Gset) // len(Hset),
            "abelianization_is_Z2": len(Gset) // len(Hset) == 2}


def group_center(gens, NS):
    """|Z(G)|：与所有生成元都交换的元素个数"""
    G = closure_perms(gens, NS)
    cnt = 0
    for g in G:
        if all([g[gg[x]] for x in range(NS)] == [gg[g[x]] for x in range(NS)]
               for gg in gens):
            cnt += 1
    return cnt


def old_family_abelianization():
    """对照组：老族（实例3 的生成元，NS=128）的阿贝尔化 + XOR 平移子群，用于横向对比

    只导入 scan3 的生成元构造函数，不修改 scan3 任何代码。
    """
    from experiments_restart_scan3 import partial_sym_gens
    gens = partial_sym_gens(7, 3)
    ab = abelianization_index(gens, 128)
    xor_gens = gens[2 + 3:]                      # 4 个自由位 XOR 生成元
    N = closure_perms(xor_gens, 128)
    Nset = set(map(tuple, N))
    normal = True
    for g in gens:
        gi = perm_inv(g)
        for h in N:
            if tuple([g[h[gi[x]]] for x in range(128)]) not in Nset:
                normal = False
                break
        if not normal:
            break
    nonid_fpf = sum(1 for h in N if h != list(range(128))
                    and all(h[s] != s for s in range(128)))
    return {"group": "实例3生成元（老族，7 位 / k=3，含自由位 XOR 平移）",
            "group_order": ab["group_order"],
            "abelianization_order": ab["abelianization_order"],
            "xor_subgroup_order": len(Nset),
            "xor_subgroup_is_normal_in_G": normal,
            "xor_subgroup_nonidentity_fixed_point_free": nonid_fpf,
            "xor_subgroup_nonidentity_total": len(Nset) - 1,
            "interpretation": (
                "老族确有「平移型」成分：自由位 XOR 生成元生成一个正规子群（阶 %d），"
                "其全部 %d 个非单位元在 128 个状态上无固定点（半正则）。"
                "K_{n,n} 群没有这种子群（见 no_xor_translation / center）。"
                % (len(Nset), len(Nset) - 1))}


def graph_aut_order_bruteforce(adj, NS):
    """暴力枚举 NS! 个置换，数骨干图自同构（只用于 n=4 这类可枚举规模）"""
    import itertools
    cnt = 0
    for p in itertools.permutations(range(NS)):
        ok = True
        for s in range(NS):
            ps = p[s]
            for t in adj[s]:
                if p[t] not in adj[ps]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            cnt += 1
    return cnt


def structure_evidence(n, trans, true_gens):
    """给出「不是 S_m、也不是 S_k×(Z_2)^m」的可复算证据"""
    NS = 2 * n
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)
    order = len(closure_perms(true_gens, NS))

    # (a) 阶不是阶乘：夹在两个相邻阶乘之间
    lo_m, hi_m = None, None
    m = 1
    while fact(m) < order:
        m += 1
    hi_m, lo_m = m, m - 1

    # (b) 非本原：保持二分块系统 {侧0, 侧1}（2 块 × n）
    blocks = [set(range(n)), set(range(n, NS))]
    preserves_bipartition = True
    for g in true_gens:
        if not ({g[s] for s in blocks[0]} in (blocks[0], blocks[1])):
            preserves_bipartition = False
    intra = sum(1 for s in range(n) for t in adj[s] if t >= n)   # 跨侧边
    side0_intra = sum(1 for s in range(n) for t in adj[s] if t < n)

    # (c) 无 (Z_2)^m 直积因子：阿贝尔化阶为 2（见函数文档）
    ab = abelianization_index(true_gens, NS)

    # (d) 无固定点元素个数（老族的 XOR 平移非单位元全无固定点，本例不构成子群）
    G = closure_perms(true_gens, NS)
    derangements = sum(1 for g in G if all(g[s] != s for s in range(NS)))
    # D(m) = 错排数；解析值 D(n)² + (n!)² 用来对账实测
    def derange(m):
        return round(fact(m) * sum((-1) ** j / float(fact(j)) for j in range(m + 1)))
    return {
        "NS": NS,
        "order": order,
        "order_formula": "2·(%d!)² = %d" % (n, order),
        "not_factorial": {
            "order": order,
            "bracket": "%d! = %d < %d < %d = %d!"
                      % (lo_m, fact(lo_m), order, fact(hi_m), hi_m),
            "is_factorial": any(fact(k) == order for k in range(1, 25)),
        },
        "imprimitive": {
            "block_system": "2 块 × %d（二分侧）" % n,
            "generators_preserve_bipartition": preserves_bipartition,
            "n_classes_wl": len(set(color.values())),
            "cross_side_edges": intra // 2 if intra else intra,
            "within_side0_edges": side0_intra // 2,
            "note": "对称群 S_{2n} 在 2n 点上无非平凡块系统；本群有 ⇒ 非对称群型",
        },
        "abelianization": ab,
        "no_xor_translation": {
            "fixed_point_free_elements": derangements,
            "analytic_D_n_sq_plus_n_fact_sq": derange(n) ** 2 + fact(n) ** 2,
            "matches_analytic": derangements == derange(n) ** 2 + fact(n) ** 2,
            "contains_identity": False,
            "is_power_of_two": (derangements & (derangements - 1)) == 0,
            "note": ("老族 (Z_2)^{n-k} 是直积因子，其非单位元在 2^n 个状态上全部无固定点（半正则、正规）；"
                     "本群无固定点元素集合不含单位元、个数也不是 2 的幂 ⇒ 不构成子群，"
                     "本群没有 XOR 平移成分"),
        },
        "center_order": group_center(true_gens, NS),
        "old_family_comparison": old_family_abelianization(),
        "bruteforce_graph_aut": (graph_aut_order_bruteforce(adj, NS)
                                 if NS <= 8 else "NS>8，10! 太大，未暴力枚举"),
    }


# ---------------------------------------------------------------- 受控扫描
def scan(trans, n, NS, caps, max_gens=NO_CAP):
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)
    rows, kepts = [], []
    for nc in caps:
        t0 = time.time()
        g = graph_automorphisms(adj, color, max_gens=max_gens, node_cap=nc)
        t1 = time.time()
        order, kept = closure_order(g, NS)
        t2 = time.time()
        row = {"node_cap": nc, "n_gens": len(g), "n_gens_kept": len(kept),
               "closure_order": order,
               "sec": round(t2 - t0, 3),
               "sec_search": round(t1 - t0, 3),
               "sec_closure": round(t2 - t1, 3)}
        rows.append(row)
        kepts.append(kept)
    return rows, adj, color, kepts


def run_instance(n, caps=CAPS, run_discover=True, with_identity_check=True):
    NS = 2 * n
    trans = build_knn(n)
    true_gens = true_gens_knn(n)
    trap_gens = trap_gens_knn(n)
    true_order, kept_true = closure_order(true_gens, NS)
    trap_order_ref, kept_trap = closure_order(trap_gens, NS)

    print("\n" + "=" * 96)
    print("[K_{%d,%d}] NS=%d ｜ 真群 Aut = (S_%d × S_%d) ⋊ Z_2 ｜ 阶 %d（公式 2·(%d!)² = %d）"
          % (n, n, NS, n, n, true_order, n, 2 * fact(n) ** 2))
    print("           点稳定子 S_%d × S_%d，阶 %d（公式 (%d-1)!·%d! = %d）"
          % (n - 1, n, trap_order_ref, n, n, (fact(n - 1) * fact(n))))
    print("=" * 96)

    rows, adj, color, kepts = scan(trans, n, NS, caps)
    print("  %-10s %-9s %-12s %-9s %s" % ("node_cap", "生成元", "闭包阶", "耗时s", "较上一档"))
    prev = None
    for row in rows:
        if prev is None:
            change = "（基线）"
        elif row["closure_order"] > prev:
            change = "↑继续上升"
        else:
            change = "＝已停滞"
        print("  %-10d %-9d %-12d %-9.1f %s"
              % (row["node_cap"], row["n_gens"], row["closure_order"], row["sec"], change))
        prev = row["closure_order"]

    identities = []
    ps_caps = []
    if with_identity_check:
        s_trap = set(map(tuple, closure_perms(kept_trap, NS)))
        s_true = set(map(tuple, closure_perms(kept_true, NS)))
        for row, kept in zip(rows, kepts):
            obs = set(map(tuple, closure_perms(kept, NS)))
            info = {"node_cap": row["node_cap"], "order": len(obs),
                    "equals_trap_subgroup": obs == s_trap,
                    "equals_true_group": obs == s_true,
                    "inside_true_group": len(obs & s_true),
                    "inside_trap_subgroup": len(obs & s_trap),
                    "index_in_true_group": (true_order // len(obs)
                                            if obs and true_order % len(obs) == 0 else None)}
            identities.append(info)
            if info["equals_trap_subgroup"]:
                ps_caps.append(info["node_cap"])
            print("  档 %-9d 阶 %-7d ==点稳定子(%d)? %s ｜ ==真群(%d)? %s ｜ 指数 %s"
                  % (info["node_cap"], info["order"], trap_order_ref,
                     info["equals_trap_subgroup"], true_order,
                     info["equals_true_group"], info["index_in_true_group"]))
    print("  点稳定子 %d 实际出现的档：%s" % (trap_order_ref, ps_caps if ps_caps else "未出现"))

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
            reason = ("陷阱阶 %d 在 node_cap %d → %d 间形成平台（生成元 %d → %d），"
                      "随后在 %d 档到达真群阶 %d；纯预算跨过平台，未形成硬顶。"
                      % (ta["trap_order"], stall["from_cap"], stall["to_cap"],
                         stall["gens_from"], stall["gens_to"], ta["escape_cap"], true_order))
    elif rows[-1]["node_cap"] >= 1000000 and top < true_order:
        verdict, label = "CAPPED", "硬顶"
        reason = ("至 10^6 档仍停在 %d < 真群 %d"
                  % (top, true_order))
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
    print("  首分支色类：大小 %s ｜ 内部边 %s ｜ 恒等分支固定节点 %s"
          % (struct["class_size"], struct["intra_edges"], struct["first_node"]))

    restart = None
    if run_discover:
        print("  [对照] 确定性 + 随机重启（discover_knn，同实例同数据）")
        t0 = time.time()
        G, diag = discover_knn(trans, n)
        el = time.time() - t0
        restart = {"closure_order": len(G), "sec": round(el, 3),
                   "full": len(G) == true_order, "diag": dict(diag)}
        print("    闭包阶 = %d（真群 %d）｜ %.1fs" % (len(G), true_order, el))

    print("  [结论] %s（%s）：%s" % (verdict, label, reason))
    return {"n": n, "NS": NS, "true_group": "(S_%d × S_%d) ⋊ Z_2" % (n, n),
            "true_order": true_order,
            "true_order_formula": "2·(%d!)² = %d" % (n, 2 * fact(n) ** 2),
            "trap_subgroup": "点稳定子 S_%d × S_%d" % (n - 1, n),
            "trap_subgroup_order": trap_order_ref,
            "trap_order_formula": "(%d-1)!·%d! = %d" % (n, n, fact(n - 1) * fact(n)),
            "caps": list(caps),
            "max_gens": NO_CAP,
            "point_stabilizer_plateau_caps": ps_caps,
            "scan": rows,
            "identities": identities,
            "stall_point": stall,
            "trap_analysis": ta,
            "first_branch_class": struct,
            "restart": restart,
            "verdict": verdict, "verdict_label": label, "verdict_reason": reason}


def compare(key, inst):
    """逐条对照预注册预测与实测（只读预测，不回写）"""
    p = PREDICTION["instances"][key]
    ta = inst["trap_analysis"]
    trap = ta.get("trap_order")
    label = inst["verdict_label"]
    items = {
        "true_order": {"prediction": p["true_order"], "observed": inst["true_order"],
                       "hit": p["true_order"] == inst["true_order"]},
        "trap_order_data_defined": {"prediction": p["trap_order"], "observed": trap,
                                    "note": "§9.6 口径 max{闭包阶 < 真群阶}",
                                    "hit": p["trap_order"] == trap},
        "hard_cap_or_plateau": {"prediction": p["verdict_label"], "observed": label,
                                "hit": p["verdict_label"] == label},
    }
    if p["escape_cap_band"]:
        lo, hi = p["escape_cap_band"]
        esc = ta.get("escape_cap")
        items["escape_cap_band"] = {
            "prediction": p["escape_cap_band_interval"], "observed_first_full_cap": esc,
            "observed_window": [ta.get("trap_last_cap"), esc],
            "hit": esc is not None and lo < esc <= hi}
    else:
        items["escape_cap_band"] = {
            "prediction": "不适用（预测不逃逸）",
            "observed_first_full_cap": ta.get("escape_cap"),
            "observed_window": [ta.get("trap_last_cap"), ta.get("escape_cap")],
            "hit": ta.get("escape_cap") is None}
    # 预注册用的是「点稳定子」口径；数据口径（§9.6 定义）另列，两者都如实记录
    items["point_stabilizer_observed"] = {
        "prediction": "点稳定子阶 %d 会作为平台出现" % p["trap_order"],
        "observed_caps": inst["point_stabilizer_plateau_caps"],
        "hit": bool(inst["point_stabilizer_plateau_caps"])}
    return items


def main():
    assert len(CAPS) >= 8
    assert CAPS[-1] / CAPS[0] >= 100
    assert 1000000 in CAPS

    print("=" * 96)
    print("第五例预注册验证：K_{n,n}，真群 Aut(K_{n,n}) = (S_n × S_n) ⋊ Z_2，阶 2·(n!)²")
    print("预测已在运行前锁定：n=4 陷阱 144 ⇒ 平台；n=5 陷阱 2,880 ⇒ 硬顶")
    print("=" * 96)

    out = {"source": "src/experiments_restart_scan5.py",
           "purpose": "换结构族（完全二分图）检验 §9.6 的 T* 判据",
           "preregistration": PREDICTION,
           "scan_design": {"n_caps": len(CAPS), "min_cap": min(CAPS), "max_cap": max(CAPS),
                           "span_ratio": max(CAPS) / min(CAPS), "covers_1e6": True},
           "instances": {}, "structure_evidence": {}, "comparison": {}}

    # ---------- 第 1 步：建模验证（真群阶闭包双确认 + 结构判别） ----------
    print("\n[1] 建模验证：真群阶 = 2·(n!)²，且不是 S_m / S_k×(Z_2)^m")
    for n in (4, 5):
        trans = build_knn(n)
        gens = true_gens_knn(n)
        ev = structure_evidence(n, trans, gens)
        out["structure_evidence"]["n=%d" % n] = ev
        print("  n=%d ｜ NS=%d ｜ 闭包阶 %d ｜ 公式 %s ｜ 暴力图自同构数 %s"
              % (n, ev["NS"], ev["order"], ev["order_formula"], ev["bruteforce_graph_aut"]))
        print("    非阶乘：%s" % ev["not_factorial"]["bracket"])
        print("    非本原：块系统 %s，生成元保持二分 = %s，WL 色类数 %s"
              % (ev["imprimitive"]["block_system"],
                 ev["imprimitive"]["generators_preserve_bipartition"],
                 ev["imprimitive"]["n_classes_wl"]))
        print("    阿贝尔化：|G^ab| = %d（[G,G] 阶 %d，= 偶置换子群? %s）"
              % (ev["abelianization"]["abelianization_order"],
                 ev["abelianization"]["commutator_subgroup_order"],
                 ev["abelianization"]["commutator_equals_even_subgroup"]))
        print("    无固定点元素 %d 个（解析 %d，一致? %s；|Z(G)| = %d，|G^ab| = %d）"
              % (ev["no_xor_translation"]["fixed_point_free_elements"],
                 ev["no_xor_translation"]["analytic_D_n_sq_plus_n_fact_sq"],
                 ev["no_xor_translation"]["matches_analytic"],
                 ev["center_order"], ev["abelianization"]["abelianization_order"]))
        # 等变检验：与 p3 同信条 —— 生成元全过则闭包必然全过（复合封闭），
        # 逐元素复检多余，只做哨兵抽样抓 closure_perms 自身实现错误。
        G = closure_perms(gens, 2 * n)
        top = top_succ(trans, n)
        worst = 0.0
        for g in gens:
            e, _c = equiv_error_knn(trans, g, n, top)
            worst = max(worst, e)
        sample = G[:64] + (G[len(G) // 2:len(G) // 2 + 64] if len(G) > 192 else [])
        worst2 = 0.0
        for g in sample:
            e, _c = equiv_error_knn(trans, g, n, top)
            worst2 = max(worst2, e)
        ev["generators_pass_equivariance"] = (worst <= 1e-9)
        ev["sentinel_pass_equivariance"] = (worst2 <= 1e-9)
        ev["sentinel_n"] = len(sample)
        ev["worst_equivariance_error"] = max(worst, worst2)
        print("    生成元 %d 个 + 哨兵抽样 %d 个过等变检验：%s / %s（最大 TV 误差 %.2e）"
              % (len(gens), len(sample), ev["generators_pass_equivariance"],
                 ev["sentinel_pass_equivariance"], ev["worst_equivariance_error"]))

    # ---------- 第 3 步：扫描 ----------
    print("\n[3] 受控扫描：max_gens 放开，只扫 node_cap")
    for n in (4, 5):
        inst = run_instance(n, CAPS, run_discover=True)
        out["instances"]["n=%d" % n] = inst
        out["comparison"]["n=%d" % n] = compare("n=%d" % n, inst)

    # ---------- n=6（算得动就跑） ----------
    n6 = {"attempted": False, "note": None}
    if time.time() - T_START < N6_TIME_GATE:
        n6["attempted"] = True
        try:
            inst6 = run_instance(6, N6_CAPS, run_discover=False, with_identity_check=True)
            n6["instance"] = inst6
        except Exception as exc:                                # 如实记录，不吞
            n6["error"] = "%s: %s" % (type(exc).__name__, exc)
            n6["note"] = "n=6 未跑完，如实记录"
    else:
        n6["note"] = ("已耗时 %.0fs 超过 %ss 闸门，按任务约束砍掉 n=6（真群 2·(6!)² = 1,036,800，"
                      "闭包枚举不可承受）" % (time.time() - T_START, N6_TIME_GATE))
    out["n6"] = n6

    # ---------- 原版 discover 是否可用（如实记录） ----------
    try:
        trans4 = build_knn(4)
        _G, _d = discover(trans4, 4)
        out["legacy_discover"] = {"usable": True, "order": len(_G)}
    except Exception as exc:
        out["legacy_discover"] = {
            "usable": False,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "reason": ("p3.discover 的 equiv_error 用 s^(1<<a) 推动作像，只对 n 位翻转 MDP "
                       "（状态 = 2^n）有意义；K_{n,n} 有 2n 个状态，s^(1<<a) 越界 ⇒ 不适用。"
                       "本文件改用 discover_knn（仅替换等变检验，其余流程同构）。")}
    print("\n  原版 p3.discover 可用性：%s" % out["legacy_discover"].get("usable"))

    # ---------- 总体结论 ----------
    hits = []
    for k, items in out["comparison"].items():
        hits += [v["hit"] for v in items.values()]
    n_hit = sum(1 for h in hits if h)
    # 三选一的判定规则（预注册前即定，不按结果挑）：
    #   判据的核心输出是「硬顶 / 平台」这一二分标签。任一实例标签预测被推翻 ⇒ 不成立；
    #   标签全中但定量条目（陷阱阶 / 逃逸窗口）未中 ⇒ 部分成立；全部命中 ⇒ 成立。
    labels = {k: (PREDICTION["instances"][k]["verdict_label"],
                  out["instances"][k]["verdict_label"]) for k in out["comparison"]}
    label_misses = [k for k, (p, o) in labels.items() if p != o]
    if label_misses:
        result = "不成立"
        correction = ("判据的核心二分输出「硬顶/平台」在 %s 上被推翻（预测 %s，实测 %s）；"
                      "T* ∈ (1,440, 5,040] 不能跨族外推，必须纳入实例相关的 c 或结构变量。"
                      % ("、".join(label_misses),
                         "、".join(labels[k][0] for k in label_misses),
                         "、".join(labels[k][1] for k in label_misses)))
    elif n_hit == len(hits):
        result, correction = "成立", "无需修正；T* ∈ (1,440, 5,040] 在换结构族后仍然成立。"
    else:
        result, correction = ("部分成立",
                              "硬顶/平台标签全中，但陷阱阶 / 逃逸窗口的定量预测未中；"
                              "保留 T* 但须纳入结构变量（群型 / 块系统 / 状态数）。")
    out["overall"] = {"n_items": len(hits), "n_hit": n_hit, "result": result,
                      "label_predictions": labels,
                      "correction_direction": correction}

    print("\n" + "=" * 96)
    print("逐条对照")
    print("=" * 96)
    for k, items in out["comparison"].items():
        print("  %s：" % k)
        for name, item in items.items():
            obs = item.get("observed", item.get("observed_first_full_cap",
                                                item.get("observed_caps")))
            print("    %-26s 命中=%s ｜ 预测=%s ｜ 实测=%s"
                  % (name, item["hit"], item["prediction"], obs))
    print("  判据：%s（%d/%d 命中）" % (result, n_hit, len(hits)))
    print("  修正方向：%s" % correction)
    print("  总耗时 %.1fs" % (time.time() - T_START))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_restart_scan5.json")


if __name__ == "__main__":
    main()
