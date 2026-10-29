# -*- coding: utf-8 -*-
"""
experiments_completeness.py —— 群完整性告警器

## 解决什么问题（判别闭环死锁里能先迈的一步）
discover / 校验链路输出一个群 G 之后，「G 没找全」与「G 已找全」在链路里不可区分：
seed 给小了（如 SYS-2 上把完全图对称群 S_n 错喂成环群 D_n）会**静默少算**。
本模块给链路补一个**可解释**的完整性评估：分数 + 是否告警 + 人读理由。

## 判据设计（证书优先，启发式只记录、永不单独告警）
【证书 = 强证据】找到一个置换 π 满足：
    (a) 通过链路自己的等变检验（equiv_fn(pi) ≤ TOL，即 max TV=0 零容忍口径）
        ⇒ π ∈ Aut(trans)；
    (b) π ∉ G。
  则 G ⊊ Aut(trans)，「群没找全」是**被证明的事实**。三个探针产生证书：
  · 动作置换探针：动作 a 的最优后继映射若是双射，把它整体当作候选状态置换检验
    （gua64 活案例即由它一击命中：综卦 τ 通过等变检验却不在 discover 群里）；
  · 重启搜索探针：把链路主搜索路线（确定性回溯 + 随机重启 + 对合搜索，末批并入
    MRV）换**新种子**独立重跑 PROBE_BATCHES 批，逐候选检验；出证书即早停。
  · 仿射探针（仅在探针 1/2 零证书时启用）：
    显式生成仿射型候选 π = T_c∘σ（σ=恒等+全部对换，c=target⊕σ(anchor)，锚=吸收态
    或 WL 色类代表元）。治「逐点回溯/对合搜索对整体位移型候选的结构性盲区」——
    SYS-3 A 的真群 Stab(goal)≅S_n（720 阶）全部是仿射型，旧探针在该环境拿不出任何
    群外元素（漏报盲区已被证明）。候选仍逐个过 equiv_fn 零容忍检验，补的是候选类、
    不是放宽容忍度。裁决与修复对照见 裁决记录（发布方留存）。
【启发式 = 弱证据】wl_gap = 群轨道数 / WL 色类数：G 在某色类内不传递 ⇒ 要么 G
  不全、要么 WL 本来就粗。校准环境 SYS-3 A 实测落差 4.571；修复前按预注册旧预期
  （阶 1 正确）归入「预期不告警」侧——该前提已被 2026-10-24 裁决推翻（Aut 实为 720），
  但「wl_gap 携带不了裁决信息」的结论不变（SYS-3 A 现由仿射探针的**证书**触发，
  仍不由 wl_gap 触发）⇒ 只折算成封顶 SUSPICION_CAP 的疑点分数记录在案。

## 阈值口径（全部事前定死，运行时不可调；取值依据与逐环境结果见
## experiments_completeness.json，回源索引见发行包 docs/evidence.md 锚点 E50）
  在 7 个已知真群校准环境实例（首版预期表：SYS-2 n=4/5/6 喂 D_n seed 为正例；
  SYS-2 n=6 喂 S_n seed、Q6、Q8、SYS-3 A 为反例）上标定；gua64 无完整 ground
  truth，只作
  展示环境，不参与标定。
  ⚠️ 2026-10-24 SYS-3 A 疑点裁决（裁决记录（发布方留存））：「SYS-3 A 无对称、
  阶 1 是正确结论」被定性为记录错（Aut=720），SYS-3 A 改判正例（预期告警）；
  阈值数值本身未动，校准预期表随之更正，修复前后对照见
  experiments_sys3a_recheck.json → blindspot_fix。

## 复用声明（全部 import，未复制未改写）
  discover 主链与全部搜索路线 ← src/experiments_p3.py（backbone_adj / wl_refine /
      graph_automorphisms / graph_automorphisms_rr / involution_automorphisms /
      graph_automorphisms_mrv / equiv_error / closure_perms）
  orbits_of ← src/experiments_e1.py
  SYS-2 环境 + 联合等变检验 ← src/experiments_sys2.py（适配器只做表示转换，
      等变裁决逻辑原样调用 equiv_error_joint）
  gua64 环境 + 泛化等变检验 ← src/experiments_gua64.py（build_gua64 / discover_gua /
      equiv_error_gua）
  本文件新增的只有：两个探针、评分与告警判定、校准编排。

运行：python -X utf8 src/experiments_completeness.py
输出：experiments_completeness.json（项目根）+ 终端人读校准表
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import orbits_of                                    # noqa: E402
from experiments_p3 import (equiv_error, closure_perms, backbone_adj,   # noqa: E402
                            wl_refine, graph_automorphisms,
                            graph_automorphisms_rr, involution_automorphisms,
                            graph_automorphisms_mrv)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ===========================================================================
# 判定常量（事前定死；运行时不可调。取值依据见 experiments_completeness.json
# → meta.constants，回源索引见发行包 docs/evidence.md 锚点 E50）
# ===========================================================================
TOL = 1e-9                  # 等变检验容忍度：与链路 discover 缺省 tol 一致（零容忍口径）
ALERT_CERT_MIN = 1          # 证书数达到此值即告警——证书是被证明的事实，1 个即足够
SCORE_ALERT_LINE = 0.5      # completeness_score 低于此线即告警（只有证书路径能到达）
SUSPICION_CAP = 0.45        # 启发式疑点分数上限：< 1-SCORE_ALERT_LINE ⇒ 结构疑点永不单独触发告警
WL_GAP_SCALE = 10.0         # wl_gap 归一化尺度：约为校准集最大实测值 4.571（SYS-3 A）的 2 倍余量
PROBE_BATCHES = 3           # 重启探针批数；告警器首版校准（2026-10-24，修复前）：4 个反例 3 批内
                            # 穷尽且 0 证书、3 正例第 0 批即出证书（实测）。2026-10-24 裁决后 SYS-3 A
                            # 改判正例，其证书由仿射探针产生——见 裁决记录（发布方留存）
RR_RESTARTS_PER_BATCH = 10  # 每批随机重启数（graph_automorphisms_rr）
INV_RESTARTS_PER_BATCH = 6  # 每批对合搜索重启数（involution_automorphisms）
RR_SEED_BASE = 101          # 探针种子基：与链路缺省 seed=7 错开 ⇒ 相对链路是独立重抽样
PROBE_MAX_GENS = 48         # 确定性路线 max_gens（与 discover 缺省一致）
MRV_MAX_GENS = 4            # MRV 末批参数（与 experiments_p3.graph_automorphisms_mrv 缺省一致）
MRV_BUDGET = 200000
USE_MRV_FINAL_BATCH = True  # 末批并入 MRV：链路主路线成功时未跑过 MRV，探针补上这块盲区
AFFINE_MAX_ANCHORS = 4      # 仿射探针锚点数上限（吸收态或 WL 色类代表元）
AFFINE_MAX_TARGETS = 3      # 仿射探针每锚点目标数上限（同色状态，吸收态优先）
AFFINE_MAX_CANDIDATES = 512 # 仿射探针候选总数上限（截断按 (锚,目标,σ) 字典序，确定性）


# ---------------------------------------------------------------- 等变检验适配
def standard_equiv_fn(trans, n_actions):
    """标准位串口径（model.json：动作 a = 翻转第 a 位）的等变检验包装。
    判据逻辑原样调用 experiments_p3.equiv_error，未改写。"""
    def fn(pi):
        return equiv_error(trans, pi, n_actions)[0]
    return fn


# ---------------------------------------------------------------- 探针
def _action_candidates(trans, n_actions):
    """动作置换探针候选：动作 a 的最优后继映射（双射时才产出）。"""
    NS = len(trans)
    for a in range(n_actions):
        m = [max(trans[s][a], key=lambda x: x[0])[1] for s in range(NS)]
        if len(set(m)) == NS:
            yield a, m


# ---------------------------------------------------------------- 仿射探针（2026-10-24 追加）
def _absorbing_states(trans, n_actions):
    """吸收态：所有动作的转移分布都是「自环点质量」的状态（build_model_n 的目标态口径）。"""
    NS = len(trans)
    out = []
    for s in range(NS):
        ok = True
        for a in range(n_actions):
            d = {}
            for (p, u, _r) in trans[s][a]:
                d[u] = d.get(u, 0.0) + p
            if len(d) != 1 or s not in d or abs(d[s] - 1.0) > 1e-12:
                ok = False
                break
        if ok:
            out.append(s)
    return out


def _bit_perm_maps(n_bits):
    """仿射探针的 σ 候选（状态位串口径）：恒等 + 全部对换 (i,j)。

    ⚠️ 2026-10-27 修复（GameWXXX 案例修复）：形参是
    **状态位串位宽 n_bits**（n_states = 2^n_bits），不是动作数。原实现按
    n_actions 造域（长度 2^n_actions），而调用方按状态数 NS 索引 ⇒ 一旦
    n_states != 2**n_actions 就 IndexError。历史全部校准环境（Q_n：n_actions=n、
    n_states=2^n）因形状巧合 n_bits == n_actions 而躲过该 bug；第一个形状不满足
    的真实系统（512 = 2^9 态 / 7 动作）即触发。
    对换生成全部位置置换 ⇒ 其仿射提升 T_{σ(goal)⊕goal}∘σ 生成整个目标点稳定子（n! 口径）。"""
    NS = 1 << n_bits
    maps = [list(range(NS))]
    for i in range(n_bits):
        for j in range(i + 1, n_bits):
            m = list(range(NS))
            for s in range(NS):
                if (s >> i) & 1 != (s >> j) & 1:
                    m[s] = s ^ ((1 << i) | (1 << j))
            maps.append(m)
    return maps


def _affine_candidates(trans, n_actions, color, max_anchors, max_targets, max_total):
    """仿射探针候选：π = T_c ∘ σ（先位置置换 σ，再整体 XOR 平移 c），c = target ⊕ σ(anchor)。

    ## 为什么需要（2026-10-24，SYS-3 A 漏报盲区的修复；裁决见 裁决记录（发布方留存））
    逐点回溯/随机重启/对合搜索对「整体位移」型候选有**结构性盲区**——`src/_audit_seed.py`
    证实逐点回溯结构上产生不了 XOR 平移类（对合搜索补的也只是对合型）；SYS-3 A 上主三路
    候选为 0、MRV 候选全被链路收进群，重启换种子也拿不出群外元素。而该环境真群
    Stab(goal) ≅ S_n（n! 阶）**全部**是 T_c∘σ 型。修法与 2026-10-16 对合搜索同思路：
    显式补候选类，等变裁决一步不松（每个候选仍要过 equiv_fn 零容忍检验）。

    锚点选取（只利用链路自己看得见的结构，不引入外部信息）：
      · 有吸收态（如目标态）⇒ 以吸收态为锚（SYS-3 A / Q_n / SYS-2 的全 1 态）；
      · 无吸收态 ⇒ 退化为 WL 色类代表元（每类一个，封顶 max_anchors）。
    目标：与锚同色的状态（吸收态优先，封顶 max_targets），c 使 π(anchor) = target。
    候选恒等式与重复候选跳过；总数封顶 max_total（按 (锚,目标,σ) 顺序截断，确定性）。

    ## 适用域（2026-10-27 修复后明确）
    σ 定义在**状态位串**上 ⇒ 位宽由状态数决定（n_bits = log2(n_states)，位串口径
    强制 n_states = 2^n_bits），与 n_actions 无关。n_states 不是 2 的幂时位串结构
    无定义 ⇒ 如实返回空候选（kind="non_power_of_two_states"），不臆造候选。"""
    NS = len(trans)
    n_bits = NS.bit_length() - 1
    if (1 << n_bits) != NS:
        # 状态数非 2 的幂：无位串结构 ⇒ 仿射候选无定义，跳过本探针（不崩溃、不臆造）
        return [], "non_power_of_two_states"
    absorbing = _absorbing_states(trans, n_actions)
    abs_set = set(absorbing)
    if absorbing:
        kind = "absorbing"
        anchors = absorbing[:max_anchors]
    else:
        kind = "wl_class_rep"
        reps = {}
        for s in sorted(range(NS), key=lambda x: (color[x], x)):
            reps.setdefault(color[s], s)
        anchors = [reps[c] for c in sorted(reps)][:max_anchors]
    sigmas = _bit_perm_maps(n_bits)
    ident = tuple(range(NS))
    cands = []
    seen = set()
    for anc in anchors:
        same = sorted(t for t in range(NS) if color[t] == color[anc])
        ordered = ([t for t in same if t in abs_set] +
                   [t for t in same if t not in abs_set])
        for tgt in ordered[:max_targets]:
            for sigma in sigmas:
                if len(cands) >= max_total:
                    return cands, kind
                c = tgt ^ sigma[anc]
                pi = [sigma[s] ^ c for s in range(NS)]
                key = tuple(pi)
                if key == ident or key in seen:
                    continue
                seen.add(key)
                cands.append((anc, tgt, pi))
    return cands, kind


def assess_completeness(trans, n_actions, group, equiv_fn, group_gens=None,
                        label=None):
    """
    群完整性评估。参数：
      trans       [s][a] -> [(p,u,r)]（model.json 口径；SYS-2 等其他表示由调用方转换）
      n_actions   动作数（backbone_adj 需要）
      group       链路输出的群（状态置换列表）
      equiv_fn    状态置换 -> max TV 误差（必须用链路自己的等变检验口径）
      group_gens  群的生成元（可选；提供且找到证书时才计算并集闭包阶）
    返回 dict（见模块 docstring）。
    """
    t0 = time.time()
    NS = len(trans)
    gset = {tuple(g) for g in group}
    n_orbits = len(orbits_of(group, NS))
    color = wl_refine(backbone_adj(trans, n_actions))
    n_classes = len(set(color.values()))
    wl_gap = n_orbits / n_classes if n_classes else float("inf")

    # ---- 探针 1：动作置换 ----
    act_cands = 0
    act_certs = []
    for a, m in _action_candidates(trans, n_actions):
        act_cands += 1
        if equiv_fn(m) <= TOL and tuple(m) not in gset:
            act_certs.append(("action", a))

    # ---- 探针 2：重启搜索（换新种子独立重跑链路主路线；出证书即早停）----
    adj = backbone_adj(trans, n_actions)
    per_batch = []
    rst_certs = []          # [(batch, perm)]，perm 留存供并集闭包使用
    n_cand = n_pass = 0
    for b in range(PROBE_BATCHES):
        gens = []
        if b == 0:
            gens += graph_automorphisms(adj, color, max_gens=PROBE_MAX_GENS)
        gens += graph_automorphisms_rr(adj, color, n_restarts=RR_RESTARTS_PER_BATCH,
                                       seed=RR_SEED_BASE + b)
        gens += involution_automorphisms(adj, color, n_restarts=INV_RESTARTS_PER_BATCH,
                                         seed=RR_SEED_BASE + b)
        if b == PROBE_BATCHES - 1 and USE_MRV_FINAL_BATCH and not rst_certs:
            gens += graph_automorphisms_mrv(adj, color, max_gens=MRV_MAX_GENS,
                                            budget=MRV_BUDGET)
        new_certs = 0
        for g in gens:
            n_cand += 1
            if equiv_fn(g) <= TOL:
                n_pass += 1
                if tuple(g) not in gset:
                    new_certs += 1
                    rst_certs.append((b, list(g)))
        per_batch.append({"batch": b, "n_candidates": len(gens),
                          "n_certificates": new_certs})
        if new_certs > 0:
            break

    # ---- 探针 3：仿射探针（仅在前两探针 0 证书时启用；2026-10-24 SYS-3 A 裁决后追加）----
    # 语义与探针 1/2 相同：候选过等变零容忍检验且不在群内 ⇒ 证书。前两探针已出证书时
    # 跳过（告警已成立，且保持旧校准记录的探针统计逐字节可比）。
    aff_kind = None
    aff_cands = aff_pass = 0
    aff_certs = []                      # [(anchor, target, perm)]
    if len(act_certs) + len(rst_certs) == 0:
        aff_list, aff_kind = _affine_candidates(trans, n_actions, color,
                                                AFFINE_MAX_ANCHORS, AFFINE_MAX_TARGETS,
                                                AFFINE_MAX_CANDIDATES)
        for anc, tgt, pi in aff_list:
            aff_cands += 1
            if equiv_fn(pi) <= TOL:
                aff_pass += 1
                if tuple(pi) not in gset:
                    aff_certs.append((anc, tgt, pi))

    certs = (act_certs + [("restart", b) for b, _p in rst_certs] +
             [("affine", anc) for anc, _tgt, _pi in aff_certs])
    n_cert = len(certs)

    # ---- 并集闭包（仅当调用方提供生成元）----
    order_after = None
    union_note = None
    if n_cert > 0 and group_gens is not None:
        extra = [list(g) for _b, g in rst_certs]
        extra += [[max(trans[s][a], key=lambda x: x[0])[1] for s in range(NS)]
                  for _src, a in act_certs]
        extra += [list(pi) for _anc, _tgt, pi in aff_certs]
        G2 = closure_perms(list(group_gens) + extra, NS)
        order_after = len(G2)
        union_note = "把证书并入生成元集取闭包：群阶 %d → %d" % (len(group), order_after)

    # ---- 评分与告警判定（常量见文件头，事前定死）----
    if n_cert >= ALERT_CERT_MIN:
        score = 0.0
        verdict = "proved_incomplete"
    else:
        suspicion = SUSPICION_CAP * min(1.0, max(0.0, (wl_gap - 1.0)
                                                 / (WL_GAP_SCALE - 1.0)))
        score = round(1.0 - suspicion, 6)
        verdict = "probe_exhausted_no_certificate"
    alert = (n_cert >= ALERT_CERT_MIN) or (score < SCORE_ALERT_LINE)

    # ---- 人读理由 ----
    reasons = []
    for src, val in act_certs:
        reasons.append("动作置换探针：动作 %d 的最优后继映射整体作为状态置换通过等变检验"
                       "（max TV≤%.0e），却不在已得群中 ⇒ 已证群不完整" % (val, TOL))
    if rst_certs:
        b0 = rst_certs[0][0]
        reasons.append("重启搜索探针：第 %d 批（种子基 %d）找到 %d 个通过等变检验却不在"
                       "群内的置换 ⇒ 已证群不完整" % (b0, RR_SEED_BASE, len(rst_certs)))
    if aff_certs:
        anc0 = aff_certs[0][0]
        reasons.append("仿射探针：%d 个仿射候选 T_c∘σ（锚=%s态 %d）中 %d 个通过等变检验"
                       "却不在群内 ⇒ 已证群不完整（该类「整体位移」型候选是逐点回溯/对合"
                       "搜索结构性产不出的，补类依据见 裁决记录（发布方留存））"
                       % (aff_cands, "吸收" if aff_kind == "absorbing" else "色类代表",
                          anc0, len(aff_certs)))
    if order_after is not None:
        reasons.append(union_note)
    if n_cert == 0:
        reasons.append("重启搜索探针 %d 批（候选 %d 个，其中 %d 个通过等变检验）+ "
                       "动作置换探针（候选 %d 个）+ 仿射探针（候选 %d 个）均未发现群外"
                       "真对称。注意：探针穷尽 ≠ 完整性的证明"
                       % (len(per_batch), n_cand, n_pass, act_cands, aff_cands))
    if wl_gap > 1.0 + 1e-9:
        reasons.append("WL 色类 %d 类 vs 群轨道 %d 个（落差 %.3f）：群在若干色类内不传递；"
                       "该结构疑点只记录、不参与告警判定" % (n_classes, n_orbits, wl_gap))

    return {
        "label": label,
        "n_states": NS, "n_actions": n_actions,
        "order": len(group), "n_orbits": n_orbits,
        "n_wl_classes": n_classes, "wl_gap": round(wl_gap, 6),
        "action_probe": {"n_candidates": act_cands, "n_certificates": len(act_certs),
                         "actions_certified": [a for _, a in act_certs]},
        "restart_probe": {"batches_run": len(per_batch), "n_candidates": n_cand,
                          "n_pass_equiv": n_pass, "n_certificates": len(rst_certs),
                          "per_batch": per_batch},
        "affine_probe": {"anchor_kind": aff_kind, "n_candidates": aff_cands,
                         "n_pass_equiv": aff_pass, "n_certificates": len(aff_certs)},
        "n_certificates": n_cert,
        "order_after_union": order_after,
        "completeness_score": score,
        "alert": alert,
        "verdict": verdict,
        "reasons": reasons,
        "assess_sec": round(time.time() - t0, 3),
    }


# ===========================================================================
# 校准编排（6 个已知真群的校准环境 + gua64 展示环境）
# 全部环境 import 既有脚本构造；群由链路原样产出（seed 链 / discover）。
# ===========================================================================
def _sys2_setup(n):
    """SYS-2 场景（import experiments_sys2）：返回 (trans3, equiv_fn, states, idx, trans)。"""
    from experiments_sys2 import (sym_mdp, equiv_error_joint, state_perm_from_sigma)
    states, idx, trans, NS, na = sym_mdp(n)
    trans3 = [[[(p, u, 0.0) for u, p in trans[(s, a)].items()] for a in range(na)]
              for s in range(NS)]

    def equiv_fn(pi):
        # 适配：把候选状态置换还原成位置置换 sigma，再走 SYS-2 的联合等变检验（原判据）
        sigma = [None] * n
        for j in range(n):
            t = pi[1 << (n - 1 - j)]
            if t == 0 or t & (t - 1):
                return float("inf")
            sigma[j] = (n - 1) - (t.bit_length() - 1)
        inv = [0] * n
        for p in range(n):
            inv[sigma[p]] = p
        for s in range(NS):
            t = 0
            for j in range(n):
                if (s >> (n - 1 - inv[j])) & 1:
                    t |= 1 << (n - 1 - j)
            if t != pi[s]:
                return float("inf")
        return equiv_error_joint(trans, sigma, states, idx, n, na)

    def state_seed_gens(pos_gens):
        return [state_perm_from_sigma(states, idx, g) for g in pos_gens]

    return trans3, equiv_fn, state_seed_gens


def _run_seed_chain(n, pos_gens):
    """SYS-2 校验链路（import experiments_sys2.verify_group）：seed 生成元 → 闭包 →
    逐元素联合等变检验。返回状态置换群。"""
    from experiments_sys2 import sym_mdp, verify_group
    states, idx, trans, NS, na = sym_mdp(n)
    _g, _tvd, s_perms, _Gpos = verify_group(states, idx, trans, NS, na, pos_gens, n)
    return s_perms


def _sys3a_premise_check():
    """SYS-3 A 前提核查（import experiments_e1.build_model_n + experiments_p3）。

    预注册把 SYS-3 A 当作「无对称环境（阶 1 是正确结论）」的反例；本核查实证：
    (1) 当前链路（discover）在该环境实得群阶（非 1）；
    (2) 仿射族 {T_c∘σ : σ ∈ S_n, c = σ(goal)^goal}（全部使 goal 不动的位置置换+
        平移）逐个过等变检验的通过数 —— 全过 ⇒ Aut(trans) ≥ n!，即该环境并非无对称，
        预注册前提与当前代码不符（早期回归核查已记录、
        待负责人拍板的前提漂移）。
    """
    from itertools import permutations
    from experiments_e1 import build_model_n
    from experiments_p3 import discover
    n = 6
    NS = 1 << n
    goal = 0b101010
    trans = build_model_n(n, {goal})
    G, diag = discover(trans, n)
    n_pass = 0
    worst = 0.0
    for perm in permutations(range(n)):
        sigma_goal = sum(((goal >> i) & 1) << perm[i] for i in range(n))
        c = sigma_goal ^ goal
        tc = [s ^ c for s in range(NS)]
        pi = [0] * NS
        for s in range(NS):
            t = 0
            for i in range(n):
                if (s >> i) & 1:
                    t |= 1 << perm[i]
            pi[s] = tc[t]
        e, _ = equiv_error(trans, pi, n)
        worst = max(worst, e)
        if e <= TOL:
            n_pass += 1
    # 两个生成元的闭包（位置对换 (0 1) 与 6-循环 (012345) 的仿射提升）
    gens = []
    for perm in ((1, 0, 2, 3, 4, 5), (1, 2, 3, 4, 5, 0)):
        sigma_goal = sum(((goal >> i) & 1) << perm[i] for i in range(n))
        c = sigma_goal ^ goal
        tc = [s ^ c for s in range(NS)]
        g = [0] * NS
        for s in range(NS):
            t = 0
            for i in range(n):
                if (s >> i) & 1:
                    t |= 1 << perm[i]
            g[s] = tc[t]
        gens.append(g)
    C = closure_perms(gens, NS)
    Cset = {tuple(g) for g in C}
    return {
        "goal_state": goal,
        "chain_order_discovered": len(G),
        "chain_orbits_discovered": len(orbits_of(G, NS)),
        "chain_diag_n_gens_main_routes": diag["n_gens"],
        "chain_diag_n_pass": diag["n_pass"],
        "affine_family_total": 720,
        "affine_family_pass": n_pass,
        "affine_family_worst_equiv": worst,
        "affine_closure_order": len(C),
        "affine_closure_orbits": len(orbits_of(C, NS)),
        "discovered_subset_of_affine_closure": all(tuple(g) in Cset for g in G),
    }


def _energy_builder():
    """能量演示环境（import wuxing_gua.demo_env.build_popcount，无吸收态，
    奖励含 popcount 项——discover 的对合路线在此能把群找满到含 XOR 平移）。"""
    proj_root = os.path.dirname(HERE)
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)
    from wuxing_gua.demo_env import build_popcount
    return build_popcount(6)


def _cli_discover_check(model_builder, tag):
    """端到端 CLI 检查：把 model_builder() 给出的环境写成 model.json，走
    `python -X utf8 -m wuxing_gua discover` 子进程，验证 stdout JSON 里
    completeness 字段可用（selftest 同款子进程口径）。"""
    import subprocess
    import tempfile
    trans, n, _goals = model_builder()
    tmp = tempfile.mkdtemp(prefix="w1_cli_check_")
    mp = os.path.join(tmp, "model_%s.json" % tag)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump({"n_bits": n, "n_actions": n, "trans": trans}, f)
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-X", "utf8", "-m", "wuxing_gua",
                        "discover", "--trans", mp],
                       cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    payload = json.loads(p.stdout)
    c = payload["completeness"]
    return {
        "tag": tag,
        "command": "python -X utf8 -m wuxing_gua discover --trans model_%s.json" % tag,
        "exit_code": p.returncode,
        "order": payload["order"], "n_orbits": payload["n_orbits"],
        "n_certificates": c["n_certificates"],
        "completeness_score": c["completeness_score"],
        "alert": c["alert"], "verdict": c["verdict"],
    }


def main():
    print("=" * 96)
    print("群完整性告警器：6 个已知真群校准环境 + gua64 活案例（阈值事前定死）")
    print("  常量：ALERT_CERT_MIN=%d SCORE_ALERT_LINE=%s SUSPICION_CAP=%s "
          "WL_GAP_SCALE=%s PROBE_BATCHES=%d RR_SEED_BASE=%d"
          % (ALERT_CERT_MIN, SCORE_ALERT_LINE, SUSPICION_CAP, WL_GAP_SCALE,
             PROBE_BATCHES, RR_SEED_BASE))
    print("=" * 96)

    out = {"meta": {
        "task": "群完整性告警器",
        "date": "2026-10-24",
        "determinism": "全部随机源种子写死（链路 seed=7，探针种子基 RR_SEED_BASE=%d）；"
                       "重跑逐字节可复现" % RR_SEED_BASE,
        "constants": {
            "TOL": TOL, "ALERT_CERT_MIN": ALERT_CERT_MIN,
            "SCORE_ALERT_LINE": SCORE_ALERT_LINE, "SUSPICION_CAP": SUSPICION_CAP,
            "WL_GAP_SCALE": WL_GAP_SCALE, "PROBE_BATCHES": PROBE_BATCHES,
            "RR_RESTARTS_PER_BATCH": RR_RESTARTS_PER_BATCH,
            "INV_RESTARTS_PER_BATCH": INV_RESTARTS_PER_BATCH,
            "RR_SEED_BASE": RR_SEED_BASE, "PROBE_MAX_GENS": PROBE_MAX_GENS,
            "MRV_MAX_GENS": MRV_MAX_GENS, "MRV_BUDGET": MRV_BUDGET,
            "USE_MRV_FINAL_BATCH": USE_MRV_FINAL_BATCH},
        "calibration_basis": "阈值数值在告警器首版校准（2026-10-24 修复前：3 正例触发 / 4 反例"
                             "不触发）上标定后未动；2026-10-24 SYS-3 A 裁决改判正例后重跑"
                             "（4 正例 / 3 反例，预期表见 裁决记录（发布方留存））；"
                             "gua64 无完整 ground truth，仅作展示，不参与标定",
    }}
    envs = {}

    # ---------- 校准 1-3：SYS-2 n=4/5/6 喂 D_n seed（已知欠完整：seed 群 2n < n!）----------
    # ---------- 校准 4：SYS-2 n=6 喂完整 S_n seed ----------
    from experiments_sys2 import dihedral_generators, symmetric_generators
    for n in (4, 5, 6):
        trans3, equiv_fn, state_seed_gens = _sys2_setup(n)
        t0 = time.time()
        G = _run_seed_chain(n, dihedral_generators(n))
        r = assess_completeness(trans3, n, G, equiv_fn,
                                group_gens=state_seed_gens(dihedral_generators(n)),
                                label="SYS-2 n=%d 喂 D_%d seed（seed 群 %d 阶 vs 真群 S_%d %d 阶）"
                                      % (n, n, 2 * n, n, _fact(n)))
        t_chain = time.time() - t0
        r["chain"] = "seed→closure→逐元素联合等变检验（experiments_sys2.verify_group）"
        r["chain_sec"] = round(t_chain, 3)
        r["expected"] = "alert"
        r["case"] = "positive"
        envs["sys2_n%d_seed_dn" % n] = r
        _print_env("P·SYS-2 n=%d D_n seed" % n, r)
    trans3, equiv_fn, state_seed_gens = _sys2_setup(6)
    G = _run_seed_chain(6, symmetric_generators(6))
    r = assess_completeness(trans3, 6, G, equiv_fn,
                            group_gens=state_seed_gens(symmetric_generators(6)),
                            label="SYS-2 n=6 喂完整 S_6 seed（真群）")
    r["chain"] = "seed→closure→逐元素联合等变检验（experiments_sys2.verify_group）"
    r["expected"] = "no_alert"
    r["case"] = "negative"
    envs["sys2_n6_seed_sn"] = r
    _print_env("校准4·SYS-2 n=6 S_n seed", r)

    # ---------- 校准 5：Q6 / Q8 自动发现（已知完整：auto == 真群 S_n）----------
    from experiments_e1 import build_model_n
    from experiments_p3 import discover
    for n in (6, 8):
        NS = 1 << n
        trans = build_model_n(n, {NS - 1})
        t0 = time.time()
        G, diag = discover(trans, n)
        t_chain = time.time() - t0
        r = assess_completeness(trans, n, G, standard_equiv_fn(trans, n),
                                label="Q%d 自动发现（真群 S_%d，阶 %d）" % (n, n, _fact(n)))
        r["chain"] = "experiments_p3.discover（默认参数，seed=7）"
        r["chain_sec"] = round(t_chain, 3)
        r["expected"] = "no_alert"
        r["case"] = "negative"
        envs["q%d_discover" % n] = r
        _print_env("校准5·Q%d discover" % n, r)

    # ---------- 校准 6：SYS-3 A（裁决改判正例：旧预期「不告警」建立在
    # 「无对称环境、阶 1 是正确结论」的错误记录上——该环境 Aut(trans)=720，机器群 6 阶
    # 确属不完整；裁决证据链见 experiments_sys3a_recheck.json）----
    n = 6
    trans = build_model_n(n, {0b101010})
    G, diag = discover(trans, n)
    r = assess_completeness(trans, n, G, standard_equiv_fn(trans, n),
                            label="SYS-3 A n=6（目标=单状态；裁决后预期：告警——Aut=720 > 机器群 6）")
    r["chain"] = "experiments_p3.discover（默认参数，seed=7）"
    r["expected"] = "alert"
    r["case"] = "positive"
    r["task_book_original_expectation"] = "no_alert"
    r["expectation_source"] = ("预注册原预期 no_alert（「无对称环境、阶 1 是正确结论」）已被 "
                               "2026-10-24 裁决定性「记录错」推翻：Aut(trans)=720 恰好"
                               "（experiments_sys3a_recheck.json → reproduction.n6.aut_lower_bound"
                               "/aut_upper_bound），机器群 6 阶确属不完整 ⇒ 改按裁决后真值预期告警")
    envs["sys3a_n6_discover"] = r
    _print_env("校准6·SYS-3 A n=6", r)

    # ---------- 活案例：gua64 discover 欠采样（无完整 ground truth，仅展示）----------
    from experiments_gua64 import build_gua64, discover_gua, equiv_error_gua
    trans, _actions, _sigma, _tau = build_gua64()
    t0 = time.time()
    M, diag = discover_gua(trans, 3)
    t_chain = time.time() - t0
    r = assess_completeness(trans, 3, M,
                            lambda pi: equiv_error_gua(trans, pi, 3)[0],
                            group_gens=diag["good_gens"],
                            label="gua64 discover（欠采样已知，无完整 ground truth）")
    r["chain"] = "experiments_gua64.discover_gua（与 Q6 同默认参数）"
    r["chain_sec"] = round(t_chain, 3)
    r["expected"] = None
    r["case"] = "live_showcase"
    envs["gua64_discover"] = r
    _print_env("LIVE·gua64 discover", r)

    # ---------- SYS-3 A 前提核查 + CLI 端到端检查 ----------
    print("\n[SYS-3 A 前提核查] ……")
    out["sys3a_premise_check"] = pc = _sys3a_premise_check()
    print("  当前链路实得群阶=%d（预注册前提：阶 1 是正确结论——与当前代码不符）"
          % pc["chain_order_discovered"])
    print("  仿射族 T_c∘σ（σ ∈ S_6，共 %d 个）等变检验通过 %d 个（worst TV=%.1e）"
          " ⇒ Aut(trans) ≥ %d：该环境并非无对称"
          % (pc["affine_family_total"], pc["affine_family_pass"],
             pc["affine_family_worst_equiv"], pc["affine_family_pass"]))
    print("  样本生成元闭包阶=%d、轨道 %d；discover 群 ⊆ 该闭包=%s"
          % (pc["affine_closure_order"], pc["affine_closure_orbits"],
             pc["discovered_subset_of_affine_closure"]))

    print("\n[CLI 端到端检查] ……")
    from experiments_e1 import build_model_n as _bmn
    out["cli_check"] = [
        _cli_discover_check(lambda: (_bmn(6, {63}), 6, {63}), "q6_std"),
        _cli_discover_check(lambda: _energy_builder(), "popcount_q6"),
    ]
    for cc in out["cli_check"]:
        print("  %s → exit=%d，order=%d，completeness：证书 %d 个、score=%s、alert=%s"
              % (cc["command"], cc["exit_code"], cc["order"], cc["n_certificates"],
                 cc["completeness_score"], cc["alert"]))

    # ---------- 校准汇总：逐环境误报 / 漏报 ----------
    cal = {}
    n_match = 0
    for k, r in envs.items():
        if r.get("expected") is None:
            r["match"] = None
            continue
        actual = "alert" if r["alert"] else "no_alert"
        r["actual"] = actual
        r["match"] = (actual == r["expected"])
        n_match += int(r["match"])
    n_pos = sum(1 for r in envs.values() if r["case"] == "positive")
    n_neg = sum(1 for r in envs.values() if r["case"] == "negative")
    fp = sum(1 for r in envs.values() if r["case"] == "negative" and r["alert"])
    fn = sum(1 for r in envs.values() if r["case"] == "positive" and not r["alert"])
    cal = {"n_calibration_environments": n_pos + n_neg,
           "n_positive": n_pos, "n_negative": n_neg,
           "n_expected_match": n_match,
           "false_positives_on_negatives": fp,
           "false_negatives_on_positives": fn,
           "note": "误报=反例告警；漏报=正例不告警（按 2026-10-24 裁决后预期表逐环境计数）。"
                   "gua64 无 ground truth，不计入。SYS-3 A 原为预注册反例 3（预期不告警），"
                   "裁决定性「记录错」（该环境 Aut=720、机器群 6 阶不完整）后改判正例，由"
                   "仿射探针出证书触发；修复前校准快照完整保留在 experiments_sys3a_recheck.json "
                   "→ blindspot_fix.before_fix_completeness_snapshot（对照用，判定不得退步核查亦在该文件）"}
    out["environments"] = envs
    out["calibration_summary"] = cal

    with open(os.path.join(ROOT, "experiments_completeness.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("\n" + "=" * 96)
    print("校准汇总：%d/%d 环境符合预注册预期（正例 %d 触发、反例 %d 不触发）｜ "
          "误报 %d、按预期表口径漏报 %d"
          % (n_match, n_pos + n_neg, n_pos - fn, n_neg - fp, fp, fn))
    for k, r in envs.items():
        exp = r.get("expected")
        print("  %-22s 证书=%-3d score=%-7s alert=%-5s 预期=%s 实际=%s %s"
              % (k, r["n_certificates"], r["completeness_score"], r["alert"],
                 exp, r.get("actual", "（展示）"),
                 "✓" if r.get("match") else ("（无 ground truth）" if exp is None else "✗")))
    print("结果已写入 experiments_completeness.json")
    return 0 if (n_match == n_pos + n_neg and fp == 0 and fn == 0) else 1


def _fact(n):
    r = 1
    for k in range(1, n + 1):
        r *= k
    return r


def _print_env(name, r):
    print("\n== %s" % name)
    print("   链路群：阶 %d、轨道 %d ｜ WL 色类 %d ｜ wl_gap=%.3f"
          % (r["order"], r["n_orbits"], r["n_wl_classes"], r["wl_gap"]))
    print("   动作置换探针：候选 %d、证书 %d ｜ 重启探针：%d 批、候选 %d（过等变 %d）、"
          "证书 %d"
          % (r["action_probe"]["n_candidates"], r["action_probe"]["n_certificates"],
             r["restart_probe"]["batches_run"], r["restart_probe"]["n_candidates"],
             r["restart_probe"]["n_pass_equiv"], r["restart_probe"]["n_certificates"]))
    print("   仿射探针：锚=%s｜候选 %d、过等变 %d、证书 %d"
          % (r["affine_probe"]["anchor_kind"] or "（未启用：前两探针已出证书）",
             r["affine_probe"]["n_candidates"], r["affine_probe"]["n_pass_equiv"],
             r["affine_probe"]["n_certificates"]))
    if r["order_after_union"] is not None:
        print("   并集闭包：群阶 %d → %d" % (r["order"], r["order_after_union"]))
    print("   ⇒ 证书 %d 个、score=%s、alert=%s、verdict=%s（评估 %.1fs）"
          % (r["n_certificates"], r["completeness_score"], r["alert"],
             r["verdict"], r["assess_sec"]))
    for msg in r["reasons"]:
        print("     · %s" % msg)


if __name__ == "__main__":
    sys.exit(main())
