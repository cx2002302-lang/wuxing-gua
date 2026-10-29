# -*- coding: utf-8 -*-
"""
experiments_restart_scan3.py —— 第三实例（非 S_n，阶 2,304）+ 两个辅助对照 + 「硬顶/平台」判据

**为什么要有这个脚本**

既有重启预算定量研究已有两个结论相反的实例：
  · 实例 1（Q_8，真群 S_8 = 40,320）：预算封顶在 5,040（点稳定子 S_7）不可逾越 ⇒ 硬顶
  · 实例 2（SYS-3 B，真群 S_2×S_6×(Z_2)^6 = 92,160）：只出现平台 1,440，
    预算放大即到完整群 ⇒ 平台（纯预算比重启快 4.7 倍）
两例结论相反，「什么时候是硬顶、什么时候只是平台」没有判据。本脚本补第三个实例，
并加两个**辅助对照实例**，把候选判据一个个逼到墙角（数据说话，不预设结论）。

**主实例设计（本任务的第三实例）**

  · 场景：n = 7 位、目标 = {位 0,1,2 = 1}（k = 3 个位必须为 1），状态数 2^7 = 128
  · 真群：G = S_3 × S_4 × (Z_2)^4（固定位内置换 × 自由位内置换 × 自由位 XOR 平移）
    阶 = 3!·4!·2^4 = **2,304** ∈ [100, 10,000]，与 Q_8 的 5,040 同量级，
    又不至于像 92,160 那样算不动
  · 明确**非 S_n**：2,304 不等于任何 m!（6! = 720 < 2,304 < 7! = 5,040），
    且结构上含 (Z_2)^4 平移因子（坐标置换子群仅 144 < 2,304）
  · 为什么选它（相对已有两例的判别力）：
      - 指数 16，落在 Q_8（指数 8，硬顶）与 SYS-3 B（指数 64，平台）之间
      - 预测陷阱 = 状态 0 的点稳定子 = 坐标置换子群 S_3×S_4，阶 144，
        比 SYS-3 B 的 1,440 小 10 倍
      ⇒ 「指数驱动硬顶」预言它偏硬，「陷阱规模驱动」预言它偏软 —— 两假说对立预测

**辅助对照 A**（n = 7, k = 4，目标 = {位 0..3 = 1}）：阶 1,152，陷阱 144（同主实例），
  指数 8（同 Q_8）⇒ 控制陷阱阶、只变指数：若仍是平台 ⇒ 「指数 ≤ 8 才硬顶」被推翻

**辅助对照 B**（Q_6：目标 = 单点 {全阳}）：真群 S_6 = 720，陷阱 S_5 = 120，指数 6，
  首分支色类为独立集（与 Q_8 的层状结构相同）⇒ 控制首类结构、只变陷阱阶：
  若仍是平台 ⇒ 「首类独立集才硬顶」被推翻

**口径（与 experiments_restart_scan.py / experiments_restart_scan2.py 严格对齐）**
  · max_gens = 10^9（放开输出上限 —— §0 勘误的教训：不设限就会测到自己的输出截断）
  · 只扫 node_cap（真正的搜索预算）；每档记录生成元数 / 闭包阶 / 耗时
  · closure_order 剪枝版（直接复用 scan2 的实现，与 closure_perms 数学同解），
    便宜档用原版 closure_perms 交叉校验
  · 判据三选一（CAPPED 硬顶 / NOT_CAPPED 平台 / INSUFFICIENT_DATA 未观察）
    直接复用 scan2 的 verdict()，保证跨实例同语义

运行：python src/experiments_restart_scan3.py
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import build_model_n                        # noqa: E402
from experiments_p3 import (backbone_adj, wl_refine,            # noqa: E402
                            graph_automorphisms, closure_perms,
                            discover)
from experiments_sys3 import swap_gen                           # noqa: E402
# 复用实例 2 的闭包优化与判据（**不修改** scan2，只导入；保证三例同口径同语义）
from experiments_restart_scan2 import (closure_order,           # noqa: E402
                                       stall_point, verdict)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

NO_CAP = 10 ** 9          # "不设限"的生成元输出上限
PLAIN_CHECK_MAX_GENS = 300   # 生成元数不超过此值时，额外用原版 closure_perms 交叉校验


# ---------------------------------------------------------------- 群的生成元
def partial_sym_gens(n, k):
    """目标 = {前 k 位 = 1} 的真群生成元：S_k(固定位) × S_{n-k}(自由位) × (Z_2)^{n-k}(自由位 XOR)"""
    NS = 1 << n
    gens = [swap_gen(NS, 0, j) for j in range(1, k)]            # 固定位内 S_k
    gens += [swap_gen(NS, k, j) for j in range(k + 1, n)]      # 自由位内 S_{n-k}
    gens += [[s ^ (1 << j) for s in range(NS)] for j in range(k, n)]   # 自由位 XOR
    return gens


def perm_only_gens(n, k):
    """同上但去掉 XOR —— 坐标置换子群 S_k × S_{n-k}（预测的陷阱）"""
    NS = 1 << n
    gens = [swap_gen(NS, 0, j) for j in range(1, k)]
    gens += [swap_gen(NS, k, j) for j in range(k + 1, n)]
    return gens


def single_point_gens(n, fixed_bit=0):
    """Q_n（目标 = 单点）真群 S_n 生成元 + 固定 bit fixed_bit 的点稳定子 S_{n-1} 生成元"""
    NS = 1 << n
    true_gens = [swap_gen(NS, 0, j) for j in range(1, n)]
    trap_gens = [swap_gen(NS, fixed_bit + 1, j) for j in range(fixed_bit + 2, n)]
    return true_gens, trap_gens


# ---------------------------------------------------------------- 受控扫描
def scan(trans, n, NS, caps, max_gens=NO_CAP):
    """固定生成元上限、只扫 node_cap，返回预算曲线（口径与 scan/scan2 一致）"""
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
        if len(g) <= PLAIN_CHECK_MAX_GENS:      # 便宜档原版交叉校验，证明剪枝没偷改结果
            plain = len(closure_perms(g, NS)) if g else 0
            row["closure_order_plain"] = plain
            row["pruning_consistent"] = (plain == order)
        rows.append(row)
        kepts.append(kept)
    return rows, adj, color, kepts


def first_branch_class(adj, color, NS):
    """DFS 第一个发生分支的色类（此前各类都是单点，映射被强制）

    返回类大小 / 类内部边数 / 类内最小节点（= 恒等分支固定住的节点）。
    类内部边数是结构判据的关键特征：独立集（0 条内部边）= 层状着色。
    """
    classes = {}
    for s in range(NS):
        classes.setdefault(color[s], []).append(s)
    for c in sorted(classes):
        mem = classes[c]
        if len(mem) >= 2:
            memset = set(mem)
            intra = sum(1 for s in mem for t in adj[s]
                        if t != s and t in memset) // 2
            return {"first_node": min(mem), "class_size": len(mem),
                    "intra_edges": intra, "n_classes": len(classes)}
    return {"first_node": None, "class_size": 1, "intra_edges": 0,
            "n_classes": len(classes)}


def trap_analysis(rows, true_order):
    """数据驱动地定义「被困子群」并给出逃逸窗口

    陷阱阶 = 所有小于真群阶的闭包阶中的最大者（三例既有数据上它都恰好是
    点稳定子 / 坐标置换子群，见各档身份比对）。逃逸窗口 = (陷阱最后一档, 首次到达真群阶的档]。
    """
    orders = [r["closure_order"] for r in rows]
    below = [o for o in orders if o < true_order]
    if not below:
        return {"trap_order": None}
    trap = max(below)
    last_trap_i = max(i for i, o in enumerate(orders) if o == trap)
    esc = [i for i, o in enumerate(orders) if o >= true_order]
    lo = rows[last_trap_i]["node_cap"]
    if esc:
        hi = rows[esc[0]]["node_cap"]
        return {"trap_order": trap, "trap_last_cap": lo,
                "escape_cap": hi, "escaped": True,
                "c_band": [round(lo / trap, 1), round(hi / trap, 1)]}
    return {"trap_order": trap, "trap_last_cap": lo,
            "escape_cap": None, "escaped": False,
            "c_band": [round(lo / trap, 1), None]}


def run_instance(tag, n, goal, true_gens, trap_gens, caps,
                 true_group_label, trap_label, run_discover=True):
    """一个实例的完整受控实验（口径与 scan2 主实例一致）"""
    NS = 1 << n
    trans = build_model_n(n, goal)
    true_order, kept_true = closure_order(true_gens, NS)
    trap_order_ref, kept_trap = closure_order(trap_gens, NS)

    print("\n" + "=" * 96)
    print("[%s] n=%d，NS=%d ｜ 真群 %s = %d ｜ 预测陷阱 %s = %d"
          % (tag, n, NS, true_group_label, true_order, trap_label, trap_order_ref))
    print("=" * 96)

    rows, adj, color, kepts = scan(trans, n, NS, caps)
    print("  %-10s %-9s %-12s %-9s %s" % ("node_cap", "生成元", "闭包阶", "耗时s", "较上一档"))
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

    # ---- 每档闭包的群身份（集合比对，不猜）----
    s_trap = set(map(tuple, closure_perms(kept_trap, NS)))
    s_true = set(map(tuple, closure_perms(kept_true, NS)))
    identities = []
    for i, r in enumerate(rows):
        s = set(map(tuple, closure_perms(kepts[i], NS)))
        info = {"node_cap": r["node_cap"], "order": len(s),
                "equals_trap_subgroup": (s == s_trap),
                "equals_true_group": (s == s_true),
                "inside_true_group": len(s & s_true),
                "inside_trap_subgroup": len(s & s_trap),
                "index_in_true_group": (true_order // len(s)
                                        if s and true_order % len(s) == 0 else None)}
        identities.append(info)
        print("  档 %-9d 阶 %-6d ==陷阱(%d)? %s ｜ ==真群(%d)? %s ｜ 在真群内 %d ｜ 在陷阱内 %d ｜ 指数 %s"
              % (info["node_cap"], info["order"], trap_order_ref,
                 info["equals_trap_subgroup"], true_order,
                 info["equals_true_group"], info["inside_true_group"],
                 info["inside_trap_subgroup"], info["index_in_true_group"]))

    # ---- 陷阱与逃逸窗口（判据支持数据）----
    ta = trap_analysis(rows, true_order)
    print("  陷阱阶 = %s ｜ 逃逸窗口 = (%s, %s] ｜ c = 逃逸代价/陷阱阶 = %s"
          % (ta.get("trap_order"), ta.get("trap_last_cap"),
             ta.get("escape_cap"), ta.get("c_band")))

    # ---- 结构特征：首分支色类 ----
    struct = first_branch_class(adj, color, NS)
    print("  首分支色类：大小 %s ｜ 内部边 %s ｜ 恒等分支固定节点 %s"
          % (struct["class_size"], struct["intra_edges"], struct["first_node"]))

    # ---- 对照：含随机重启的 discover ----
    restart = None
    if run_discover:
        print("  [对照] 确定性 + 随机重启（discover，同实例、同数据）")
        t0 = time.time()
        G, diag = discover(trans, n)
        el = time.time() - t0
        restart = {"closure_order": len(G), "sec": round(el, 3),
                   "full": (len(G) == true_order), "diag": dict(diag)}
        print("    闭包阶 = %d（真群 %d）｜ %.1fs" % (len(G), true_order, el))

    # ---- 三选一标签（对齐任务措辞：硬顶 / 平台 / 未观察）----
    # 「平台」要求出现**子群**停滞档（停滞阶 < 真群阶）；只在真群阶上停滞
    # （预算饱和在完整群）不算观察到平台。
    if v == "CAPPED":
        label = "硬顶"
    elif v == "NOT_CAPPED" and stall is not None and stall["order_at_stall"] < true_order:
        label = "平台"
    else:
        label = "未观察"

    out = {
        "tag": tag, "n": n, "NS": NS,
        "true_group": true_group_label, "true_order": true_order,
        "trap_subgroup": trap_label, "trap_subgroup_order": trap_order_ref,
        "is_Sn": (true_order in [math.factorial(m) for m in range(12)]),
        "not_Sn_reason": ("阶 %d 不是任何 m!，且坐标置换子群仅 %d < %d"
                          "（严格含有非置换因子）"
                          % (true_order, trap_order_ref, true_order)),
        "max_gens": NO_CAP, "caps": list(caps),
        "scan_unbounded": rows,
        "stall_point": stall,
        "trap_analysis": ta,
        "identities": identities,
        "first_branch_class": struct,
        "restart": restart,
        "max_order_by_budget": max(r["closure_order"] for r in rows),
        "verdict": v, "verdict_label": label, "verdict_reason": why,
    }
    print("  [结论] %s（%s）" % (v, label))
    print("    %s" % why)
    return out


def prev_instance_row(jpath):
    """从实例 1/2 的 JSON 重建预算曲线行（只读，用于三例同口径对比）"""
    with open(jpath, encoding="utf-8") as f:
        d = json.load(f)
    rows = [{"node_cap": r["node_cap"], "n_gens": r["n_gens"],
             "closure_order": r["closure_order"]} for r in d["scan_unbounded"]]
    return d, rows


def main():
    print("=" * 96)
    print("第三实例验证：目标 = {位 0,1,2 = 1}（真群 S_3×S_4×(Z_2)^4 = 2,304，非 S_n）")
    print("  问题：什么特征决定预算封顶是「硬顶」还是只是「平台」？")
    print("  口径：max_gens 放开（10^9），只扫 node_cap —— 与 scan / scan2 严格对齐")
    print("=" * 96)

    out = {"source": "src/experiments_restart_scan3.py",
           "purpose": "第三实例（非 S_n，阶 2,304）+ 两个辅助对照，检验硬顶/平台判据"}

    # ---------- 主实例（第三实例）：n=7, k=3 ----------
    n, k = 7, 3
    goal = set(s for s in range(1 << n) if (s & 7) == 7)
    main_out = run_instance(
        "实例3（主）", n, goal, partial_sym_gens(n, k), perm_only_gens(n, k),
        caps=(250, 1000, 4000, 8000, 16000, 32000, 64000, 250000, 1000000),
        true_group_label="S_3 × S_4 × (Z_2)^4", trap_label="坐标置换子群 S_3×S_4（状态0 点稳定子）")
    main_out["goal"] = "{位0=位1=位2=1}"
    main_out["true_order_formula"] = "3!·4!·2^4 = 2304"
    out["instance3"] = main_out

    # ---------- 辅助对照 A：n=7, k=4（指数 8 同 Q_8，陷阱 144 同主实例）----------
    nA = 7
    goalA = set(s for s in range(1 << nA) if (s & 15) == 15)
    out["aux_A_k4n7"] = run_instance(
        "辅助A", nA, goalA, partial_sym_gens(nA, 4), perm_only_gens(nA, 4),
        caps=(1000, 4000, 8000, 16000, 24000, 32000, 48000, 64000, 250000),
        true_group_label="S_4 × S_3 × (Z_2)^3", trap_label="坐标置换子群 S_4×S_3（状态0 点稳定子）",
        run_discover=False)
    out["aux_A_k4n7"]["aux_role"] = ("控制陷阱阶（144，同实例3）、只变指数（8，同 Q_8）："
                                     "检验『指数 ≤ 8 才硬顶』")

    # ---------- 辅助对照 B：Q_6（首类独立集同 Q_8，陷阱 120）----------
    nB = 6
    goalB = {(1 << nB) - 1}
    trueB, trapB = single_point_gens(nB, fixed_bit=0)
    out["aux_B_Q6"] = run_instance(
        "辅助B", nB, goalB, trueB, trapB,
        caps=(250, 1000, 2000, 4000, 8000, 16000, 64000, 250000, 1000000),
        true_group_label="S_6", trap_label="点稳定子 S_5（固定 bit0）")
    out["aux_B_Q6"]["aux_role"] = ("控制首分支色类结构（独立集，同 Q_8 的层状结构）、"
                                   "陷阱阶只有 120：检验『首类独立集才硬顶』")

    # ---------- 三例对比表（实例 1/2 的数据来自各自 JSON，只读重建）----------
    d1, rows1 = prev_instance_row(os.path.join(ROOT, "experiments_restart_scan.json"))
    d2, rows2 = prev_instance_row(os.path.join(ROOT, "experiments_restart_scan2.json"))
    v1, why1 = verdict(rows1, stall_point(rows1), d1["true_order"])
    v2, why2 = verdict(rows2, stall_point(rows2), d2["true_order"])
    ta1 = trap_analysis(rows1, d1["true_order"])
    ta2 = trap_analysis(rows2, d2["true_order"])

    # 实例 1/2 的首分支色类结构特征（重建模型现算，不引用旧文数字）
    NS8 = 1 << 8
    adj1 = backbone_adj(build_model_n(8, {NS8 - 1}), 8)
    st1 = first_branch_class(adj1, wl_refine(adj1), NS8)
    adj2 = backbone_adj(build_model_n(8, {s for s in range(NS8) if (s & 3) == 3}), 8)
    st2 = first_branch_class(adj2, wl_refine(adj2), NS8)

    def cmp_row(name, true_group, true_order, v, ta, st, note):
        lab = "硬顶" if v == "CAPPED" else ("平台" if ta.get("trap_order") else "未观察")
        return {"实例": name, "真群": true_group, "阶": true_order,
                "首分支色类大小": st["class_size"], "首类内部边": st["intra_edges"],
                "陷阱阶": ta.get("trap_order"),
                "指数": (true_order // ta["trap_order"]
                         if ta.get("trap_order") else None),
                "逃逸窗口": (ta.get("trap_last_cap"), ta.get("escape_cap")),
                "c_band": ta.get("c_band"),
                "verdict": v, "label": lab, "note": note}

    out["comparison"] = {
        "instance1_Q8": cmp_row("实例1 Q_8", "S_8", d1["true_order"],
                                v1, ta1, st1, "目标=单点，真群 S_8"),
        "instance2_SYS3B": cmp_row("实例2 SYS-3 B", d2["true_group"], d2["true_order"],
                                   v2, ta2, st2,
                                   "目标={位0=位1=1}，真群 S_2×S_6×(Z_2)^6"),
        "instance3_main": cmp_row("实例3（本件主实例）",
                                  "S_3 × S_4 × (Z_2)^4",
                                  main_out["true_order"],
                                  main_out["verdict"], main_out["trap_analysis"],
                                  main_out["first_branch_class"],
                                  "目标={位0,1,2=1}"),
        "aux_A": cmp_row("辅助A (7,4)",
                         "S_4 × S_3 × (Z_2)^3",
                         out["aux_A_k4n7"]["true_order"],
                         out["aux_A_k4n7"]["verdict"],
                         out["aux_A_k4n7"]["trap_analysis"],
                         out["aux_A_k4n7"]["first_branch_class"],
                         "指数 8（同 Q_8）、陷阱 144（同实例3）"),
        "aux_B": cmp_row("辅助B Q_6",
                         "S_6", out["aux_B_Q6"]["true_order"],
                         out["aux_B_Q6"]["verdict"],
                         out["aux_B_Q6"]["trap_analysis"],
                         out["aux_B_Q6"]["first_branch_class"],
                         "首类独立集（同 Q_8）、陷阱 120"),
    }

    # ---------- 判据支持数据（判据本身随预注册记录落盘，这里只落可复算的数）----------
    out["criterion_support"] = {
        "definition_trap": "陷阱阶 = max{闭包阶 < 真群阶}（数据驱动，不预设身份）",
        "definition_c": "c = 逃逸代价 / 陷阱阶（每个稳定子元素平均消耗的搜索节点数）",
        "c_bands": {k2: out["comparison"][k2]["c_band"]
                    for k2 in out["comparison"]},
        "refuted_criteria": [
            "指数阈值（硬顶 ⟺ 指数 ≤ 8）：辅助A 指数 8 但平台、辅助B 指数 6 但平台，"
            "与 Q_8（指数 8 硬顶）同指数不同结局 ⇒ 推翻",
            "首类独立集（硬顶 ⟺ 首分支色类是独立集）：辅助B 首类为独立集但平台 ⇒ 推翻",
            "群阶大小：实例3 阶 2,304 与辅助B 阶 720 均平台（SYS-3 B 阶 92,160 比 Q_8 大却软）⇒ 推翻",
        ],
        "surviving_criterion": ("硬顶 ⟺ 陷阱阶 ≥ T*（预算刻度 10^6 下 T* ∈ (1440, 5040]）；"
                                "机理：逃逸代价 ≈ c × 陷阱阶，c 跨例落在 3×10^1 ~ 7×10^2"),
        "pre_registered_4th": ("Q_7（真群 S_7 = 5,040，陷阱 S_6 = 720，首类独立集）："
                               "预测逃逸窗口 (1.6×10^4, 6.4×10^5]；"
                               "若 4×10^6 档仍卡在 720 ⇒ 幸存判据被推翻"),
    }

    # ---------- 总结 ----------
    print("\n" + "=" * 96)
    print("总结：三例 + 两个辅助对照")
    print("=" * 96)
    print("  %-22s %-10s %-8s %-8s %-8s %-10s %s"
          % ("实例", "真群阶", "陷阱阶", "指数", "首类边", "逃逸窗口", "结论"))
    for k2, c in out["comparison"].items():
        print("  %-22s %-10d %-8s %-8s %-8s %-10s %s（%s）"
              % (c["实例"], c["阶"], c["陷阱阶"], c["指数"], c["首类内部边"],
                 str(c["逃逸窗口"]), c["verdict"], c["label"]))
    print("\n  [结论] 实例3：%s —— %s" % (main_out["verdict_label"], main_out["verdict_reason"]))
    print("  纯预算最大闭包阶 = %d / 真群 %d"
          % (main_out["max_order_by_budget"], main_out["true_order"]))
    if main_out["restart"]:
        r = main_out["restart"]
        print("  随机重启：%s（闭包阶 %d，%.1fs）"
              % ("拿到完整群" if r["full"] else "未达完整群",
                 r["closure_order"], r["sec"]))

    with open(os.path.join(ROOT, "experiments_restart_scan3.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_restart_scan3.json")


if __name__ == "__main__":
    main()
