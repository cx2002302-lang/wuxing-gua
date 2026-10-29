# -*- coding: utf-8 -*-
"""
experiments_canonical_search.py —— 编号无关（relabeling-invariant）搜索：canonize 后 ovh 是否还随编号变

> 对应归因分析预注册记录。

**出发点（§15 已证明）**：ovh 是**实现伪像**——同一张图只换顶点编号，ovh 就能从 1.04 变到 9.40
（相对极差 336%）。根因：`experiments_p3.graph_automorphisms` 里全部 id 依赖只有两处——

    1. order = sorted(range(NS), key=(color[s], len(adj[s])))   ⇒ 正则图下单色类 ⇒ order = id 升序
    2. by_color[c] 按 id 升序 append                            ⇒ 候选枚举序 = id 升序

`experiments_c_attribution.order_of` 同样依赖编号 ⇒ Σ 也一并受影响。

**本实验的干预**：在把图交给**原封不动的搜索器之前**，先做**规范化重编号（canonical relabeling）**，
使得「同一个抽象图的任意两种输入编号，canonize 后得到**逐位相同**的邻接矩阵」。
若这一点成立，则搜索器看到的输入完全相同 ⇒ ① / Σ / ovh 必然相同 ⇒ 编号依赖被消除。

**canonize 的实现（关键在"并列怎么打破"）**

  Step 1  规范 WL 细化 `canon_refine`
          与 p3.wl_refine 的差别：色名不是"按 id 首次出现顺序"分配（那会带编号依赖），
          而是**按不变量签名的字典序**分配：
              sig[v] = (color[v], tuple(sorted(color[u] for u in adj[v])))
              色名 = 所有不同 sig 排序后的下标
          初值取全 0（不变量）⇒ 第 1 轮按度分裂，此后逐轮按邻居色多重集分裂。
          这样得到的**划分与色名都是编号无关的**（等变）。

  Step 2  个体化-细化树（individualization–refinement，nauty 的基本结构）
          WL 在顶点传递图上恒为单色类 ⇒ 色类内顶点**结构上不可区分**（属同一自同构轨道），
          任何"局部规则"都无法把它们排成规范序（这就是预注册担心的并列）。
          处理方式：**不做局部并列打破，而是遍历**——
            · 目标色类 = 最小的非单元素色类（同大小取色名最小者）；
            · 对该类内**每一个**顶点 v 分支，把 v 个体化（赋予唯一负色 −(depth+1)），重新细化，递归；
            · 直到划分离散（每点一色）⇒ 一个叶 = 一个全序 = 一个重编号。
          因细化与目标色类选择都是等变的，**叶集合本身是同构不变量**。

  Step 3  规范形 = 全体叶里**字典序最小**的重编号后邻接矩阵（lex-min certificate）
          min over 一个不变量集合 ⇒ 不变量。自同构群的每个元素都把某个叶映到另一个叶，
          这些叶给出**相同**的 certificate，取 min 不产生歧义。
          ⇒ 真正的 canonical labeling，**不需要按原始 id 打破并列**。

  对照组 V4（naive）：只做 WL + 色类内按**原始 id** 打破并列（预注册提到的"确定性并列打破"）。
          对顶点传递图 WL 恒单色类 ⇒ V4 的规范序 = id 升序 = 恒等重编号 ⇒ 编号依赖**原封不动**。
          本实验同时报告 V4，用来说明"确定性并列打破"并不能消除依赖。

**测量协议：与 §15 逐字相同**（`experiments_ovh_relabel.scan_label` 直接复用）：
  搜索器 graph_automorphisms（确定性回溯，无随机重启）、max_gens = 10^9、标准 13 档 CAPS_STD、
  ① = 逃逸档/n_gens@逃逸档、Σ = stabilizer_chain_sum(全部 Aut, NS, order_of(adj,color))、ovh = ①/Σ。

**预注册判定（写于实测之前）**：canonize 后 ovh 的相对极差
    <  30%  ⇒ 消除     ：编号依赖被 canonize 消除，ovh 成为同构类上的良定义量
    30~100% ⇒ 部分消除
    > 100%  ⇒ 未消除   ：依赖不在顶点顺序，而在别处
（相对极差 = (max − min) / median，三图 × 9 编号，含恒等编号；取三图中最差者判决。）

运行：python src/experiments_canonical_search.py   # 产出 experiments_canonical_search.json
"""
import json
import os
import random
import statistics as st
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from experiments_p3 import wl_refine                                  # noqa: E402
from experiments_ovh_relabel import (K_RELABEL, RELABEL_SEED, isom_map_ok,  # noqa: E402
                                     inv_key, relabel, scan_label)
from experiments_restart_scan6 import heawood_neighbors               # noqa: E402
from experiments_ovh_girth import gp_nbrs, prism_nbrs                 # noqa: E402

OUT = os.path.join(ROOT, "experiments_canonical_search.json")
RAW_JSON = os.path.join(ROOT, "experiments_ovh_relabel.json")

CANON_NODE_CAP = 400000       # canonize 搜索树节点上限（超限即报错，不静默截断）
EXTRA_CANON_CHECK = 20        # 额外随机编号数：验证 canonize 的同构不变性（超出 §15 的 9 种）


# ================================================================== canonize
def _cells(color):
    """按色名升序列出色类（色名已是规范名 ⇒ 该顺序编号无关）。"""
    d = {}
    for v, c in enumerate(color):
        d.setdefault(c, []).append(v)
    return [d[c] for c in sorted(d)]


def canon_refine(adj, color0):
    """
    规范 WL 细化。adj: list[set]。color0: 初值；个体化顶点用负色 −1,−2,…（在细化中保持不变）。

    与 p3.wl_refine 的唯一实质差别：色名按**不变量签名 sig 的字典序**分配，
    而不是按顶点 id 的首次出现顺序分配 ⇒ 划分与色名都不带编号依赖（等变）。
    """
    NS = len(adj)
    color = list(color0)
    prev_key = None
    for _ in range(NS + 2):
        sig = [(color[v], tuple(sorted(color[u] for u in adj[v]))) for v in range(NS)]
        name = {s: i for i, s in enumerate(sorted(set(sig)))}
        new = [color[v] if color[v] < 0 else name[sig[v]] for v in range(NS)]
        key = tuple(tuple(c) for c in _cells(new))
        if key == prev_key:
            return new
        prev_key = key
        color = new
    return color


def _certificate(adj, order):
    """order[新 id] = 旧顶点。返回重编号后邻接矩阵的**上三角行主序** 0/1 元组（规范形指纹）。"""
    bits = []
    NS = len(order)
    for i in range(NS):
        ai = adj[order[i]]
        for j in range(i + 1, NS):
            bits.append(1 if order[j] in ai else 0)
    return tuple(bits)


def canonize(adj, variant="min_smallest"):
    """
    规范重编号。返回 (order, cert, nodes)。
      order[新 id] = 旧顶点；cert = 该编号下邻接矩阵的上三角位串（同构类上的规范形）。

    variant：
      "min_smallest" 主口径：叶里取字典序 **最小** certificate；目标色类 = 最小非单元素色类
      "max_smallest" 稳健性变体：取字典序 **最大**
      "min_first"    稳健性变体：目标色类 = 色名最靠前的非单元素色类（不按大小选）
    """
    assert variant in ("min_smallest", "max_smallest", "min_first")
    lex_min = variant.startswith("min")
    NS = len(adj)
    best = {"cert": None, "order": None}
    nodes = [0]

    def rec(color, depth):
        nodes[0] += 1
        if nodes[0] > CANON_NODE_CAP:
            raise RuntimeError("canonize 搜索树超过节点上限 %d" % CANON_NODE_CAP)
        multi = [c for c in _cells(color) if len(c) > 1]
        if not multi:
            order = [c[0] for c in _cells(color)]      # 离散 ⇒ 每个色类恰 1 点 ⇒ 一个全序
            cert = _certificate(adj, order)
            if best["cert"] is None or (cert < best["cert"] if lex_min
                                        else cert > best["cert"]):
                best["cert"] = cert
                best["order"] = order
            return
        if variant.endswith("first"):
            tgt = multi[0]
        else:
            tgt = min(multi, key=len)
        for v in tgt:
            nc = list(color)
            nc[v] = -(depth + 1)                       # 个体化：唯一负色
            rec(canon_refine(adj, nc), depth + 1)

    rec(canon_refine(adj, [0] * NS), 0)
    if best["order"] is None:
        raise RuntimeError("canonize 未找到离散叶")
    return best["order"], best["cert"], nodes[0]


def canonize_naive(adj):
    """
    对照组 V4：WL 着色 + 色类内按**原始 id** 打破并列（预注册提到的"确定性并列打破"）。
    这不是真正的 canonical labeling——并列是按输入编号打破的，所以不同输入编号会得到不同顺序。
    """
    color = wl_refine([sorted(a) for a in adj])
    return sorted(range(len(adj)), key=lambda s: (color[s], s))


def canon_adj(nbrs, order):
    """按 order（order[新 id]=旧 id）重编号后的邻接表（边集代表的同构类不变）。"""
    return [sorted(a) for a in relabel(nbrs, order)]


# ================================================================== 统计
def spread(v):
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": min(v), "max": max(v),
            "median": round(st.median(v), 4), "mean": round(st.mean(v), 4),
            "sd": (round(st.pstdev(v), 4) if len(v) > 1 else 0.0),
            "rel_range": round((max(v) - min(v)) / st.median(v), 4) if st.median(v) else None}


def verdict_of(rel_range):
    """§16 预注册判定：相对极差 <30% 消除 / 30~100% 部分消除 / >100% 未消除。"""
    if rel_range is None:
        return "无数据"
    if rel_range < 0.30:
        return "消除"
    if rel_range <= 1.00:
        return "部分消除"
    return "未消除"


# ================================================================== 编号
def make_labels(NS, k=K_RELABEL, seed=RELABEL_SEED):
    """与 §15 逐字相同的编号生成（含 ρ₀ = 恒等），保证前后对照用的是同一批编号。"""
    rng = random.Random(seed + NS)
    labels = [("id", list(range(NS)))]
    seen = {tuple(range(NS))}
    while len(labels) < k + 1:
        p = list(range(NS))
        rng.shuffle(p)
        tp = tuple(p)
        if tp in seen:
            continue
        seen.add(tp)
        labels.append(("rnd%02d" % len(seen - {tuple(range(NS))}), p))
    return labels


# ================================================================== 每图实验
def run_graph(name, base_nbrs, expect_order, desc, raw_ref):
    NS = len(base_nbrs)
    labels = make_labels(NS)
    base_adj = [set(x) for x in base_nbrs]

    raw_recs, canon_recs, canon_orders, canon_certs = [], [], [], []
    base_inv = None
    can_first = None

    for lname, perm in labels:
        nbrs = relabel(base_nbrs, perm)
        assert isom_map_ok(base_adj, [set(x) for x in nbrs], perm), "重编号破坏同构：%s/%s" % (
            name, lname)

        # ---------- ① canonize 之前（= §15 的口径，与既有数据对照）----------
        r_raw = scan_label("%s/%s" % (name, lname), nbrs, expect_order)
        key = inv_key(r_raw["invariants"])
        if base_inv is None:
            base_inv = key
        assert key == base_inv, "%s: 编号 %s 的不变量漂移" % (name, lname)
        if raw_ref is not None and lname in raw_ref:
            assert abs(r_raw["ovh"] - raw_ref[lname]) < 5e-4, (
                "%s/%s: 复跑 ovh=%s 与 §15 的 %s 不一致（协议漂移）"
                % (name, lname, r_raw["ovh"], raw_ref[lname]))
        r_raw["perm_new_to_old"] = perm
        raw_recs.append(r_raw)

        # ---------- ② canonize 之后 ----------
        adj = [set(x) for x in nbrs]
        order, cert, nodes = canonize(adj)
        assert isom_map_ok([set(x) for x in nbrs], [set(x) for x in canon_adj(nbrs, order)],
                           order), "%s/%s: canonize 不是同构重编号" % (name, lname)
        if can_first is None:
            can_first = canon_adj(nbrs, order)
        assert canon_adj(nbrs, order) == can_first, (
            "%s: 编号 %s 的 canonize 结果与其它编号不一致（canonize 非规范）" % (name, lname))
        canon_orders.append(order)
        canon_certs.append(cert)

        r_can = scan_label("%s/%s#canon" % (name, lname), canon_adj(nbrs, order), expect_order)
        assert inv_key(r_can["invariants"]) == base_inv, "%s/%s: canonize 改变了图不变量" % (
            name, lname)
        r_can["canon_order_new_to_old"] = order
        r_can["canon_nodes"] = nodes
        canon_recs.append(r_can)

        print("  [%-16s] ovh: %-9s → %-9s | ① : %-10s → %-10s | Σ : %-8s → %-8s | 逃逸 %s→%s"
              % ("%s/%s" % (name, lname), r_raw["ovh"], r_can["ovh"],
                 r_raw["nodes_per_aut"], r_can["nodes_per_aut"],
                 r_raw["sigma"], r_can["sigma"],
                 r_raw["escape_cap"], r_can["escape_cap"]))

    # ---------- 额外同构不变性检查（超出 §15 的 9 种编号）----------
    rng = random.Random(RELABEL_SEED + 997 * NS)
    extra_ok = True
    for _ in range(EXTRA_CANON_CHECK):
        p = list(range(NS))
        rng.shuffle(p)
        nb = relabel(base_nbrs, p)
        o, c, _n = canonize([set(x) for x in nb])
        if canon_adj(nb, o) != can_first:
            extra_ok = False
            break
    assert extra_ok, "%s: canonize 在额外 %d 种随机编号下未给出同一规范形" % (
        name, EXTRA_CANON_CHECK)

    # ---------- 稳健性变体（换 canonize 的实现口径，看 ovh 是否仍唯一）----------
    variants = {}
    for var in ("max_smallest", "min_first"):
        adjs = set()
        for nbrs, perm in [(relabel(base_nbrs, p), p) for _, p in labels]:
            o, _c, _n = canonize([set(x) for x in nbrs], variant=var)
            adjs.add(tuple(tuple(a) for a in canon_adj(nbrs, o)))
        variants[var] = {"n_distinct_canonical_forms": len(adjs)}
        rec = scan_label("%s#%s" % (name, var), canon_adj(base_nbrs, canonize(
            [set(x) for x in base_nbrs], variant=var)[0]), expect_order)
        variants[var].update({"ovh": rec["ovh"], "sigma": rec["sigma"],
                              "nodes_per_aut": rec["nodes_per_aut"],
                              "escape_cap": rec["escape_cap"],
                              "n_gens_at_escape": rec["n_gens_at_escape"],
                              "trap_order": rec["trap_order"],
                              "c": (round(rec["escape_cap"] / rec["trap_order"], 4)
                                    if rec["escape_cap"] and rec["trap_order"] else None)})
    # 对照组 V4：WL + 按原始 id 打破并列
    naive_ovhs = []
    for nbrs, _p in [(relabel(base_nbrs, p), p) for _, p in labels]:
        o = canonize_naive([set(x) for x in nbrs])
        r = scan_label("%s#naive" % name, canon_adj(nbrs, o), expect_order)
        naive_ovhs.append(r["ovh"])
    variants["naive_id_tiebreak"] = {
        "ovh_by_label": {l: v for (l, _), v in zip(labels, naive_ovhs)},
        "spread": spread(naive_ovhs),
        "verdict": verdict_of(spread(naive_ovhs)["rel_range"]),
        "note": "对照组：色类内按原始 id 打破并列（非真 canonize）",
    }

    def ovs(recs):
        return [r["ovh"] for r in recs if r["ovh"] is not None]

    def sig_of(recs):
        return [r["sigma"] for r in recs]

    def c_of(recs):
        out = []
        for r in recs:
            if r["escape_cap"] and r["trap_order"]:
                out.append(round(r["escape_cap"] / r["trap_order"], 4))
        return out

    ovh_b, ovh_a = ovs(raw_recs), ovs(canon_recs)
    sb, sa = spread(ovh_b), spread(ovh_a)

    summary = {
        "graph": name, "desc": desc, "NS": NS, "expect_order": expect_order,
        "n_labels": len(labels),
        "invariants_all_identical": True,
        "canonical_form_identical_across_labels": True,
        "canonical_form_identical_extra_checks": extra_ok,
        "canonical_adjacency": can_first,
        "canon_tree_nodes_per_label": [r["canon_nodes"] for r in canon_recs],
        "ovh_before_by_label": {r["tag"].split("/")[1]: r["ovh"] for r in raw_recs},
        "ovh_after_by_label": {r["tag"].split("/")[1]: r["ovh"] for r in canon_recs},
        "sigma_before_by_label": {r["tag"].split("/")[1]: r["sigma"] for r in raw_recs},
        "sigma_after_by_label": {r["tag"].split("/")[1]: r["sigma"] for r in canon_recs},
        "c_before_by_label": {l: v for l, v in zip(
            [r["tag"].split("/")[1] for r in raw_recs], c_of(raw_recs))},
        "c_after_by_label": {l: v for l, v in zip(
            [r["tag"].split("/")[1] for r in canon_recs], c_of(canon_recs))},
        "ovh_spread_before": sb, "ovh_spread_after": sa,
        "sigma_spread_before": spread(sig_of(raw_recs)), "sigma_spread_after": spread(sig_of(canon_recs)),
        "c_spread_before": spread(c_of(raw_recs)), "c_spread_after": spread(c_of(canon_recs)),
        "verdict": verdict_of(sa["rel_range"]),
        "variants": variants,
    }
    print("  ⇒ %s: ovh 相对极差 %.1f%% → %.1f%% ；Σ %.1f%% → %.1f%% ；c %.1f%% → %.1f%%"
          % (name, 100 * sb["rel_range"], 100 * sa["rel_range"],
             100 * summary["sigma_spread_before"]["rel_range"],
             100 * summary["sigma_spread_after"]["rel_range"],
             100 * summary["c_spread_before"]["rel_range"],
             100 * summary["c_spread_after"]["rel_range"]))
    return {"summary": summary,
            "records_raw": [{k: v for k, v in r.items() if k != "adjacency"} for r in raw_recs],
            "records_canon": [{k: v for k, v in r.items() if k != "adjacency"} for r in canon_recs]}


# ================================================================== 主流程
def main():
    t0 = time.time()
    print("=" * 104)
    print("§16 编号无关搜索：先 canonize（规范重编号）再交给原搜索器，看 ovh 的编号依赖是否消除")
    print("预注册判定：canonize 后 ovh 相对极差 <30%% 消除 / 30~100%% 部分消除 / >100%% 未消除")
    print("=" * 104)

    raw_ref = None
    if os.path.exists(RAW_JSON):
        raw_ref = {k: v["ovh_by_label"] for k, v in
                   json.load(open(RAW_JSON, encoding="utf-8"))["graphs"].items()}

    hb, _lines, _idx = heawood_neighbors()
    cases = [
        ("Heawood", hb, 336, "Heawood 图（14 点 3-正则二部，围长 6，VT）；§15 相对极差 336.4%"),
        ("MK16", gp_nbrs(8, 3), 96, "Möbius–Kantor G(8,3)（16 点 3-正则，围长 6，VT）；§15 122.2%"),
        ("Prism7", prism_nbrs(7), 28, "棱柱 C7□K2（14 点 3-正则，围长 4，VT）；§15 204.4%"),
    ]

    out = {}
    for name, nbrs, exp, desc in cases:
        print("\n[%s] %s" % (name, desc))
        out[name] = run_graph(name, [sorted(x) for x in nbrs], exp, desc,
                              raw_ref.get(name) if raw_ref else None)

    # ---------------- 总判定 ----------------
    per_graph = {}
    for name, b in out.items():
        s0, s1 = b["summary"]["ovh_spread_before"], b["summary"]["ovh_spread_after"]
        per_graph[name] = {
            "rel_range_before": s0["rel_range"], "rel_range_after": s1["rel_range"],
            "verdict": b["summary"]["verdict"],
            "ovh_after": s1["min"], "ovh_after_unique": s1["min"] == s1["max"],
            "sigma_after": b["summary"]["sigma_spread_after"]["min"],
            "c_after": b["summary"]["c_spread_after"]["min"],
            "c_before_natural_id": b["summary"]["c_before_by_label"]["id"],
            "c_before_min": b["summary"]["c_spread_before"]["min"],
            "c_before_max": b["summary"]["c_spread_before"]["max"],
        }
    worst_after = max(v["rel_range_after"] for v in per_graph.values())
    verdict = verdict_of(worst_after)

    print("\n" + "=" * 104)
    print("判决：%s —— canonize 后三图 ovh 相对极差的最大值为 %.1f%%"
          % (verdict, 100 * worst_after))
    for name, v in per_graph.items():
        print("  %-8s ovh 相对极差 %8.1f%% → %8.1f%% | canonize 后 ovh = %.4f（Σ=%.4f, c=%.4f）"
              % (name, 100 * v["rel_range_before"], 100 * v["rel_range_after"],
                 v["ovh_after"], v["sigma_after"], v["c_after"]))
        print("          修正版 c = Σ × f × ovh = %.4f ；自然编号下的实测 c = %.4f"
              % (v["c_after"], v["c_before_natural_id"]))
    print("=" * 104)

    json.dump({
        "source": "src/experiments_canonical_search.py",
        "purpose": "§16：先做规范重编号（canonical relabeling）再跑原搜索器，检验 ovh 的编号依赖是否消除",
        "preregistered": {
            "rule": "canonize 后 ovh 相对极差 <30% 消除 / 30~100% 部分消除 / >100% 未消除",
            "definition": "rel_range = (max − min) / median，三图 × 9 编号（含恒等），取三图最差者判决",
            "note": "规则写于任何实测之前，禁止事后修改",
        },
        "canonize": {
            "step1": "canon_refine：规范 WL，色名按不变量签名 (color, 邻居色多重集) 的字典序分配（非按 id）",
            "step2": "个体化-细化树：目标色类=最小非单元素色类，对类内每个顶点分支个体化后重新细化",
            "step3": "规范形 = 全体离散叶中字典序最小的重编号邻接矩阵（min over 同构不变量集合 ⇒ 不变量）",
            "tie_break": "不按原始 id 打破并列：并列由「遍历所有分支 + 取 lex-min」消解",
            "guarantee": "叶集合等变 ⇒ 规范形只依赖同构类 ⇒ canonize(ρG) 逐位相等（脚本内 assert + 额外 20 种编号复核）",
            "control": "naive_id_tiebreak = WL + 色类内按原始 id 排（非真 canonize），作为对照",
        },
        "protocol": {
            "searcher": "experiments_p3.graph_automorphisms（原封不动，确定性回溯，无随机重启）",
            "scan": "复用 experiments_ovh_relabel.scan_label（max_gens=10^9, CAPS_STD 13 档）",
            "regression": "canonize 前的 9 种编号 ovh 与 experiments_ovh_relabel.json 逐位一致（assert）",
            "definitions": {"①": "逃逸档 node_cap / n_gens@逃逸档",
                            "Σ": "stabilizer_chain_sum(全部 Aut, NS, order_of(adj,color))",
                            "ovh": "① / Σ",
                            "f": "② = n_gens@逃逸 / 陷阱阶",
                            "c": "① × ② = Σ × f × ovh = 逃逸档 / 陷阱阶"},
        },
        "graphs": {k: v["summary"] for k, v in out.items()},
        "records_raw": {k: v["records_raw"] for k, v in out.items()},
        "records_canon": {k: v["records_canon"] for k, v in out.items()},
        "per_graph": per_graph,
        "verdict": verdict,
        "verdict_reason": "canonize 后三图 ovh 相对极差的最大值 = %.1f%%" % (100 * worst_after),
        "sec_total": round(time.time() - t0, 2),
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s in %.1fs" % (OUT, time.time() - t0))


if __name__ == "__main__":
    main()
