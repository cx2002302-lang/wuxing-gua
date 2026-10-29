# -*- coding: utf-8 -*-
"""
experiments_ovh_girth.py —— ovh（死分支开销）的围长对照实验

> 对应预注册方案 #2：「直接操纵 ovh：Heawood 的 ovh=9.4
> 归因于『3-正则 + 围长 6 + WL 单色类 ⇒ 局部剪枝弱』。取一组同 NS、同度、
> 不同围长的图，只变围长，看 ovh 是否随之变。」

**实验设计（运行前锁定）**
  固定：NS（14 或 16）、度 = 3（3-正则 ⇒ WL 必然只有 1 个色类，见下）、
        测量协议（与 experiments_restart_scan6 / experiments_c_attribution 完全相同：
        同一 graph_automorphisms、同一 13 档 CAPS、同一 ovh 定义）
  只变：围长（4 / 5 / 6）

  为什么「WL 单色类」自动满足：wl_refine 的初始色 = 度数，3-正则图全图同色；
  第一轮 refine 的签名 = (色, 邻居色多重集) 全图相同 ⇒ 任意正则图 WL 恒为 1 类。
  因此本实验固定 NS + 度后，WL 色类数自动固定为 1，「只有围长在变」成立。

**预注册决策规则（运行前锁定，照 §7 方案 #2 的预注册决策规则操作化）**
  R1（支持）：在每个 NS 组内 ovh 随围长单调不减（g4 ≤ g5 ≤ g6），
     且 g6 组 ovh 最大值 > 2 × g4 组 ovh 最大值（「远大于」的操作化）。
  R2（推翻）：任一 NS 组内出现 (a) 非单调（低围长 ovh > 高围长 ovh），
     或 (b) g6 与 g4 无分离（min(g6) ≤ max(g4)）。
  R3（数据不足）：以上皆非。

**图来源**
  · Heawood：scan6 的 Fano 点-线关联构造（experiments_restart_scan6.heawood_neighbors）
  · 棱柱 C_n□K_2 / Möbius 梯 M_{2n} / 广义 Petersen G(n,k)：显式构造
  · 围长 5 的中间档：结构化代表 G(7,2)（广义 Petersen，Aut=D14 阶 14，非 VT）
    + 4 个随机 3-正则图（配对模型，种子 20261024，邻接表硬编码，试验号记录在
    provenance），真群由穷举枚举确认
  · 14 点 3-正则 VT 普查（结构证据）：全部 3-正则 circulant（C14(1,7) 与 C14(3,7)
    互相同构，即 M14）+ 广义 Petersen 族。结果：VT 者围长均为 4；围长 6 的 VT 图
    只有 Heawood（Fano 关联图，不在这两个族里）；围长 5 的成员（G(7,2) 与 4 个
    随机图）全部非 VT ⇒ 「围长 5 中间档必然同时改变 VT 性」是本实验的固有降级
    条件，如实记录（见 docs §10 诚实边界）

**真群阶的确认方式（不猜）**
  穷举回溯枚举全部保色保邻接双射（all_automorphisms）⇒ |Aut| 为完备计数；
  与已知群阶（PGL(2,7)=336 / D14×Z2=28 / D14=28 / 96 / D8×Z2=32）逐一对账；
  另用贪心生成元闭包与穷举集做集合相等断言。

**ovh 定义（与 docs §2 逐字一致，未做任何调整）**
  ① = 逃逸档 node_cap / 该档 n_gens（实测「每找到 1 个自同构平均消耗的节点数」）
  Σ = Σ_{d=0}^{NS} 1/|S_d|（experiments_c_attribution.stabilizer_chain_sum，
       S_d = 按 graph_automorphisms 节点顺序钉住前 d 个状态后的逐点稳定子）
  ovh = ① / Σ ；② = n_gens@逃逸 / 陷阱阶 ；c = ① × ② = 逃逸档 / 陷阱阶（恒等校验）

运行：python src/experiments_ovh_girth.py     # 产出 experiments_ovh_girth.json
"""
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from experiments_p3 import (backbone_adj, closure_perms,  # noqa: E402
                            dist_of, graph_automorphisms,
                            tvd, wl_refine)
from experiments_c_attribution import (adj_stats, build_graph_mdp,  # noqa: E402
                                       order_of, stabilizer_chain_sum)
from experiments_restart_scan6 import heawood_neighbors  # noqa: E402

OUT = os.path.join(ROOT, "experiments_ovh_girth.json")

NO_CAP = 10 ** 9
# 标准栅：与 scan6 / attribution 的 13 档完全一致（主测量，保证与既有 12 例同协议）
CAPS_STD = (100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000,
            64000, 128000, 256000, 1000000)
# 细栅：仅作稳健性（逃逸档定位分辨率），约 1.22× 步长
CAPS_FINE = [int(round(50 * (1.22 ** k))) for k in range(52)]
CAPS_FINE = sorted(set(c for c in CAPS_FINE if c <= 1000000))


# ------------------------------------------------------------------ 图构造
def prism_nbrs(n):
    """棱柱 C_n □ K_2：顶点 (l,i) -> n*l+i，两层各一个 n-环 + 竖直辐条"""
    def v(l, i):
        return n * l + (i % n)
    return [[v(l, i + 1), v(l, i - 1), v(1 - l, i)]
            for l in (0, 1) for i in range(n)]


def mobius_nbrs(n):
    """Möbius 梯 M_{2n}：Z_{2n} 上 2n-环（±1）+ 对径弦（i, i+n）"""
    N = 2 * n
    return [[(i + 1) % N, (i - 1) % N, (i + n) % N] for i in range(N)]


def circulant_nbrs(N, jumps):
    """Z_N 上带连接集 ±jumps 的 circulant 图"""
    S = set()
    for j in jumps:
        S.add(j % N)
        S.add((-j) % N)
    return [sorted({(i + s) % N for s in S}) for i in range(N)]


def gp_nbrs(n, k):
    """广义 Petersen G(n,k)：外 n-环 + 内星形 {n/k} + 辐条"""
    N = 2 * n
    nbrs = [[] for _ in range(N)]
    for i in range(n):
        nbrs[i] = [(i + 1) % n, (i - 1) % n, n + i]
    for i in range(n):
        nbrs[n + i] = [n + (i + k) % n, n + (i - k) % n, i]
    return nbrs


# 围长 5 的 14 点 3-正则图（随机配对模型，种子 20261024；邻接表硬编码，试验号见 provenance）
GIRTH5_GRAPHS = {
    "G5-A": {"trial": 648, "nbrs": [[2, 7, 12], [3, 10, 12], [0, 6, 11], [1, 7, 8],
                                    [7, 11, 13], [8, 9, 10], [2, 9, 13], [0, 3, 4],
                                    [3, 5, 11], [5, 6, 12], [1, 5, 13], [2, 4, 8],
                                    [0, 1, 9], [4, 6, 10]]},
    "G5-B": {"trial": 1195, "nbrs": [[4, 7, 8], [5, 6, 12], [3, 6, 11], [2, 8, 9],
                                     [0, 11, 13], [1, 8, 13], [1, 2, 10], [0, 9, 12],
                                     [0, 3, 5], [3, 7, 10], [6, 9, 13], [2, 4, 12],
                                     [1, 7, 11], [4, 5, 10]]},
    "G5-C": {"trial": 4786, "nbrs": None},   # 运行期由确定性搜索回填（见 find_girth5）
    "G5-D": {"trial": 6559, "nbrs": None},
}


def find_girth5(seed=20261024, want=(648, 1195, 4786, 6559), n_vertices=14):
    """确定性复现围长 5 图的随机搜索（配对模型），按试验号取回邻接表。"""
    rng = random.Random(seed)
    got = {}
    for trial in range(20000):
        if len(got) == len(want):
            break
        stubs = [v for v in range(n_vertices) for _ in range(3)]
        rng.shuffle(stubs)
        adj = [set() for _ in range(n_vertices)]
        ok = True
        for a in range(0, len(stubs), 2):
            u, w = stubs[a], stubs[a + 1]
            if u == w or w in adj[u]:
                ok = False
                break
            adj[u].add(w)
            adj[w].add(u)
        if not ok or any(len(a) != 3 for a in adj):
            continue
        if trial in want and trial not in got:
            if girth(adj) == 5:
                got[trial] = [sorted(s) for s in adj]
    missing = [t for t in want if t not in got]
    assert not missing, "围长5图搜索失败: %s" % missing
    return got


# ------------------------------------------------------------------ 图论工具
def girth(adj):
    """最短环长：对每点 BFS，遇非树边即得环"""
    best = None
    for s in range(len(adj)):
        dist = {s: 0}
        par = {s: None}
        q = [s]
        for u in q:
            for w in adj[u]:
                if w not in dist:
                    dist[w] = dist[u] + 1
                    par[w] = u
                    q.append(w)
        for u in q:
            for w in adj[u]:
                if w in dist and u < w and par[u] != w and par[w] != u:
                    c = dist[u] + dist[w] + 1
                    best = c if best is None else min(best, c)
    return best


def all_automorphisms(adj, color, node_limit=4 * 10 ** 6):
    """穷举全部自同构（含单位元）——真群阶的完备计数，不依赖任何群论先验"""
    NS = len(adj)
    order = sorted(range(NS), key=lambda s: (color[s], len(adj[s])))
    by_color = {}
    for s in range(NS):
        by_color.setdefault(color[s], []).append(s)
    pi = [None] * NS
    used = [False] * NS
    inv = [None] * NS
    out = []
    budget = [node_limit]

    def ok(s, t):
        for v in adj[s]:
            if pi[v] is not None and pi[v] not in adj[t]:
                return False
        for w in adj[t]:
            pv = inv[w]
            if pv is not None and pv not in adj[s]:
                return False
        return True

    def bt(i):
        if budget[0] <= 0:
            raise RuntimeError("穷举预算耗尽（图过大？）")
        budget[0] -= 1
        if i == NS:
            out.append(tuple(pi))
            return
        s = order[i]
        for t in by_color[color[s]]:
            if used[t] or not ok(s, t):
                continue
            pi[s], used[t], inv[t] = t, True, s
            bt(i + 1)
            pi[s], used[t], inv[t] = None, False, None

    bt(0)
    return out


def greedy_gens(elems, NS):
    """从群元素集中贪心取生成元（闭包等于全集即停）"""
    gens, seen = [], {tuple(range(NS))}
    for g in elems:
        if tuple(g) in seen:
            continue
        gens.append(list(g))
        clo = closure_perms(gens, NS)
        seen = set(map(tuple, clo))
        if len(seen) == len(elems):
            break
    return gens


def cycle_types(elems, NS):
    from collections import Counter
    c = Counter()
    for g in elems:
        seen = [False] * NS
        lens = []
        for s in range(NS):
            if not seen[s]:
                l, t = 0, s
                while not seen[t]:
                    seen[t] = True
                    t = g[t]
                    l += 1
                lens.append(l)
        c[tuple(sorted(lens, reverse=True))] += 1
    return {"%s" % (k,): v for k, v in sorted(c.items(), key=lambda kv: -kv[1])}


# ------------------------------------------------------------------ MDP 等变抽查
def top_succ(trans, n):
    return [[max(trans[s][a], key=lambda x: x[0])[1] for a in range(n)]
            for s in range(len(trans))]


def equiv_error_graph(trans, pi, n, top):
    """与 scan6.equiv_error_heawood 同语义的通用版（不写死 NS）"""
    worst, checked = 0.0, 0
    for s in range(len(trans)):
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


# ------------------------------------------------------------------ 扫描与分析
def scan_caps(adj, color, caps):
    rows = []
    for cap in caps:
        gens = graph_automorphisms(adj, color, max_gens=NO_CAP, node_cap=cap)
        order = len(closure_perms(gens, len(adj))) if gens else 1
        rows.append({"node_cap": cap, "n_gens": len(gens), "closure_order": order})
    return rows


def trap_identity(trap_set, auts, adj, NS):
    """陷阱闭包集是哪个标准子群？保二分部 / 保前半层 / 点稳定子(v0)"""
    ident = tuple(range(NS))
    if len(trap_set) <= 1:
        return {"kind": "无实质陷阱", "order": len(trap_set), "index": None}
    cands = {}
    side = {0: 0}
    q = [0]
    bipart = True
    while q and bipart:
        u = q.pop()
        for w in adj[u]:
            if w not in side:
                side[w] = 1 - side[u]
                q.append(w)
            elif side[w] == side[u]:
                bipart = False
                break
    if bipart:
        cands["保二分部子群"] = set(g for g in auts
                                if all(side[g[s]] == side[s] for s in range(NS)))
    half = NS // 2
    cands["保前半层子群"] = set(g for g in auts
                             if all((g[s] < half) == (s < half) for s in range(NS)))
    cands["点稳定子(v0)"] = set(g for g in auts if g[0] == 0)
    for k, v in cands.items():
        if v == trap_set:
            return {"kind": k, "order": len(trap_set),
                    "index": len(auts) // len(trap_set)}
    return {"kind": "非上述标准子群", "order": len(trap_set),
            "index": len(auts) // len(trap_set)}


def analyze(tag, nbrs, desc, expect_order, prov=None):
    trans, d = build_graph_mdp(nbrs)
    adj = backbone_adj(trans, d)
    color = wl_refine(adj)
    NS = len(adj)
    adjset = [set(x) for x in adj]

    # ---- 结构特征 ----
    st = adj_stats(adj)
    g = girth(adjset)
    ncls = len(set(color.values()))
    # 骨干图 == 输入的 3-正则图（断言，防建模错位）
    assert all(adjset[v] == set(nbrs[v]) for v in range(NS)), "骨干图与输入图不一致"

    # ---- 真群：穷举 + 贪心生成元 + 闭包核对 + 已知群阶对账 ----
    auts = all_automorphisms(adjset, color)
    true_order = len(auts)
    gens = greedy_gens(auts, NS)
    clo = set(map(tuple, closure_perms(gens, NS)))
    assert clo == set(auts), "贪心生成元闭包 != 穷举真群"
    known_ok = (expect_order is None) or (true_order == expect_order)

    # ---- MDP 等变抽查（真群生成元应全是 MDP 自同构）----
    top = top_succ(trans, d)
    worst_equiv = 0.0
    for gm in gens[:6]:
        e, _c = equiv_error_graph(trans, gm, d, top)
        worst_equiv = max(worst_equiv, e)

    # ---- 轨道 / 传递性 ----
    orb0 = set()
    for gm in auts:
        orb0.add(gm[0])
    vt = len(orb0) == NS

    # ---- Σ（解析下界，与 attribution 同函数同搜索序）----
    order = order_of(adj, color)
    sigma = stabilizer_chain_sum(auts, NS, order)["theoretical_nodes_per_aut"]

    # ---- 双栅扫描 ----
    scans = {}
    for gname, caps in (("std", CAPS_STD), ("fine", CAPS_FINE)):
        rows = scan_caps(adj, color, caps)
        true_orders = [r["closure_order"] for r in rows]
        trap = max([o for o in true_orders if o < true_order] or [1])
        trap_caps = [r["node_cap"] for r in rows if r["closure_order"] == trap]
        trap_last = max(trap_caps) if trap_caps else 0
        esc = [r["node_cap"] for r in rows if r["closure_order"] == true_order]
        escape = min(esc) if esc else None
        n_esc = next((r["n_gens"] for r in rows if r["node_cap"] == escape), None)
        if escape and n_esc:
            one = escape / n_esc
            ovh = one / sigma
            two = n_esc / trap
            c_band = [round(trap_last / trap, 3), round(escape / trap, 3)]
            assert abs(one * two - escape / trap) < 1e-9, "c = ①×② 恒等校验失败"
        else:
            one = ovh = two = None
            c_band = [round(CAPS_STD[-1] / trap, 3), None]
        # 陷阱闭包集与身份
        if trap > 1 and trap_caps:
            gcap = min(trap_caps)
            tgens = graph_automorphisms(adj, color, max_gens=NO_CAP, node_cap=gcap)
            tset = set(map(tuple, closure_perms(tgens, NS))) if tgens else {tuple(range(NS))}
            tident = trap_identity(tset, auts, adjset, NS)
            ttypes = cycle_types(tset, NS)
        else:
            tident = {"kind": "无实质陷阱（陷阱阶=%d）" % trap, "order": trap,
                      "index": (true_order // trap) if trap else None}
            ttypes = {}
        scans[gname] = {
            "rows": rows, "trap_order": trap, "trap_first_cap": (min(trap_caps) if trap_caps else None),
            "trap_last_cap": trap_last, "escape_cap": escape, "n_gens_at_escape": n_esc,
            "nodes_per_aut": (round(one, 4) if one else None),
            "sigma": round(sigma, 4),
            "ovh": (round(ovh, 4) if ovh else None),
            "factor2": (round(two, 4) if two else None),
            "c_band": c_band, "trap_identity": tident, "trap_cycle_types": ttypes,
            "plateau_cap_ratio": (round(trap_last / min(trap_caps), 2)
                                  if trap_caps and trap > 1 else None),
        }

    rec = {
        "tag": tag, "desc": desc, "provenance": prov,
        "NS": NS, "n_actions": d, "p_pert": 0.05,
        "degree_min": st["degree_min"], "degree_max": st["degree_max"],
        "n_edges": st["n_edges"], "density": st["density"],
        "girth": g, "wl_n_classes": ncls,
        "true_order": true_order, "true_order_matches_known": known_ok,
        "expect_order": expect_order,
        "n_greedy_gens": len(gens),
        "vertex_transitive": vt, "orbit0_size": len(orb0),
        "worst_equivariance_error": worst_equiv,
        "adjacency": [sorted(x) for x in adjset],
        "scans": scans,
    }
    print("[ok] %-14s NS=%2d deg=%d girth=%d WL类=%d |Aut|=%-4d VT=%-5s orb0=%-2d "
          "trap=%-4d esc(std)=%-7s ovh(std)=%-8s ovh(fine)=%-8s"
          % (tag, NS, st["degree_max"], g, ncls, true_order, vt, len(orb0),
             scans["std"]["trap_order"], scans["std"]["escape_cap"],
             scans["std"]["ovh"], scans["fine"]["ovh"]))
    return rec


# ------------------------------------------------------------------ VT 普查
def vt_census():
    """14 点 3-正则点传递图普查（结构证据，实测围长/群阶/VT 性）"""
    out = []
    cases = [
        ("C14(1,7)（Möbius 梯 M14）", circulant_nbrs(14, (1, 7)), 28),
        ("C14(3,7)", circulant_nbrs(14, (3, 7)), 28),
        ("G(7,1)（棱柱 C7□K2）", gp_nbrs(7, 1), 28),
        ("G(7,2)", gp_nbrs(7, 2), 14),
    ]
    for name, nbrs, exp in cases:
        adj = [set(x) for x in nbrs]
        color = wl_refine(adj)
        auts = all_automorphisms(adj, color)
        orb0 = len({g[0] for g in auts})
        out.append({"graph": name, "girth": girth(adj), "aut_order": len(auts),
                    "expect_order": exp, "matches": (exp is None or exp == len(auts)),
                    "vertex_transitive": orb0 == len(adj), "orbit0_size": orb0,
                    "nbrs": [sorted(x) for x in adj]})
        print("[普查] %-24s 围长=%d |Aut|=%-3d VT=%-5s orb0=%d"
              % (name, girth(adj), len(auts), orb0 == len(adj), orb0))
    return out


# ------------------------------------------------------------------ 主流程
def main():
    t0 = time.time()
    print("=" * 100)
    print("ovh 的围长对照实验：固定 NS / 度=3 / WL 单色类，只变围长")
    print("预注册决策规则：R1 支持=每组内 ovh 随围长单调不减且 g6>2×g4；")
    print("                R2 推翻=任一组内非单调或 g6 与 g4 无分离；R3 数据不足")
    print("=" * 100)

    g5 = find_girth5()
    for tag, info in GIRTH5_GRAPHS.items():
        info["nbrs"] = g5[info["trial"]]

    hb, _lines, _idx = heawood_neighbors()
    cases = [
        ("Heawood", hb, "Heawood 图（Fano 点-线关联图，3-正则二部）", 336,
         "scan6 构造；基准实例（docs §2: ovh=9.40）"),
        ("Prism7", prism_nbrs(7), "棱柱 C7□K2（14 点 3-正则，围长 4）", 28,
         "显式构造；Aut=D14×Z2"),
        ("M14", mobius_nbrs(7), "Möbius 梯 M14（14 点 3-正则，围长 4）", 28,
         "显式构造；Aut=D14"),
        ("GP72", gp_nbrs(7, 2), "广义 Petersen G(7,2)（14 点 3-正则，围长 5）", 14,
         "显式构造；Aut=D14 阶 14，轨道 7+7（非 VT）；围长5的结构化中间档"),
    ]
    for tag in ("G5-A", "G5-B", "G5-C", "G5-D"):
        info = GIRTH5_GRAPHS[tag]
        cases.append((tag, info["nbrs"],
                      "随机 3-正则（14 点，围长 5，配对模型种子 20261024 试验 %d）"
                      % info["trial"], None,
                      "配对模型随机生成；真群由穷举枚举确认（非 VT 是围长5图的固有性质）"))
    cases += [
        ("MK16", gp_nbrs(8, 3), "Möbius–Kantor 图 G(8,3)（16 点 3-正则，围长 6）", 96,
         "显式构造；Aut 阶 96"),
        ("Prism8", prism_nbrs(8), "棱柱 C8□K2（16 点 3-正则，围长 4）", 32,
         "显式构造；Aut=D8×Z2"),
        ("M16", mobius_nbrs(8), "Möbius 梯 M16（16 点 3-正则，围长 4）", 32,
         "显式构造；Aut 阶 32"),
    ]

    recs = {}
    for tag, nbrs, desc, exp, prov in cases:
        recs[tag] = analyze(tag, nbrs, desc, exp, prov)

    print("\n[VT 普查] 14 点 3-正则点传递图（结构证据）")
    census = vt_census()

    # ---- Heawood 基准复现核对（vs experiments_restart_scan6.json）----
    base = json.load(open(os.path.join(ROOT, "experiments_restart_scan6.json"),
                          encoding="utf-8"))["instances"]["heawood"]
    h = recs["Heawood"]["scans"]["std"]
    repro = {
        "trap_order": {"baseline": base["trap_analysis"]["trap_order"],
                       "rerun": h["trap_order"],
                       "match": base["trap_analysis"]["trap_order"] == h["trap_order"]},
        "escape_cap": {"baseline": base["trap_analysis"]["escape_cap"],
                       "rerun": h["escape_cap"],
                       "match": base["trap_analysis"]["escape_cap"] == h["escape_cap"]},
        "n_gens_at_escape": {"baseline": 295, "rerun": h["n_gens_at_escape"],
                             "match": 295 == h["n_gens_at_escape"]},
        "sigma": {"baseline": 11.5446, "rerun": h["sigma"],
                  "match": abs(11.5446 - h["sigma"]) < 1e-3},
        "ovh": {"baseline": 9.40, "rerun": h["ovh"],
                "match": abs(9.40 - h["ovh"]) < 0.05},
    }
    print("\n[Heawood 基准复现] %s" %
          {k: v["match"] for k, v in repro.items()})

    # ---- 预注册判决 ----
    def group(nsv):
        g4 = [r["scans"]["std"]["ovh"] for r in recs.values()
              if r["NS"] == nsv and r["girth"] == 4 and r["scans"]["std"]["ovh"]]
        g5 = [r["scans"]["std"]["ovh"] for r in recs.values()
              if r["NS"] == nsv and r["girth"] == 5 and r["scans"]["std"]["ovh"]]
        g6 = [r["scans"]["std"]["ovh"] for r in recs.values()
              if r["NS"] == nsv and r["girth"] == 6 and r["scans"]["std"]["ovh"]]
        return g4, g5, g6

    verdict_detail = {}
    for nsv in (14, 16):
        g4, g5, g6 = group(nsv)
        if not (g4 and g6):
            verdict_detail["NS=%d" % nsv] = {"note": "g4/g6 样本不足", "g4": g4, "g5": g5, "g6": g6}
            continue
        seq = g4 + g5 + g6
        mono = all(a <= b for a, b in zip(sorted(g4) + sorted(g5), sorted(g5) + sorted(g6))) \
            if g5 else max(g4) <= min(g6)
        sep = max(g6) > 2 * max(g4)
        nonmono = (max(g5) > min(g6)) if g5 else False
        nosep = min(g6) <= max(g4)
        verdict_detail["NS=%d" % nsv] = {
            "ovh_g4": g4, "ovh_g5": g5, "ovh_g6": g6,
            "monotone_nondecreasing": bool(mono),
            "g6_separation_gt_2x": bool(sep),
            "nonmonotone_low_girth_above_high": bool(nonmono),
            "g6_g4_no_separation": bool(nosep),
        }
    print("\n[预注册判决明细] %s" % json.dumps(verdict_detail, ensure_ascii=False))

    if any(v.get("nonmonotone_low_girth_above_high") or v.get("g6_g4_no_separation")
           for v in verdict_detail.values()):
        verdict = "推翻"
        why = ("任一 NS 组内出现「低围长 ovh > 高围长 ovh」的非单调，或 g6 与 g4 无分离"
               "⇒ ovh 不随围长变化，「围长（在同 NS/度/WL 下）决定 ovh」的猜想被推翻")
    elif all(v.get("monotone_nondecreasing") and v.get("g6_separation_gt_2x")
             for v in verdict_detail.values() if "ovh_g4" in v):
        verdict = "支持"
        why = "两个 NS 组内 ovh 均随围长单调不减且 g6 > 2×g4"
    else:
        verdict = "数据不足"
        why = "样本不满足任一判决条件"

    # ---- VT 子族内的方向性核对（辅助，非预注册单元）----
    vt14 = {r["girth"]: r["scans"]["std"]["ovh"] for r in recs.values()
            if r["NS"] == 14 and r["vertex_transitive"]}
    aux = {"NS14_VT_only": vt14,
           "note": "预注册单元是「同 NS 同度不同围长」全体；VT 子族单列仅作方向性参考"}

    print("\n" + "=" * 100)
    print("判决：%s —— %s" % (verdict, why))
    print("=" * 100)

    json.dump({
        "source": "src/experiments_ovh_girth.py",
        "purpose": "§7 方案 #2：固定 NS/度/WL色类，只变围长，检验 ovh 是否随之变",
        "design": {
            "fixed": ["NS（14 或 16）", "度=3（⇒WL 恒 1 色类）", "13 档标准 CAPS",
                      "graph_automorphisms 搜索", "ovh 定义（①=逃逸档/n_gens@逃逸档, ovh=①/Σ）"],
            "varied": "围长（4/5/6）",
            "decision_rule_preregistered": {
                "R1_support": "每组内 ovh 随围长单调不减 且 max(g6) > 2×max(g4)",
                "R2_refute": "任一组内非单调（低围长>高围长）或 g6 与 g4 无分离",
                "R3_insufficient": "以上皆非"},
        },
        "instances": recs,
        "vt_census_14": census,
        "heawood_baseline_reproduction": repro,
        "verdict_detail": verdict_detail,
        "aux_vt_subset": aux,
        "verdict": verdict, "verdict_reason": why,
        "sec_total": round(time.time() - t0, 2),
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s in %.1fs" % (OUT, time.time() - t0))


if __name__ == "__main__":
    main()
