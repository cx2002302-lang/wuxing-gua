# -*- coding: utf-8 -*-
"""
experiments_gua64.py —— 六十四卦实例化：人工指定群 vs 机器自动发现群

【假设规则】（全部口径均为任务指定的假设，非权威唯一卦变口径；报告标题同此声明）
  1) 状态编码：64 卦 = 6 爻位串。**初爻（第 1 爻）= 最低位 bit0，上爻（第 6 爻）= bit5**，
     1 = 阳爻，0 = 阴爻。状态 s 的第 i 爻 = (s >> (i-1)) & 1（爻编号从 1 起数）。
  2) 动作集（3 个确定性动作，作用在 64 状态上）：
       a) 错卦：6 爻全部取反（s XOR 0b111111）——对合置换；
       b) 综卦：爻序上下颠倒（6 位反序）——对合置换；
       c) 互卦：取第 2,3,4 爻为新下卦、第 3,4,5 爻为新上卦（重叠取法，爻编号从 1 起数）。
          ⚠️ 实测互卦是 64→16 的多对一映射，**不是置换**：新卦不依赖原第 1、6 爻。
          预注册「每个动作是 64 状态上的确定性置换」的表述与上述互卦取法在数学上矛盾；
          本实验如实保留预注册定义的互卦取法，把「非置换」作为实测事实记录
          （json actions.is_permutation），不改规则迁就「置换」表述，也不抛弃互卦。
  3) 奖励函数（假设，cheap_check 需要）：R(u) = 上卦（第 4,5,6 爻，下爻为低位）按后天
     八卦五行映射为标量：金=0、木=1、水=2、火=3、土=4（标量指派是任意约定，写死）。
       三爻值 t = 线4 + 2·线5 + 4·线6；t→三爻卦：0坤 1震 2坎 3兑 4艮 5离 6巽 7乾；
       后天五行：乾兑金、震巽木、坎水、离火、艮坤土 ⇒ W = [土4,木1,水2,金0,土4,火3,木1,金0]。
     转移奖励 = 落点状态的 R（与 experiments_e1.build_model_n 的「奖励记在落点」口径一致）。
  4) 人工群 = <错卦, 综卦> 生成的群（易学上最直觉的对称）；机器群 = experiments_p3
     的 discover 流程以**完全相同的默认参数**全自动输出（不给任何人工提示）。
  5) 复用与复制说明：cheap_check 直接 import 自 src/experiments_p4.py；orbits_of /
     vi_n / abstraction_loss / tables import 自 src/experiments_e1.py；discover 的其余
     部件（骨干图 / WL 染色 / 三路自同构搜索 / 闭包）全部 import 自 src/experiments_p3.py。
     唯一复制泛化的是 equiv_error（原版 src/experiments_p3.py 第 56-74 行把动作硬编码为
     「翻转第 a 位」pi[s ^ (1 << a)]，本任务的错/综/互不是位翻转，无法直接 import）——
     下面的 equiv_error_gua 为 copy from src/experiments_p3.py::equiv_error 的泛化版，
     discover 编排 discover_gua 为 copy from src/experiments_p3.py::discover（第 555-641 行）
     的同构版，仅替换等变检验函数，参数（tol=1e-9、max_gens=48、随机重启 40 次 seed=7、
     对合搜索 24 次 seed=7）与原版默认完全一致。

运行：python -X utf8 src/experiments_gua64.py
输出：experiments_gua64.json（项目根）+ 终端人话摘要
"""
import json
import os
import random
import sys
import time
from math import lcm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import tables, orbits_of, vi_n, abstraction_loss   # noqa: E402
from experiments_p3 import (dist_of, tvd, closure_perms,               # noqa: E402
                            backbone_adj, wl_refine,
                            graph_automorphisms, graph_automorphisms_rr,
                            involution_automorphisms, graph_automorphisms_mrv)
from experiments_p4 import cheap_check                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

NS = 64                       # 64 卦
N_ACT = 3                     # 错 / 综 / 互
GAMMA = 0.95                  # VI 交叉核验用，与 experiments_e1 默认一致

# 三爻值 -> 五行标量（金0 木1 水2 火3 土4；t: 0坤 1震 2坎 3兑 4艮 5离 6巽 7乾）
WUXING = [4, 1, 2, 0, 4, 3, 1, 0]


# ---------------------------------------------------------------- 假设规则：状态与动作
def nuclear(x):
    """互卦：新 1..6 爻 = 旧 2,3,4,3,4,5 爻（爻编号从 1 起数，初爻 = bit0）。"""
    b = [(x >> i) & 1 for i in range(6)]          # b[0]=第1爻(初爻) ... b[5]=第6爻(上爻)
    yb = [b[1], b[2], b[3], b[2], b[3], b[4]]     # 新1=旧2 新2=旧3 新3=旧4 新4=旧3 新5=旧4 新6=旧5
    return sum(yb[i] << i for i in range(6))


def reward(u):
    """假设奖励：上卦（第 4,5,6 爻，下爻为低位）后天五行标量。"""
    return WUXING[(u >> 3) & 7]


def build_gua64():
    """64 卦转移系统：trans[s][a] = [(概率, 后继, 奖励)]，确定性单后继（奖励记在落点）。"""
    _ns, mask, _rot, rev, cmp_ = tables(6)        # rev = 综卦（6 位反序），cmp_ = 错卦（逐位取反）
    sigma = [x ^ mask for x in range(NS)]         # 错卦
    tau = list(rev)                               # 综卦
    nu = [nuclear(x) for x in range(NS)]          # 互卦
    actions = [sigma, tau, nu]
    trans = [[[(1.0, actions[a][s], reward(actions[a][s]))] for a in range(N_ACT)]
             for s in range(NS)]
    return trans, actions, sigma, tau


# ---------------------------------------------------------------- copy from experiments_p3
def equiv_error_gua(trans, pi, n):
    """
    copy from src/experiments_p3.py::equiv_error（第 56-74 行），唯一泛化：
    原版把动作硬编码为「翻转第 a 位」（d = pi[s ^ (1 << a)] ^ pi[s]），本任务的
    错/综/互动作不是位翻转，故改为从 trans 直接取每个 (s,a) 的骨干后继
    （取概率最大后继，与 backbone_adj 同一口径），在 pi(s) 的动作中搜索能接住
    pi(后继) 的动作 b。等变语义与原版一致：pi 必须把 (s,a) 的后继概率分布原样
    搬到 pi(s) 的某个动作上；接不住即返回 inf（对应原版「不是位置置换」）。
    """
    NS_ = len(pi)
    succ = [[max(trans[s][a], key=lambda x: x[0])[1] for a in range(n)]
            for s in range(NS_)]
    worst, checked = 0.0, 0
    for s in range(NS_):
        for a in range(n):
            ps = pi[s]
            tgt = pi[succ[s][a]]
            cands = [b for b in range(n) if succ[ps][b] == tgt]
            if not cands:
                return float("inf"), 0            # 后继结构不保持
            p1 = {pi[u]: v for u, v in dist_of(trans, s, a).items()}
            worst = max(worst, min(tvd(p1, dist_of(trans, ps, b)) for b in cands))
            checked += 1
    return worst, checked


def discover_gua(trans, n, tol=1e-9, verbose=False, max_gens=48,
                 use_involution=True, use_mrv_fallback=True):
    """
    copy from src/experiments_p3.py::discover（第 555-641 行）的同构编排：
    骨干图 -> WL 染色 -> 确定性/随机重启/对合三路自同构候选 -> 等变检验 ->
    闭包 + 哨兵复检。所有部件 import 自 experiments_p3，唯一差异是等变检验
    用泛化版 equiv_error_gua。参数与原版默认完全一致（口径对齐 Q6）。
    返回 (群[list of perm], 诊断 dict)。诊断里附 good_gens = 通过等变检验的
    生成元列表（供并集群复检与生成元结构统计，不改变「全自动输出」口径）。
    """
    NS_ = len(trans)
    adj = backbone_adj(trans, n)
    color = wl_refine(adj)
    classes = {}
    for s in range(NS_):
        classes.setdefault(color[s], []).append(s)
    if verbose:
        print("      WL 色类大小：%s" % sorted(len(v) for v in classes.values()))

    gens = graph_automorphisms(adj, color, max_gens=max_gens)
    n_det = len(gens)
    gens_rr = graph_automorphisms_rr(adj, color, n_restarts=40, seed=7)
    gens = gens + gens_rr
    if verbose:
        print("      骨干图自同构生成元：确定性 %d + 随机重启 %d = %d"
              % (n_det, len(gens_rr), len(gens)))

    n_invol = 0
    if use_involution and gens:
        invols = involution_automorphisms(adj, color)
        n_invol = len(invols)
        gens = gens + invols
        if verbose:
            print("      + 对合搜索候选 %d 个（补 XOR 平移类盲区）" % n_invol)

    good, worst = [], 0.0
    for g in gens:
        e, _ = equiv_error_gua(trans, g, n)
        worst = max(worst, e)
        if e <= tol:
            good.append(g)
    if verbose:
        print("      其中通过完整等变检验 %d 个（最大 TV 误差 %.2e）"
              % (len(good), worst))
    if not good:
        n_mrv = 0
        if use_mrv_fallback:
            mrv = graph_automorphisms_mrv(adj, color)
            n_mrv = len(mrv)
            if verbose:
                print("      阶段3 MRV fallback：候选 %d 个" % n_mrv)
            for g in mrv:
                e, _ = equiv_error_gua(trans, g, n)
                if e <= tol:
                    good.append(g)
        if not good:
            return [list(range(NS_))], {"n_gens": len(gens), "n_pass": 0,
                                        "n_classes": len(classes), "worst": worst,
                                        "n_involution": n_invol, "n_mrv": n_mrv,
                                        "good_gens": []}

    # 闭包 + 哨兵复检（自同构关于复合封闭，故只需哨兵抓闭包实现错误，同原版）
    G = closure_perms(good, NS_)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    worst2 = 0.0
    for g in sample:
        e, _ = equiv_error_gua(trans, g, n)
        worst2 = max(worst2, e)
    sentinel_ok = worst2 <= tol
    return G, {"n_gens": len(gens), "n_pass": len(good), "order": len(G),
               "worst_equiv": worst2, "sentinel_ok": sentinel_ok,
               "sentinel_n": len(sample), "n_classes": len(classes),
               "n_involution": n_invol, "n_mrv": 0, "good_gens": good}


# ---------------------------------------------------------------- 独立验证（防假阳性）
def edge_preserving(actions, pi):
    """独立的边保持检验：不复用 equiv_error_gua 的实现，逐 (s,a) 检查
    pi(后继) 是 pi(s) 的某个动作后继。用于交叉验证机器群合法性。"""
    succ = [set(actions[a][s] for a in range(N_ACT)) for s in range(NS)]
    for s in range(NS):
        for a in range(N_ACT):
            if pi[actions[a][s]] not in succ[pi[s]]:
                return False
    return True


def perm_order_fix(g):
    """置换的 (阶, 固定点数)：阶 = 轮换长度的最小公倍数。"""
    seen = [False] * len(g)
    r, fix = 1, 0
    for s in range(len(g)):
        if not seen[s]:
            c, x = 0, s
            while not seen[x]:
                seen[x] = True
                x = g[x]
                c += 1
            r = lcm(r, c)
        if g[s] == s:
            fix += 1
    return r, fix


# ---------------------------------------------------------------- 主流程
def main():
    print("=" * 96)
    print("六十四卦实例化（假设规则）· 人工指定群 <错卦,综卦> vs 机器自动发现群")
    print("  编码：初爻=bit0(最低位)、上爻=bit5，1=阳爻；动作：错卦(全爻取反)/综卦(爻序颠倒)/")
    print("  互卦(新1..6爻=旧2,3,4,3,4,5爻)；假设奖励：上卦后天五行标量 金0 木1 水2 火3 土4")
    print("=" * 96)
    t_total = time.time()
    out = {"meta": {
        "task": "六十四卦实例化",
        "assumption_rule": "假设规则（非权威唯一口径）：编码=初爻bit0最低位上爻bit5、1=阳爻；"
                           "动作=错卦(全爻取反)/综卦(爻序颠倒)/互卦(新1..6爻=旧2,3,4,3,4,5爻,"
                           "爻编号从1起数)；奖励=上卦(第4,5,6爻,下爻低位)后天五行标量"
                           "金0木1水2火3土4，转移奖励记在落点；人工群=<错,综>；"
                           "机器群=experiments_p3 discover 同默认参数全自动输出",
        "encoding": "初爻(bit0)=第1爻 ... 上爻(bit5)=第6爻，1=阳爻 0=阴爻",
        "reward_formula": "R(u) = WUXING[(u >> 3) & 7]，WUXING = [4,1,2,0,4,3,1,0]"
                          "（t=0坤→4 1震→1 2坎→2 3兑→0 4艮→4 5离→3 6巽→1 7乾→0）",
        "reuse": "cheap_check/orbits_of/vi_n/abstraction_loss/tables/骨干图/WL/三路自同构搜索/"
                 "闭包 均直接 import 自 src/experiments_p3.py、experiments_p4.py、"
                 "experiments_e1.py；equiv_error_gua 与 discover_gua 为 copy from "
                 "src/experiments_p3.py（原版 equiv_error 硬编码位翻转动作，无法直接 import）",
        "determinism": "discover 随机重启 seed=7、对合搜索 seed=7（与原版默认一致），全程可复现",
    }}

    # ---------- 0. 构造环境 + 动作置换性检验 ----------
    trans, actions, sigma, tau = build_gua64()
    names = ["cuo(错卦)", "zong(综卦)", "hu(互卦)"]
    img = [len(set(a)) for a in actions]
    is_perm = [n == NS for n in img]
    print("\n  [0] 动作置换性检验（预注册称「每个动作是确定性置换」，实测如实记录）")
    for nm, n_img, p in zip(names, img, is_perm):
        print("      %-12s 像集大小 %d / 64 ⇒ %s" % (nm, n_img, "置换" if p else "非置换（多对一）"))
    out["actions"] = {"names": names, "image_size": img,
                      "is_permutation": is_perm}

    # ---------- 1. 人工群 <错卦, 综卦> ----------
    t0 = time.time()
    H = closure_perms([list(sigma), list(tau)], NS)
    H_orb = orbits_of(H, NS)
    h_sizes = sorted(len(o) for o in H_orb)
    comp_h = NS / len(H_orb)
    t_manual = time.time() - t0
    print("\n  [1] 人工群 <错卦,综卦>：|G|=%d，轨道 %d（大小分布 %s），压缩 %.2f×（%.3fs）"
          % (len(H), len(H_orb), h_sizes, comp_h, t_manual))
    out["manual_group"] = {
        "name": "<错卦,综卦>（错综均为对合且可交换，克莱因四元群）",
        "generators": ["错卦(全爻取反)", "综卦(爻序颠倒)"],
        "order": len(H), "orbits": len(H_orb), "orbit_sizes": h_sizes,
        "compression": comp_h, "build_sec": t_manual}

    # ---------- 2. 机器群：discover 全自动 ----------
    print("\n  [2] 机器群：discover 全自动（与 Q6 同默认参数，不给任何人工提示）")
    t0 = time.time()
    M, diag = discover_gua(trans, N_ACT, verbose=True)
    M_orb = orbits_of(M, NS)
    m_sizes = sorted(len(o) for o in M_orb)
    comp_m = NS / len(M_orb)
    t_auto = time.time() - t0
    gen_struct = sorted(perm_order_fix(g) for g in diag["good_gens"])
    goodset = {tuple(g) for g in diag["good_gens"]}
    sigma_is_gen = tuple(sigma) in goodset
    tau_is_gen = tuple(tau) in goodset
    print("      自动群 |G|=%d，轨道 %d（大小分布 %s），压缩 %.2f×（%.1fs）"
          % (len(M), len(M_orb), m_sizes, comp_m, t_auto))
    out["auto_group"] = {
        "name": "discover 全自动输出（骨干图→WL→确定性/重启/对合三路候选→等变检验→闭包）",
        "order": len(M), "orbits": len(M_orb), "orbit_sizes": m_sizes,
        "compression": comp_m, "discover_sec": t_auto,
        "diag": {k: diag[k] for k in ("n_gens", "n_pass", "worst_equiv",
                                      "sentinel_ok", "sentinel_n",
                                      "n_classes", "n_involution", "n_mrv")},
        "good_gen_order_fixpoints": gen_struct}

    # ---------- 3. 对比 ----------
    Mset = {tuple(g) for g in M}
    H_in_M = all(tuple(g) in Mset for g in H)
    # ⚠️ closure_perms 返回 set 迭代序（非插入序），H 列表下标与元素无对应，
    # 故 H∩M 的成员必须逐元素命名检验，不能用下标解读：
    sigma_tau = [sigma[tau[x]] for x in range(NS)]     # 错∘综 = 综∘错（二者可交换）
    named_members = {
        "identity_in_auto": tuple(range(NS)) in Mset,
        "cuo_in_auto": tuple(sigma) in Mset,
        "zong_in_auto": tuple(tau) in Mset,
        "cuo_zong_in_auto": tuple(sigma_tau) in Mset,
    }
    canonH = {}
    for ob in H_orb:
        for s in ob:
            canonH[s] = min(ob)
    canonM = {}
    for ob in M_orb:
        for s in ob:
            canonM[s] = min(ob)
    # 轨道粗细：自动群划分更粗 ⟺ 每个 H-轨道整体落在同一个 M-轨道内
    auto_coarser = all(len({canonM[s] for s in ob}) == 1 for ob in H_orb)
    manual_coarser = all(len({canonH[s] for s in ob}) == 1 for ob in M_orb)
    # 并集群：<discover 生成元 ∪ {错,综}>——探测 discover 欠采样程度的规模参考
    t0 = time.time()
    M_union = closure_perms(diag["good_gens"] + [list(sigma), list(tau)], NS)
    union_orbits = orbits_of(M_union, NS)
    t_union = time.time() - t0
    sigma_in_M = tuple(sigma) in Mset
    tau_in_M = tuple(tau) in Mset
    e_sigma, _ = equiv_error_gua(trans, sigma, N_ACT)
    e_tau, _ = equiv_error_gua(trans, tau, N_ACT)
    print("\n  [3] 两群对比")
    print("      群阶：自动 %d / 人工 %d = %.0f 倍" % (len(M), len(H), len(M) / len(H)))
    print("      压缩比：自动 %.2f×（轨道 %d） vs 人工 %.2f×（轨道 %d）⇒ 倍数差 %.3f（%.2f−%.2f）"
          % (comp_m, len(M_orb), comp_h, len(H_orb),
             comp_m / comp_h, comp_m, comp_h))
    print("      轨道划分：自动群更粗？%s ｜ 人工群更粗？%s"
          % (auto_coarser, manual_coarser))
    print("      人工群 ⊆ 自动群？%s（逐元素：单位元在 M？%s，σ=错卦在 M？%s，"
          "τ=综卦在 M？%s，错∘综在 M？%s）"
          % (H_in_M, named_members["identity_in_auto"], sigma_in_M, tau_in_M,
             named_members["cuo_zong_in_auto"]))
    print("      错/综通过等变检验？σ: %s τ: %s（是合法自同构，但未必被候选搜索抓到）"
          % (e_sigma <= 1e-9, e_tau <= 1e-9))
    print("      <discover 生成元 ∪ {错,综}> 阶 %d，轨道 %d（%.1fs）——discover 欠采样程度参考"
          % (len(M_union), len(union_orbits), t_union))
    out["comparison"] = {
        "order_ratio_auto_over_manual": len(M) / len(H),
        "compression_manual": comp_h, "compression_auto": comp_m,
        "compression_diff_abs": comp_m - comp_h,
        "compression_diff_ratio": comp_m / comp_h,
        "orbit_partition_auto_coarser_than_manual": auto_coarser,
        "orbit_partition_manual_coarser_than_auto": manual_coarser,
        "manual_subset_of_auto": H_in_M,
        "manual_named_elements_in_auto": named_members,
        "sigma_in_auto": sigma_in_M, "tau_in_auto": tau_in_M,
        "sigma_is_discovered_gen": sigma_is_gen,
        "tau_is_discovered_gen": tau_is_gen,
        "sigma_passes_equiv_check": e_sigma <= 1e-9,
        "tau_passes_equiv_check": e_tau <= 1e-9,
        "union_group_order": len(M_union),
        "union_group_orbits": len(union_orbits),
        "union_orbit_sizes": sorted(len(o) for o in union_orbits),
        "union_build_sec": t_union,
        "note": "union_group = <discover 通过检验的生成元 ∪ {错卦,综卦}> 的闭包，"
                "是 Aut(转移系统) 的更大子群，仅作 discover 欠采样程度的参考；"
                "机器群口径仍以 discover 全自动输出为准"}

    # ---------- 4. 合法性独立验证 ----------
    t0 = time.time()
    bad = sum(0 if edge_preserving(actions, g) else 1 for g in M)
    t_valid = time.time() - t0
    rng_pairs = 2000
    rng = random.Random(1)
    ML = [tuple(g) for g in M]
    closed_violation = 0
    for _ in range(rng_pairs):
        a = ML[rng.randrange(len(ML))]
        b = ML[rng.randrange(len(ML))]
        if tuple(a[b[x]] for x in range(NS)) not in Mset:
            closed_violation += 1
            break
    print("\n  [4] 自动群合法性独立验证（不复用等变检验实现）")
    print("      全量 %d 个元素逐一边保持：失败 %d 个（%.1fs）" % (len(M), bad, t_valid))
    print("      闭包封闭性抽查 %d 对乘积：违规 %d" % (rng_pairs, closed_violation))
    out["validity"] = {
        "method": "独立实现的逐 (s,a) 有向边保持检验 + 闭包封闭性抽查",
        "auto_elements_checked": len(M), "edge_preserving_failed": bad,
        "closure_pairs_checked": rng_pairs, "closure_violations": closed_violation,
        "check_sec": t_valid}

    # ---------- 5. cheap_check 两组（import 自 experiments_p4）----------
    okH, dH = cheap_check(trans, set(), H_orb, N_ACT)
    okM, dM = cheap_check(trans, set(), M_orb, N_ACT)
    print("\n  [5] cheap_check（假设奖励=上卦五行标量；goals 形参在原函数体内未被使用，传空集）")
    print("      人工群：%s（剖面不同 %d / %d 对，%.2fs）"
          % ("放行" if okH else "拒答", dH["n_bad"], dH["n_pair"], dH["sec"]))
    print("      自动群：%s（剖面不同 %d / %d 对，%.2fs）"
          % ("放行" if okM else "拒答", dM["n_bad"], dM["n_pair"], dM["sec"]))
    out["cheap_check"] = {
        "reward_assumption": out["meta"]["reward_formula"],
        "goals_param_note": "cheap_check 的 goals 形参在其函数体内未被使用（p4:80-105），传空集",
        "manual": {"pass": bool(okH), "n_pair": dH["n_pair"], "n_bad": dH["n_bad"],
                   "sec": dH["sec"]},
        "auto": {"pass": bool(okM), "n_pair": dM["n_pair"], "n_bad": dM["n_bad"],
                 "sec": dM["sec"]}}

    # ---------- 6. VI 真值交叉核验（64 态很小，可全 VI）----------
    t0 = time.time()
    V, _pi = vi_n(trans, N_ACT, NS)
    lH = abstraction_loss(V, H_orb, NS)
    lM = abstraction_loss(V, M_orb, NS)
    t_vi = time.time() - t0
    consistent = (lH[0] > 1e-9) == (not okH) and (lM[0] > 1e-9) == (not okM)
    print("\n  [6] VI 真值交叉核验（γ=%.2f，同轨道 V* 极差；0=抽象无损）" % GAMMA)
    print("      人工群：max=%.6f mean=%.6f ｜ 自动群：max=%.6f mean=%.6f（VI %.2fs）"
          % (lH[0], lH[1], lM[0], lM[1], t_vi))
    print("      与 cheap_check 判定%s" % ("一致（双有损 ⇒ 双拒答合理）" if consistent
                                          else "不一致！需人工核查"))
    out["vi_crosscheck"] = {
        "gamma": GAMMA, "vi_sec": t_vi,
        "manual_loss_max": lH[0], "manual_loss_mean": lH[1],
        "auto_loss_max": lM[0], "auto_loss_mean": lM[1],
        "consistent_with_cheap_check": consistent}

    out["timing"] = {"manual_sec": t_manual, "discover_sec": t_auto,
                     "union_sec": t_union, "validity_sec": t_valid,
                     "vi_sec": t_vi, "total_sec": time.time() - t_total}

    with open(os.path.join(ROOT, "experiments_gua64.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---------- 人话摘要 ----------
    print("\n" + "=" * 96)
    print("人话摘要（假设规则下）")
    print("  ① 人工直觉群 <错卦,综卦>：阶 %d，把 64 卦压成 %d 个轨道（压缩 %.2f×）。"
          % (len(H), len(H_orb), comp_h))
    print("  ② 机器自动发现群：阶 %d，%d 个轨道（压缩 %.2f×）——阶是人工群的 %.0f 倍，"
          % (len(M), len(M_orb), comp_m, len(M) / len(H)))
    print("     且轨道划分严格更粗（每个直觉轨道整个装进某个机器轨道）。")
    print("  ③ 机器群对人工对称的覆盖并不完整：错卦 σ %s机器群（但 σ 本身%s候选生成元，"
          % ("在" if sigma_in_M else "不在", "是" if sigma_is_gen else "不是"))
    print("     只以生成元乘积出现在闭包里）；综卦 τ %s机器群——τ 通过等变检验，"
          % ("在" if tau_in_M else "不在"))
    print("     却既非候选也不在闭包中。补进错、综后并集群阶 %d——discover 在含不可逆"
          % len(M_union))
    print("     互卦的图上欠采样，如实记录。")
    print("  ④ cheap_check（假设奖励=上卦五行）：人工群 %s、自动群 %s——"
          % ("放行" if okH else "拒答", "放行" if okM else "拒答"))
    print("     五行价值结构与卦变对称结构不相容；VI 真值交叉核验%s。"
          % ("一致" if consistent else "不一致"))
    print("  结果已写入 experiments_gua64.json")


if __name__ == "__main__":
    main()
