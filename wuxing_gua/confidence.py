# -*- coding: utf-8 -*-
"""
confidence.py —— 校准判别分的 CLI 侧只读诊断

## 是什么
`discover --report-confidence` 的实现：在证书静默时（completeness 无证书），
给使用者一个可解释、可校准的「这个群找全了吗」判读。研究侧预注册与 9 环境
×13 编号矩阵校准（115 实例）的结论：主判别分 AUC=1.0、两端错误率 0、
结论态=可用（校准记录 experiments_w3_discriminator.json 由发布方留存，
摘要见仓库 docs/evidence.md）。

## 指标（与预注册评估实现同公式同阈值）
证明层：同模型的任何一次重测（plain / canonize / extra 配置臂）输出群阶严格
大于当前输出群阶 ⇒ 当前群 ≠ Aut——「当前漏找」是被证明的事实（discover 各臂
输出都逐元素过 max TV=0 等变检验，都是 Aut 的子群，Aut 唯一）。
统计层（无分歧时）：wl_gap = 当前群轨道数 / WL 色类数，判别分 = min(1, wl_gap−1)；
判读线 0.5（⇔ wl_gap 1.5），满格线 2.0。阈值事前定死（预注册口径）。

## 边界（note 三句必带，预注册 §6）
  1. 统计层阈值是 9×13 矩阵上的经验值，不是数学保证；
  2. 「无漏找证据」≠ 找全的证明；
  3. 一致漏找型（SYS-1 n=6 随机重编号型：全部配置、全部编号一致地漏到同一子群）
     在无分歧时不触发。
"""
from . import core_discover as _cd

SCORE_TAU = 0.5
WL_TAU = 2.0

_NOTE = ("判读为只读诊断，不改变 discover 的退出码。统计层阈值（wl_gap 分界 1.5/"
         "满格 2.0）是 9 环境×13 编号矩阵上的经验标定，不是数学保证；「无漏找证据」"
         "≠ 找全的证明；一致漏找型（如 SYS-1 n=6 随机重编号：全部配置全部编号一致"
         "地漏到同一真子群）在无分歧时不触发。证明层与 completeness 完整性告警器的证书互补："
         "证书找群外元素，本指标找更大的 Aut 子群阶。")

# 统计层判读命中等疑点档时，
# 输出块强制附「分布外环境提示」固定文案（常量进代码，措辞可润色、语义不变）。
# 出处：ticketfsm 试点实锤统计层分布外假阳性（verdict=statistical_suspicion、wl_gap=6.0
# 满格，而独立暴力验证 |Aut|=2、群已完整；pilot/aut_bruteforce.json）——判别分校准域
# 是 9 研究×13 编号矩阵，真实业务 FSM 属分布外。方向安全（宁疑不放过、不改退出码），
# 本提示是产品信任层动作；**不在单点假阳性上改阈值**（单点假阳性即冻结阈值的
# 既定停止条件），重新标定等
# 新环境数据另立预注册。
_OOD_HINT = ("分布外环境提示：统计层阈值（wl_gap 分界 1.5/满格 2.0）在 9 个研究"
             "环境×13 编号矩阵上标定，真实业务 FSM 等分布外环境不保证——请以 "
             "completeness 证书/独立验证为准，不要单凭本统计判读下结论。")


def _arm_orders(trans, n_acts, current_kind):
    """同模型三配置臂的群阶（使用者可见信息；与预注册 §2 同源）。
    current_kind 对应臂不重跑（即本次 discover 本身）；canonize 臂失败（如超大图
    超节点上限）记 None、不崩——证明层降级为可用臂集合，语义不变。"""
    NS = len(trans)
    orders = {}
    if current_kind != "plain":
        try:
            G, _ = _cd._discover(trans, n_acts)
            orders["plain"] = len(G)
        except Exception as e:                    # noqa: BLE001 降级记录，不崩
            orders["plain"] = None
            orders["plain_error"] = repr(e)[:120]
    if current_kind != "canonize":
        try:
            order_c, inv_c, _info = _cd._canonize_model(trans, n_acts)
            G, _diag = _cd._discover_canonized(trans, n_acts, order_c, inv_c)
            orders["canonize"] = len(G)
        except Exception as e:                    # noqa: BLE001
            orders["canonize"] = None
            orders["canonize_error"] = repr(e)[:120]
    if current_kind != "extra":
        try:
            G, _diag, _xinfo = _cd._discover_extra(trans, n_acts)
            orders["extra"] = len(G)
        except Exception as e:                    # noqa: BLE001
            orders["extra"] = None
            orders["extra_error"] = repr(e)[:120]
    return orders


def assess_confidence(order_current, arm_orders, n_orbits, n_classes):
    """判别分判读（纯函数；输入全部使用者可见，无真群）。
    arm_orders: dict{臂名: 群阶或 None}（不含当前臂）。"""
    peers = [order_current] + [o for o in arm_orders.values() if o]
    peers_max = max(peers)
    proof_miss = peers_max > order_current
    wl_gap = (n_orbits / n_classes) if (n_orbits and n_classes) else None
    if proof_miss:
        w3d, verdict = 1.0, "proved_incomplete"
        basis = ("proof:同模型重测（配置/编号臂）最大阶 %d > 当前阶 %d ⇒ 当前群 "
                 "⊊ Aut 被证明（各臂输出均为 Aut 子群、Aut 唯一）"
                 % (peers_max, order_current))
    elif wl_gap is None:
        w3d, verdict = 0.0, "no_evidence_of_missing"
        basis = "wl_gap 原料缺失（轨道数或 WL 色类数不可用）：原料缺失不是无罪证明"
    else:
        w3d = min(1.0, wl_gap - 1.0)
        if wl_gap >= WL_TAU:
            verdict = "statistical_suspicion"
            basis = ("wl_gap=%.6f ≥ 2.0（群轨道数超 WL 色类 2 倍：群连 WL 可分辨的"
                     "结构都拼不起传递）⇒ 统计性漏找疑点" % wl_gap)
        elif w3d >= SCORE_TAU:
            verdict = "statistical_suspicion"
            basis = ("wl_gap=%.6f 落灰带 [1.5, 2.0)：弱统计疑点（9×13 矩阵内无实例"
                     "落在该带，阈值为经验外推）" % wl_gap)
        else:
            verdict = "no_evidence_of_missing"
            basis = ("全部可用重测同阶且 wl_gap=%.6f < 1.5：未发现漏找证据"
                     "（矩阵残余集 69/69 达真侧全落此档；仍不是找全的证明）" % wl_gap)
    result = {
        "order_current": order_current,
        "arm_orders": arm_orders,
        "peers_max": peers_max,
        "proof_miss": proof_miss,
        "wl_gap": (round(wl_gap, 6) if wl_gap is not None else None),
        "w3d_score": round(w3d, 6),
        "verdict": verdict,
        "basis": basis,
        "thresholds": {"w3d_tau": SCORE_TAU, "wl_tau_full": WL_TAU,
                       "source": "预注册口径（阈值事前定死）"},
        "note": _NOTE,
    }
    # 统计层疑点档强制附分布外提示（阈值语义
    # 零改动——只加提示，不动 SCORE_TAU/WL_TAU，不改退出码；证明层/无证据档不附，
    # 因为这两档不依赖统计阈值）。
    if verdict == "statistical_suspicion":
        result["ood_hint"] = _OOD_HINT
    return result


def build_confidence_block(model, payload, current_kind):
    """discover payload 的 confidence 块（--report-confidence 开启时附加）。
    current_kind ∈ {"plain","canonize","extra","multi","combined"}——前两类三
    （单臂输出路径）当前臂即本次 discover、不重跑、阶直接抄 payload["order"]；
    multi/combined（并集型输出）三臂全跑：并集阶 ≥ 各单臂，证明层对其静默属
    预期（并集的漏找由 completeness 证书与 wl_gap 统计层负责），basis/note 如实说明。"""
    trans, n_acts = model["trans"], model["n_actions"]
    arms = _arm_orders(trans, n_acts, current_kind)
    # 当前臂（本次 discover 本身）也进报告：值 = payload["order"]（不重跑）
    if current_kind in ("plain", "canonize", "extra"):
        arms[current_kind] = payload["order"]
    # WL 色类数（同环境编号无关的共轭不变量；与 discover 内部同一 wl_refine）
    color = _cd.wl_refine(_cd.backbone_adj(trans, n_acts))
    n_classes = len(set(color.values()))
    block = assess_confidence(payload["order"], arms, payload["n_orbits"], n_classes)
    block["current_kind"] = current_kind
    if current_kind in ("multi", "combined"):
        block["basis"] += ("；当前输出为并集型（阶 ≥ 各单臂），证明层对并集静默属"
                           "预期——并集自身的漏找请看 completeness 证书与 wl_gap")
    block["wl_classes"] = n_classes
    return block
