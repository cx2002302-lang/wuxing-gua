# -*- coding: utf-8 -*-
"""
experiments_restart_scan2.py —— 第二实例验证：『预算封顶在子群、重启能跨越』是否只在 Q_n 上成立

**为什么要有这个脚本**

既有重启预算定量研究的结论（Q_8 上预算 4,000→1,000,000 闭包阶 24→120→720→5,040 后卡死，
封顶于点稳定子 S_7；随机重启直达 S_8 = 40,320）**只在 Q_8 一个实例上实测过**，
而 Q_8 的真群恰好是 **S_8**。该文档 §5 自己承认这是硬伤：

    "我们**未**提供第二个非 S_n 实例（如 SYS-1 的 D_n）来佐证；该实例需额外实验"

本脚本补上第二个实例。实例选择（文档 §5 给了两条备选，按优先级实现）：

  · **主实例 SYS-3 B**（`src/experiments_sys3.py` 的 B 场景，目标 = {位0=位1=1}）：
    真群 **G = S_2 × S_{n-2} × (Z_2)^{n-2}**，阶 **2·(n-2)!·2^(n-2)**，n=8 ⇒ **92,160**。
    它**明确不是 S_n**：92,160 不等于任何 m!（8!=40,320 < 92,160 < 9!=362,880），
    且结构上含 (Z_2)^{n-2} 平移因子，与对称群不同构。
  · **为什么不取 SYS-1 的 D_n 作主实例**：D_6 阶仅 12，真群本身太小，
    「预算封顶」在数学上不可观测 —— 顶就是整个群，预算极小即饱和，
    「看不出封顶」在这里**不能用来反驳机制**，只能造出一个假阴性。
    故 D_n 降级为**辅助对照**，用来坐实「小群上封顶不可观测」这一判断。

**口径（与 experiments_restart_scan.py 严格对齐，保证可比）**
  · `max_gens = 10**9`（放开输出上限）—— §0 勘误的教训：不设限，
    否则测到的是自己的输出截断而不是搜索预算曲线。
  · 只扫 `node_cap`（真正的搜索预算），5 档，跨度 250 倍。
  · 每档记录：生成元数 / 闭包阶 / 耗时；判据是「**闭包阶停涨但生成元数继续虚增**」。

**一个必要的工程改动：`closure_order()`（不是改口径，只是让大群算得动）**
`closure_perms` 的代价是 O(|G|·|gens|)。本实例满群 92,160，而大预算档会搜出
4,000+ 个生成元，直接喂进去是 O(4×10^8) 次复合 —— 单档就要几十分钟。
`closure_order()` 先把生成元压到极小再调 `closure_perms`：
  · 维护 `seen = <已保留生成元>` 的闭包；
  · 若 g ∈ seen ⇒ 冗余，O(NS) 成员测试滤掉；
  · 若 g ∉ seen ⇒ 由 Lagrange，`<seen, g>` 的阶至少翻倍 ⇒ 这种「真正扩张」的生成元
    最多 log2(92,160) ≈ 17 个。
结果是**精确同解**（下面对便宜档做了 plain-vs-pruned 交叉校验），但把 |gens| 从
4×10^3 降到 ≤17。它**不改变任何搜索口径**，只影响闭包这一步的算法复杂度。

运行：python src/experiments_restart_scan2.py
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import build_model_n                       # noqa: E402
from experiments_p3 import (backbone_adj, wl_refine,           # noqa: E402
                            graph_automorphisms, closure_perms,
                            discover)
from experiments_sys3 import free_sym_gens, swap_gen           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

NO_CAP = 10 ** 9          # "不设限"的生成元输出上限
CAPS = (4000, 16000, 64000, 250000, 1000000, 4000000)   # 6 档，跨度 1000 倍
PLAIN_CHECK_MAX_GENS = 300   # 生成元数不超过此值时，额外用原版 closure_perms 交叉校验


# ---------------------------------------------------------------- 闭包（精确 + 可算）
def closure_order(gens, NS):
    """
    精确求 <gens> 的阶，返回 (阶, 保留下来的极小生成元表)。

    见文件头说明：先用成员测试滤掉冗余生成元，只把真正扩张群的那些喂给
    `closure_perms`。与直接 `len(closure_perms(gens, NS))` **数学上同解**，
    只是把 O(|G|·|gens|) 里的 |gens| 从数千降到 ≤ log2(|G|)。
    """
    ident = list(range(NS))
    seen = {tuple(ident)}
    kept = []
    for g in gens:
        t = tuple(g)
        if t in seen:
            continue
        cl = closure_perms(kept + [g], NS)
        if len(cl) <= len(seen):     # 理论上不可能（g∉H ⇒ 阶必增）；保守防御
            seen.add(t)
            continue
        kept.append(g)
        seen = set(map(tuple, cl))
    return len(seen), kept


def scan(trans, n, NS, caps=CAPS, max_gens=NO_CAP):
    """固定生成元上限、只扫 node_cap，返回预算曲线"""
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
        # 便宜档用原版 closure_perms 交叉校验，证明 pruning 没有偷改结果
        if len(g) <= PLAIN_CHECK_MAX_GENS:
            plain = len(closure_perms(g, NS)) if g else 0
            row["closure_order_plain"] = plain
            row["pruning_consistent"] = (plain == order)
        rows.append(row)
        kepts.append(kept)
    return rows, adj, color, kepts


def stall_point(rows):
    """定位停滞点：闭包阶与上一档相同（且生成元数仍在涨）的第一档"""
    for i in range(1, len(rows)):
        if rows[i]["closure_order"] == rows[i - 1]["closure_order"]:
            return {"from_cap": rows[i - 1]["node_cap"],
                    "to_cap": rows[i]["node_cap"],
                    "cap_ratio": rows[i]["node_cap"] / rows[i - 1]["node_cap"],
                    "order_at_stall": rows[i]["closure_order"],
                    "gens_from": rows[i - 1]["n_gens"],
                    "gens_to": rows[i]["n_gens"],
                    "gens_still_grew": rows[i]["n_gens"] > rows[i - 1]["n_gens"]}
    return None


def verdict(rows, stall, true_order):
    """
    三选一的硬结论，不许含糊：
      CAPPED           —— 观察到封顶（停滞档之后**所有更大预算**都涨不过这个阶，
                          且该阶 < 真群阶，即卡在真子群里出不来）
      NOT_CAPPED       —— 没观察到封顶（一路涨到真群阶／停滞点就等于真群阶／
                          或停滞平台被更大预算跨过）
      INSUFFICIENT_DATA—— 数据不足（档位不够，顶档仍在增长且未达真群，无法判定）

    ⚠️ 关键区分：**平台 ≠ 封顶**。若某档停住但更大预算又涨上去，那只是平台，
    不是封顶。第一实例（Q_8）的 5,040 是到 250,000→1,000,000 都恒为 5,040，
    且**没有更大档能突破**，才叫封顶。本脚本因此必须扫到出现「突破或确认不突破」为止。
    """
    if not rows:
        return "INSUFFICIENT_DATA", "没有有效档位数据"
    top = rows[-1]["closure_order"]
    if stall is None:
        if top >= true_order:
            return "NOT_CAPPED", ("闭包阶随预算一路上升到 %d，已抵达真群阶 %d，"
                                  "全程无停滞档 ⇒ 未观察到封顶" % (top, true_order))
        return "INSUFFICIENT_DATA", (
            "扫到最大预算 %d 仍无停滞档且顶档 %d < 真群 %d，无法判定，需更大预算"
            % (rows[-1]["node_cap"], top, true_order))

    o = stall["order_at_stall"]
    later = [r for r in rows if r["node_cap"] > stall["to_cap"]]
    broke = any(r["closure_order"] > o for r in later)
    if not broke:
        if o >= true_order:
            return "NOT_CAPPED", ("停滞点阶 %d 已等于真群阶 %d，即预算饱和在完整群上，"
                                  "不存在真子群封顶" % (o, true_order))
        return "CAPPED", ("预算 %d → %d（再放大 %.1f 倍）闭包阶恒为 %d < 真群 %d，"
                          "且此后所有更大预算（至 %d）均未突破；同期生成元 %d → %d 虚增"
                          " ⇒ 封顶在阶 %d 的真子群"
                          % (stall["from_cap"], stall["to_cap"], stall["cap_ratio"],
                             o, true_order, rows[-1]["node_cap"],
                             stall["gens_from"], stall["gens_to"], o))
    if top >= true_order:
        return "NOT_CAPPED", (
            "预算 %d → %d（放大 %.1f 倍）出现过闭包阶恒为 %d 的**平台**（同期生成元 "
            "%d → %d 虚增），但该平台被更大预算跨过：%d 档起闭包阶升到 %d = 真群阶，"
            "纯预算即可拿到完整群 ⇒ 本实例**未观察到**不可逆的封顶，只观察到平台"
            % (stall["from_cap"], stall["to_cap"], stall["cap_ratio"], o,
               stall["gens_from"], stall["gens_to"], later[0]["node_cap"], top))
    return "INSUFFICIENT_DATA", (
        "停滞平台 %d 已被更大的 %d 档突破（升到 %d），但顶档 %d 仍未达真群 %d，"
        "无法判定最终是否存在封顶，需更大预算"
        % (o, later[0]["node_cap"], later[0]["closure_order"], top, true_order))


def main():
    print("=" * 96)
    print("第二实例验证：SYS-3 B（真群 S_2 × S_{n-2} × (Z_2)^{n-2}，非 S_n）")
    print("  问题：『预算封顶在子群、重启能跨越』是否只在 Q_n(S_n) 上成立？")
    print("  口径：max_gens 放开（10^9），只扫 node_cap —— 与原 scan 严格对齐")
    print("=" * 96)

    n, NS = 8, 1 << 8
    goal = set(s for s in range(NS) if (s & 3) == 3)     # 目标 = {位0=位1=1}
    trans = build_model_n(n, goal)

    # ---------- 真群 ----------
    all_gens = free_sym_gens(n)
    # 拆成两块，用来给「封顶点」验明身份
    perm_gens = [swap_gen(NS, 2, k) for k in range(3, n)]   # 自由位上的 S_{n-2}
    perm_gens.append(swap_gen(NS, 0, 1))                    # 交换 (0,1) 的 S_2
    xor_gens = [[s ^ (1 << j) for s in range(NS)] for j in range(2, n)]
    true_order, kept_true = closure_order(all_gens, NS)
    perm_order, kept_perm = closure_order(perm_gens, NS)
    formula = 2 * math.factorial(n - 2) * (2 ** (n - 2))
    print("\n真群 G = S_2 × S_{n-2} × (Z_2)^{n-2}：阶 = %d（n=%d，公式 2·%d!·2^%d = %d）"
          % (true_order, n, n - 2, n - 2, formula))
    print("  坐标置换子群 S_2 × S_{n-2} 阶 = %d ｜ 陪集数 = %s"
          % (perm_order, true_order // perm_order if true_order % perm_order == 0 else "?"))
    print("  非 S_n 的反证：%d 不等于任何 m!（%d!=%d < %d < %d!=%d）"
          % (true_order, n, math.factorial(n), true_order, n + 1, math.factorial(n + 1)))

    # ---------- 口径 A：放开输出上限，只扫搜索预算 ----------
    print("\n[口径A] max_gens 不设限，只扫 node_cap —— 纯预算效应")
    print("  %-10s %-9s %-12s %-9s %s" % ("node_cap", "生成元", "闭包阶", "耗时s", "较上一档"))
    rows, adj, color, kepts = scan(trans, n, NS)
    prev = None
    for r in rows:
        chg = ("闭包阶 %s -> %s %s"
               % (prev, r["closure_order"],
                  "↑继续上升" if prev is not None and r["closure_order"] > prev
                  else ("＝已停滞" if prev is not None else "（基线）")))
        print("  %-10d %-9d %-12d %-9.1f %s"
              % (r["node_cap"], r["n_gens"], r["closure_order"], r["sec"], chg))
        prev = r["closure_order"]
    ck = [r for r in rows if "pruning_consistent" in r]
    if ck:
        print("  交叉校验（原版 closure_perms vs 剪枝版）：%d 档，全部一致 = %s"
              % (len(ck), all(r["pruning_consistent"] for r in ck)))

    stall = stall_point(rows)
    v, why = verdict(rows, stall, true_order)

    # ---------- 停滞点 / 顶档的群身份识别（对应第一实例的『点稳定子 S_7』）----------
    print("\n[群身份] 展开真群元素集合用于比对（一次）…")
    s_true = set(map(tuple, closure_perms(kept_true, NS)))
    s_perm = set(map(tuple, closure_perms(kept_perm, NS)))

    def identify(idx, label):
        cl = closure_perms(kepts[idx], NS)
        s = set(map(tuple, cl))
        info = {"node_cap": rows[idx]["node_cap"], "order": len(s),
                "equals_coord_perm_subgroup": (s == s_perm),
                "equals_true_group": (s == s_true),
                "elements_inside_true_group": len(s & s_true),
                "index_in_true_group": (true_order // len(s)
                                        if s and true_order % len(s) == 0 else None)}
        print("  %s（node_cap=%d）阶 %d ｜ ==坐标置换子群 S_2×S_{n-2}(%d)? %s "
              "｜ ==真群(%d)? %s ｜ 落在真群内 %d/%d ｜ 指数 %s"
              % (label, info["node_cap"], info["order"], perm_order,
                 info["equals_coord_perm_subgroup"], true_order,
                 info["equals_true_group"], info["elements_inside_true_group"],
                 info["order"], info["index_in_true_group"]))
        return info

    cap_id = None
    if stall is not None:
        i_stall = [i for i, r in enumerate(rows)
                   if r["node_cap"] == stall["to_cap"]][0]
        cap_id = identify(i_stall, "停滞档")
    top_id = identify(len(rows) - 1, "顶档  ")

    # ---------- 对照：含随机重启的 discover ----------
    print("\n[对照] 确定性 + 随机重启（discover，同实例、同数据）")
    t0 = time.time()
    G, diag = discover(trans, n)
    el = time.time() - t0
    print("  闭包阶 = %d（真群 %d）｜ %.1fs" % (len(G), true_order, el))
    restart_full = (len(G) == true_order)

    # ---------- 辅助对照：SYS-1 的 D_n（小群，预期封顶不可观测）----------
    print("\n[辅助对照] SYS-1 哲学家就餐 D_n —— 验证『小群上封顶不可观测』")
    small = {}
    try:
        from experiments_sys1 import dining_states, dining_trans
        for m in (5,):
            st = dining_states(m)
            NSm = len(st)
            trm = dining_trans(m, st)
            adjm = backbone_adj(trm, m)
            cm = wl_refine(adjm)
            rr = []
            for nc in (1000, 4000, 16000, 64000):
                tA = time.time()
                gm = graph_automorphisms(adjm, cm, max_gens=NO_CAP, node_cap=nc)
                om, _k = closure_order(gm, NSm)
                rr.append({"node_cap": nc, "n_gens": len(gm),
                           "closure_order": om,
                           "sec": round(time.time() - tA, 3)})
            small["D_%d" % m] = {"NS": NSm, "true_group_order": 2 * m, "rows": rr}
            print("  D_%d（真群阶 %d，状态数 %d）：%s"
                  % (m, 2 * m, NSm,
                     " / ".join("cap%d→阶%d(gens%d)" % (r["node_cap"],
                                                        r["closure_order"], r["n_gens"])
                                for r in rr)))
    except Exception as e:                       # 辅助对照失败不影响主结论
        small["error"] = "%s: %s" % (type(e).__name__, e)
        print("  辅助对照未跑成：%s" % small["error"])

    # ---------- 落盘 ----------
    out = {
        "instance": "SYS-3 B（目标 = {位0=位1=1}）",
        "source": "src/experiments_restart_scan2.py（建模复用 src/experiments_sys3.py）",
        "n": n, "NS": NS,
        "true_group": "S_2 × S_{n-2} × (Z_2)^{n-2}",
        "true_order": true_order,
        "true_order_formula": "2*(n-2)!*2^(n-2) = %d" % formula,
        "is_Sn": False,
        "not_Sn_reason": ("阶 %d 不等于任何 m!（%d!=%d < %d < %d!=%d），且含 (Z_2)^{n-2} "
                          "平移因子，与对称群不同构"
                          % (true_order, n, math.factorial(n), true_order,
                             n + 1, math.factorial(n + 1))),
        "coord_perm_subgroup": "S_2 × S_{n-2}",
        "coord_perm_subgroup_order": perm_order,
        "n_xor_gens": len(xor_gens),
        "max_gens": NO_CAP,
        "caps": list(CAPS),
        "scan_unbounded": rows,
        "stall_point": stall,
        "plateau": ({"node_cap_from": stall["from_cap"],
                     "node_cap_to": stall["to_cap"],
                     "order": stall["order_at_stall"],
                     "budget_ratio": stall["cap_ratio"],
                     "broken_by_larger_budget":
                         any(r["closure_order"] > stall["order_at_stall"]
                             for r in rows if r["node_cap"] > stall["to_cap"])}
                    if stall else None),
        "cap_identity": cap_id,
        "top_identity": top_id,
        "restart": {"closure_order": len(G), "sec": round(el, 3),
                    "full": restart_full, "diag": dict(diag)},
        "max_order_by_budget": max(r["closure_order"] for r in rows),
        "verdict": v,
        "verdict_reason": why,
        "aux_Dn": small,
    }

    print("\n[结论] %s" % v)
    print("  %s" % why)
    print("  纯预算能拿到的最大闭包阶 = %d / 真群 %d（差 %.1f 倍）"
          % (out["max_order_by_budget"], true_order,
             true_order / max(out["max_order_by_budget"], 1)))
    print("  随机重启：%s（闭包阶 %d）"
          % ("拿到完整群" if restart_full else "未达完整群", len(G)))

    with open(os.path.join(ROOT, "experiments_restart_scan2.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_restart_scan2.json")


if __name__ == "__main__":
    main()
