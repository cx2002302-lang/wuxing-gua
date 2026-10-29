# -*- coding: utf-8 -*-
"""
core_discover.py —— 自动找群（只给转移数据，机器自己发现对称性）

━━ 出处（import 复用，未复制、未改写判据逻辑）━━━━━━━━━━━━━━━━━━━━━━━━━
  discover / equiv_error / closure_perms / backbone_adj / wl_refine /
  graph_automorphisms(_rr) / involution_automorphisms / graph_automorphisms_mrv
      ← src/experiments_p3.py（三路候选 + 等变裁决 + 闭包 + 哨兵复检，
        裁决口径 = max TV=0 零容忍；种子/重启数等超参全部沿用原缺省值）
  orbits_of ← src/experiments_e1.py
  assess_completeness / standard_equiv_fn ← src/experiments_completeness.py
      （群完整性告警器：证书探针 + 启发式分数，阈值事前定死；
        只作为 payload 里的 completeness 字段附加输出，不改变本命令的退出码）
  canonize ← src/experiments_canonical_search.py（§16：规范 WL + 个体化-细化树
      + lex-min 证书，原封 import，未复制改写）
  relabel / isom_map_ok ← src/experiments_ovh_relabel.py（§15：重编号与同构硬校验）

本文件新增的只有「调用 + 输出编排」（run_discover / _canonize_model /
_discover_canonized / _sec_magnitude，另加输出层 helper _compact_generators
——只从已得群抽紧凑生成元表示，不做任何裁决）。
"""
import random
import sys
import time
from collections import deque

from experiments_p3 import (discover as _discover, equiv_error,  # noqa: F401
                            closure_perms, backbone_adj, wl_refine,
                            graph_automorphisms, graph_automorphisms_rr,
                            involution_automorphisms, graph_automorphisms_mrv)
from experiments_e1 import orbits_of
from experiments_completeness import (assess_completeness, standard_equiv_fn,
                                      _action_candidates)
from experiments_canonical_search import canonize as _graph_canonize
from experiments_ovh_relabel import relabel as _relabel_adj, isom_map_ok as _isom_map_ok


def _sec_magnitude(sec):
    """计时量级桶（数字纪律：单次运行计时必然漂移，只报量级不报精确值）。"""
    for lim, tag in ((0.1, "<0.1s"), (1.0, "0.1-1s"), (10.0, "1-10s"),
                     (100.0, "10-100s")):
        if sec < lim:
            return tag
    return ">=100s"


def _compact_generators(G, NS):
    """
    从闭包群 G 抽一组**不冗余生成元**（discover 输出补 generators 顶层字段
    ——试点反馈「生成元混在 elements 里需自行识别」）。纯输出编排层：只描述已得群、
    不做任何等变裁决，判据语义零改动。

    口径：按 G 的元素序贪心扫描——元素不在当前已生成子群里就收进生成元集并增量
    闭包（新增生成元使子群严格变大 ⇒ 至少翻倍，增量次数 ≤ log2|G|）。确定性：
    同一 G 必得同一生成元集（无随机源）。正确性由实现内 assert 硬保证：
    生成元闭包 == G 全集（含平凡群：G=[恒等] ⇒ 生成元为空表）。
    复合顺序与 closure_perms 同约定（c = g∘a）。
    """
    ident = tuple(range(NS))
    H = {ident}
    gens = []
    for g in G:
        t = tuple(g)
        if t in H:
            continue
        gens.append(list(t))
        queue = deque()
        for x in list(H):                    # 旧生成元下 H 已闭，只需乘新生成元
            y = [t[x[i]] for i in range(NS)]
            ty = tuple(y)
            if ty not in H:
                H.add(ty)
                queue.append(y)
        while queue:                         # 新元素在全生成元下闭包
            x = queue.popleft()
            for gg in gens:
                y = [gg[x[i]] for i in range(NS)]
                ty = tuple(y)
                if ty not in H:
                    H.add(ty)
                    queue.append(y)
    assert H == {tuple(g) for g in G}, \
        "生成元闭包 != 输出群全集（实现 bug，拒绝输出）"
    return gens


def _canonize_model(trans, n_acts):
    """
    规范化重编号（--canonize 的第一步）。

    口径（结构图规范化，README 已写明）：canonize 的判定在**骨干图**上
    （与 discover 内部 backbone_adj 同一张图，无向 + 目标态自环；§16 的图口径），
    得到 order[新 id] = 旧状态。不重排整张转移表——等变裁决 equiv_error 沿用
    研究实现的位串口径（动作 a = 翻转第 a 位，experiments_p3.py），对状态做任意
    重编号会破坏该口径；故规范化只用于搜索阶段（见 _discover_canonized），
    判据数据始终保持原编号。

    返回 (order, inv, info)：inv = order 的逆（旧状态 → 新 id）；
    info = 报告字段（canonize 用时量级 / 映射摘要 / 搜索树节点数）。

    ⚠️ 2026-10-27 多分量分流（GameWXXX 案例修复）：骨干图
    **非连通**时不再对整图做个体化-细化 canonize，改走
    experiments_discover_labeling.canonize_model_generic（逐分量 canonize + 按分量
    证书排序拼接，与 --preset robust 的 canonize 臂同一实现）。原因：整图口径的
    个体化-细化树在「多个同构分量」上会爆炸——每个同构分量都要逐个分支个体化，
    分量数为 m 时叶数 ~ m!（GameWXXX：47 个 pad 哑态 = 47 个同构单点分量 ⇒ 47!），
    且单节点成本 O(NS²)（canon_refine 迭代 NS+2 轮 × NS 顶点）在 512 态上实测
    ~11ms/节点 ⇒ 触达 CANON_NODE_CAP=400000 需 ~75 分钟，31 分钟硬停时连节点上限
    都没到。逐分量口径下同一张图 496 节点 / 5.6s 完成。单分量图（全部历史环境）
    行为逐位不变。
    """
    NS = len(trans)
    backbone = [sorted(a) for a in backbone_adj(trans, n_acts)]
    # 惰性 import：experiments_discover_labeling 模块级反向 import 本包（循环）
    from experiments_discover_labeling import (canonize_model_generic,
                                               weak_components_of)
    if len(weak_components_of(backbone)) > 1:
        return canonize_model_generic(trans, n_acts)
    t0 = time.perf_counter()
    order, _cert, nodes = _graph_canonize([set(x) for x in backbone])
    canon_sec = time.perf_counter() - t0
    # 硬校验：canonize 给出的映射必须是骨干图同构（防实现回归；isom_map_ok ← §15）
    assert _isom_map_ok([set(x) for x in backbone],
                        [set(x) for x in _relabel_adj(backbone, order)], order), \
        "canonize 映射不是骨干图同构（实现回归，拒绝继续）"
    inv = [0] * NS
    for new, old in enumerate(order):
        inv[old] = new
    info = {
        "canon_search_nodes": nodes,
        "canon_sec_magnitude": _sec_magnitude(canon_sec),
        "mapping": {
            "is_identity": order == list(range(NS)),
            "n_fixed_points": sum(1 for i in range(NS) if order[i] == i),
            "n_states": NS,
        },
    }
    return order, inv, info


def _discover_canonized(trans, n, order, inv):
    """
    规范编号上的 discover 搜索（--canonize 的第二步）。

    与 src/experiments_p3.py 的 discover **同编排、同超参**（确定性回溯
    max_gens=48 → 随机重启 40 次 seed=7 → 对合搜索 → 等变裁决 tol=1e-9 →
    MRV fallback → 闭包 → 哨兵复检，全部 import 原实现、零改动）；
    唯一差别：三路图搜索（确定性 / 随机重启 / 对合 / MRV）在**规范化重编号后
    的骨干图**上跑——搜索器的全部 id 依赖（变量序 = id 序、候选枚举序 = id 序，
    §15 指认的 ovh 伪像来源）因此都作用在规范编号上；候选生成元映射回原编号
    （π_old[order[i]] = order[π_new[i]]）后过等变裁决与闭包，判据数据
    （trans）自始至终是原编号。
    """
    NS = len(trans)
    adj_orig = backbone_adj(trans, n)
    adj_canon = [set(x) for x in _relabel_adj([sorted(a) for a in adj_orig], order)]
    color_canon = wl_refine(adj_canon)
    classes = {}
    for s in range(NS):
        classes.setdefault(color_canon[s], []).append(s)

    def _back(pi_canon):
        return [order[pi_canon[inv[x]]] for x in range(NS)]

    # 三路候选（编排与超参照抄 experiments_p3.discover，只换搜索所在的编号）
    gens_canon = graph_automorphisms(adj_canon, color_canon, max_gens=48)
    gens_canon = gens_canon + graph_automorphisms_rr(adj_canon, color_canon,
                                                     n_restarts=40, seed=7)
    n_invol = 0
    if gens_canon:
        invols = involution_automorphisms(adj_canon, color_canon)
        n_invol = len(invols)
        gens_canon = gens_canon + invols

    # 等变裁决（原实现、原编号数据；max TV=0 零容忍口径不变）
    good, _worst = [], 0.0
    for g in gens_canon:
        e, _ = equiv_error(trans, _back(g), n)
        _worst = max(_worst, e)
        if e <= 1e-9:
            good.append(_back(g))
    if not good:
        # 阶段 3 MRV fallback（照抄原编排：前两路全空时启用）
        n_mrv = 0
        mrv = graph_automorphisms_mrv(adj_canon, color_canon)
        n_mrv = len(mrv)
        for g in mrv:
            e, _ = equiv_error(trans, _back(g), n)
            if e <= 1e-9:
                good.append(_back(g))
        if not good:
            return [list(range(NS))], {"n_gens": len(gens_canon), "n_pass": 0,
                                       "n_classes": len(classes), "worst": _worst,
                                       "n_involution": n_invol, "n_mrv": n_mrv}
    else:
        n_mrv = 0

    # 闭包 + 哨兵复检（原实现、原编号数据）
    G = closure_perms(good, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _ = equiv_error(trans, g, n)
        worst2 = max(worst2, e)
    sentinel_ok = worst2 <= 1e-9
    return G, {"n_gens": len(gens_canon), "n_pass": len(good), "order": len(G),
               "worst_equiv": worst2, "sentinel_ok": sentinel_ok,
               "sentinel_n": len(sample), "n_classes": len(classes),
               "n_involution": n_invol}


def _discover_multilabel(trans, n, k, seed):
    """
    K 个随机重编号骨干图搜索的**生成元并集**（--multi-label 路径）。

    口径（与 _discover_canonized 同构，只把「规范重编号」换成「随机重编号」）：
      每臂 i：ρ_i = random.Random(seed) 流的第 i 个均匀随机置换（ρ[旧] = 新），
      三路图搜索（确定性 max_gens=48 → 随机重启 40 次 seed=7 → 对合 → 全空时
      MRV fallback，编排与超参照抄 discover）在 **ρ 重编号后的骨干图**上跑，
      候选生成元映射回原编号（g_orig[x] = ρ⁻¹[g_new[ρ[x]]]）后过等变裁决
      equiv_error（原实现、原编号数据，max TV=0 零容忍）；
      K 臂幸存生成元并集（去重）取闭包 + 哨兵复检（原编号，同 discover 口径）。
      判据数据（trans）自始至终是原编号。

    与实验口径的一致性：src/experiments_multilabel_union.py 的 plain 臂是
    「重编号整张转移表 + discover_gua（泛化 judge）」；本函数是「只重编号骨干图
    + 原编号位串 judge」——两条管线在位串模型上收获相同候选（同一重编号骨干图
    喂同一搜索器），逐元素集合相等已由该 json → pipeline_checks.
    judge_equivalence_random_instance（Q6 随机实例 arm(a) 阶 6 == arm(b) 阶 6，
    sets_equal=true）实证。等变裁决触发条件（MRV 仅在前两路全空时启用）与
    discover 逐项一致。

    返回 (并集群, 诊断 dict)；诊断含逐臂记录（n_candidates/n_pass/n_mrv/order）。
    """
    NS = len(trans)
    rng = random.Random(seed)
    adj_orig = [sorted(a) for a in backbone_adj(trans, n)]
    union_gens, arms = [], []
    for i in range(k):
        rho = list(range(NS))
        rng.shuffle(rho)
        inv = [0] * NS
        for old, new in enumerate(rho):
            inv[new] = old
        adj_i = [set() for _ in range(NS)]
        for old in range(NS):
            adj_i[rho[old]] = {rho[v] for v in adj_orig[old]}
        color = wl_refine(adj_i)
        gens_i = graph_automorphisms(adj_i, color, max_gens=48)
        gens_i = gens_i + graph_automorphisms_rr(adj_i, color, n_restarts=40, seed=7)
        if gens_i:
            gens_i = gens_i + involution_automorphisms(adj_i, color)
        good_i, n_mrv = [], 0
        for g in gens_i:
            gb = [inv[g[rho[x]]] for x in range(NS)]
            e, _ = equiv_error(trans, gb, n)
            if e <= 1e-9:
                good_i.append(gb)
        if not good_i:                       # 阶段 3 MRV fallback（同触发条件）
            mrv = graph_automorphisms_mrv(adj_i, color)
            n_mrv = len(mrv)
            for g in mrv:
                gb = [inv[g[rho[x]]] for x in range(NS)]
                e, _ = equiv_error(trans, gb, n)
                if e <= 1e-9:
                    good_i.append(gb)
        G_i = closure_perms(good_i, NS) if good_i else [list(range(NS))]
        arms.append({"i": i, "n_candidates": len(gens_i), "n_pass": len(good_i),
                     "n_mrv": n_mrv, "order": len(G_i)})
        union_gens.extend(good_i)

    dedup, seen = [], set()
    for g in union_gens:
        t = tuple(g)
        if t not in seen:
            seen.add(t)
            dedup.append(list(t))
    G = closure_perms(dedup, NS) if dedup else [list(range(NS))]
    sample = G[:64]                          # 哨兵复检（原编号，同 discover 口径）
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _ = equiv_error(trans, g, n)
        worst2 = max(worst2, e)
    sentinel_ok = worst2 <= 1e-9
    diag = {"n_arms": k, "seed": seed, "arms": arms, "n_union_gens": len(dedup),
            "order": len(G), "worst_equiv": worst2, "sentinel_ok": sentinel_ok,
            "sentinel_n": len(sample)}
    return G, diag


def _discover_extra(trans, n):
    """
    动作置换候选源版 discover（--extra-candidates 路径，生成器盲区修复）。

    背景（src/experiments_gua64_gapfix.py Part 1 诊断，代码级实证）：discover 的
    候选只来自三路图搜索器（experiments_p3.py discover 630-646 行），环境自身的
    动作置换（动作 a 的骨干后继映射 δ_a 为双射时）从不进候选集；gua64 上缺口
    294,912→589,824（= 缺综卦 τ 所在陪集）正是该候选源缺失 + 三路搜索器产出
    类型偏置的合力。修法 = 把 δ_a（双射动作）追加进候选集，与三路候选一起过
    **同一个**零容忍等变裁决（裁决口径不变 ⇒ 不可能引入伪自同构；闭包负责复合）。

    编排（copy from experiments_p3.py::discover 第 589-713 行默认路径同构，
    超参不动：max_gens=48 / 随机重启 40 次 seed=7 / 对合搜索 24 次 seed=7 /
    tol=1e-9 / MRV fallback 仅在三路全空时启用 / 闭包 + 哨兵复检），唯一差别：
    候选列表追加动作置换候选（copy from experiments_completeness.py::
    _action_candidates 第 103-109 行同口径——告警器「动作置换探针」的候选源
    升格进 discover 主体）。

    返回 (群, diag, extra_info)；extra_info = {"actions": 双射动作下标,
    "n_candidates": 候选数, "n_pass": 过等变数}。
    """
    NS = len(trans)
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)
    classes = {}
    for s in range(NS):
        classes.setdefault(color[s], []).append(s)

    gens = graph_automorphisms(adj, color, max_gens=48)
    gens = gens + graph_automorphisms_rr(adj, color, n_restarts=40, seed=7)
    n_invol = 0
    if gens:
        invols = involution_automorphisms(adj, color)
        n_invol = len(invols)
        gens = gens + invols

    extra = list(_action_candidates(trans, n))
    extra_actions = [a for a, _m in extra]
    gens = gens + [m for _a, m in extra]

    good, worst = [], 0.0
    for g in gens:
        e, _ = equiv_error(trans, g, n)
        worst = max(worst, e)
        if e <= 1e-9:
            good.append(g)
    extra_pass = sum(1 for _a, m in extra
                     if equiv_error(trans, m, n)[0] <= 1e-9)
    n_mrv = 0
    if not good:
        mrv = graph_automorphisms_mrv(adj, color)
        n_mrv = len(mrv)
        for g in mrv:
            e, _ = equiv_error(trans, g, n)
            if e <= 1e-9:
                good.append(g)
        if not good:
            return [list(range(NS))], {"n_gens": len(gens), "n_pass": 0,
                                       "n_classes": len(classes), "worst": worst,
                                       "n_involution": n_invol, "n_mrv": n_mrv}, {
                "actions": extra_actions, "n_candidates": len(extra),
                "n_pass": extra_pass}

    G = closure_perms(good, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _ = equiv_error(trans, g, n)
        worst2 = max(worst2, e)
    diag = {"n_gens": len(gens), "n_pass": len(good), "order": len(G),
            "worst_equiv": worst2, "sentinel_ok": worst2 <= 1e-9,
            "sentinel_n": len(sample), "n_classes": len(classes),
            "n_involution": n_invol}
    return G, diag, {"actions": extra_actions, "n_candidates": len(extra),
                     "n_pass": extra_pass}


# ---------------------------------------------------------------- 组合路径（三标志组合放开）
def _combined_arm(adj_x, color_x, back, judge, extra_list):
    """
    组合路径的单臂搜索：三路图搜索（确定性 max_gens=48 → 随机重启 40 次 seed=7 →
    对合，编排与超参照抄 discover / _discover_canonized）+ 可选动作置换候选，
    全部候选经 back 映回**原编号**后过 judge（泛化等变裁决，max TV=0 零容忍口径
    不变），三路与 extra 全空时 MRV fallback（同触发条件）。

    extra 候选在**原编号**上计算（_action_candidates(trans) 的 δ_a）：δ_a 与状态
    重编号可交换（转移行内容不随行位置变 ⇒ argmax 逐位不变；实验层 F5 恒等式
    「回搬候选 == std δ_a」逐环境 assert 同一事实，experiments_fullflags.py
    run_scan_c5_arm 第四步），故与实验层「重编号坐标算 extra 再回搬」逐位同收获。
    返回 (good 原编号幸存生成元, 诊断 dict)。
    """
    gens_x = graph_automorphisms(adj_x, color_x, max_gens=48)
    gens_x = gens_x + graph_automorphisms_rr(adj_x, color_x, n_restarts=40, seed=7)
    n_invol = 0
    if gens_x:
        invols = involution_automorphisms(adj_x, color_x)
        n_invol = len(invols)
        gens_x = gens_x + invols
    good, worst = [], 0.0
    for g in gens_x:
        gb = back(g)
        e = judge(gb)
        worst = max(worst, e)
        if e <= 1e-9:
            good.append(gb)
    n_extra_pass = 0
    for m in extra_list:
        if judge(m) <= 1e-9:
            good.append(list(m))
            n_extra_pass += 1
    n_mrv = 0
    if not good:
        mrv = graph_automorphisms_mrv(adj_x, color_x)
        n_mrv = len(mrv)
        for g in mrv:
            gb = back(g)
            if judge(gb) <= 1e-9:
                good.append(gb)
    return good, {"n_gens": len(gens_x), "n_pass": len(good),
                  "n_involution": n_invol, "n_mrv": n_mrv,
                  "n_extra_candidates": len(extra_list),
                  "n_extra_pass": n_extra_pass, "worst": worst}


def _closure_sentinel(good, judge, NS):
    """闭包 + 哨兵抽查（头 64 / 中 64 / 尾 32，discover 同款口径）。"""
    G = closure_perms(good, NS) if good else [list(range(NS))]
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        worst2 = max(worst2, judge(g))
    return G, {"order": len(G), "worst_equiv": worst2,
               "sentinel_ok": worst2 <= 1e-9, "sentinel_n": len(sample)}


def _union_closure(gen_lists, NS):
    """
    逐臂累计生成元并集去重取闭包（增量捷径 + 单调 assert）。
    copy 语义 = src/experiments_fullflags.py::c6_union_curve（C6 并集同口径：
    canonize 臂生成元恒在池内、k = multi 臂数、闭包只增不减）。
    返回 (并集群, 去重后并集生成元数)。
    """
    cur_set = {tuple(range(NS))}
    cur_order = 1
    cumulative, seen = [], set()
    for gl in gen_lists:
        for g in gl:
            t = tuple(g)
            if t not in seen:
                seen.add(t)
                cumulative.append(list(t))
        if not cumulative:
            continue
        if all(tuple(g) in cur_set for g in cumulative):
            continue                    # 捷径：累计并集生成元已全在当前闭包内
        G = closure_perms(cumulative, NS)
        assert len(G) >= cur_order, "并集闭包阶单调性违规（实现 bug）"
        cur_set = {tuple(g) for g in G}
        cur_order = len(G)
    return [list(g) for g in cur_set], len(cumulative)


def _detect_pad_states(trans, n_acts):
    """
    pad 哑态检测（S47 同口径，copy 自 pilot/s47_blindspot.py::load_scene 的 pad 判据）：
    所有动作都是「单后继、自环、奖励 0」的状态行 = 无信息哑态。
    只用于 --pad-aware 新臂的候选生成；判据与既有路径零接触。
    """
    return [s for s in range(len(trans))
            if all(len(trans[s][a]) == 1 and trans[s][a][0][1] == s
                   and trans[s][a][0][2] == 0.0 for a in range(n_acts))]


def _padaware_arm(trans, n, judge):
    """
    哑态商图臂（--pad-aware，pad 感知候选生成修复；判据零改动）。

    ## 为什么需要（S47 判决 = 生成侧隔离，pilot/s47_blindspot_v2.json）
    含 pad 哑态的模型上四路候选系统性漏掉跨哑态-真态对称元素（512 模型池普查
    real_touch_pass=0；σ 本体双口径 TV=0 但进不了候选池 ⇒ 阶 1 拒答）：
      · det：pad 色类（47 元）在回溯枚举序里先耗尽 max_gens=48，48 个候选全 pad-only；
      · rr：node_cap 死区（打乱候选序破坏恒等首降）；
      · 对合：全部 WL 色类大小 15/47/75 皆奇数 ⇒ 配对搜索结构性无解；
      · MRV fallback：DFS 回溯末位类先变体 ⇒ pad-only 完成式淹没 max_gens=4。
    四路同一根因 = 含 pad 全图上生成不了动真实态的候选 ⇒ 补「真态商图臂」：
    哑态折叠（删 pad 行、压缩重编号）后在商图上跑**同款**三路搜索（编排与超参
    照抄 _combined_arm：确定性 max_gens=48 → 随机重启 40 次 seed=7 → 对合 →
    全空时 MRV fallback），候选**哑态定点回填**全空间（真态按商图映射、pad 逐点
    不动）后过 judge（泛化等变判据 equiv_error_gua，max TV=0 零容忍口径不变）。

    ## 判据口径为何是泛化版（选型依据，探针实测 pilot/_w5_padprobe.py）
    位串版 equiv_error 的「动作 = 翻转第 a 位」口径对 pad 定点回填结构性不适用
    （512 模型商图候选回填后 4 个全部 bit=inf——pad 定点破坏位翻结构，与 75→5
    可见群机理同源）；泛化版从 trans 取骨干后继搜索动作像，对回填候选判定正常
    （4 个中 2 个 gua TV=0）。S47 预注册判据即 equiv_error_gua 泛化零容忍；
    CLI 组合路径同款口径。零容忍语义零改动：判据不过就是不过，不可能引入伪自同构。

    ## 守卫（收缩不保结构时如实跳过，不硬造候选）
      · 无 pad 哑态：skipped="no_pad_states"（新臂空转，其余路径照常）；
      · 真实行引用 pad：skipped="real_rows_reference_pad"（删除 pad 行会改变真实态
        的转移结构，商图候选与全空间判据不等价——如实跳过不冒进）。

    返回 (good 幸存生成元[原编号], 诊断 dict)。
    """
    NS = len(trans)
    pads = _detect_pad_states(trans, n)
    padset = set(pads)
    reals = [s for s in range(NS) if s not in padset]
    if not pads:
        return [], {"n_pad": 0, "n_real": len(reals), "n_candidates": 0,
                    "n_pass": 0, "n_involution": 0, "n_mrv": 0, "worst": 0.0,
                    "skipped": "no_pad_states"}
    if any(u in padset for s in reals for a in range(n)
           for (_p, u, _r) in trans[s][a]):
        return [], {"n_pad": len(pads), "n_real": len(reals), "n_candidates": 0,
                    "n_pass": 0, "n_involution": 0, "n_mrv": 0, "worst": 0.0,
                    "skipped": "real_rows_reference_pad"}
    # 真态商图：删 pad 行、压缩重编号（原 id 升序 = 保持相对序；真实行零 pad 引用
    # 已由守卫保证，故收缩只删自环行、不改变真实态之间的转移结构）
    idx = {s: i for i, s in enumerate(reals)}
    t_small = [[[ [p, idx[u], r] for (p, u, r) in trans[s][a]] for a in range(n)]
               for s in reals]
    adj_s = backbone_adj(t_small, n)
    color_s = wl_refine(adj_s)

    # 三路搜索（编排与超参照抄 _combined_arm，只换搜索所在的编号 = 商图编号）
    gens_s = graph_automorphisms(adj_s, color_s, max_gens=48)
    gens_s = gens_s + graph_automorphisms_rr(adj_s, color_s, n_restarts=40, seed=7)
    n_invol = 0
    if gens_s:
        invols = involution_automorphisms(adj_s, color_s)
        n_invol = len(invols)
        gens_s = gens_s + invols

    # 候选哑态定点回填全空间，再过同一判据（判据数据 trans 自始至终原编号）
    def _extend(pi_small):
        g = list(range(NS))
        for j, s in enumerate(reals):
            g[s] = reals[pi_small[j]]
        return g                            # pad 全定点：g[p] = p

    good, worst = [], 0.0
    for g_s in gens_s:
        g_full = _extend(g_s)
        e = judge(g_full)
        worst = max(worst, e)
        if e <= 1e-9:
            good.append(g_full)
    # MRV fallback（同触发条件：三路候选全空手时启用；商图上跑，回填后裁决）
    n_mrv = 0
    if not good:
        mrv_s = graph_automorphisms_mrv(adj_s, color_s)
        n_mrv = len(mrv_s)
        for g_s in mrv_s:
            g_full = _extend(g_s)
            if judge(g_full) <= 1e-9:
                good.append(g_full)
    return good, {"n_pad": len(pads), "n_real": len(reals),
                  "n_candidates": len(gens_s), "n_pass": len(good),
                  "n_involution": n_invol, "n_mrv": n_mrv,
                  "worst": worst, "skipped": None}


def _discover_combined(trans, n, canonize, multi_label, multi_seed, extra_candidates,
                       pad_aware=False):
    """
    三标志组合路径（--preset robust = canonize+extra+multi(k=8)）。

    语义 = 实验层 C5/C6 同口径（src/experiments_fullflags.py；judgment 见
    experiments_fullflags.json：C5 canonize+extra 达真 7/9、C6 三开 9/9 = 推荐配置）：
      · canonize 臂（canonize=True）：canonize_model_generic 规范化重编号——单分量
        骨干图直接走 CLI --canonize 同一 _canonize_model 路径；多分量骨干图
        （gua64 类）逐分量 canonize + 按分量证书字典序拼接（编号扫描同款扩展，
        整图 canonize 会超 CANON_NODE_CAP）——三路图搜索在规范编号骨干图上跑，
        候选映射回原编号过裁决（与 _discover_canonized 同构）；
      · multi 臂 i（multi_label=K）：random.Random(multi_seed) 流第 i 个均匀随机
        置换重编号骨干图上三路图搜索（--multi-label 同款编号批，同种子同编号、
        结果确定可复现；实验层 C6 的编号批是 per-seed batch_pi——同分布不同流，
        收获口径同构），候选映射回原编号过裁决；
      · extra（extra_candidates=True）：动作置换候选 δ_a（双射时）追加进每一臂
        候选集，与三路候选过同一个零容忍裁决（只增候选不减裁决）；
      · pad_aware（pad_aware=True，--pad-aware）：哑态商图臂追加进并集
        （真态商图 pad 折叠搜索 + 哑态定点回填 + 同一泛化判据，见 _padaware_arm；
        pad_aware=True 且其余标志全关 = plain 臂 + pad 臂的最小组合，编排同款）；
      · 幸存生成元逐臂累计并集去重取闭包（canonize 臂恒在池内 = C5 恒在池内，
        c6_union_curve 同款增量捷径与单调 assert）；判据数据（trans）自始至终
        是原编号。
    等变裁决 = equiv_error_gua（编号无关泛化判据，max TV=0 零容忍口径不变；
    位串实例上与位串版判定等价——experiments_discover_labeling.json → bridge）。
    plain 对照臂（consistency 基线）用同一泛化判据跑原编号三路搜索（不带标志
    口径 = 三路 only、不进并集）。

    返回 (并集群 G, plain 群 G_plain, 组合诊断 dict, 逐臂记录 list)。
    """
    NS = len(trans)
    # 惰性 import：experiments_discover_labeling 模块级反向 import 本包（循环），
    # experiments_gua64 为研究模块（import 无副作用）——都不能放模块级。
    from experiments_gua64 import equiv_error_gua

    def judge(g):
        return equiv_error_gua(trans, g, n)[0]

    adj_orig = backbone_adj(trans, n)
    color_orig = wl_refine(adj_orig)
    extra_list = [m for _a, m in _action_candidates(trans, n)] if extra_candidates else []
    arms, gen_lists = [], []
    sec_mags = {}

    # ---- plain 对照臂（不进并集；pad-aware 单独给时走专用分支，不进本函数）----
    t0 = time.perf_counter()
    good_plain, d_plain = _combined_arm(adj_orig, color_orig, lambda g: g, judge, [])
    G_plain, s_plain = _closure_sentinel(good_plain, judge, NS)
    sec_mags["plain_arm"] = _sec_magnitude(time.perf_counter() - t0)
    arms.append(dict(kind="plain(consistency-baseline)", diag=d_plain, sentinel=s_plain))

    # pad-aware 真实动元过滤口径：并集只收「动真实态」的幸存生成元。
    # 依据（512 实测，gw_padaware_run.json 实现记录）：组合路径 plain 臂用泛化
    # 判据，pad-only 结构自同构（48 个 det 候选全过 gua）会以 120 阶 Junk 淹没
    # 并集（600 = 120×5），违反 pad-aware 的验收口径（pad 全定点 + ⊆抽象 Aut）；
    # pad-only 元素在商图上是恒同，不承载跨哑态-真态信息。过滤是**候选池编排**
    # 选择，判据（零容忍裁决）一字不动。
    if pad_aware:
        _pad_ids = set(_detect_pad_states(trans, n))
        _reals = [s for s in range(NS) if s not in _pad_ids]

        def _real_movers(gens):
            return [g for g in gens
                    if any(g[s] != s for s in _reals)]
    else:
        def _real_movers(gens):
            return gens

    # ---- canonize 臂 ----
    cinfo = None
    if canonize:
        from experiments_discover_labeling import canonize_model_generic
        t0 = time.perf_counter()
        order_c, inv_c, cinfo = canonize_model_generic(trans, n)
        sec_canonize = time.perf_counter() - t0
        adj_canon = [set(x) for x in _relabel_adj([sorted(a) for a in adj_orig], order_c)]
        color_canon = wl_refine(adj_canon)

        def _back(pi):
            return [order_c[pi[inv_c[x]]] for x in range(NS)]

        good_c, d_c = _combined_arm(adj_canon, color_canon, _back, judge, extra_list)
        G_c, s_c = _closure_sentinel(good_c, judge, NS)
        sec_mags["canonize"] = _sec_magnitude(sec_canonize)
        sec_mags["canon_arm"] = _sec_magnitude(time.perf_counter() - t0)
        arms.append(dict(kind="canonical", diag=d_c, sentinel=s_c))
        gen_lists.append(_real_movers(good_c))

    # ---- multi 臂 ----
    if multi_label is not None:
        t0 = time.perf_counter()
        rng = random.Random(multi_seed)
        adj_sorted = [sorted(a) for a in adj_orig]
        for i in range(multi_label):
            rho = list(range(NS))
            rng.shuffle(rho)
            inv = [0] * NS
            for old, new in enumerate(rho):
                inv[new] = old
            adj_i = [set() for _ in range(NS)]
            for old in range(NS):
                adj_i[rho[old]] = {rho[v] for v in adj_sorted[old]}
            color_i = wl_refine(adj_i)

            def _back_i(pi, _inv=inv, _rho=rho):
                return [_inv[pi[_rho[x]]] for x in range(NS)]

            good_i, d_i = _combined_arm(adj_i, color_i, _back_i, judge, extra_list)
            G_i, s_i = _closure_sentinel(good_i, judge, NS)
            arms.append(dict(kind="random", i=i, diag=d_i, sentinel=s_i))
            gen_lists.append(_real_movers(good_i))
        sec_mags["multi_arms"] = _sec_magnitude(time.perf_counter() - t0)

    # ---- pad-aware 臂（哑态商图臂，--pad-aware 时启用；见 _padaware_arm）----
    if pad_aware:
        t0 = time.perf_counter()
        good_p, d_p = _padaware_arm(trans, n, judge)
        G_p, s_p = _closure_sentinel(good_p, judge, NS)
        sec_mags["pad_arm"] = _sec_magnitude(time.perf_counter() - t0)
        arms.append(dict(kind="pad-aware", diag=d_p, sentinel=s_p))
        gen_lists.append(_real_movers(good_p))

    # ---- 并集闭包 + 哨兵 ----
    t0 = time.perf_counter()
    G, n_union_gens = _union_closure(gen_lists, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        worst2 = max(worst2, judge(g))
    sec_mags["union_closure"] = _sec_magnitude(time.perf_counter() - t0)
    max_arm_order = max((a["sentinel"]["order"] for a in arms if a["kind"] != "plain(consistency-baseline)"),
                        default=1)
    assert len(G) >= max_arm_order, \
        "并集阶 %d < 最大单臂阶 %d（并集单调性违规 = 实现 bug）" % (len(G), max_arm_order)
    diag = {"order": len(G), "n_union_gens": n_union_gens,
            "worst_equiv": worst2, "sentinel_ok": worst2 <= 1e-9,
            "sentinel_n": len(sample)}
    return G, G_plain, diag, arms, {"canonize_info": cinfo, "sec_magnitudes": sec_mags}


def _discover_padaware(trans, n):
    """
    --pad-aware 单标志路径：**plain（位串判据，与不带标志同管线）**
    ∪ **哑态商图臂**（泛化判据，见 _padaware_arm）的幸存生成元并集取闭包。

    ## 为什么 plain 臂保留位串判据、并集不做真实动元过滤（与组合路径的差异）
    单标志语义 = 「不带标志的 plain 之上只增候选」：plain 臂与不带标志的
    discover 逐位同管线（同编排同超参同判据），其幸存生成元原样进并集——
    位串判据自身把 pad-only 结构自同构拒之门外（512 实测 48 候选全 inf），
    无需额外过滤；商图臂候选天生动真实态（pad 不在商图里）且 pad 全定点。
    ⇒ 并集里不会混入 pad-only Junk（512 实测：plain 臂 0 幸存 + 商图臂 2 幸存
    ⇒ 阶 5、pad 全定点、⊆抽象 Aut=75）。组合路径（≥2 标志）的 plain 臂用泛化
    判据（C5/C6 口径），pad-only 元素会过判据，故那边需要真实动元过滤——
    两条路径口径不同、各自自洽，见各自 docstring。

    判据零改动：两个判据都是原实现 import（位串 equiv_error / 泛化
    equiv_error_gua，max TV=0 零容忍）；哨兵复检用泛化判据（并集含商图臂元素，
    位串判据对 pad 定点回填结构性不适用；plain 臂幸存元过位串判据 ⇒ 必过泛化）。
    退出码语义零改动（trivial → 1）。

    返回 (群 G, plain 群 G_plain, 诊断 dict, pad-aware payload 块)。
    """
    NS = len(trans)
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)

    # plain 臂（位串判据；_combined_arm 与 experiments_p3.discover 默认路径
    # 同编排同超参：det max_gens=48 → rr 40 次 seed=7 → 对合 → 全空 MRV fallback）
    def _judge_bit(g):
        return equiv_error(trans, g, n)[0]

    good_plain, d_plain = _combined_arm(adj, color, lambda g: g, _judge_bit, [])
    G_plain = closure_perms(good_plain, NS) if good_plain else [list(range(NS))]

    # 哑态商图臂（泛化判据；惰性 import 研究模块）
    from experiments_gua64 import equiv_error_gua

    def _judge_gua(g):
        return equiv_error_gua(trans, g, n)[0]

    good_pad, d_pad = _padaware_arm(trans, n, _judge_gua)

    # 并集去重取闭包 + 哨兵（泛化判据；plain 幸存元过位串判据 ⇒ 必过泛化）
    union, seen = [], set()
    for g in good_plain + good_pad:
        t = tuple(g)
        if t not in seen:
            seen.add(t)
            union.append(list(t))
    G, s_union = _closure_sentinel(union, _judge_gua, NS)
    diag = {"n_plain_pass": len(good_plain), "n_pad_pass": len(good_pad),
            "n_union_gens": len(union), "order": len(G),
            "worst_equiv": s_union["worst_equiv"],
            "sentinel_ok": s_union["sentinel_ok"], "sentinel_n": s_union["sentinel_n"],
            "plain_diag": d_plain}
    padinfo = {"enabled": True,
               "scope": ("哑态商图臂口径（生成侧隔离修复）：检测 pad 哑态"
                         "（全动作单后继自环 r=0 行）后，在真态商图（删 pad 行、压缩"
                         "重编号）上跑同款三路图搜索（确定性 max_gens=48 → 随机重启 "
                         "40 次 seed=7 → 对合 → 全空时 MRV fallback，超参不动），"
                         "候选哑态定点回填全空间后过同一个 max TV=0 零容忍等变裁决"
                         "（泛化判据 equiv_error_gua——位串判据「动作=翻第 a 位」口径"
                         "对 pad 定点回填结构性不适用，探针实测 4 候选全 bit=inf，"
                         "pilot/_w5_padprobe.py）。判据零容忍语义与退出码零改动；"
                         "无 pad 哑态或真实行引用 pad 时本臂如实跳过不冒进"),
               "pad_arm": d_pad,
               "plain_arm": {"n_pass": len(good_plain),
                             "judge": "equiv_error（位串，与不带标志同管线）"},
               "consistency": {}}
    return G, G_plain, diag, padinfo


_RECURSION_TRIGGER_HEADROOM = 128   # 现余量低于此才介入（NS≤512 按构造零触碰）
_RECURSION_MARGIN = 4096            # 介入时给足裕量（覆盖 bt 外层帧与 canonize 树）


def _ensure_recursion_depth(n_states):
    """
    图搜索回溯的递归深度护栏——16k 带无需外部 setrecursionlimit。

    诊断：graph_automorphisms / graph_automorphisms_rr / graph_automorphisms_mrv
    的回溯 bt 每处理一个顶点递归一层（src/experiments_p3.py:198/272/425），
    canonize 个体化-细化树同款（src/experiments_canonical_search.py:142）——
    深度上界都是状态数 NS。NS=16,384 > Python 默认上限 1000 ⇒ RecursionError
    ⇒ CLI exit 3（证据：pilot/gw_teambattle_discover_main.json，≈4s 崩溃）。

    修法（选型 b，包内自适应上限；预注册 pilot/prereg_w1_recursion_fix.json）：
    只动递归上限、零字节不改任何搜索器/判据——当前上限连 NS+128 头寸都不够时，
    提到 max(当前, NS+4096)。NS+4096 与实证够用的外部 30000 同量级
    （belt2_discover_v2 跑通 900s 无 RecursionError）；CPython 3.11+ 纯 Python
    递归不逐帧吃 C 栈，帧对象堆分配，20,480 深度的内存代价为 ~10MB 量级。

    回归保护（按构造）：默认上限 1000 时，NS≤872 完全不触碰递归上限——
    历史全部环境（NS≤512）的行为与输出逐位不变；仅在真正的大规模上介入。

    本函数静默（不写 stderr/stdout）——discover 的 stdout 是 JSON payload，
    任何插话都会污染逐位回归比对。返回 (介入前上限, 介入后上限, 是否介入)。
    """
    cur = sys.getrecursionlimit()
    if cur < n_states + _RECURSION_TRIGGER_HEADROOM:
        target = max(cur, n_states + _RECURSION_MARGIN)
        sys.setrecursionlimit(target)
        return cur, target, True
    return cur, cur, False


def run_discover(model, canonize=False, multi_label=None, multi_label_seed=20261025,
                 extra_candidates=False, preset=None, pad_aware=False):
    """
    对模型跑 src/experiments_p3.py 的 discover，编排成 stdout JSON payload。
    只找到平凡群（阶 1）时 trivial=true，按「群不可用」拒答（CLI 退出码 1）。
    payload 附带 completeness 字段（完整性告警器：分数/是否告警/理由）——
    它评估「这个群可能没找全」，是启发式评估，不改变退出码语义。

    canonize=True（--canonize 标志）：规范化重编号后再跑同一套搜索
    （结构图规范化口径，见 _canonize_model / _discover_canonized）。
    群阶/轨道数与不 canonize 的对照写入 payload 的 canonize.consistency 字段，
    **不做硬 assert、不改变退出码**——实测发现 discover 的发现结果本身就有
    编号伪像（平移编号 Q₆ 上 plain 只找到 6/32，--canonize 找到完整 720/7），
    不一致恰恰说明 plain 被编号伪像削弱、canonize 结果更可信（哨兵复检与
    max TV=0 等变裁决照常执行）；一致性硬断言只放在 selftest 的标准环境分支。
    输出 elements/orbits 始终是原编号（可直接当 group.json 用于原模型），
    并附加 canonize 字段（用时量级 / 映射摘要 / 一致性对照）。

    multi_label=K（--multi-label K）：K 个随机重编号骨干图搜索的生成元
    并集取闭包（见 _discover_multilabel），种子由 multi_label_seed 控制。consistency
    语义与 canonize 同款（对照 plain、只报告不报错、不改变退出码）；K 较小时并集
    可能低于幸运编号上的 plain（如实报告），增大 K 并集只增不减（闭包单调）。依据：
    experiments_multilabel_union.json（k 曲线 + 预注册判读）；选型对照见本包
    README「三标志怎么选」一节。

    组合（三标志任意组合 + preset=None|"robust"）：两枚及以上
    标志同时给出时走 _discover_combined（实验层 C5/C6 同口径，见其 docstring）；
    preset="robust"（CLI --preset robust 解析而成）= canonize+extra+multi(k=8，
    k 由 --multi-label 覆盖)。单标志路径行为与组合放开前逐位一致；不带任何标志
    的默认路径与本函数加入前逐位一致（回归硬约束）。
    """
    trans, n_acts, NS = model["trans"], model["n_actions"], model["n_states"]
    _ensure_recursion_depth(NS)     # 递归护栏：NS 大于头寸时抬高递归上限（NS≤872 零触碰）
    if not canonize and multi_label is None and not extra_candidates and not pad_aware:
        G, diag = _discover(trans, n_acts)
        orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
        trivial = len(G) <= 1
        completeness = assess_completeness(trans, n_acts, G,
                                           standard_equiv_fn(trans, n_acts),
                                           label="wuxing_gua discover")
        return {
            "command": "discover",
            "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
            "order": len(G),
            "trivial": trivial,
            "n_orbits": len(orbits),
            "compression": (NS / len(orbits)) if orbits else None,
            "orbits": orbits,
            "elements": [list(g) for g in G],
            "generators": _compact_generators(G, NS),
            "diagnostics": diag,
            "completeness": completeness,
            "note": ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
                     "注意：discover 只看转移、不看奖励；若奖励破坏了对称，"
                     "发现的群还须过 check 的奖励剖面层" if trivial else
                     "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
                     "用前建议先过 check 两层判据" % NS),
        }

    # ---------------------------------------------------------- --pad-aware 路径（单标志）
    if pad_aware and not canonize and multi_label is None and not extra_candidates:
        from experiments_gua64 import equiv_error_gua   # 惰性（研究模块，import 无副作用）
        G, G_plain, diag, padinfo = _discover_padaware(trans, n_acts)
        orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
        orbits_plain = sorted((sorted(ob) for ob in orbits_of(G_plain, NS)),
                              key=lambda o: o[0])
        trivial = len(G) <= 1
        # completeness 评估域守卫（与组合路径同款）：仿射探针按位串口径构造
        # （_bit_perm_maps 假设 n_states = 2^n_actions），本模型 512 = 2^9 态
        # 7 动作不满足 ⇒ 如实跳过；判据本身不受影响。
        if (1 << n_acts) == NS:
            completeness = assess_completeness(
                trans, n_acts, G, lambda pi: equiv_error_gua(trans, pi, n_acts)[0],
                label="wuxing_gua discover(pad-aware)")
        else:
            completeness = {
                "skipped": True,
                "reason": ("completeness 评估器的仿射探针按位串口径构造（假设 "
                           "n_states = 2^n_actions），本模型 n_actions=%d、n_states=%d "
                           "不满足（如 GameWXXX 512=2^9 态 7 动作）——如实跳过；"
                           "判据本身不受影响（max TV=0 等变裁决、闭包、哨兵复检"
                           "全部照常执行）" % (n_acts, NS)),
            }
        order_match = (len(G) == len(G_plain))
        orbits_match = (len(orbits) == len(orbits_plain))
        note = ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
                "注意：discover 只看转移、不看奖励；若奖励破坏了对称，"
                "发现的群还须过 check 的奖励剖面层" if trivial else
                "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
                "用前建议先过 check 两层判据" % NS)
        if not (order_match and orbits_match):
            note += ("；pad_aware.consistency 显示与 plain 臂的结果不一致：含 pad "
                     "哑态时 plain 臂的发现被「生成侧隔离」削弱（S47 判决：四路候选"
                     "进不了跨哑态-真态对称元素），哑态商图臂补上的正是这一路；全部"
                     "候选仍过 max TV=0 零容忍等变裁决，哨兵复检照常执行")
        padinfo["consistency"] = {
            "order_plain": len(G_plain), "order_padaware": len(G),
            "order_match": order_match,
            "n_orbits_plain": len(orbits_plain), "n_orbits_padaware": len(orbits),
            "n_orbits_match": orbits_match,
            "elements_same_set_as_plain":
                ({tuple(g) for g in G} == {tuple(g) for g in G_plain}),
            "orbits_identical_as_sets": orbits == orbits_plain,
        }
        return {
            "command": "discover",
            "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
            "order": len(G),
            "trivial": trivial,
            "n_orbits": len(orbits),
            "compression": (NS / len(orbits)) if orbits else None,
            "orbits": orbits,
            "elements": [list(g) for g in G],
            "generators": _compact_generators(G, NS),
            "diagnostics": diag,
            "completeness": completeness,
            "pad_aware": padinfo,
            "note": note,
        }

    # ---------------------------------------------------------- --extra-candidates 路径（单标志）
    if extra_candidates and not canonize and multi_label is None and not pad_aware:
        G_plain, _diag_plain = _discover(trans, n_acts)
        G, diag, xinfo = _discover_extra(trans, n_acts)
        orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
        orbits_plain = sorted((sorted(ob) for ob in orbits_of(G_plain, NS)),
                              key=lambda o: o[0])
        trivial = len(G) <= 1
        completeness = assess_completeness(trans, n_acts, G,
                                           standard_equiv_fn(trans, n_acts),
                                           label="wuxing_gua discover(extra-candidates)")
        order_match = len(G) == len(G_plain)
        orbits_match = len(orbits) == len(orbits_plain)
        note = ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
                "注意：discover 只看转移、不看奖励；若奖励破坏了对称，"
                "发现的群还须过 check 的奖励剖面层" if trivial else
                "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
                "用前建议先过 check 两层判据" % NS)
        if not (order_match and orbits_match):
            note += ("；extra_candidates.consistency 显示与不带标志的结果不一致："
                     "动作置换候选源补充了三路图搜索漏掉的生成元（群阶更大、更可信——"
                     "全部候选仍过 max TV=0 零容忍等变裁决，哨兵复检照常执行）")
        return {
            "command": "discover",
            "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
            "order": len(G),
            "trivial": trivial,
            "n_orbits": len(orbits),
            "compression": (NS / len(orbits)) if orbits else None,
            "orbits": orbits,
            "elements": [list(g) for g in G],
            "generators": _compact_generators(G, NS),
            "diagnostics": diag,
            "completeness": completeness,
            "extra_candidates": {
                "enabled": True,
                "scope": ("动作置换候选源：每个动作 a 的最优后继映射 δ_a（与告警器"
                          "动作置换探针同口径，experiments_completeness."
                          "_action_candidates）为双射时作为候选生成元，与三路图"
                          "搜索候选一起过同一个 max TV=0 零容忍等变裁决；闭包负责"
                          "复合。判据与超参不变，只增候选不减裁决"),
                "actions": xinfo["actions"],
                "n_candidates": xinfo["n_candidates"],
                "n_pass": xinfo["n_pass"],
                "consistency": {
                    "order_plain": len(G_plain), "order_extra": len(G),
                    "order_match": order_match,
                    "n_orbits_plain": len(orbits_plain), "n_orbits_extra": len(orbits),
                    "n_orbits_match": orbits_match,
                    "elements_same_set_as_plain":
                        ({tuple(g) for g in G} == {tuple(g) for g in G_plain}),
                    "orbits_identical_as_sets": orbits == orbits_plain,
                },
            },
            "note": note,
        }

    # ---------------------------------------------------------- --multi-label 路径（单标志）
    if multi_label is not None and not canonize and not extra_candidates and not pad_aware:
        G_plain, _diag_plain = _discover(trans, n_acts)
        G, diag = _discover_multilabel(trans, n_acts, multi_label, multi_label_seed)
        orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
        orbits_plain = sorted((sorted(ob) for ob in orbits_of(G_plain, NS)),
                              key=lambda o: o[0])
        trivial = len(G) <= 1
        elements_same_set = ({tuple(g) for g in G} == {tuple(g) for g in G_plain})
        orbits_identical = (orbits == orbits_plain)
        order_match = (len(G) == len(G_plain))
        orbits_match = (len(orbits) == len(orbits_plain))
        completeness = assess_completeness(trans, n_acts, G,
                                           standard_equiv_fn(trans, n_acts),
                                           label="wuxing_gua discover(multi-label)")
        note = ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
                "注意：discover 只看转移、不看奖励；若奖励破坏了对称，"
                "发现的群还须过 check 的奖励剖面层" if trivial else
                "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
                "用前建议先过 check 两层判据" % NS)
        if not (order_match and orbits_match):
            note += ("；multi_label.consistency 显示与不带标志的结果不一致："
                     "plain 的发现随输入编号变（编号伪像），并集策略不依赖任何"
                     "编号假设（K 个随机重编号的生成元并集取闭包，增大 K 并集"
                     "只增不减——闭包单调）；K 较小时并集也可能低于幸运编号上的"
                     " plain（如实报告，不改变退出码；哨兵复检与 max TV=0 等变"
                     "裁决照常执行）")
        return {
            "command": "discover",
            "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
            "order": len(G),
            "trivial": trivial,
            "n_orbits": len(orbits),
            "compression": (NS / len(orbits)) if orbits else None,
            "orbits": orbits,
            "elements": [list(g) for g in G],
            "generators": _compact_generators(G, NS),
            "diagnostics": diag,
            "completeness": completeness,
            "multi_label": {
                "enabled": True,
                "k": multi_label,
                "seed": multi_label_seed,
                "scope": ("随机重编号口径：每臂把骨干图按一个固定种子流出的均匀随机"
                          "置换重编号后跑同一套三路图搜索（确定性/重启/对合/MRV "
                          "fallback），候选生成元映射回原编号过等变裁决；K 臂幸存"
                          "生成元并集去重取闭包 + 哨兵复检。判据数据自始至终是"
                          "原编号。与 --canonize 的差异：重编号不取规范形、取随机"
                          "——不依赖任何编号假设，代价是 K 臂重复搜索"),
                "arms": diag["arms"],
                "n_union_gens": diag["n_union_gens"],
                "consistency": {
                    "order_plain": len(G_plain), "order_union": len(G),
                    "order_match": order_match,
                    "n_orbits_plain": len(orbits_plain), "n_orbits_union": len(orbits),
                    "n_orbits_match": orbits_match,
                    "elements_same_set_as_plain": elements_same_set,
                    "orbits_identical_as_sets": orbits_identical,
                },
            },
            "note": note,
        }

    # ---------------------------------------------------------- 组合路径（≥2 标志同给 / --preset robust / --pad-aware）
    if pad_aware or (canonize and (multi_label is not None or extra_candidates)) or \
            (multi_label is not None and extra_candidates):
        from experiments_gua64 import equiv_error_gua   # 惰性（研究模块，import 无副作用）
        G, G_plain, diag, arms, xinfo = _discover_combined(
            trans, n_acts, canonize, multi_label, multi_label_seed, extra_candidates,
            pad_aware=pad_aware)
        orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
        orbits_plain = sorted((sorted(ob) for ob in orbits_of(G_plain, NS)),
                              key=lambda o: o[0])
        trivial = len(G) <= 1
        # completeness 评估域守卫：仿射探针按位串口径构造（_bit_perm_maps 假设
        # n_states = 2^n_actions，src/experiments_completeness.py），非位串动作
        # 模型（n_actions ≠ n_bits，如六十四卦错/综/互 3 动作 64 态）超出其适用
        # 域——如实跳过、不输出误导性评分；判据本身（等变裁决/闭包/哨兵）不受影响。
        if (1 << n_acts) == NS:
            completeness = assess_completeness(
                trans, n_acts, G, lambda pi: equiv_error_gua(trans, pi, n_acts)[0],
                label="wuxing_gua discover(combined)")
        else:
            completeness = {
                "skipped": True,
                "reason": ("completeness 评估器的仿射探针按位串口径构造（假设 "
                           "n_states = 2^n_actions；src/experiments_completeness."
                           "py::_bit_perm_maps），本模型 n_actions=%d、n_states=%d "
                           "为非位串动作模型（如六十四卦错/综/互），超出其适用域——"
                           "如实跳过；判据本身不受影响（max TV=0 等变裁决、闭包、"
                           "哨兵复检全部照常执行）" % (n_acts, NS)),
            }
        order_match = (len(G) == len(G_plain))
        orbits_match = (len(orbits) == len(orbits_plain))
        note = ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
                "注意：discover 只看转移、不看奖励；若奖励破坏了对称，发现的群"
                "还须过 check 的奖励剖面层" if trivial else
                "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
                "用前建议先过 check 两层判据" % NS)
        if not (order_match and orbits_match):
            note += ("；combination.consistency 显示与不带标志的结果不一致：并集策略"
                     "不依赖任何编号假设（增大 K 并集只增不减——闭包单调），不一致"
                     "通常说明 plain 发现被编号伪像削弱；哨兵复检与 max TV=0 等变"
                     "裁决照常执行")
        ci = xinfo["canonize_info"]
        return {
            "command": "discover",
            "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
            "order": len(G),
            "trivial": trivial,
            "n_orbits": len(orbits),
            "compression": (NS / len(orbits)) if orbits else None,
            "orbits": orbits,
            "elements": [list(g) for g in G],
            "generators": _compact_generators(G, NS),
            "diagnostics": diag,
            "completeness": completeness,
            "combination": {
                "enabled": True,
                "config": {
                    "preset": preset,
                    "canonize": bool(canonize),
                    "multi_label": multi_label,
                    "extra_candidates": bool(extra_candidates),
                    # pad_aware 键只在 --pad-aware 给出时出现（不带标志的组
                    # 合路径输出逐字节不变——回归硬约束口径）。
                    **({"pad_aware": True} if pad_aware else {}),
                    "seed": multi_label_seed,
                },
                "preset_note": (None if preset is None else
                                "--preset robust = --canonize --extra-candidates "
                                "--multi-label 8（k 可由 --multi-label 覆盖，种子由 "
                                "--seed 控制）"),
                "scope": ("组合口径（实验层 C5/C6 同构，experiments_fullflags.json → "
                          "judgment：C5 canonize+extra 达真 7/9、C6 三开 9/9 = 推荐"
                          "配置）：canonize 臂在规范编号骨干图上搜索、multi 臂在随机"
                          "重编号骨干图上搜索（--multi-label 同款种子流）、extra 把"
                          "双射动作 δ_a 追加进每臂候选集；幸存生成元逐臂"
                          "累计并集去重取闭包（canonize 臂恒在池内，增量捷径 + 单调 "
                          "assert）。判据数据自始至终原编号；等变裁决 = equiv_error_gua "
                          "泛化版（max TV=0 零容忍口径不变；位串实例上与位串版判定"
                          "等价，experiments_discover_labeling.json → bridge）"
                          + ("；pad_aware=True 时再追加哑态商图臂（真态商图 pad 折叠"
                             "搜索 + 哑态定点回填，S47 生成侧隔离修复，判据同款泛化"
                             "零容忍）并只收「动真实态」的幸存生成元进并集（pad-only "
                             "结构自同构在商图上是恒同，不承载跨哑态-真态信息）"
                             if pad_aware else "")),
                "implementation": ("同构实现（core_discover._discover_combined）："
                                   "canonize = import canonize_model_generic（单分量"
                                   "骨干图即 CLI --canonize 同一 _canonize_model 路径，"
                                   "多分量逐分量拼接）；判据 = import experiments_gua64."
                                   "equiv_error_gua；并集闭包 copy 自 experiments_"
                                   "fullflags.c6_union_curve；三路搜索编排/超参照抄 "
                                   "discover"),
                "arms": [({"kind": a["kind"]} |
                          ({"i": a["i"]} if "i" in a else {}) |
                          {"order": a["sentinel"]["order"],
                           "sentinel_ok": a["sentinel"]["sentinel_ok"]} |
                          {k: v for k, v in a["diag"].items()}) for a in arms],
                "n_union_gens": diag["n_union_gens"],
                "canonize_info": (None if ci is None else {
                    "canon_search_nodes": ci["canon_search_nodes"],
                    "canon_sec_magnitude": ci["canon_sec_magnitude"],
                    "mapping": ci["mapping"]}),
                "sec_magnitudes": xinfo["sec_magnitudes"],
                "consistency": {
                    "order_plain": len(G_plain), "order_union": len(G),
                    "order_match": order_match,
                    "n_orbits_plain": len(orbits_plain), "n_orbits_union": len(orbits),
                    "n_orbits_match": orbits_match,
                    "elements_same_set_as_plain":
                        ({tuple(g) for g in G} == {tuple(g) for g in G_plain}),
                    "orbits_identical_as_sets": orbits == orbits_plain,
                },
            },
            "note": note,
        }

    # ---------------------------------------------------------- --canonize 路径（单标志）
    order, inv, cinfo = _canonize_model(trans, n_acts)
    G_plain, _diag_plain = _discover(trans, n_acts)
    G, diag = _discover_canonized(trans, n_acts, order, inv)
    orbits = sorted((sorted(ob) for ob in orbits_of(G, NS)), key=lambda o: o[0])
    orbits_plain = sorted((sorted(ob) for ob in orbits_of(G_plain, NS)),
                          key=lambda o: o[0])
    trivial = len(G) <= 1
    elements_same_set = ({tuple(g) for g in G} == {tuple(g) for g in G_plain})
    orbits_identical = (orbits == orbits_plain)
    order_match = (len(G) == len(G_plain))
    orbits_match = (len(orbits) == len(orbits_plain))
    completeness = assess_completeness(trans, n_acts, G,
                                       standard_equiv_fn(trans, n_acts),
                                       label="wuxing_gua discover(canonize)")
    note = ("仅找到平凡群（阶 1）：未发现非平凡对称 ⇒ 按判据拒答（退出码 1）。"
            "注意：discover 只看转移、不看奖励；若奖励破坏了对称，"
            "发现的群还须过 check 的奖励剖面层" if trivial else
            "elements 字段可直接用作 group.json 的 elements（配 n_states=%d）；"
            "用前建议先过 check 两层判据" % NS)
    if not (order_match and orbits_match):
        note += ("；canonize.consistency 显示与不 canonize 的结果不一致："
                 "plain 发现被编号伪像削弱（同环境下编号不同的输入会找到不同的群），"
                 "本结果在规范编号上搜索、更可信（哨兵复检与 max TV=0 等变裁决照常执行）")
    return {
        "command": "discover",
        "n_bits": model["n_bits"], "n_states": NS, "n_actions": n_acts,
        "order": len(G),
        "trivial": trivial,
        "n_orbits": len(orbits),
        "compression": (NS / len(orbits)) if orbits else None,
        "orbits": orbits,
        "elements": [list(g) for g in G],
        "generators": _compact_generators(G, NS),
        "diagnostics": diag,
        "completeness": completeness,
        "canonize": {
            "enabled": True,
            "scope": ("结构图规范化口径：canonize 在骨干图上判定（§16 图口径，"
                      "不重排整张转移表——等变裁决的位串口径要求动作=翻转第 a 位），"
                      "三路图搜索在规范编号上跑，候选映射回原编号后过等变裁决与闭包"),
            "implementation": ("import 复用 src/experiments_canonical_search.py 的 canonize"
                               "（规范 WL + 个体化-细化树 + lex-min 证书，未复制改写）"),
            "canon_search_nodes": cinfo["canon_search_nodes"],
            "canon_sec_magnitude": cinfo["canon_sec_magnitude"],
            "mapping": cinfo["mapping"],
            "consistency": {
                "order_plain": len(G_plain), "order_canon": len(G),
                "order_match": order_match,
                "n_orbits_plain": len(orbits_plain), "n_orbits_canon": len(orbits),
                "n_orbits_match": orbits_match,
                "elements_same_set_as_plain": elements_same_set,
                "orbits_identical_as_sets": orbits_identical,
            },
        },
        "note": note,
    }
