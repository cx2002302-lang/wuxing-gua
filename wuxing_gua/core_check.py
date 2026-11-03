# -*- coding: utf-8 -*-
"""
core_check.py —— check / check-sample 共用的装载、校验与两层零容忍判据

━━ 出处（import 复用，未复制、未改写判据逻辑）━━━━━━━━━━━━━━━━━━━━━━━━━
  · 转移等变（max TV = 0 零容忍）   equiv_error    ← src/experiments_p3.py（discover
    的最终裁决（等变检验是零容忍最终裁决 max TV = 0 才放行）
  · 奖励剖面（n_bad = 0 零容忍）     cheap_check    ← src/experiments_p4.py（完整转移表版）
  · 轨道划分 orbits_of                              ← src/experiments_e1.py
  · 置换群闭包 closure_perms                         ← src/experiments_p3.py

本文件新增的只有「装载 + 输入校验 + 闭包 + 两层编排」；判据本身一行未改。
容忍度 TV_TOL = 1e-9 与 src/experiments_p3.py discover 的 tol 缺省值一致。
"""
import json
import math
import os
import random

from experiments_p3 import equiv_error, closure_perms, tvd, dist_of
from experiments_gua64 import equiv_error_gua   # 泛化判据：动作不必是「翻第 a 位」
from experiments_p4 import cheap_check
from experiments_e1 import orbits_of

from .errors import GroupInvalid, InputError

# 完整表版等变校验的容忍度：与 src/experiments_p3.py discover 缺省 tol 一致
TV_TOL = 1e-9
# 逐元素等变复检的规模上限；超过则按 discover 的哨兵口径抽查
# （贪心生成元 + 头/中/尾样本），依据「等变关于复合封闭」的数学论证。
ELEM_VERIFY_CAP = 5000
# 转移概率和的输入校验容差
PROB_SUM_TOL = 1e-6


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ---------------------------------------------------------------- 模型装载
def load_model(path):
    """装载并校验 model.json（README 输入格式）。不合法 → InputError（退出码 3）。"""
    if not os.path.isfile(path):
        raise InputError("模型文件不存在：%s" % path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise InputError("模型文件读取/解析失败：%s" % e)
    if not isinstance(raw, dict):
        raise InputError("模型 JSON 顶层必须是对象")
    for key in ("n_bits", "n_actions", "trans"):
        if key not in raw:
            raise InputError("模型缺少字段 %r（输入格式见 wuxing_gua/README.md）" % key)

    n_bits, n_actions = raw["n_bits"], raw["n_actions"]
    if not (_is_int(n_bits) and n_bits >= 1):
        raise InputError("n_bits 必须是 >=1 的整数")
    if not (_is_int(n_actions) and n_actions >= 1):
        raise InputError("n_actions 必须是 >=1 的整数")
    # 2026-10-29：原校验要求 n_actions <= n_bits（「动作 a = 翻第 a 位」的编码假设）。
    # 该假设只约束**位串判据**；泛化判据 equiv_error_gua 不依赖它，故这里放行，
    # 由转移层按 n_actions 与 n_bits 的关系分派判据。
    n_states = 1 << n_bits
    if "n_states" in raw and raw["n_states"] != n_states:
        raise InputError("n_states=%r 与 2**n_bits=%d 不一致" % (raw["n_states"], n_states))

    trans_raw = raw["trans"]
    if not (isinstance(trans_raw, list) and len(trans_raw) == n_states):
        raise InputError("trans 必须是长度 2**n_bits=%d 的列表（实际 %r）"
                         % (n_states, len(trans_raw) if isinstance(trans_raw, list) else type(trans_raw)))
    trans = []
    for s, row in enumerate(trans_raw):
        if not (isinstance(row, list) and len(row) == n_actions):
            raise InputError("trans[%d] 必须是长度 n_actions=%d 的列表" % (s, n_actions))
        srow = []
        for a, lst in enumerate(row):
            if not (isinstance(lst, list) and lst):
                raise InputError("trans[%d][%d] 必须是非空列表" % (s, a))
            out = []
            total = 0.0
            for k, tr in enumerate(lst):
                if not (isinstance(tr, (list, tuple)) and len(tr) == 3):
                    raise InputError("trans[%d][%d][%d] 必须是 [p, u, r] 三元组" % (s, a, k))
                p, u, r = tr
                if not (isinstance(p, (int, float)) and not isinstance(p, bool)
                        and math.isfinite(p) and p >= 0.0):
                    raise InputError("trans[%d][%d][%d] 概率 p=%r 非法（需非负有限数）" % (s, a, k, p))
                if not (_is_int(u) and 0 <= u < n_states):
                    raise InputError("trans[%d][%d][%d] 后继 u=%r 越界（应为 0..%d）" % (s, a, k, u, n_states - 1))
                if not (isinstance(r, (int, float)) and not isinstance(r, bool) and math.isfinite(r)):
                    raise InputError("trans[%d][%d][%d] 奖励 r=%r 非法（需有限数）" % (s, a, k, r))
                total += float(p)
                out.append((float(p), u, float(r)))
            if abs(total - 1.0) > PROB_SUM_TOL:
                raise InputError("trans[%d][%d] 概率和 %.9f 偏离 1 超过 %g"
                                 % (s, a, total, PROB_SUM_TOL))
            srow.append(out)
        trans.append(srow)

    goals_raw = raw.get("goals", [])
    if not isinstance(goals_raw, list):
        raise InputError("goals 必须是状态列表")
    goals = set()
    for g in goals_raw:
        if not (_is_int(g) and 0 <= g < n_states):
            raise InputError("goals 中的状态 %r 越界（应为 0..%d）" % (g, n_states - 1))
        goals.add(g)

    return {"n_bits": n_bits, "n_actions": n_actions, "n_states": n_states,
            "goals": goals, "trans": trans, "path": path}


# ---------------------------------------------------------------- 群装载
def close_group(elements, n_states):
    """
    自动取闭包（closure_perms import 自 src/experiments_p3.py）。
    elements：去重后的置换元组列表。返回 (闭包元素升序列表, info dict)。
    贪心找生成元：当前闭包装不下的元素就升级为生成元，生成元个数 ≤ log2|G| 量级。
    """
    ident = tuple(range(n_states))
    gens = []
    cur = {ident}
    for t in elements:
        if t not in cur:
            gens.append(list(t))
            cur = {tuple(g) for g in closure_perms(gens, n_states)}
    closed = (cur == set(elements))
    info = {"n_unique_input": len(elements), "closed_input": closed,
            "n_generators": len(gens), "generators": gens}
    if not closed:
        info["n_added_by_closure"] = len(cur) - len(elements)
    return sorted(cur), info


# ---------------------------------------------------------------- 逐元素动作映射
# 2026-11-04（第 36 波，队长裁定规格）：explicit 口径逐元素化。
# 新增 semantics.action_maps：与群文件 elements 一一对应的逐元素动作映射排列
# （背景：旧单全局 action_map 把恒等元也按同一 ρ 判，恒等元等变强制 ρ=id，
# 任何非平凡动作改名在数学上必被拒——逐元素映射解除这一退化）。
# 铁律：判据数学（dist_of / tvd / 位串 / 泛化 / strict / explicit 判据本体）
# 零改动——本节只做「声明层」结构校验与元素-映射配对。校验失败一律
# InputError（退出码 3，干净报错无 traceback）；legacy action_map 的
# GroupInvalid(1) 既有口径一行不动。
HOMOM_FULL_CAP = 500        # 元素数 ≤ 500：同态律全检全部有序对
HOMOM_SAMPLE_PAIRS = 200    # 元素数 > 500：生成元对全检 + 确定性抽样 200 对
HOMOM_SAMPLE_SEED = 20261104


def _validate_action_maps(elements_raw, closed, info, n_states, g_na, amaps):
    """校验 semantics.action_maps（逐元素动作映射声明）。

    规格：与群文件 elements 列表（原序，含重复时映射须一致）一一对应；每条
    是动作集上的排列且长度一致（群文件声明 n_actions 时须与其相等）；恒等
    元素对应恒等映射；同态律 ρ_(g∘h) = ρ_g∘ρ_h（本仓置换复合约定同
    closure_perms：(g∘h)[s] = g[h[s]]，故定律右端为 ρ_g[ρ_h[a]]）。元素数
    ≤ HOMOM_FULL_CAP 全检全部有序对；> HOMOM_FULL_CAP 生成元有序对全检 +
    确定性抽样 HOMOM_SAMPLE_PAIRS 对（固定种子，可复现）。逐元素映射必须
    覆盖每个群元素，故要求声明元素本身已构成封闭群。

    返回 (maps_sorted, homomorphism_checked)：maps_sorted[i] 与 load_group
    返回的 elements（排序去重闭包）逐位对齐，check 按元素索引取 ρ；
    homomorphism_checked ∈ {"full", "sampled"}，原样进 payload。
    """
    if not isinstance(amaps, list) or not amaps:
        raise InputError("semantics.action_maps 必须是与 elements 一一对应的"
                         "非空列表（逐元素动作映射）")
    if len(amaps) != len(elements_raw):
        raise InputError("semantics.action_maps 长度 %d 与 elements 长度 %d "
                         "不一致（逐元素映射必须一一对应）"
                         % (len(amaps), len(elements_raw)))
    maps = []
    for i, m in enumerate(amaps):
        if not (isinstance(m, list) and m and all(_is_int(x) for x in m)):
            raise InputError("semantics.action_maps[%d] 必须是动作编号列表" % i)
        if sorted(m) != list(range(len(m))):
            raise InputError("semantics.action_maps[%d] 不是动作集上的排列"
                             "（必须是 0..len-1 的双射，实得 %r）" % (i, m))
        maps.append(list(m))
    lens = {len(m) for m in maps}
    if len(lens) != 1:
        raise InputError("semantics.action_maps 各元素映射长度不一致 %r"
                         "（必须同为同一动作集上的排列）" % sorted(lens))
    n_acts = len(maps[0])
    if g_na is not None and n_acts != g_na:
        raise InputError("semantics.action_maps 映射长度 %d 与群文件 "
                         "n_actions=%d 不一致" % (n_acts, g_na))
    by_perm = {}
    for e, m in zip(elements_raw, maps):
        key = tuple(e)
        if key in by_perm and by_perm[key] != m:
            raise InputError("elements 重复元素 %r 对应了不同的 action_maps "
                             "条目（逐元素映射必须一一对应）" % (list(key),))
        by_perm[key] = m
    if not closed:
        raise InputError("semantics.action_maps 要求 elements 本身构成封闭群"
                         "（逐元素映射必须覆盖每个群元素；当前声明缺闭包补入"
                         "的 %d 个元素，其映射无从定义）"
                         % info.get("n_added_by_closure", 0))
    ident = tuple(range(n_states))
    if ident not in by_perm:
        raise InputError("semantics.action_maps：elements 缺恒等元 %r"
                         % (list(ident),))
    if by_perm[ident] != list(range(n_acts)):
        raise InputError("恒等元素必须对应恒等映射（ρ_id = id，实得 %r）"
                         % (by_perm[ident],))

    def law_violated(g, h):
        """ρ_(g∘h) == ρ_g∘ρ_h？（(g∘h)[s]=g[h[s]] ⇒ 右端 ρ_g[ρ_h[a]]）"""
        rho_gh = by_perm.get(tuple(g[x] for x in h))
        if rho_gh is None:
            return True
        rho_g, rho_h = by_perm[g], by_perm[h]
        return any(rho_gh[a] != rho_g[rho_h[a]] for a in range(n_acts))

    perms = sorted(by_perm)          # 与 load_group 返回的 elements 逐位一致
    if len(perms) <= HOMOM_FULL_CAP:
        mode = "full"
        for g in perms:
            for h in perms:
                if law_violated(g, h):
                    raise InputError(
                        "同态律违反：ρ_(g∘h) ≠ ρ_g∘ρ_h（g=%r, h=%r；逐元素"
                        "映射必须构成群同态 G→Sym(actions)）" % (list(g), list(h)))
    else:
        mode = "sampled"
        rng = random.Random(HOMOM_SAMPLE_SEED)
        gens = [tuple(x) for x in info.get("generators", [])]
        pairs = [(g, h) for g in gens for h in gens]
        for _ in range(HOMOM_SAMPLE_PAIRS):
            pairs.append((perms[rng.randrange(len(perms))],
                          perms[rng.randrange(len(perms))]))
        for g, h in pairs:
            if law_violated(g, h):
                raise InputError(
                    "同态律违反（生成元对/确定性抽样对）：ρ_(g∘h) ≠ ρ_g∘ρ_h"
                    "（g=%r, h=%r）" % (list(g), list(h)))
    return [by_perm[t] for t in perms], mode


def load_group(path):
    """装载并校验 group.json。文件缺失/解析失败 → InputError(3)；内容不是置换群 → GroupInvalid(1)。"""
    if not os.path.isfile(path):
        raise InputError("群文件不存在：%s" % path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise InputError("群文件读取/解析失败：%s" % e)
    if not isinstance(raw, dict) or "elements" not in raw:
        raise InputError("群 JSON 顶层必须是对象且含 elements 字段（输入格式见 wuxing_gua/README.md）")
    elements_raw = raw["elements"]
    if not (isinstance(elements_raw, list) and elements_raw):
        raise GroupInvalid("elements 必须是非空列表")

    n_states = raw.get("n_states")
    if n_states is not None and not (_is_int(n_states) and n_states >= 1):
        raise GroupInvalid("n_states 必须是正整数")
    if n_states is None:
        if not isinstance(elements_raw[0], list):
            raise GroupInvalid("elements[0] 必须是置换列表")
        n_states = len(elements_raw[0])

    for i, e in enumerate(elements_raw):
        if not (isinstance(e, list) and len(e) == n_states):
            raise GroupInvalid("elements[%d] 必须是长度 n_states=%d 的置换列表（实际 %r）"
                               % (i, n_states, len(e) if isinstance(e, list) else type(e)))
        seen = set()
        for v in e:
            if not _is_int(v) or not (0 <= v < n_states) or v in seen:
                raise GroupInvalid("elements[%d] 不是 0..%d 上的双射（置换）" % (i, n_states - 1))
            seen.add(v)

    uniq = sorted({tuple(e) for e in elements_raw})
    closed, info = close_group(uniq, n_states)
    info["n_duplicate"] = len(elements_raw) - len(uniq)

    g_goals = raw.get("goals")
    if g_goals is not None:
        if not isinstance(g_goals, list):
            raise GroupInvalid("group.json 的 goals 必须是状态列表")
        for g in g_goals:
            if not (_is_int(g) and 0 <= g < n_states):
                raise GroupInvalid("group.json 的 goals 含越界状态 %r" % (g,))
        g_goals = set(g_goals)
    g_na = raw.get("n_actions")
    if g_na is not None and not (_is_int(g_na) and g_na >= 1):
        raise GroupInvalid("group.json 的 n_actions 必须是正整数")

    # 2026-10-29：可选 semantics 块（动作语义显式声明，判据口径工程的声明层）。
    #   {"action": "relabel"|"fixed"|"explicit", "action_map": [..] 仅 explicit}
    #   relabel  = 动作可随状态换名（开关/里程碑位类系统的正确口径；历史默认）
    #   fixed    = 动作名不可换（事件驱动状态机的正确口径；= 旧 --strict）
    #   explicit = 逐动作映射（action_map 必须是动作集上的双射）
    # 2026-11-04（第 36 波）：explicit 另可给 action_maps——与 elements 一一
    #   对应的逐元素动作映射排列（含同态律校验，见 _validate_action_maps）；
    #   旧单 action_map = 全部元素同一映射（恒等元也被同一 ρ 判定 ⇒ 非平凡
    #   改名必拒的退化口径），行为不变、文档标 deprecated。
    #   块内允许附加 "assumed": true（discover 自动标注其默认口径时盖上——
    #   未被模型作者确认过的声明，check 如实按「假定为真」警示）与任意说明
    #   字段（如 note）；未知键一律忽略，discover stdout 直接落盘仍可用。
    g_sem = raw.get("semantics")
    if g_sem is not None:
        if not isinstance(g_sem, dict):
            raise GroupInvalid("group.json 的 semantics 必须是对象"
                               "（{\"action\": \"relabel\"|\"fixed\"|\"explicit\""
                               "[, \"action_map\": [...]]}，见 wuxing_gua/README.md）")
        g_sem_action = g_sem.get("action")
        if g_sem_action not in ("relabel", "fixed", "explicit"):
            raise GroupInvalid("semantics.action 必须是 \"relabel\" | \"fixed\" | "
                               "\"explicit\" 之一（实得 %r）" % (g_sem_action,))
        g_sem_map = g_sem.get("action_map")
        g_sem_amaps = g_sem.get("action_maps")
        # 2026-11-04（第 36 波）：action_maps 仅 explicit 可带（与 action_map
        # 同一条作用域规则；两字段互斥——legacy 单全局映射已弃用但行为不变）。
        if g_sem_action != "explicit" and g_sem_amaps is not None:
            raise GroupInvalid("仅 semantics.action == \"explicit\" 可给 action_maps"
                               "（relabel/fixed 的动作映射由判据口径决定，不逐元素指定）")
        if g_sem_action == "explicit" and g_sem_amaps is not None \
                and g_sem_map is not None:
            raise InputError("semantics.action_map（legacy 单全局映射，已弃用）与 "
                             "semantics.action_maps（逐元素映射）只能二选一")
        if g_sem_action == "explicit" and g_sem_amaps is not None:
            amaps_aligned, homo_mode = _validate_action_maps(
                elements_raw, info["closed_input"], info, n_states, g_na,
                g_sem_amaps)
            g_sem = {"action": g_sem_action, "action_map": None,
                     "action_maps": amaps_aligned,
                     "homomorphism_checked": homo_mode,
                     "assumed_flag": (g_sem.get("assumed") is True)}
        else:
            if g_sem_action == "explicit":
                if not (isinstance(g_sem_map, list) and g_sem_map
                        and all(_is_int(x) for x in g_sem_map)):
                    raise GroupInvalid("semantics.action == \"explicit\" 时 action_map "
                                       "必须是动作编号列表（0..n_actions-1 的双射）")
                if sorted(g_sem_map) != list(range(len(g_sem_map))):
                    raise GroupInvalid("semantics.action_map 必须是动作集上的双射"
                                       "（实得 %r）" % (g_sem_map,))
            elif g_sem_map is not None:
                raise GroupInvalid("仅 semantics.action == \"explicit\" 可给 action_map"
                                   "（relabel/fixed 的动作映射由判据口径决定，不逐动作指定）")
            g_sem = {"action": g_sem_action, "action_map": g_sem_map,
                     "action_maps": None, "homomorphism_checked": None,
                     "assumed_flag": (g_sem.get("assumed") is True)}

    return {"path": path, "n_states": n_states, "elements": closed,
            "info": info, "goals": g_goals, "n_actions": g_na,
            "semantics": g_sem}


def orbits_of_group(group):
    """群 → 轨道划分（orbits_of import 自 src/experiments_e1.py），排序保证输出确定。"""
    obs = [sorted(ob) for ob in orbits_of(group["elements"], group["n_states"])]
    return sorted(obs, key=lambda o: o[0])


# ---------------------------------------------------------------- check 主判定
def _equiv_error_strict(trans, pi, n):
    """严格等变：**动作名必须原样对应**。

    与 equiv_error / equiv_error_gua 的区别：那两者允许「动作跟着状态一起改名」
    （在 π(s) 的所有动作里找一个能接住后继的）。本函数要求动作 a 在 π(s) 上
    仍然是动作 a——这才对应「事件语义不变」。

    返回 (最大 TV, 检查过的 (s,a) 数)。
    """
    NS = len(pi)
    worst = 0.0
    for s in range(NS):
        ps = pi[s]
        for a in range(n):
            p1 = {pi[u]: v for u, v in dist_of(trans, s, a).items()}
            p2 = dist_of(trans, ps, a)
            worst = max(worst, tvd(p1, p2))
    return worst, NS * n


def _equiv_error_explicit(trans, pi, rho, n):
    """显式映射口径：**动作映射由群文件逐动作声明**（semantics.action_map）。

    与 _equiv_error_strict 的唯一差别：strict 要求 b == a（动作名原样对应），
    本函数取声明给出的 rho[a]。等变不等式与 TV 机制（dist_of / tvd，import 自
    src/experiments_p3.py）逐字同源——判据数学零改动，新增的只是「动作下标
    查声明表」这一层分派。

    返回 (最大 TV, 检查过的 (s,a) 数)。
    """
    NS = len(pi)
    worst = 0.0
    for s in range(NS):
        ps = pi[s]
        for a in range(n):
            p1 = {pi[u]: v for u, v in dist_of(trans, s, a).items()}
            p2 = dist_of(trans, ps, rho[a])
            worst = max(worst, tvd(p1, p2))
    return worst, NS * n


# check 的动作语义四分派（2026-10-29 起；此前只有 strict 布尔一根开关）：
#   bitstring   = 位串判据 equiv_error（动作 a=翻第 a 位，动作名由 π 推导——relabel）
#   generalized = 泛化判据 equiv_error_gua（在 π(s) 的动作里搜——relabel）
#   strict      = _equiv_error_strict（b==a——fixed）
#   explicit    = _equiv_error_explicit（按声明映射——explicit）
_JUDGES = ("bitstring", "generalized", "strict", "explicit")


def resolve_semantics(model, group, strict_flag=False):
    """
    把（群文件声明, --strict 标志）解析成 check 实际使用的动作语义。
    返回 dict：action / judge / action_map / action_maps / homomorphism_checked /
    declared / assumed / source。（action_maps = 第 36 波逐元素口径，与群元素
    一一对应；homomorphism_checked ∈ {"full","sampled",None}。）

    优先级：--strict 覆盖一切（= fixed；显式覆盖不算假定）；
    群文件声明次之；都无 → relabel（历史默认）但 assumed=True——
    准入工具的宽容默认必须显眼，不得静默。
    """
    decl = group.get("semantics")
    n_acts, n_bits = model["n_actions"], model["n_bits"]
    if strict_flag:
        return {"action": "fixed", "judge": "strict", "action_map": None,
                "action_maps": None, "homomorphism_checked": None,
                "declared": decl is not None, "assumed": False,
                "source": "flag_strict",
                "declared_action": (decl or {}).get("action")}
    if decl is None:
        return {"action": "relabel",
                "judge": ("generalized" if n_acts > n_bits else "bitstring"),
                "action_map": None, "action_maps": None,
                "homomorphism_checked": None,
                "declared": False, "assumed": True,
                "source": "default", "declared_action": None}
    action = decl["action"]
    if action == "fixed":
        judge = "strict"
    elif action == "explicit":
        judge = "explicit"
    else:
        judge = ("generalized" if n_acts > n_bits else "bitstring")
    # 2026-11-04（第 36 波）：explicit 两形态——逐元素 action_maps（新）或
    # legacy 单 action_map（行为不变）。映射长度都必须等于模型 n_actions。
    has_amaps = (action == "explicit" and decl.get("action_maps") is not None)
    if action == "explicit":
        if has_amaps:
            if len(decl["action_maps"][0]) != n_acts:
                raise InputError(
                    "semantics.action_maps 映射长度 %d 与模型 n_actions=%d "
                    "不一致（逐元素映射必须作用于模型的动作集）"
                    % (len(decl["action_maps"][0]), n_acts))
        elif len(decl["action_map"]) != n_acts:
            raise InputError("semantics.action_map 长度 %d 与模型 n_actions=%d 不一致"
                             % (len(decl["action_map"]), n_acts))
    return {"action": action, "judge": judge,
            "action_map": (list(decl["action_map"])
                           if action == "explicit" and not has_amaps else None),
            "action_maps": ([list(m) for m in decl["action_maps"]]
                            if has_amaps else None),
            "homomorphism_checked": (decl.get("homomorphism_checked")
                                     if has_amaps else None),
            "declared": True,
            "assumed": bool(decl.get("assumed_flag")),
            "source": "group_file", "declared_action": action}


def _check_transition(model, elements, close_info, sem=None, strict=False):
    """
    转移等变层（零容忍）：每个群元素 π 的等变误差（max TV）必须 ≤ TV_TOL。
    |G| ≤ ELEM_VERIFY_CAP 时逐元素全查；否则按 discover 的哨兵口径
    （贪心生成元 + 头/中/尾样本）抽查。

    sem（2026-10-29 口径声明分派）：resolve_semantics 的解析结果，judge ∈
    bitstring / generalized / strict / explicit，explicit 附 action_map。
    sem=None 时退回旧布尔口径（strict=True → strict 判据；否则 relabel 家族
    按 n_actions 与 n_bits 关系分派）——旧行为逐位保留。
    """
    trans, n_acts, NS = model["trans"], model["n_actions"], model["n_states"]
    if sem is not None:
        judge_kind = sem["judge"]
        action_map = sem["action_map"]
    else:
        judge_kind = "strict" if strict else (
            "generalized" if n_acts > model["n_bits"] else "bitstring")
        action_map = None
    # 2026-11-04（第 36 波）：explicit 逐元素口径——action_maps 与群元素
    # 一一对应，按元素索引取该元素的 ρ。判据本体 _equiv_error_explicit
    # 一行未动（等变不等式与 TV 机制不变）；变的只是「每个元素喂哪个映射」
    # 这一声明层分派。legacy 单映射（action_map）仍对全部元素同一 ρ。
    rho_by_elem = None
    if sem is not None and judge_kind == "explicit" \
            and sem.get("action_maps") is not None:
        if len(sem["action_maps"]) != len(elements):
            raise InputError("semantics.action_maps 长度 %d 与群元素数 %d "
                             "不一致" % (len(sem["action_maps"]), len(elements)))
        rho_by_elem = {tuple(e): sem["action_maps"][i]
                       for i, e in enumerate(elements)}
    if len(elements) <= ELEM_VERIFY_CAP:
        targets, mode = elements, "all_elements"
    else:
        mid = len(elements) // 2
        sentinel = list(elements[:64]) + list(elements[mid:mid + 64]) + list(elements[-32:])
        seen, targets = set(), []
        for g in [tuple(x) for x in close_info["generators"]] + [tuple(x) for x in sentinel]:
            if g not in seen:
                seen.add(g)
                targets.append(g)
        mode = "generators+sentinel"

    worst, has_inf, n_failed, first_bad = 0.0, False, 0, None
    for idx, pi in enumerate(targets):
        try:
            if judge_kind == "strict":
                e, _ = _equiv_error_strict(trans, list(pi), n_acts)
            elif judge_kind == "explicit":
                if rho_by_elem is not None:
                    rho = rho_by_elem.get(tuple(pi))
                    if rho is None:
                        raise InputError("群元素 %r 缺逐元素映射"
                                         "（semantics.action_maps 未覆盖）"
                                         % (list(pi),))
                else:
                    rho = action_map
                e, _ = _equiv_error_explicit(trans, list(pi), rho, n_acts)
            elif judge_kind == "generalized":
                e, _ = equiv_error_gua(trans, list(pi), n_acts)
            else:
                e, _ = equiv_error(trans, list(pi), n_acts)
        except IndexError:
            # 元素把动作 a 的位翻转映射到了动作集之外（位号 ≥ n_actions）：
            # 它不可能与该 MDP 的动作结构相容，按不等变处理
            e = float("inf")
        if e > TV_TOL:
            n_failed += 1
            if e == float("inf"):
                has_inf = True
            if first_bad is None:
                is_inf = (e == float("inf"))
                first_bad = {
                    "index_in_checked": idx,
                    "tv": None if is_inf else min(e, 1.0),
                    "reason": ("元素不是位置置换：π(s^(1<<a)) ^ π(s) 不是单个位翻转，"
                               "与「动作 a = 翻转第 a 位」的口径不相容" if is_inf
                               else "转移分布在 π 映射下的 TV 超过容忍（判据 max TV=0 零容忍）"),
                }
            worst = max(worst, 1.0 if e == float("inf") else e)
    return {"passed": n_failed == 0, "tol": TV_TOL, "mode": mode,
            "judge": judge_kind,
            "n_checked": len(targets), "n_failed": n_failed,
            "worst_tv": worst, "worst_tv_is_inf": has_inf, "first_bad": first_bad}


def run_check(model, group, strict=False):
    """
    完整转移表版判定（两层，均零容忍，都跑、都报告）：
      层 T 转移等变：equiv_error（src/experiments_p3.py）max TV ≤ 1e-9
      层 R 奖励剖面：cheap_check（src/experiments_p4.py 完整转移表版）n_bad == 0
    返回 stdout JSON payload；verdict ∈ {"pass", "reject"}。

    动作语义（2026-10-29）：由群文件可选 semantics 块声明（relabel / fixed /
    explicit），--strict 覆盖为 fixed；未声明时按 relabel 判读并在 payload 里
    如实标注 semantics_assumed=true（宽容默认必须显眼）。判据数学零改动：
    relabel 分派与历史行为逐位一致（开关类结论不翻案）。
    """
    if group["n_states"] != model["n_states"]:
        raise InputError("群 n_states=%d 与模型 2**n_bits=%d 不一致"
                         % (group["n_states"], model["n_states"]))
    NS = model["n_states"]
    elements = group["elements"]
    orbits = orbits_of_group(group)
    n_orbits = len(orbits)

    sem = resolve_semantics(model, group, strict_flag=strict)
    layer_t = _check_transition(model, elements, group["info"], sem=sem)
    r_ok, r_diag = cheap_check(model["trans"], model["goals"], orbits, model["n_actions"])
    layer_r = {"passed": bool(r_ok), "n_pair": r_diag["n_pair"],
               "n_bad": r_diag["n_bad"], "sec": r_diag["sec"]}

    passed = layer_t["passed"] and layer_r["passed"]
    verdict = "pass" if passed else "reject"
    if passed:
        reason = ("两层判据均通过：转移等变（max TV=%.2e ≤ tol=%g）+ 奖励剖面（n_bad=0）"
                  % (layer_t["worst_tv"], TV_TOL))
    else:
        parts = []
        if not layer_t["passed"]:
            parts.append("转移等变层失败：max TV=%s > tol=%g（%d/%d 个受检元素不过）"
                         % ("inf（含非位置置换元素）" if layer_t["worst_tv_is_inf"]
                            else "%.4g" % layer_t["worst_tv"],
                            TV_TOL, layer_t["n_failed"], layer_t["n_checked"]))
        if not layer_r["passed"]:
            parts.append("奖励剖面层失败：同轨道剖面不同 %d/%d 对（判据 n_bad=0 零容忍）"
                         % (layer_r["n_bad"], layer_r["n_pair"]))
        reason = "；".join(parts)

    info = group["info"]
    note = None
    if passed and len(elements) <= 1:
        note = ("平凡群（阶 1）：判据上合法（恒放行），但压缩比 1.00×，没有抽象价值；"
                "如需找非平凡群请用 discover 子命令")
    semantics_block = {"action": sem["action"], "judge": sem["judge"],
                       "declared": sem["declared"], "assumed": sem["assumed"],
                       "source": sem["source"]}
    if sem["declared"] and sem.get("declared_action") is not None \
            and sem["declared_action"] != sem["action"]:
        semantics_block["declared_action"] = sem["declared_action"]
    if sem["action"] == "explicit":
        # 2026-11-04（第 36 波）：逐元素 action_maps（新口径）回显全表 + 记录
        # 同态律校验策略（full = 全部有序对 / sampled = 生成元对+确定性抽样）；
        # legacy 单映射口径 homomorphism_checked 如实为 null（同态律不单检——
        # 恒等元也被同一 ρ 判定，非平凡改名由判据本身拒绝）。
        if sem.get("action_maps") is not None:
            semantics_block["action_maps"] = [list(m) for m in sem["action_maps"]]
            semantics_block["homomorphism_checked"] = \
                sem.get("homomorphism_checked")
        else:
            semantics_block["action_map"] = list(sem["action_map"])
            semantics_block["homomorphism_checked"] = None
    return {
        "command": "check",
        "verdict": verdict,
        "exit_code": 0 if passed else 1,
        "reason": reason,
        "note": note,
        "semantics": semantics_block,
        "semantics_assumed": sem["assumed"],
        "n_bits": model["n_bits"], "n_states": NS, "n_actions": model["n_actions"],
        "group": {
            "n_states": NS,
            "order": len(elements),
            "n_orbits": n_orbits,
            "compression": (NS / n_orbits) if n_orbits else None,
            "input_elements": info["n_unique_input"] + info.get("n_duplicate", 0),
            "unique_elements": info["n_unique_input"],
            "duplicates_dropped": info.get("n_duplicate", 0),
            "input_was_closed_group": info["closed_input"],
            "elements_added_by_closure": info.get("n_added_by_closure", 0),
            "generators_found": info["n_generators"],
        },
        "layer_transition": layer_t,
        "layer_reward_profile": layer_r,
    }
