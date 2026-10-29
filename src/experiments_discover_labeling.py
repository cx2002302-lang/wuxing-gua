# -*- coding: utf-8 -*-
"""
experiments_discover_labeling.py —— discover 编号伪像系统化扫描

【问题】升级前事件实证了「discover 的最终群本身随输入编号变」
  （平移 Q₆：plain 只找到 6 阶/32 轨道，--canonize 找到完整 720 阶/7 轨道，
   selftest 分支 9 / audit w5.canon.crippled 同源构造）。这提出一个问题：
  项目历史所有 discover 数字（720/40320/294912/…）会不会都是
  「标准编号下的幸运值」？本脚本把伪像的影响面量出来。

【设计（预注册纪律：判读规则先落盘再跑，规则常量见 RULES）】
  1. 环境集（全部有 ground truth 真群可对照，真群全部本脚本内实跑验证/回源）：
       Q4 / Q5 / Q6 / Q7  —— n 位翻转 MDP（experiments_e1.build_model_n，
                             目标 {2^n-1}），真群 = 单点目标超立方体自同构稳定子
                             = S_n（本脚本对全部 n!·2^n 个超立方体自同构候选
                             穷举 + 通用等变检验逐一判定，见 verify_true_group_bitflip）
       K44                —— 完全二分图 MDP（experiments_restart_scan5.build_knn），
                             真群穷举 = 全部 8! 置换逐一判定（期望 (S_4×S_4)⋊Z_2 = 1152）
       Heawood            —— Heawood 图 MDP（experiments_restart_scan6.build_heawood），
                             真群 = 完整回溯穷举（保邻接一致 + 叶点全量通用判定，
                             期望 PGL(2,7) = 336；与 true_gens_heawood 闭包对拍）
       六十四卦            —— experiments_gua64.build_gua64；真群(soft 口径) =
                             589,824（回源 experiments_gua64_aut.json 穷举定论；
                             本脚本真跑复验：机器群 294,912 + 并集群 589,824 两个
                             交叉 assert 与该 json 逐位一致）
  2. 编号集（每环境 13 个编号实例）：标准编号 + 随机重编号 10 个种子
     （random.Random(seed).sample，seed=1..10）+ 平移 + 反转。
     重编号 = 状态置换 π，转移/奖励/目标随 π 共轭：trans'[π(s)][a] =
     [(p, π(u), r) for (p,u,r) in trans[s][a]]——环境数学上同构，仅名字变；
     真群变为 π·G·π^{-1}（阶不变）。
  3. 每实例跑两臂：plain discover（discover_gua）与 canonize discover
     （_canonize_model / _discover_canon_generic：与 wuxing_gua/core_discover 的
     canonize 路径同口径——同一个 canonize（§16 规范 WL + 个体化-细化树 +
     lex-min 证书）+ 同一套三路图搜索超参（max_gens=48 / 重启 40 次 seed=7 /
     对合搜索 24 次 seed=7 / MRV fallback / 闭包 + 哨兵复检），唯一差异是
     等变检验函数用泛化版 equiv_error_gua（动作 = 从 trans 取骨干后继再配对，
     编号无关），因为随机重编号后的转移表不再是「动作 a = 翻转第 a 位」的
     位串口径，p3.equiv_error 的位串闸门对它不适用。位串实例（标准/平移/
     反转编号的 Q_n）上两judge 等价——本脚本在 Q₆ 标准与平移两个桥接实例上
     真跑 p3.discover 与 discover_gua 断言同阶同轨道（结果记 bridge.judge_equiv）。
     六十四卦骨干图是 64 顶点非连通图（2 个 32 态弱分量），整体 canonize 超
     CANON_NODE_CAP（实测探针超限）⇒ 对该环境用「逐分量 canonize + 按证书排序
     拼接」的规范化扩展（两分量去重出边数 94/86 不同构 ⇒ 分量证书互异 ⇒ 全序
     良定义；拼接序经 isom_map_ok 硬校验），其余单分量环境走 _canonize_model 原路径。
  4. 预注册判读规则（先写死，见 RULES）：完全丢失 / 部分损失 / 幸运全中 /
     canonize 修复率 / canonize 残余伪像。
  5. 汇总口径：按环境与全局两层分布（中位/最小群阶比/完全丢失率/修复率/
     残余伪像数），落 experiments_discover_labeling.json（每环境跑完即增量落盘）。

【断点续跑】脚本每次启动先读已有输出 json，复用其中已完成的 ground truth / 桥接 /
  历史重查 / 矩阵条目，只补算缺失的条目（矩阵条目按 (env, kind, seed) 索引，并逐条
  比对编号置换 π 与真群阶后才复用，防止口径漂移后误用旧数）。被中断后直接重跑同一条
  命令即可续跑；`--fresh` 强制从零重跑。meta.resume 记录本次「复用/新算」的条目数。

【运行】python -X utf8 src/experiments_discover_labeling.py            # 全量（自动续跑）
        python -X utf8 src/experiments_discover_labeling.py --envs Q6  # 单环境（调试）
        python -X utf8 src/experiments_discover_labeling.py --fresh    # 忽略已有 json，从零重跑
        python -X utf8 src/experiments_discover_labeling.py --out <路径>  # 指定输出（续跑自测用）
【输出】experiments_discover_labeling.json（项目根）+ 终端人话摘要
"""
import argparse
import hashlib
import itertools
import json
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from experiments_e1 import build_model_n, orbits_of                       # noqa: E402
from experiments_p3 import (backbone_adj, closure_perms, discover as      # noqa: E402
                            discover_p3, graph_automorphisms,
                            graph_automorphisms_rr, involution_automorphisms,
                            graph_automorphisms_mrv, wl_refine)
from experiments_gua64 import build_gua64, discover_gua, equiv_error_gua   # noqa: E402
from experiments_restart_scan5 import build_knn, true_gens_knn             # noqa: E402
from experiments_restart_scan6 import build_heawood, true_gens_heawood     # noqa: E402
from experiments_canonical_search import canonize as graph_canonize        # noqa: E402
from experiments_ovh_relabel import relabel as relabel_adj, isom_map_ok    # noqa: E402
from experiments_c_attribution import true_gens_nk                         # noqa: E402
from wuxing_gua.core_discover import _canonize_model, run_discover         # noqa: E402

OUT_JSON = os.path.join(ROOT, "experiments_discover_labeling.json")
GT_AUT_JSON = "experiments_gua64_aut.json"     # 真群回源（穷举定论）

# ================================================================ 预注册区
# 判读规则（预注册原文口径，写死于矩阵跑之前）
RULES = {
    "completely_lost": "plain 群阶 < 真群/10 ⇒ 完全丢失",
    "partial_loss": "真群/10 ≤ plain 群阶 < 真群 ⇒ 部分损失",
    "lucky_full_hit": "plain 群阶 == 真群 ⇒ 幸运全中",
    "canon_repair_rate": "canon 臂达真群（== 真群）的实例比例",
    "canon_residual_artifact": "canon 臂仍 < 真群的实例数；若 >0 是重要发现："
                               "canonize 只部分消除实现敏感性",
    "note": "顺序不可换：先判完全丢失，再判部分损失，再判幸运全中；"
            "ratio ≤ 1 恒成立（通过等变检验的候选都是真自同构，闭包 ⊆ 真群），"
            "脚本对越界硬 assert。",
}

# 预注册预测（写于矩阵跑之前；跑完在 result.json 里逐条核对，不作为判据）
PREREG_PREDICTIONS = [
    "Q_n 标准编号 plain = n!（幸运全中；历史 p3.json Q6=720/Q8=40320 同口径复现）；",
    "Q6 平移编号（c=51）plain = 6/32（documented 事件复现，selftest 分支 9 同源）；",
    "随机重编号上 plain 大幅塌陷（候选生成器只产生当前编号下骨干图自同构，"
    "搜索收获随编号变）；",
    "canon 臂在同一环境的不同编号实例上结果恒定（canonize 规范编号消去 id 依赖）；",
    "Q_n 环境 canon 臂 = n!（Q6 平移实例 documented 720/7 外推）；",
    "六十四卦 canon 臂 < 真群（探针实测 32，canonize 残余伪像实锤）。",
]

N_RANDOM_SEEDS = 10            # 随机重编号种子数（预注册 ≥10）
SHIFT_C = 51                   # 平移量（与 documented 平移 Q₆ 事件 demo_env.TRANSLATE_C 同源）
TOL = 1e-9                     # 等变判 tolerance（与 p3/gua64 原版一致）


def sec_of(t0):
    return round(time.perf_counter() - t0, 2)


# ================================================================ 断点续跑
def load_prior(path):
    """
    读已有输出 json 供续跑复用；文件不存在/损坏/口径漂移则返回 None（本次从零跑）。
    口径漂移 = 已有 json 的编号计划常量（平移量 shift_c、随机种子表）与本脚本不一致。
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            prior = json.load(f)
    except (ValueError, OSError) as e:
        print("  [续跑] 已有 json 无法解析（%s），本次从零跑" % e)
        return None
    meta = prior.get("meta") or {}
    if meta.get("shift_c") != SHIFT_C or meta.get("random_seeds") != list(
            range(1, N_RANDOM_SEEDS + 1)):
        print("  [续跑] 已有 json 的编号计划与本脚本不一致（shift_c=%r / seeds=%r），"
              "拒绝复用，本次从零跑" % (meta.get("shift_c"), meta.get("random_seeds")))
        return None
    return prior


def prior_matrix_index(prior):
    """已有矩阵条目索引：key = (env, kind, seed) → 记录。"""
    idx = {}
    for rec in (prior.get("matrix") or []):
        num = rec.get("numbering") or {}
        idx[(rec.get("env"), num.get("kind"), num.get("seed"))] = rec
    return idx


def reusable_matrix_record(rec, num, true_order):
    """已有条目能否复用：编号置换 π 逐位一致 + 真群阶一致（防口径漂移后误用旧数）。"""
    return (rec.get("numbering", {}).get("pi") == num["pi"]
            and rec.get("true_order") == true_order
            and rec.get("plain", {}).get("order") is not None
            and rec.get("canon", {}).get("order") is not None)


# ================================================================ 通用等变 judge
# 编号无关判据 = equiv_error_gua（experiments_gua64.py 建立的泛化版：
# 从 trans 取每个 (s,a) 的骨干后继，在 π(s) 的动作中搜索能接住 π(后继) 的动作；
# max TV=0 零容忍）。位串实例上与 p3.equiv_error 判定等价（bridge.judge_equiv 实证）。

# ================================================================ 真群验证
def permute_bits(x, perm, n):
    """按坐标置换 perm 重排 x 的位：结果第 i 位 = x 第 perm[i] 位。"""
    y = 0
    for i in range(n):
        if (x >> perm[i]) & 1:
            y |= 1 << i
    return y


def verify_true_group_bitflip(n):
    """
    Q_n 真群穷举验证：候选全集 = 全部超立方体自同构（n!·2^n 个，坐标置换 × XOR 平移），
    完全必要条件过滤（π(目标) ∈ 目标集——吸收态必须映到吸收态），
    幸存者逐一过通用等变 judge（max TV=0）。
    数学完备性：等变 ⇒ 骨干有向边保持 ⇒ π 是超立方体图自同构且目标映目标
    （目标态吸收自环是唯一自环 ⇒ 必须不动）⇒ 候选全集覆盖真群。
    交叉对拍：幸存集 == closure(true_gens_nk(n, n))（S_n，阶 n!）。
    """
    NS = 1 << n
    goal = NS - 1
    trans = build_model_n(n, {goal})
    survivors = []
    t0 = time.perf_counter()
    for c in range(NS):
        v = goal ^ c
        for perm in itertools.permutations(range(n)):
            if permute_bits(v, perm, n) != goal:
                continue                      # 目标必须映到目标（完全必要条件）
            pi = [permute_bits(s ^ c, perm, n) for s in range(NS)]
            e, _ = equiv_error_gua(trans, pi, n)
            if e == 0:
                survivors.append(tuple(pi))
    gens = [list(g) for g in true_gens_nk(n, n)]
    ref = {tuple(g) for g in closure_perms(gens, NS)}
    surv_set = set(survivors)
    assert len(survivors) == len(surv_set), "穷举幸存集有重复"
    assert surv_set == ref, ("Q%d 穷举真群 != closure(true_gens_nk)：穷举 %d vs 闭包 %d"
                             % (n, len(surv_set), len(ref)))
    order = len(surv_set)
    assert order == math.factorial(n), "Q%d 真群阶 != n!" % n
    return {
        "env": "Q%d" % n, "n_states": NS, "n_actions": n,
        "true_order": order, "true_orbits": len(orbits_of([list(g) for g in surv_set], NS)),
        "method": ("穷举全部 %d 个超立方体自同构候选（目标固定过滤 + 通用等变 judge 逐一判定），"
                   "与 closure(true_gens_nk(%d,%d)) 逐元素对拍相等" % (NS * math.factorial(n), n, n)),
        "candidates_total": (1 << n) * math.factorial(n),
        "elements": [list(g) for g in surv_set],
        "sec": sec_of(t0),
    }


def verify_true_group_allperms(trans, n_act, expect_gens, tag):
    """
    小状态数环境真群穷举：枚举全部 NS! 置换逐一过通用 judge（K44：8!=40320）。
    交叉对拍：幸存集 == closure(expect_gens)。
    """
    NS = len(trans)
    t0 = time.perf_counter()
    survivors = []
    for perm in itertools.permutations(range(NS)):
        e, _ = equiv_error_gua(trans, list(perm), n_act)
        if e == 0:
            survivors.append(perm)
    ref = {tuple(g) for g in closure_perms([list(g) for g in expect_gens], NS)}
    surv_set = set(survivors)
    assert len(survivors) == len(surv_set), "%s 穷举幸存集有重复" % tag
    assert surv_set == ref, ("%s 穷举真群 != closure(expect_gens)：穷举 %d vs 闭包 %d"
                             % (tag, len(surv_set), len(ref)))
    return {
        "env": tag, "n_states": NS, "n_actions": n_act,
        "true_order": len(surv_set),
        "true_orbits": len(orbits_of([list(g) for g in surv_set], NS)),
        "method": "穷举全部 %d! 置换逐一过通用等变 judge，与 closure(文档真生成元) 对拍相等" % NS,
        "candidates_total": math.factorial(NS),
        "elements": [list(g) for g in surv_set],
        "sec": sec_of(t0),
    }


def verify_true_group_heawood(trans, n_act):
    """
    Heawood 真群完整回溯穷举（14! 不可直接枚举）：
    保邻接一致性（无向边保持，双向）逐点回溯，叶点全量过通用 judge。
    完备性：一致性条件是自同构必要条件，每个自同构对应唯一搜索路径 ⟹ 叶数 = |Aut|。
    交叉对拍：叶集 == closure(true_gens_heawood())（PGL(2,7)，阶 336）。
    """
    NS = len(trans)
    adj = [sorted(a) for a in backbone_adj(trans, n_act)]
    outm = [0] * NS
    for s in range(NS):
        m = 0
        for y in adj[s]:
            m |= 1 << y
        outm[s] = m
    img = [-1] * NS
    used = [False] * NS
    leaves = []
    nodes = [0]
    t0 = time.perf_counter()

    def consistent(i, c):
        for j in range(NS):
            w = img[j]
            if w == -1:
                continue
            if ((outm[j] >> i) & 1) != ((outm[w] >> c) & 1):
                return False
            if ((outm[i] >> j) & 1) != ((outm[c] >> w) & 1):
                return False
        return True

    def rec():
        nodes[0] += 1
        i = next((x for x in range(NS) if img[x] == -1), None)
        if i is None:
            leaves.append(img[:])
            return
        for c in range(NS):
            if used[c] or not consistent(i, c):
                continue
            img[i] = c
            used[c] = True
            rec()
            img[i] = -1
            used[c] = False

    rec()
    bad = sum(1 for pi in leaves if equiv_error_gua(trans, pi, n_act)[0] != 0)
    assert bad == 0, "Heawood 叶点全量 judge 失败 %d 个" % bad
    ref = {tuple(g) for g in closure_perms([list(g) for g in true_gens_heawood()], NS)}
    leaf_set = {tuple(g) for g in leaves}
    assert len(leaves) == len(leaf_set), "Heawood 叶集有重复"
    assert leaf_set == ref, ("Heawood 穷举叶集 != closure(true_gens_heawood)："
                             "穷举 %d vs 闭包 %d" % (len(leaf_set), len(ref)))
    return {
        "env": "Heawood", "n_states": NS, "n_actions": n_act,
        "true_order": len(leaf_set),
        "true_orbits": len(orbits_of([list(g) for g in leaf_set], NS)),
        "method": ("完整回溯穷举（无向边保持一致性 + 叶点全量通用 judge，%d 节点），"
                   "与 closure(true_gens_heawood) 逐元素对拍相等" % nodes[0]),
        "search_nodes": nodes[0],
        "elements": [list(g) for g in leaf_set],
        "sec": sec_of(t0),
    }


def verify_true_group_gua64():
    """
    六十四卦真群（soft 口径）：回源 experiments_gua64_aut.json（穷举定论），
    本脚本真跑复验两个交叉 assert：
      ① discover_gua（seed=7 确定性）机器群闭包阶 == 294,912 == aut json cross_check；
      ② <机器群生成元 ∪ {错,综}> 闭包阶 == 589,824 == aut json aut.soft.order
        （穷举定理：并集群 = Aut_soft）。
    真群轨道 = 并集群轨道（并集群 == Aut_soft）。
    """
    from experiments_p3 import closure_perms as cp
    from experiments_gua64_aut import soft_ok          # 独立实现判定（穷举口径）
    t0 = time.perf_counter()
    with open(os.path.join(ROOT, GT_AUT_JSON), "r", encoding="utf-8") as f:
        aut = json.load(f)
    true_order = aut["aut"]["soft"]["order"]
    trans, actions, sigma, tau = build_gua64()
    M, diag = discover_gua(trans, 3)
    good = [tuple(g) for g in diag["good_gens"]]
    m_order = len({tuple(g) for g in M})
    assert m_order == 294912 == aut["cross_check"]["machine_order_closure"], \
        "gua64 机器群阶 %d != 294912" % m_order
    union = cp(good + [list(sigma), list(tau)], 64)
    u_order = len(union)
    assert u_order == true_order == 589824, "gua64 并集群阶 %d != 真群 %d" % (u_order, true_order)
    # 独立实现抽查：并集群随机 500 元素过 soft_ok（独立判定口径）
    rng = random.Random(7)
    UL = list(union)
    bad = sum(0 if soft_ok(list(UL[rng.randrange(u_order)])) else 1 for _ in range(500))
    assert bad == 0, "gua64 并集群 soft_ok 独立抽查失败 %d/500" % bad
    return {
        "env": "gua64", "n_states": 64, "n_actions": 3,
        "true_order": true_order, "true_orbits": len(orbits_of(union, 64)),
        "method": ("回源 %s（结构分割+精确回溯穷举定论）+ 本脚本真跑复验："
                   "机器群 %d、并集群 %d（=Aut_soft）、soft_ok 独立抽查 500 元素 0 失败"
                   % (GT_AUT_JSON, m_order, u_order)),
        "machine_order": m_order, "union_order": u_order,
        "elements": None,          # 589,824 元素不落 json（体积），成员判定用 soft_ok
        "sec": sec_of(t0),
        "source_json": GT_AUT_JSON,
    }


# ================================================================ canonize 路径
def weak_components_of(adj):
    """无向骨干图的弱分量（顶点列表列表，保序）。"""
    NS = len(adj)
    und = [set() for _ in range(NS)]
    for s in range(NS):
        for y in adj[s]:
            und[s].add(y)
            und[y].add(s)
    seen = [False] * NS
    comps = []
    for s in range(NS):
        if seen[s]:
            continue
        stack, comp = [s], []
        seen[s] = True
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in und[x]:
                if not seen[y]:
                    seen[y] = True
                    stack.append(y)
        comps.append(sorted(comp))
    return comps


def _cert_of(adj, order):
    """规范形指纹（上三角行主序位串，同 experiments_canonical_search._certificate 口径）。"""
    bits = []
    NS = len(order)
    for i in range(NS):
        ai = adj[order[i]]
        for j in range(i + 1, NS):
            bits.append(1 if order[j] in ai else 0)
    return tuple(bits)


def canonize_model_generic(trans, n_act):
    """
    规范化重编号（canonize 臂第一步；_canonize_model 的泛化包装）。
    单分量骨干图 → 直接 import wuxing_gua.core_discover._canonize_model
    （CLI --canonize 同一路径：图口径 canonize + isom_map_ok 硬校验）。
    多分量骨干图（六十四卦：2 个 32 态弱分量）→ 逐分量 canonize + 按分量证书
    字典序排序拼接（拼接映射过 isom_map_ok 硬校验）。
    返回 (order, inv, info)。

    ⚠️ 2026-10-27 放宽一处过强断言（游戏案例修复）：
    原实现 assert「分量证书两两互异」（len(set(certs)) == len(certs)），遇到同构分量
    直接崩（47 个 pad 哑态 = 47 个同构单点分量 ⇒ AssertionError）。该断言是**过强**
    的：分量各自 canonize 后得到的是该分量同构类的唯一规范形 ⇒ 两个同构分量的规范
    块**逐位相同** ⇒ 整图邻接矩阵是这些规范块按分量次序拼成的块对角阵，**互换同构
    分量的先后不改变重编号后的整图邻接矩阵**（搜索器只看这张矩阵 ⇒ 下游逐位相同）。
    故「证书互异」只是良定义的充分条件，不是必要条件：需要的是**确定性全序**
    （证书优先、同证书时按分量的最小原始顶点 id 兜底），正确性由末尾 isom_map_ok
    硬校验兜住（与单分量路径同一道闸）。影响：不再因同构分量拒答；判定强度零变化。
    """
    NS = len(trans)
    backbone = [sorted(a) for a in backbone_adj(trans, n_act)]
    comps = weak_components_of(backbone)
    if len(comps) == 1:
        order, inv, info = _canonize_model(trans, n_act)
        return order, inv, info
    # 多分量扩展（仅六十四卦需要；探针实测整体 canonize 超 CANON_NODE_CAP）
    from wuxing_gua.core_discover import _sec_magnitude
    t0 = time.perf_counter()
    pos_in_comp = {}
    orders, certs, nodes_tot = [], [], 0
    adj_sets = [set(x) for x in backbone]
    for comp in comps:
        idx = {s: k for k, s in enumerate(comp)}
        sub = [{idx[y] for y in backbone[s]} for s in comp]
        order_c, cert_c, nodes_c = graph_canonize([set(x) for x in sub])
        orders.append((order_c, comp, cert_c))
        certs.append(cert_c)
        nodes_tot += nodes_c
    # 证书全序：证书字典序优先；同证书（= 同构分量，规范块逐位相同 ⇒ 互换不改变
    # 重编号后的整图邻接矩阵）时按分量的最小原始顶点 id 兜底，保证映射确定性。
    # 原 assert「证书两两互异」过强（见函数 docstring），已放宽；正确性由下面的
    # isom_map_ok 硬校验兜住。
    n_cert_ties = len(certs) - len(set(certs))
    cert_sorted = sorted(range(len(certs)), key=lambda i: (certs[i], comps[i][0]))
    order = [None] * NS
    w = 0
    for ci in cert_sorted:
        order_c, comp, _ = orders[ci]
        for new, old in enumerate(order_c):
            order[w] = comp[old]
            w += 1
    assert w == NS
    # 硬校验：拼接映射必是整张骨干图的同构（防实现回归，同 CLI 口径）
    assert isom_map_ok([set(x) for x in backbone],
                       [set(x) for x in relabel_adj(backbone, order)], order), \
        "逐分量 canonize 拼接映射不是骨干图同构（实现回归，拒绝继续）"
    inv = [0] * NS
    for new, old in enumerate(order):
        inv[old] = new
    info = {
        "canon_search_nodes": nodes_tot,
        "canon_sec_magnitude": _sec_magnitude(time.perf_counter() - t0),
        "n_components": len(comps),
        "n_cert_ties": n_cert_ties,      # 同证书（同构）分量数：>0 表示走了放宽分支
        "mapping": {
            "is_identity": order == list(range(NS)),
            "n_fixed_points": sum(1 for i in range(NS) if order[i] == i),
            "n_states": NS,
        },
    }
    return order, inv, info


def discover_canon_generic(trans, n_act, order, inv):
    """
    规范编号上的 discover 搜索（canonize 臂第二步）。
    copy from wuxing_gua/core_discover.py::_discover_canonized 的同构编排，
    唯一差异 = 等变检验函数换泛化版 equiv_error_gua（编号无关判据；位串实例上
    与原版判定等价，bridge.judge_equiv 实证）。三路图搜索（确定性 max_gens=48 /
    随机重启 40 次 seed=7 / 对合搜索 seed=7 / MRV fallback）与闭包 + 哨兵复检
    的编排与超参逐项照抄原版，全部 import 原实现、零改动。
    """
    NS = len(trans)
    adj_orig = backbone_adj(trans, n_act)
    adj_canon = [set(x) for x in relabel_adj([sorted(a) for a in adj_orig], order)]
    color_canon = wl_refine(adj_canon)
    classes = {}
    for s in range(NS):
        classes.setdefault(color_canon[s], []).append(s)

    def back(pi_canon):
        return [order[pi_canon[inv[x]]] for x in range(NS)]

    gens_canon = graph_automorphisms(adj_canon, color_canon, max_gens=48)
    gens_canon = gens_canon + graph_automorphisms_rr(adj_canon, color_canon,
                                                     n_restarts=40, seed=7)
    n_invol = 0
    if gens_canon:
        invols = involution_automorphisms(adj_canon, color_canon)
        n_invol = len(invols)
        gens_canon = gens_canon + invols

    good, _worst = [], 0.0
    for g in gens_canon:
        e, _ = equiv_error_gua(trans, back(g), n_act)
        _worst = max(_worst, e)
        if e <= TOL:
            good.append(back(g))
    if not good:
        n_mrv = 0
        mrv = graph_automorphisms_mrv(adj_canon, color_canon)
        n_mrv = len(mrv)
        for g in mrv:
            e, _ = equiv_error_gua(trans, back(g), n_act)
            if e <= TOL:
                good.append(back(g))
        if not good:
            return [list(range(NS))], {"n_gens": len(gens_canon), "n_pass": 0,
                                       "n_classes": len(classes), "worst": _worst,
                                       "n_involution": n_invol, "n_mrv": n_mrv}
    else:
        n_mrv = 0

    G = closure_perms(good, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _ = equiv_error_gua(trans, g, n_act)
        worst2 = max(worst2, e)
    sentinel_ok = worst2 <= TOL
    return G, {"n_gens": len(gens_canon), "n_pass": len(good), "order": len(G),
               "worst_equiv": worst2, "sentinel_ok": sentinel_ok,
               "sentinel_n": len(sample), "n_classes": len(classes),
               "n_involution": n_invol, "n_mrv": n_mrv}


# ================================================================ 环境与编号
def build_envs():
    """返回 {name: dict(trans, n_act, NS, num_mode, desc)}。num_mode 决定平移/反转的构造口径。"""
    envs = {}
    for n in (4, 5, 6, 7):
        envs["Q%d" % n] = {
            "trans": build_model_n(n, {(1 << n) - 1}), "n_act": n,
            "NS": 1 << n, "num_mode": "bit",
            "desc": "%d 位翻转 MDP，目标 {全阳}（experiments_e1.build_model_n）" % n,
        }
    envs["K44"] = {
        "trans": build_knn(4), "n_act": 4, "NS": 8, "num_mode": "cyclic",
        "desc": "完全二分图 K4,4 MDP（experiments_restart_scan5.build_knn）",
    }
    envs["Heawood"] = {
        "trans": build_heawood(), "n_act": 3, "NS": 14, "num_mode": "cyclic",
        "desc": "Heawood 图（Fano 点-线关联图）MDP（experiments_restart_scan6.build_heawood）",
    }
    envs["gua64"] = {
        "trans": build_gua64()[0], "n_act": 3, "NS": 64, "num_mode": "bit",
        "desc": "六十四卦转移系统（experiments_gua64.build_gua64，动作=错/综/互；"
                "状态为 6 爻位串，故平移/反转沿用位串口径）",
    }
    return envs


def make_numberings(NS, num_mode):
    """
    13 个编号实例：标准 + 随机×10（seed=1..10）+ 平移 + 反转。
    num_mode="bit"（Q4-Q7 与 gua64：状态为位串）：平移 = XOR c（c = SHIFT_C mod 2^log2(NS)，
    与平移 Q₆ 事件同源；gua64 的位倒序恰为综卦 τ ∈ 真群 ⇒ 控制实例）；
    num_mode="cyclic"（K44/Heawood）：平移 = 循环平移 (s+c) mod NS，反转 = s → NS-1-s。
    返回 [{kind, seed?, pi, note}]，pi[旧状态] = 新编号。
    """
    out = [{"kind": "std", "pi": list(range(NS)), "note": "标准编号（恒等）"}]
    for seed in range(1, N_RANDOM_SEEDS + 1):
        pi = random.Random(seed).sample(range(NS), NS)
        out.append({"kind": "random", "seed": seed, "pi": pi,
                    "note": "random.Random(%d).sample 均匀随机置换" % seed})
    c = SHIFT_C % NS
    if num_mode == "bit":
        pi = [s ^ c for s in range(NS)]
        sh_note = "XOR 平移 c=%d（位串口径保持，平移 Q₆ 事件同源构造）" % c
        n = NS.bit_length() - 1
        pi_r = []
        for s in range(NS):
            r = 0
            for j in range(n):
                if (s >> j) & 1:
                    r |= 1 << (n - 1 - j)
            pi_r.append(r)
        rv_note = ("位倒序（Q_n 上属 S_n ⊆ 真群 ⇒ 表恒同控制实例；"
                   "gua64 上即综卦 τ ∈ 真群，同为控制实例）")
    else:
        pi = [(s + c) % NS for s in range(NS)]
        sh_note = "循环平移 c=%d（非位串环境的平移口径）" % c
        pi_r = [NS - 1 - s for s in range(NS)]
        rv_note = "id 反转 s → %d-s" % (NS - 1)
    out.append({"kind": "shift", "shift_c": c, "pi": pi, "note": sh_note})
    out.append({"kind": "reversal", "pi": pi_r, "note": rv_note})
    return out


def relabel_trans(trans, pi):
    """重编号：trans'[π(s)][a] = [(p, π(u), r) for (p,u,r) in trans[s][a]]。"""
    NS = len(trans)
    inv = [0] * NS
    for old, new in enumerate(pi):
        inv[new] = old
    n_act = len(trans[0])
    return [[[(p, pi[u], r) for (p, u, r) in trans[inv[i]][a]] for a in range(n_act)]
            for i in range(NS)]


# ================================================================ 矩阵
def classify(order, true_order):
    """预注册判读规则（RULES）：返回 'completely_lost' | 'partial_loss' | 'lucky_full_hit'。"""
    if order < true_order / 10.0:
        return "completely_lost"
    if order < true_order:
        return "partial_loss"
    assert order == true_order, "群阶 %d 超过真群 %d（不可能：闭包 ⊆ 真群）" % (order, true_order)
    return "lucky_full_hit"


def run_arm_pair(env_name, env, num, true_order, true_elements):
    """单个编号实例的两臂（plain / canonize），返回记录 dict。"""
    trans, n_act, NS = env["trans"], env["n_act"], env["NS"]
    pi = num["pi"]
    trans_p = relabel_trans(trans, pi)
    inv_pi = [0] * NS
    for old, new in enumerate(pi):
        inv_pi[new] = old
    pi_is_aut = (equiv_error_gua(trans, pi, n_act)[0] == 0)   # π 是原环境自同构 ⇔ 表恒同

    t0 = time.perf_counter()
    G_plain, diag_plain = discover_gua(trans_p, n_act)
    sec_plain = sec_of(t0)
    t0 = time.perf_counter()
    order_c, inv_c, cinfo = canonize_model_generic(trans_p, n_act)
    G_canon, diag_canon = discover_canon_generic(trans_p, n_act, order_c, inv_c)
    sec_canon = sec_of(t0)

    o_plain, o_canon = len(G_plain), len(G_canon)
    ob_plain = len(orbits_of(G_plain, NS))
    ob_canon = len(orbits_of(G_canon, NS))
    assert o_plain <= true_order and o_canon <= true_order, \
        "%s/%s：发现群阶超过真群（判据被破坏）" % (env_name, num["kind"])
    assert diag_plain["sentinel_ok"] and diag_canon["sentinel_ok"], \
        "%s/%s：哨兵复检失败" % (env_name, num["kind"])

    # 合法性：发现群 ⊆ π·G_true·π^{-1}。有真群元素集的环境做全量子集检验；
    # gua64（589,824 元素不落内存全集）对两臂各抽 200 元素做 judge 复验。
    if true_elements is not None:
        true_set = {tuple(g) for g in true_elements}
        for tag, G in (("plain", G_plain), ("canon", G_canon)):
            bad = sum(0 if tuple(inv_pi[g[pi[x]]] for x in range(NS)) in true_set else 1
                      for g in G)
            assert bad == 0, "%s/%s %s 臂 %d 个元素 ∉ π·G_true·π^{-1}" % (
                env_name, num["kind"], tag, bad)
        subset_checked = "full"
    else:
        rng = random.Random(11)
        for tag, G in (("plain", G_plain), ("canon", G_canon)):
            GL = list(G)
            bad = 0
            for _ in range(200):
                g = GL[rng.randrange(len(GL))]
                if equiv_error_gua(trans, [inv_pi[g[pi[x]]] for x in range(NS)], n_act)[0] != 0:
                    bad += 1
            assert bad == 0, "%s/%s %s 臂抽样 judge 复验失败" % (env_name, num["kind"], tag)
        subset_checked = "sample200"

    rec = {
        "env": env_name,
        "numbering": {"kind": num["kind"], "seed": num.get("seed"),
                      "shift_c": num.get("shift_c"), "note": num["note"],
                      "pi": pi, "pi_is_aut": pi_is_aut},
        "true_order": true_order,
        "plain": {"order": o_plain, "n_orbits": ob_plain,
                  "ratio": round(o_plain / true_order, 6),
                  "class": classify(o_plain, true_order),
                  "sec": sec_plain,
                  "diag": {k: diag_plain[k] for k in
                           ("n_gens", "n_pass", "n_classes", "n_involution", "n_mrv")}},
        "canon": {"order": o_canon, "n_orbits": ob_canon,
                  "ratio": round(o_canon / true_order, 6),
                  "class": classify(o_canon, true_order),
                  "sec": sec_canon,
                  "canon_search_nodes": cinfo["canon_search_nodes"],
                  "canon_mapping_is_identity": cinfo["mapping"]["is_identity"],
                  "diag": {k: diag_canon[k] for k in
                           ("n_gens", "n_pass", "n_classes", "n_involution", "n_mrv")}},
        "subset_check": subset_checked,
    }
    # 控制实例：π 是真群元素 ⇔ 重编号后表与原表逐位相同 ⇒ plain 必与标准编号
    # 实例完全一致（discover 确定性：seed=7）。此断言在矩阵跑完由主流程核对
    # （标准实例的记录此时可能尚未产生），见 run()。
    return rec


def dist_stats(ratios, orders, true_order, n):
    """分布汇总（中位/最小群阶比/各判读类计数与率）。"""
    cls = {"completely_lost": 0, "partial_loss": 0, "lucky_full_hit": 0}
    for o in orders:
        cls[classify(o, true_order)] += 1
    return {
        "n": n,
        "ratio_median": round(statistics.median(ratios), 6) if ratios else None,
        "ratio_min": round(min(ratios), 6) if ratios else None,
        "order_min": min(orders) if orders else None,
        "n_lucky_full_hit": cls["lucky_full_hit"],
        "n_partial_loss": cls["partial_loss"],
        "n_completely_lost": cls["completely_lost"],
        "completely_lost_rate": round(cls["completely_lost"] / n, 4) if n else None,
    }


def run(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", default=None, help="逗号分隔环境名（默认全部 7 个）")
    ap.add_argument("--out", default=None,
                    help="输出 json 路径（默认项目根 experiments_discover_labeling.json）")
    ap.add_argument("--fresh", action="store_true",
                    help="忽略已有 json，从零重跑（默认：自动续跑，复用已完成条目）")
    args = ap.parse_args(argv)
    env_filter = args.envs.split(",") if args.envs else None
    out_path = args.out or OUT_JSON

    prior = None if args.fresh else load_prior(out_path)
    reused = {"ground_truth": [], "bridge_cli": False,
              "historical_rechecks": 0, "matrix": 0}

    print("=" * 96)
    print("discover 编号伪像系统化扫描：7 环境 × 13 编号 × plain/canonize 两臂")
    print("  判读规则（预注册，先落盘后跑）：")
    for k in ("completely_lost", "partial_loss", "lucky_full_hit",
              "canon_repair_rate", "canon_residual_artifact"):
        print("    · %s" % RULES[k])
    print("  输出：%s" % out_path)
    print("  断点续跑：%s" % ("关闭（--fresh，从零重跑）" if args.fresh else
                              ("复用已有 %d 条矩阵条目" % len(prior.get("matrix") or [])
                               if prior else "开启（无已有 json，本次全算）")))
    print("=" * 96)

    out = {
        "meta": {
            "task": "discover 编号伪像系统化扫描",
            "question": "项目历史所有 discover 数字（720/40320/294912/…）会不会都是"
                        "「标准编号下的幸运值」？把伪像的影响面量出来。",
            "rules": RULES,
            "prereg_predictions": PREREG_PREDICTIONS,
            "numbering_plan": "每环境 13 个编号实例：标准 + 随机×10（seed=1..10，"
                              "random.Random(seed).sample）+ 平移 + 反转；"
                              "重编号 = 状态置换 π 共轭（转移/奖励/目标随 π），真群变 "
                              "π·G·π^{-1}（阶不变）",
            "judge": ("编号无关通用等变判据 equiv_error_gua（max TV=0 零容忍；"
                      "experiments_gua64.py 建立口径）。位串实例上与 p3.equiv_error "
                      "位串 judge 判定等价——bridge.judge_equiv 实证"),
            "canon_arm": ("与 wuxing_gua/core_discover --canonize 同口径（同一 §16 canonize + "
                          "同一套三路搜索超参，_discover_canon_generic 唯一差异=等变检验函数）；"
                          "gua64 骨干图整体 canonize 超 CANON_NODE_CAP（探针实测），改用"
                          "逐分量 canonize + 证书排序拼接（isom_map_ok 硬校验通过）"),
            "shift_c": SHIFT_C,
            "random_seeds": list(range(1, N_RANDOM_SEEDS + 1)),
            "script_sha256": hashlib.sha256(
                open(os.path.abspath(__file__), "rb").read()).hexdigest(),
        },
        "resume": {},
        "ground_truth": {},
        "bridge_cli": {},
        "historical_rechecks": [],
        "matrix": [],
        "summary": {},
    }

    def dump():
        tmp = out_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out_path)      # 原子替换：中断不会留下半截 json

    # ---------------- ① 真群 ground truth（先做，失败即停） ----------------
    print("\n[1] 真群 ground truth 验证（穷举/回源）")
    gt_elements = {}
    for name, fn in (("Q4", lambda: verify_true_group_bitflip(4)),
                     ("Q5", lambda: verify_true_group_bitflip(5)),
                     ("Q6", lambda: verify_true_group_bitflip(6)),
                     ("Q7", lambda: verify_true_group_bitflip(7)),
                     ("K44", lambda: verify_true_group_allperms(
                         build_knn(4), 4, true_gens_knn(4), "K44")),
                     ("Heawood", lambda: verify_true_group_heawood(
                         build_heawood(), 3)),
                     ("gua64", verify_true_group_gua64)):
        if env_filter and name not in env_filter:
            continue
        prior_rec = (prior.get("ground_truth") or {}).get(name) if prior else None
        if prior_rec and prior_rec.get("true_order") and prior_rec.get("true_orbits"):
            rec = prior_rec
            reused["ground_truth"].append(name)
            print("    %-8s 真群阶 %-7d 轨道 %-3d（续跑沿用已有 json，跳过重算）"
                  % (name, rec["true_order"], rec["true_orbits"]))
        else:
            rec = fn()
            print("    %-8s 真群阶 %-7d 轨道 %-3d（%s，%.1fs）"
                  % (name, rec["true_order"], rec["true_orbits"],
                     rec["method"][:38] + "…", rec["sec"]))
        out["ground_truth"][name] = rec
        gt_elements[name] = rec["elements"]
        dump()

    envs = build_envs()

    # ---------------- ② 桥接：CLI 口径复现 + judge 等价 ----------------
    # （--envs 过滤模式仅在包含 Q6 时执行；全量跑无条件执行）
    run_bridge = (env_filter is None) or ("Q6" in env_filter)
    if run_bridge and prior and prior.get("bridge_cli"):
        out["bridge_cli"] = prior["bridge_cli"]
        reused["bridge_cli"] = True
        print("\n[2] 桥接实例（续跑沿用已有 json，跳过重算）")
        print("    CLI 标准 Q₆：%d/%d；平移 Q₆ plain %d/%d → canonize %d/%d；"
              "judge 等价 %s"
              % (out["bridge_cli"]["q6_std_cli"]["order"],
                 out["bridge_cli"]["q6_std_cli"]["n_orbits"],
                 out["bridge_cli"]["q6_translated_cli"]["order_plain"],
                 out["bridge_cli"]["q6_translated_cli"]["n_orbits_plain"],
                 out["bridge_cli"]["q6_translated_cli"]["order_canon"],
                 out["bridge_cli"]["q6_translated_cli"]["n_orbits_canon"],
                 out["bridge_cli"]["judge_equiv"]))
        dump()
    elif run_bridge:
        print("\n[2] 桥接实例（CLI --canonize 口径 + judge 等价实证，Q₆）")
        from wuxing_gua.demo_env import build_standard, build_translated_standard
        tr_std, n6, goals_std = build_standard(6)
        m_std = {"n_bits": n6, "n_actions": n6, "n_states": 64,
                 "goals": sorted(goals_std), "trans": tr_std}
        p_std_plain = run_discover(m_std)
        p_std_canon = run_discover(m_std, canonize=True)
        m_tr = build_translated_standard(6)
        p_tr = run_discover(m_tr, canonize=True)
        cons = p_tr["canonize"]["consistency"]
        # judge 等价实证：p3.discover（位串 judge）vs discover_gua（通用 judge）
        G1, _d1 = discover_p3(tr_std, 6)
        G2, _d2 = discover_gua(tr_std, 6)
        trT = m_tr["trans"]
        G3, _d3 = discover_p3(trT, 6)
        G4, _d4 = discover_gua(trT, 6)
        judge_equiv = (
            {tuple(g) for g in G1} == {tuple(g) for g in G2}
            and len(G3) == len(G4) and len(orbits_of(G3, 64)) == len(orbits_of(G4, 64)))
        assert judge_equiv, "p3.discover 与 discover_gua 在位串实例上判定不等价（桥接失败）"
        assert p_std_canon["order"] == 720 and p_std_canon["n_orbits"] == 7
        assert cons["order_plain"] == 6 and cons["n_orbits_plain"] == 32
        assert cons["order_canon"] == 720 and cons["n_orbits_canon"] == 7
        out["bridge_cli"] = {
            "q6_std_cli": {"order": p_std_canon["order"], "n_orbits": p_std_canon["n_orbits"],
                           "order_plain": p_std_plain["order"]},
            "q6_translated_cli": {"order_plain": cons["order_plain"],
                                  "n_orbits_plain": cons["n_orbits_plain"],
                                  "order_canon": cons["order_canon"],
                                  "n_orbits_canon": cons["n_orbits_canon"]},
            "judge_equiv": judge_equiv,
            "note": ("CLI run_discover（wuxing_gua.core_discover，README --canonize 一节口径）"
                     "真跑复现：标准 720/7 双向一致；平移 c=51 plain 6/32 → canonize 720/7。"
                     "通用 judge 与位串 judge 在两个桥接实例上判定逐位等价"),
        }
        print("    CLI 标准 Q₆：%d/%d；平移 Q₆ plain %d/%d → canonize %d/%d；"
              "judge 等价 %s" % (p_std_canon["order"], p_std_canon["n_orbits"],
                                 cons["order_plain"], cons["n_orbits_plain"],
                                 cons["order_canon"], cons["n_orbits_canon"], judge_equiv))
        dump()

    # ---------------- ③ 历史实例重查（历史发现力实例；--envs 过滤模式同 bridge 门） ----
    if run_bridge and prior and prior.get("historical_rechecks"):
        out["historical_rechecks"] = list(prior["historical_rechecks"])
        reused["historical_rechecks"] = len(out["historical_rechecks"])
        print("\n[3] 历史实例重查（续跑沿用已有 json，跳过重算）")
        r0 = out["historical_rechecks"][0]
        print("    plain %d/%d（%s）→ canonize %d/%d（%s）；真群 %d"
              % (r0["plain"]["order"], r0["plain"]["n_orbits"], r0["plain"]["class"],
                 r0["canon"]["order"], r0["canon"]["n_orbits"], r0["canon"]["class"],
                 r0["true_order"]))
        dump()
    elif run_bridge:
        print("\n[3] 历史实例重查：历史发现力实例（Q₆ 目标 {0b000111}，experiments_p3.json"
              " discovery.auto_order=6）")
        trans_p3 = build_model_n(6, {0b000111})
        t0 = time.perf_counter()
        Gp, _dp = discover_gua(trans_p3, 6)
        sec_p = sec_of(t0)
        order_cp, inv_cp, _ci = canonize_model_generic(trans_p3, 6)
        Gc, _dc = discover_canon_generic(trans_p3, 6, order_cp, inv_cp)
        true_p3 = out["ground_truth"]["Q6"]
        # 该环境与 Q6（目标 {63}）经 XOR 56 同构 ⇒ 真群阶同为 720
        assert true_p3["true_order"] == 720
        rec_p3 = {
            "instance": "p3_discovery_Q6_goal_0b000111",
            "historical_value": {"order": 6, "n_orbits": 32,
                                 "source": "experiments_p3.json discovery.auto_order/orbits"},
            "plain": {"order": len(Gp), "n_orbits": len(orbits_of(Gp, 64)), "sec": sec_p,
                      "class": classify(len(Gp), 720)},
            "canon": {"order": len(Gc), "n_orbits": len(orbits_of(Gc, 64)),
                      "class": classify(len(Gc), 720)},
            "true_order": 720,
            "note": ("该环境与扫描环境 Q6（目标 {63}）经 XOR 平移 56 同构 ⇒ 真群同为 S₆=720；"
                     "历史 discover 值 6/32 是标准编号下 plain 臂的读数"),
        }
        out["historical_rechecks"].append(rec_p3)
        print("    plain %d/%d（%s）→ canonize %d/%d（%s）；真群 720"
              % (len(Gp), len(orbits_of(Gp, 64)), rec_p3["plain"]["class"],
                 len(Gc), len(orbits_of(Gc, 64)), rec_p3["canon"]["class"]))
        dump()

    # ---------------- ④ 矩阵：7 环境 × 13 编号 × 两臂 ----------------
    print("\n[4] 矩阵：环境 × 编号 × 两臂")
    prior_idx = prior_matrix_index(prior) if prior else {}
    for env_name, env in envs.items():
        if env_filter and env_name not in env_filter:
            continue
        true_order = out["ground_truth"][env_name]["true_order"]
        true_orbits = out["ground_truth"][env_name]["true_orbits"]
        elements = gt_elements[env_name]
        nums = make_numberings(env["NS"], env["num_mode"])
        assert len(nums) == 2 + N_RANDOM_SEEDS + 1
        print("  [%s] 真群 %d/%d 轨道，%d 个编号实例…"
              % (env_name, true_order, true_orbits, len(nums)))
        std_plain = None
        n_env_reuse = 0
        t_env = time.perf_counter()
        for num in nums:
            tag = num["kind"] + ("" if num.get("seed") is None else "#%d" % num["seed"])
            # 断点续跑：该 (env, kind, seed) 已完成且 π / 真群阶一致 ⇒ 直接复用，不重算
            prior_rec = prior_idx.get((env_name, num["kind"], num.get("seed")))
            if prior_rec is not None and reusable_matrix_record(prior_rec, num, true_order):
                rec = prior_rec
                rec["true_orbits"] = true_orbits
                n_env_reuse += 1
                reused["matrix"] += 1
                print("    %-8s plain %-7d(%s)  canon %-7d(%s)  [续跑沿用]"
                      % (tag, rec["plain"]["order"], rec["plain"]["class"],
                         rec["canon"]["order"], rec["canon"]["class"]))
            else:
                rec = run_arm_pair(env_name, env, num, true_order, elements)
                rec["true_orbits"] = true_orbits
                print("    %-8s plain %-7d(%s)  canon %-7d(%s)  [%.1fs]"
                      % (tag, rec["plain"]["order"], rec["plain"]["class"],
                         rec["canon"]["order"], rec["canon"]["class"],
                         rec["plain"]["sec"] + rec["canon"]["sec"]))
                dump()
            out["matrix"].append(rec)
            if num["kind"] == "std":
                std_plain = rec["plain"]
            # 控制断言：π ∈ 真群 ⇒ 表恒同 ⇒ plain 与标准编号实例逐位一致
            if rec["numbering"]["pi_is_aut"] and num["kind"] != "std":
                assert (rec["plain"]["order"], rec["plain"]["n_orbits"]) == \
                       (std_plain["order"], std_plain["n_orbits"]), \
                    "%s/%s：表恒同控制实例 plain 与标准实例不一致" % (env_name, num["kind"])
        print("    环境累计 %.1fs（本环境复用 %d 条 / 新算 %d 条）"
              % (sec_of(t_env), n_env_reuse, len(nums) - n_env_reuse))
        dump()

    # ---------------- ⑤ 汇总 ----------------
    print("\n[5] 汇总分布")
    by_env = {}
    for env_name in (env_filter or list(envs.keys())):
        recs = [r for r in out["matrix"] if r["env"] == env_name]
        if not recs:
            continue
        true_order = recs[0]["true_order"]
        pe = {
            "n_instances": len(recs),
            "true_order": true_order,
            "plain": dist_stats([r["plain"]["ratio"] for r in recs],
                                [r["plain"]["order"] for r in recs], true_order, len(recs)),
            "canon": dist_stats([r["canon"]["ratio"] for r in recs],
                                [r["canon"]["order"] for r in recs], true_order, len(recs)),
            "canon_repair_rate": round(
                sum(1 for r in recs if r["canon"]["order"] == true_order) / len(recs), 4),
            "canon_residual_count": sum(1 for r in recs
                                        if r["canon"]["order"] < true_order),
            "canon_orders_constant": len({r["canon"]["order"] for r in recs}) == 1,
        }
        by_env[env_name] = pe
        print("  %-8s n=%d  plain 中位比 %.3f 最小 %.4f 完全丢失 %d/%d | "
              "canon 修复 %d/%d 残余 %d 恒定 %s"
              % (env_name, pe["n_instances"], pe["plain"]["ratio_median"],
                 pe["plain"]["ratio_min"], pe["plain"]["n_completely_lost"],
                 pe["n_instances"], round(pe["canon_repair_rate"] * pe["n_instances"]),
                 pe["n_instances"], pe["canon_residual_count"],
                 pe["canon_orders_constant"]))

    all_recs = out["matrix"]
    n_all = len(all_recs)
    global_summary = {
        "n_envs": len(by_env),
        "instances_total": n_all,
        "arm_runs_total": 2 * n_all,
        "plain": {
            "n_lucky_full_hit": sum(1 for r in all_recs if r["plain"]["class"] == "lucky_full_hit"),
            "n_partial_loss": sum(1 for r in all_recs if r["plain"]["class"] == "partial_loss"),
            "n_completely_lost": sum(1 for r in all_recs if r["plain"]["class"] == "completely_lost"),
            "completely_lost_rate": round(sum(1 for r in all_recs
                                              if r["plain"]["class"] == "completely_lost")
                                          / n_all, 4) if n_all else None,
            "ratio_median": round(statistics.median([r["plain"]["ratio"]
                                                     for r in all_recs]), 6) if n_all else None,
            "ratio_min": round(min(r["plain"]["ratio"] for r in all_recs), 6) if n_all else None,
        },
        "canon_repair_count": sum(1 for r in all_recs if r["canon"]["order"] == r["true_order"]),
        "canon_repair_rate": round(sum(1 for r in all_recs
                                       if r["canon"]["order"] == r["true_order"]) / n_all, 4)
                               if n_all else None,
        "canon_residual_count": sum(1 for r in all_recs if r["canon"]["order"] < r["true_order"]),
        "canon_residual_rate": round(sum(1 for r in all_recs
                                         if r["canon"]["order"] < r["true_order"]) / n_all, 4)
                                if n_all else None,
    }
    global_summary["plain"]["lucky_full_hit_rate"] = round(
        global_summary["plain"]["n_lucky_full_hit"] / n_all, 4) if n_all else None
    out["summary"] = {"by_env": by_env, "global": global_summary}
    try:
        out_rel = os.path.relpath(out_path, ROOT)
    except ValueError:                       # Windows 跨盘符时 relpath 抛错
        out_rel = os.path.abspath(out_path)
    out["resume"] = {
        "out_json": out_rel.replace("\\", "/"),
        "resumed_from_existing": bool(prior),
        "reused_ground_truth": reused["ground_truth"],
        "recomputed_ground_truth": [k for k in out["ground_truth"]
                                    if k not in reused["ground_truth"]],
        "reused_bridge_cli": reused["bridge_cli"],
        "reused_historical_rechecks": reused["historical_rechecks"],
        "reused_matrix_records": reused["matrix"],
        "new_matrix_records": n_all - reused["matrix"],
        "matrix_records_total": n_all,
    }
    dump()

    print("\n" + "=" * 96)
    print("人话摘要（判读规则 = 预注册 RULES）")
    print("  实例总数 %d（%d 环境 × %d 编号），两臂共 %d 次 discover"
          % (n_all, global_summary["n_envs"], n_all // max(len(by_env), 1), 2 * n_all))
    print("  plain：幸运全中 %d（%s）、部分损失 %d、完全丢失 %d（丢失率 %s）；"
          "中位群阶比 %s、最小 %s"
          % (global_summary["plain"]["n_lucky_full_hit"],
             global_summary["plain"]["lucky_full_hit_rate"],
             global_summary["plain"]["n_partial_loss"],
             global_summary["plain"]["n_completely_lost"],
             global_summary["plain"]["completely_lost_rate"],
             global_summary["plain"]["ratio_median"],
             global_summary["plain"]["ratio_min"]))
    print("  canonize：修复 %d/%d（修复率 %s）、残余伪像 %d（%s）"
          % (global_summary["canon_repair_count"], n_all,
             global_summary["canon_repair_rate"],
             global_summary["canon_residual_count"], global_summary["canon_residual_rate"]))
    print("  本次续跑：复用 %d 条矩阵条目、新算 %d 条（meta.resume 逐项记录）"
          % (reused["matrix"], n_all - reused["matrix"]))
    print("  结果已写入 %s" % out_rel.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(run())
