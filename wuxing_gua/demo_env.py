# -*- coding: utf-8 -*-
"""
demo_env.py —— 内置演示环境构造器（Q_n 位串口径，n ≤ 6 ⇒ ≤ 64 状态，确定性可重建）

━━ 出处 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  · build_model_n（标准环境 Q_n / 动作=翻转一位 / 目标=全阳 / 失效10%+爻动12%）
      ← import 自 src/experiments_e1.py（未复制改写）
  · swap_gen（坐标对换生成元 → 真群 S_n）
      ← import 自 src/experiments_cheap_sample.py（其场景①构造）
  · xor_group（XOR 平移群 (Z_2)^n）
      ← 构造同 src/cheap_check_sample.py 自检与 src/experiments_cheap_sample.py
        场景③（非法群·XOR 平移）
  · build_popcount（能量环境）★ 新写（本文件）：
      用 build_model_n(n, goals=∅) 的 (p, u) 结构——无吸收态、纯结构随机游走，
      奖励改写为 R_STEP + W_POP·popcount(u)。用途：构造「保转移概率但不保奖励」
      的非法群演示——XOR 平移把全部 2^n 态合成一个轨道，转移结构在平移下严格
      不变（max TV=0，实测），但奖励随 popcount 变化 ⇒ 奖励剖面层必然报警。
      （标准环境做不到这一点：目标态的吸收自环本身就不是 XOR 不变的，
        XOR 群在标准环境连转移层都过不了——实测 max TV=0.894。）
  · build_translated_standard（平移编号环境）★ 新写（本文件）：
      把标准环境的状态号做 XOR 平移 s → s^c（c = TRANSLATE_C），goals 同步平移。
      位串口径保持成立（平移与「翻转第 a 位」可交换）⇒ 仍是合法 model.json；
      与 build_standard 同构（ρ 为双射、结构逐位对应），只是状态编号不同。
      用途：discover 发现结果的**编号伪像**削弱案例——同一抽象环境换个编号，
      plain discover 找到的群显著变小，--canonize 恢复完整（README「--canonize」
      一节、selftest 削弱分支、audit 现算断言共用本构造，数字确定性可复算）。

所有构造都是 n 的确定函数（无随机），采样生成用固定种子（见 write_fixtures）。
"""
import json
import os
import random

from experiments_e1 import build_model_n
from experiments_cheap_sample import swap_gen
from experiments_p3 import closure_perms

from .core_sample import make_sampler, sample_from_model

# 与 src/experiments_e1.py 一致的环境参数（此处仅用于能量环境的奖励式）
R_STEP = -0.02
W_POP = 0.05          # 能量环境：奖励 = R_STEP + W_POP·popcount(u)
MAX_N = 6             # 演示规模上限：2^6 = 64 状态（预注册口径）
TRANSLATE_C = 0b110011  # 平移编号环境的平移量（51；确定值，selftest/audit/README 共用）


def _check_n(n):
    if not (isinstance(n, int) and 1 <= n <= MAX_N):
        raise ValueError("演示环境要求 1 ≤ n ≤ %d（2^%d=%d 状态），收到 %r"
                         % (MAX_N, MAX_N, 1 << MAX_N, n))


# ---------------------------------------------------------------- 环境构造
def build_standard(n=6, goals=None):
    """
    标准演示环境：Q_n，目标 = {2^n - 1}（全阳），奖励 R_GOAL/R_STEP。
    == src/experiments_e1.build_model_n（import 复用）。
    返回 (trans, n, goals)。
    """
    _check_n(n)
    if goals is None:
        goals = {(1 << n) - 1}
    return build_model_n(n, set(goals)), n, set(goals)


def build_popcount(n=6):
    """
    能量演示环境：无吸收态（goals=∅），奖励 = R_STEP + W_POP·popcount(u)。
    (p, u) 结构 == build_model_n(n, ∅)（import 复用）；奖励剖面为本文件新写。
    真群 S_n 仍是完整对称（popcount 是坐标置换不变量）；
    XOR 平移群保转移（TV=0）但不保奖励（剖面不同）⇒ 演示「保转移概率但不保奖励」。
    返回 (trans, n, goals=∅)。
    """
    _check_n(n)
    base = build_model_n(n, set())
    trans = [[[(p, u, R_STEP + W_POP * bin(u).count("1")) for (p, u, _r) in row]
              for row in s_row] for s_row in base]
    return trans, n, set()


def build_translated_standard(n=6, c=None):
    """
    平移编号的标准环境（削弱案例）：ρ(s) = s ^ c 的 XOR 平移重编号。
    new_trans[i][a] = ρ_#(base_trans[ρ⁻¹(i)][a])，goals 同步平移；位串口径保持
    （平移与翻位可交换）⇒ 合法 model.json。与 build_standard 同构、仅编号不同。
    返回 model dict（run_discover 可直接消费的 (p,u,r) 元组口径）。
    """
    _check_n(n)
    if c is None:
        c = TRANSLATE_C
    NS = 1 << n
    if not (0 <= c < NS):
        raise ValueError("平移量 c 必须在 [0, 2^n) 内，收到 %r" % c)
    base_trans, _n, _goals = build_standard(n)
    trans = [[[(p, u ^ c, r) for (p, u, r) in base_trans[i ^ c][a]]
              for a in range(n)] for i in range(NS)]
    return {
        "n_bits": n, "n_actions": n, "n_states": NS,
        "goals": sorted({((1 << n) - 1) ^ c}),
        "trans": trans,
    }


# ---------------------------------------------------------------- 群构造
def true_group(n=6):
    """真群：坐标置换 S_n。生成元 = 相邻位对换（src/experiments_cheap_sample.swap_gen）。"""
    _check_n(n)
    NS = 1 << n
    return closure_perms([swap_gen(NS, i, i + 1) for i in range(n - 1)], NS)


def xor_group(n=6):
    """XOR 平移群 (Z_2)^n：能量环境上的「保转移概率但不保奖励」非法群。"""
    _check_n(n)
    NS = 1 << n
    return closure_perms([[s ^ (1 << j) for s in range(NS)] for j in range(n)], NS)


# ---------------------------------------------------------------- 序列化
def model_payload(trans, n, goals):
    """转成 README 定义的 model.json 结构。"""
    return {
        "n_bits": n,
        "n_actions": n,
        "n_states": 1 << n,
        "goals": sorted(goals),
        "trans": [[[[p, u, r] for (p, u, r) in row] for row in s_row]
                  for s_row in trans],
    }


def _dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    return path


def write_fixtures(out_dir, n=6):
    """
    生成 README 示例与 selftest 共用的夹具文件（确定性：同一 n 每次重建逐字节一致）。
    采样种子公式与 src/experiments_cheap_sample.py 相同：rng = random.Random(seed*7919+B)，
    seed 取 101（其扫描所用三个种子之一）。
    返回 {名字: 绝对路径}。
    """
    _check_n(n)
    os.makedirs(out_dir, exist_ok=True)
    NS = 1 << n
    tag = "q%d" % n
    paths = {}

    tr_std, _, goals_std = build_standard(n)
    paths["model_standard"] = _dump(
        os.path.join(out_dir, "model_%s.json" % tag),
        model_payload(tr_std, n, goals_std))

    tr_pop, _, goals_pop = build_popcount(n)
    paths["model_popcount"] = _dump(
        os.path.join(out_dir, "model_popcount_%s.json" % tag),
        model_payload(tr_pop, n, goals_pop))

    m_tr = build_translated_standard(n)
    paths["model_translated"] = _dump(
        os.path.join(out_dir, "model_translated_%s.json" % tag),
        {"n_bits": m_tr["n_bits"], "n_actions": m_tr["n_actions"],
         "n_states": m_tr["n_states"], "goals": m_tr["goals"],
         "trans": [[[[p, u, r] for (p, u, r) in row] for row in s_row]
                   for s_row in m_tr["trans"]]})

    paths["group_true"] = _dump(
        os.path.join(out_dir, "group_true_s%d.json" % n),
        {"n_states": NS, "elements": [list(g) for g in true_group(n)]})

    paths["group_xor"] = _dump(
        os.path.join(out_dir, "group_xor_z2n.json"),
        {"n_states": NS, "elements": [list(g) for g in xor_group(n)]})

    cum = make_sampler(tr_std, n)
    for b in (100, 10000):
        rng = random.Random(101 * 7919 + b)
        smp = sample_from_model(cum, n, b, rng)
        p = os.path.join(out_dir, "samples_%d.jsonl" % b)
        with open(p, "w", encoding="utf-8") as f:
            for (s, a, u, r) in smp:
                f.write(json.dumps([s, a, u, r]) + "\n")
        paths["samples_%d" % b] = p
    return paths
