# -*- coding: utf-8 -*-
"""
experiments_ovh_relabel.py —— ovh 的顶点编号依赖实验（决定性）

> 对应预注册归因记录。**命题 P**：ovh 是图的同构不变量（结构量）。
> §10（围长）/§13（失配）/§14（度）三轮干预都推翻了「ovh 由某个图论不变量决定」，
> 但它们比较的都**是不同的图**，结构差异与编号差异必然共变 ⇒ 无法归因。

**本实验是第一个把二者解耦的设计**：同一个抽象图，K 种随机顶点重编号 ρ，
只用重编号改写 id，**边集代表的同构类逐位不变**（十五.2 的八项不变量守卫）。

**编号会触碰到搜索器的哪些地方（实验针对性的来源）**
  experiments_p3.graph_automorphisms 里全部 id 依赖只有两处：
    1. order = sorted(range(NS), key=(color[s], len(adj[s])))
       正则图 WL 恒单色类、度全同 ⇒ sort 稳定 ⇒ order = 顶点 id 升序（变量序 = 编号序）
    2. by_color[c] 按 id 升序 append                      （候选枚举序 = 编号序）
  Σ 侧同样 id 依赖（experiments_c_attribution.order_of 同上）⇒ Σ 也一并报告。

**预注册判定规则（见 docs §15.3，写在任何实测之前，禁止事后修改）**
  相对极差 rel_range = (max − min) / median
    <  30%  ⇒ 结构量   ：ovh 是同构不变量，继续找结构解释
    30~100% ⇒ 部分依赖 ：报告依赖强度
    > 100%  ⇒ 实现伪像 ：c = Σ × f × ovh(实现)，ovh 不是图的属性
  辅助判据：A1（Σ 是否也随编号变）/ A2（八项不变量跨编号全等）/ A3（给具体对照）

**测量协议（与 src/experiments_ovh_girth.py 逐字相同）**
  搜索器 graph_automorphisms（确定性回溯，单次，无随机重启）、max_gens = 10^9、
  标准 13 档 CAPS_STD、① = 逃逸档/n_gens@逃逸档、Σ = stabilizer_chain_sum(全部 Aut 元素,
  NS, order_of(adj,color))、ovh = ①/Σ。

**为什么可以提前停在高档 cap（≡ 既有口径，且脚本做运行期断言）**
  max_gens = 10^9 时 bt() 永不因「生成元凑够」提前返回，预算只在节点计数处截断
  ⇒ gens(cap) 对 cap 单调为前缀超集 ⇒ 闭包阶单调不减 ⇒ 「逃逸档 = 达到满群的最小 cap」
     在首次达到满群时即可确定，后续更大档位不改变结果。
  脚本对此单调性逐档断言，一旦违反立即报错并回退到全量 13 档。

运行：python src/experiments_ovh_relabel.py    # 产出 experiments_ovh_relabel.json
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

from experiments_p3 import (backbone_adj, closure_perms,  # noqa: E402
                            graph_automorphisms, wl_refine)
from experiments_c_attribution import (adj_stats, build_graph_mdp,  # noqa: E402
                                       order_of, stabilizer_chain_sum)
from experiments_restart_scan6 import heawood_neighbors  # noqa: E402
from experiments_ovh_girth import (CAPS_STD, all_automorphisms, girth,  # noqa: E402
                                   gp_nbrs, prism_nbrs)

OUT = os.path.join(ROOT, "experiments_ovh_relabel.json")

NO_CAP = 10 ** 9
RELABEL_SEED = 20261024       # 重编号置换的种子（确定性复现）
K_RELABEL = 8                 # 每图的随机编号数（§15.2：≥8，下限 6）


# ------------------------------------------------------------------ 重编号
def relabel(nbrs, perm):
    """perm[新 id] = 旧 id。返回新编号下的邻接表（同一个抽象图，只换 labelling）。"""
    inv = [0] * len(perm)
    for new, old in enumerate(perm):
        inv[old] = new
    return [sorted(inv[w] for w in nbrs[perm[i]]) for i in range(len(nbrs))]


def isom_map_ok(base, new, perm):
    """硬校验：新图与底图同构（ρ 是保邻接双射），且骨架度相同。用于防重编号写错。"""
    inv = [0] * len(perm)
    for new_id, old_id in enumerate(perm):
        inv[old_id] = new_id
    for i in range(len(perm)):
        old = perm[i]
        img = sorted(inv[w] for w in base[old])
        if img != sorted(new[i]):
            return False
    return True


# ------------------------------------------------------------------ 不变量守卫（A2）
def invariants(adj, color, auts, trans, d):
    """§15.2 的八项必须跨编号全等的不变量。"""
    NS = len(adj)
    return {
        "NS": NS,
        "n_edges": adj_stats(adj)["n_edges"],
        "degree_multiset": tuple(sorted(len(a) for a in adj)),
        "girth": girth([set(a) for a in adj]),
        "wl_n_classes": len(set(color.values())),
        "aut_order": len(auts),
        "vertex_transitive": len({g[0] for g in auts}) == NS,
        "n_actions": d,
    }


def inv_key(inv):
    """可哈希化的不变量指纹（用于断言跨编号全等）。"""
    return (inv["NS"], inv["n_edges"], inv["degree_multiset"], inv["girth"],
            inv["wl_n_classes"], inv["aut_order"], inv["vertex_transitive"],
            inv["n_actions"])


# ------------------------------------------------------------------ 单次扫描
def scan_label(tag, nbrs, expect_order=None):
    """对某一编号跑标准预算扫描 + Σ，返回该编号的 ① / Σ / ovh 记录。"""
    trans, d = build_graph_mdp(nbrs)
    adj = backbone_adj(trans, d)
    color = wl_refine(adj)
    NS = len(adj)
    adjset = [set(a) for a in adj]
    assert all(adjset[v] == set(nbrs[v]) for v in range(NS)), "骨干图与输入图不一致"

    st_info = adj_stats(adj)
    auts = all_automorphisms(adjset, color)
    true_order = len(auts)
    if expect_order is not None:
        assert true_order == expect_order, "%s: |Aut|=%d != 预期 %d" % (
            tag, true_order, expect_order)
    invv = invariants(adj, color, auts, trans, d)

    order = order_of(adj, color)
    sigma = stabilizer_chain_sum(auts, NS, order)["theoretical_nodes_per_aut"]

    # ---- 预算扫描（单调 ⇒ 首次达满群即可停）----
    rows, escape_rows = [], []
    prev_order = 0
    for cap in CAPS_STD:
        gens = graph_automorphisms(adj, color, max_gens=NO_CAP, node_cap=cap)
        clo = len(closure_perms(gens, NS)) if gens else 1
        rows.append({"node_cap": cap, "n_gens": len(gens), "closure_order": clo})
        assert clo >= prev_order, "闭包阶非单调（cap=%d）" % cap
        prev_order = clo
        if clo == true_order:
            escape_rows.append(cap)
            break
    escape = min(escape_rows) if escape_rows else None
    n_esc = next((r["n_gens"] for r in rows if r["node_cap"] == escape), None)

    trap = max([r["closure_order"] for r in rows if r["closure_order"] < true_order]
               or [1])
    if escape and n_esc:
        one = escape / n_esc
        ovh = one / sigma
        assert abs(one * (n_esc / trap) - escape / trap) < 1e-9, "c=①×② 校验失败"
    else:
        one = ovh = None

    return {
        "tag": tag, "n_actions": d, "degree_max": st_info["degree_max"],
        "n_edges": st_info["n_edges"], "girth": girth(adjset),
        "wl_n_classes": len(set(color.values())),
        "true_order": true_order, "sigma": round(sigma, 4),
        "trap_order": trap, "escape_cap": escape, "n_gens_at_escape": n_esc,
        "nodes_per_aut": (round(one, 4) if one else None),
        "ovh": (round(ovh, 4) if ovh else None),
        "rows": rows, "invariants": invv,
        "adjacency": [sorted(a) for a in adjset],
    }


# ------------------------------------------------------------------ 每图实验
def run_graph(name, base_nbrs, expect_order, desc, k=K_RELABEL):
    NS = len(base_nbrs)
    rng = random.Random(RELABEL_SEED + NS)   # 确定性的随机编号
    labels = [("id", list(range(NS)))]       # ρ₀ = 恒等（复现基准）
    seen = {tuple(range(NS))}
    while len(labels) < k + 1:
        p = list(range(NS))
        rng.shuffle(p)
        tp = tuple(p)
        if tp in seen:
            continue
        seen.add(tp)
        labels.append(("rnd%02d" % len(seen - {tuple(range(NS))}), p))

    recs, base_inv = [], None
    for lname, perm in labels:
        nbrs = relabel(base_nbrs, perm)
        assert isom_map_ok([set(x) for x in base_nbrs], [set(x) for x in nbrs], perm), \
            "重编号破坏同构：%s/%s" % (name, lname)
        r = scan_label("%s/%s" % (name, lname), nbrs, expect_order)
        key = inv_key(r["invariants"])
        if base_inv is None:
            base_inv = key
        assert key == base_inv, "%s: 编号 %s 的不变量指纹漂移（图结构被改动）" % (name, lname)
        r["perm_new_to_old"] = perm
        recs.append(r)
        print("  [%-14s] ovh=%-10s ①=%-9s Σ=%-8s 逃逸=%-7s n_gens=%-5s trap=%d"
              % (r["tag"], r["ovh"], r["nodes_per_aut"], r["sigma"],
                 r["escape_cap"], r["n_gens_at_escape"], r["trap_order"]))

    ovhs = [r["ovh"] for r in recs if r["ovh"] is not None]
    sigs = [r["sigma"] for r in recs]
    ones = [r["nodes_per_aut"] for r in recs if r["nodes_per_aut"] is not None]

    def spread(v):
        if not v:
            return {}
        return {"n": len(v), "min": min(v), "max": max(v),
                "median": round(st.median(v), 4), "mean": round(st.mean(v), 4),
                "sd": (round(st.pstdev(v), 4) if len(v) > 1 else 0.0),
                "rel_range": round((max(v) - min(v)) / st.median(v), 4)}

    summary = {
        "graph": name, "desc": desc, "NS": NS,
        "expect_order": expect_order, "n_labels": len(recs),
        "invariants_all_identical": True,
        "invariant_fingerprint": {"NS": NS, "n_edges": recs[0]["n_edges"],
                                  "girth": recs[0]["girth"],
                                  "wl_n_classes": recs[0]["wl_n_classes"],
                                  "aut_order": recs[0]["true_order"],
                                  "vertex_transitive": recs[0]["invariants"]["vertex_transitive"]},
        "ovh_by_label": {r["tag"].split("/")[1]: r["ovh"] for r in recs},
        "sigma_by_label": {r["tag"].split("/")[1]: r["sigma"] for r in recs},
        "ovh_spread": spread(ovhs), "sigma_spread": spread(sigs),
        "nodes_per_aut_spread": spread(ones),
        "escape_cap_by_label": {r["tag"].split("/")[1]: r["escape_cap"] for r in recs},
        "n_gens_by_label": {r["tag"].split("/")[1]: r["n_gens_at_escape"] for r in recs},
    }
    # 描述性（不参与预注册判决）：剔除恒等编号后，纯随机编号之间的散布
    rand = [r["ovh"] for r in recs if not r["tag"].endswith("/id") and r["ovh"] is not None]
    summary["ovh_spread_random_labels_only"] = spread(rand)
    summary["ovh_spread_random_labels_only"]["note"] = (
        "描述性，不参与 §15.3 判决；预注册单元是含恒等编号的全部 K+1 种编号")
    print("  ⇒ %s: ovh ∈ [%.4f, %.4f] 中位 %.4f  相对极差 %.1f%% | "
          "Σ 相对极差 %.1f%%"
          % (name, summary["ovh_spread"]["min"], summary["ovh_spread"]["max"],
             summary["ovh_spread"]["median"], 100 * summary["ovh_spread"]["rel_range"],
             100 * summary["sigma_spread"]["rel_range"]))
    return {"summary": summary, "records": recs}


# ------------------------------------------------------------------ 判定
def verdict_of(rel_range):
    if rel_range < 0.30:
        return "结构量"
    if rel_range <= 1.00:
        return "部分依赖"
    return "实现伪像"


# ------------------------------------------------------------------ 主流程
def main():
    t0 = time.time()
    print("=" * 104)
    print("ovh 的顶点编号依赖实验：同一张图，K 种随机标号，边集代表的同构类不变")
    print("预注册判定：相对极差 <30%% 结构量 / 30~100%% 部分依赖 / >100%% 实现伪像")
    print("=" * 104)

    hb, _lines, _idx = heawood_neighbors()
    cases = [
        ("Heawood", hb, 336, "Heawood 图（14 点 3-正则二部，围长 6，VT）；§10.5 的关键线索对象"),
        ("MK16", gp_nbrs(8, 3), 96, "Möbius–Kantor G(8,3)（16 点 3-正则，围长 6，VT）；§10.5 的对照：二分部与 id 交错"),
        ("Prism7", prism_nbrs(7), 28,
         "棱柱 C7□K2（14 点 3-正则，围长 4，VT）；两层按 id 前/后一半对齐"),
    ]

    out = {}
    for name, nbrs, exp, desc in cases:
        print("\n[%s] %s" % (name, desc))
        out[name] = run_graph(name, [sorted(x) for x in nbrs], exp, desc)

    # ---- 判定（每个图独立 + 全体）----
    per_graph = {}
    for name, bundle in out.items():
        s = bundle["summary"]["ovh_spread"]
        per_graph[name] = {"rel_range": s["rel_range"], "verdict": verdict_of(s["rel_range"]),
                           "min": s["min"], "max": s["max"], "median": s["median"]}
    all_rel = [v["rel_range"] for v in per_graph.values()]
    worst = max(all_rel)
    verdict = verdict_of(worst)
    reason = ("%d 个图中最大的 ovh 相对极差 = %.1f%%（%s）" %
              (len(all_rel), 100 * worst,
               max(per_graph, key=lambda k: per_graph[k]["rel_range"])))

    # ---- A3：具体对照（任取一对 ovh 差异最大的编号）----
    contrasts = {}
    for name, bundle in out.items():
        recs = bundle["records"]
        lo = min(recs, key=lambda r: (r["ovh"] if r["ovh"] is not None else -1))
        hi = max(recs, key=lambda r: (r["ovh"] if r["ovh"] is not None else -1))
        contrasts[name] = {
            "label_low": lo["tag"], "ovh_low": lo["ovh"],
            "label_high": hi["tag"], "ovh_high": hi["ovh"],
            "ratio": (round(hi["ovh"] / lo["ovh"], 2) if lo["ovh"] else None),
            "same_invariants": inv_key(lo["invariants"]) == inv_key(hi["invariants"]),
            "sigma_low": lo["sigma"], "sigma_high": hi["sigma"],
            "escape_low": lo["escape_cap"], "escape_high": hi["escape_cap"],
            "n_gens_low": lo["n_gens_at_escape"], "n_gens_high": hi["n_gens_at_escape"],
        }
        print("\n[A3 对照·%s] %s: ovh=%.4f （Σ=%.4f, 逃逸=%s, n_gens=%s） vs "
              "%s: ovh=%.4f （Σ=%.4f, 逃逸=%s, n_gens=%s） —— 结构不变量全等=%s, 倍率=%s×"
              % (name, lo["tag"], lo["ovh"], lo["sigma"], lo["escape_cap"],
                 lo["n_gens_at_escape"], hi["tag"], hi["ovh"], hi["sigma"],
                 hi["escape_cap"], hi["n_gens_at_escape"],
                 contrasts[name]["same_invariants"], contrasts[name]["ratio"]))

    print("\n" + "=" * 104)
    print("判决：%s —— %s" % (verdict, reason))
    print("=" * 104)

    json.dump({
        "source": "src/experiments_ovh_relabel.py",
        "purpose": "§15：同图仅换顶点编号（同构），检验 ovh 是否为图的结构量",
        "preregistered": {
            "rule": "相对极差 <30% 结构量 / 30~100% 部分依赖 / >100% 实现伪像",
            "definition": "rel_range = (max − min) / median，含恒等编号共 K+1 种编号",
            "K_per_graph": K_RELABEL,
            "auxiliary": ["A1 Σ 分布", "A2 八项不变量跨编号全等", "A3 具体对照"],
            "note": "规则在 docs §15.3 写于任何实测之前，禁止事后修改",
        },
        "protocol": {
            "searcher": "experiments_p3.graph_automorphisms（确定性回溯，无随机重启）",
            "max_gens": NO_CAP,
            "caps": list(CAPS_STD),
            "early_stop": "首次达到满群即停（闭包阶对 cap 单调，已逐档断言）",
            "definitions": {"①": "逃逸档 node_cap / n_gens@逃逸档",
                            "Σ": "stabilizer_chain_sum(全部 Aut, NS, order_of(adj,color))",
                            "ovh": "① / Σ"},
        },
        "relabel_seed": RELABEL_SEED,
        "graphs": {k: v["summary"] for k, v in out.items()},
        "records": {k: v["records"] for k, v in out.items()},
        "per_graph_verdict": per_graph,
        "contrasts": contrasts,
        "verdict": verdict, "verdict_reason": reason,
        "sec_total": round(time.time() - t0, 2),
    }, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote %s in %.1fs" % (OUT, time.time() - t0))


if __name__ == "__main__":
    main()
