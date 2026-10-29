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

from experiments_p3 import equiv_error, closure_perms
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
    if not (_is_int(n_actions) and 1 <= n_actions <= n_bits):
        raise InputError("n_actions 必须是 1..n_bits 的整数（研究口径：动作 a = 翻转第 a 位）")
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

    return {"path": path, "n_states": n_states, "elements": closed,
            "info": info, "goals": g_goals, "n_actions": g_na}


def orbits_of_group(group):
    """群 → 轨道划分（orbits_of import 自 src/experiments_e1.py），排序保证输出确定。"""
    obs = [sorted(ob) for ob in orbits_of(group["elements"], group["n_states"])]
    return sorted(obs, key=lambda o: o[0])


# ---------------------------------------------------------------- check 主判定
def _check_transition(model, elements, close_info):
    """
    转移等变层（零容忍）：每个群元素 π 的 equiv_error（max TV）必须 ≤ TV_TOL。
    |G| ≤ ELEM_VERIFY_CAP 时逐元素全查；否则按 discover 的哨兵口径
    （贪心生成元 + 头 64 / 中 64 / 尾 32 样本）抽查。
    """
    trans, n_acts, NS = model["trans"], model["n_actions"], model["n_states"]
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
            "n_checked": len(targets), "n_failed": n_failed,
            "worst_tv": worst, "worst_tv_is_inf": has_inf, "first_bad": first_bad}


def run_check(model, group):
    """
    完整转移表版判定（两层，均零容忍，都跑、都报告）：
      层 T 转移等变：equiv_error（src/experiments_p3.py）max TV ≤ 1e-9
      层 R 奖励剖面：cheap_check（src/experiments_p4.py 完整转移表版）n_bad == 0
    返回 stdout JSON payload；verdict ∈ {"pass", "reject"}。
    """
    if group["n_states"] != model["n_states"]:
        raise InputError("群 n_states=%d 与模型 2**n_bits=%d 不一致"
                         % (group["n_states"], model["n_states"]))
    NS = model["n_states"]
    elements = group["elements"]
    orbits = orbits_of_group(group)
    n_orbits = len(orbits)

    layer_t = _check_transition(model, elements, group["info"])
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
    return {
        "command": "check",
        "verdict": verdict,
        "exit_code": 0 if passed else 1,
        "reason": reason,
        "note": note,
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
