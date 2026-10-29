# -*- coding: utf-8 -*-
"""
selftest.py —— 端到端自检（canonize / multi-label / extra-candidates / preset robust /
report-confidence 分支全覆盖）

十二个分支，全部通过 CLI 子进程真实执行（python -X utf8 -m wuxing_gua ...），
不是函数级调用——退出码就是交付的退出码：

  1 discover 真群发现        → 退出码 0；order==720 且 n_orbits==7
                               （= experiments_p3.json → recovery[n=6].auto_order /
                                 auto_orbits），sentinel_ok 为真；
                               completeness 不告警且证书 0（= experiments_completeness.json
                                 → environments.q6_discover，完整性告警器）
  2 check 真群放行           → 退出码 0（验收①第一支）
  3 check 发现群复核         → 退出码 0（discover → check 全链路）
  4 check-sample 达门槛放行  → 退出码 0；B=10000
                               （= experiments_cheap_sample.json →
                                 threshold.overall_min_budget；验收②采样侧）
  5 check 非法群拒答         → 退出码 1（验收①第二支）：能量环境 + XOR 平移群
                               ——保转移概率（layer_transition.passed == true）
                                 不保奖励（layer_reward_profile.passed == false）
  6 check 能量环境真群仍放行 → 退出码 0（能量环境的真群 S_n 两层都过）
  7 check-sample 样本不足    → 退出码 2（验收①第三支）；B=100，只说样本不足
  8 discover --canonize 标准环境 → 退出码 0；order==720 且 n_orbits==7，
                               与分支 1（同一环境不带标志）**双向一致**——
                               群阶/轨道数一致性硬断言放在本分支（Q₆ 标准口径）；
                               canonize.enabled 为真、consistency 全 true、
                               sentinel_ok 为真
  9 discover --canonize 削弱环境（一命令双期望）：
                               平移编号 Q₆（demo_env.build_translated_standard，
                               XOR 平移 s→s^51，与标准环境同构、仅编号不同）——
                               --canonize 一条命令：canonize 侧期望完整
                              （order==720 / n_orbits==7，sentinel_ok 为真，
                               退出码 0——绝不在这类环境报错）；plain 侧期望
                               欠完整（consistency.order_plain==6 /
                               n_orbits_plain==32——同构环境换个编号，plain
                               discover 找到的群显著变小 = 编号伪像），
                               consistency.order_match / n_orbits_match 如实
                               为 False（不硬 assert 一致、不改变退出码）。
  10 discover --multi-label 削弱环境：平移编号 Q₆ 上
                               --multi-label 2（默认种子 20261025）：两臂各找到
                               阶 6（n_pass=4、MRV fallback 同签名），并集去重
                               8 生成元闭包成阶 120 / 12 轨道——**显著大于
                               plain 的 6/32**（并集策略不依赖编号假设的修复
                               实证；同一命令在标准环境上 union@2=120 < plain
                               720，幸运编号上的回落由 consistency 如实报告、
                               不改变退出码）。退出码 0、sentinel_ok 为真、
                               multi_label.enabled/k/seed 与逐臂记录为实测定值
                               （期望值源 = 本分支同构造同种子的确定性重跑）。
  11 discover --extra-candidates 动作置换候选源（生成器盲区修复）：
                               标准 Q₆ 环境（目标态自环使动作映射非双射）：
                               零候选（保守性闸门），群阶 720/7 轨道与分支 1
                               **完全一致**（不引入伪自同构、零候选不误报；
                               活火案例——能量环境 6 候选 6 过、群 46080 零增量，
                               与 gua64 修复 294,912→589,824——因 plain discover
                               本身耗时超出 selftest 预算，记录于
                               experiments_gua64_gapfix.json 与 README，不在
                               本分支跑）。退出码 0、sentinel_ok 为真、
                               completeness 不告警且证书 0、
                               extra_candidates.enabled/n_candidates=0/n_pass=0
                               与 consistency 全 true 为实测定值（期望值源 =
                               本分支同构造的确定性重跑）。
  12 discover --preset robust 一键推荐配置：16 状态能量
                               环境 Q₄（demo_env.build_popcount(4)，无吸收态 ⇒
                               4 个动作的 δ_a 全为双射 = 双射动作环境，gua64 类）
                               上单命令达真群（soft 口径）**384**（= 2⁴·4!；n=6
                               同构造实测 46080 = 2⁶·6! 的降维同构型，全部臂一致
                               384 + completeness 零证书），退出码 0。验证组合
                               payload 契约：config.preset=robust / 三标志全开 /
                               k=8（默认，--multi-label 可覆盖）/ seed=20261025；
                               arms = plain 对照 + canonical + 8 随机编号臂（各
                               384，extra 4 候选 4 过）；并集闭包 + consistency
                               与 plain 全一致。期望值 = 本分支同构造确定性重跑的
                               实测定值。预算纪律：gua64 全量 preset 单命令为分钟
                               量级（以 experiments_fullflags.json → environments.
                               gua64 各 sec 字段为准）、32 状态同构 mini 实测
                               数十秒量级——为守 selftest 120s 总上限，本分支用
                               16 状态档（实测秒级），大环境数字见 README
                               「--preset robust」一节（引 experiments_fullflags.json）。
  13 discover --report-confidence（校准判别分）：两条子命令双期望——
                               ①标准 Q₆（三臂 plain/canonize/extra 全 720 同阶，
                               wl_gap=7/7=1）⇒ verdict=no_evidence_of_missing、
                               proof_miss=False、w3d_score=0；②平移 Q₆
                               （demo_env.build_translated_standard，CLI 行为源
                               experiments_discover_labeling.json → bridge_cli.
                               q6_translated_cli：plain 6 / canonize 720）⇒
                               proof_miss=True、peers_max=720、verdict=
                               proved_incomplete。两例退出码均 0（confidence 是
                               只读诊断，绝不改变退出码语义）；note 必含
                               「不是数学保证」「≠ 找全的证明」「一致漏找」三句
                               （预注册口径；矩阵校准
                               experiments_w3_discriminator.json：AUC=1.0、
                               两端错误率 0）。预注册 §6 原文写「Q6 随机编号
                               seed1」，落地换平移 Q₆（等价实例：plain 6 vs
                               canonize 720 同源数字、demo_env 现成确定性构造，
                               免将包自检耦合实验脚本内部编号生成器——形态等效
                               替换，判读/阈值不动，已在判别分校准记录
                               如实注明）。

夹具与 README 示例完全同一套（demo_env.write_fixtures，确定性重建；
model_translated_q6.json 由 build_translated_standard 确定性构造）。
自检自身退出码：全过 = 0；任何分支不合预期 / 超时 / 超总时长上限 = 3（内部错误）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from . import PROJECT_ROOT, demo_env

N_BRANCHES = 13             # 分支数与下方 step 调用数一致（audit 现读本常量核对 README）
TOTAL_SEC_LIMIT = 180.0     # 13 分支时代（含 --report-confidence 分支）；上限随分支数演进，以实跑汇总为准
PER_BRANCH_TIMEOUT = 100.0


def _run_cli(args):
    exe = [sys.executable, "-X", "utf8", "-m", "wuxing_gua"] + [str(a) for a in args]
    env = dict(os.environ)
    env["PYTHONPATH"] = PROJECT_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(exe, cwd=PROJECT_ROOT, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=PER_BRANCH_TIMEOUT)


# ---------------------------------------------------------------- 分支断言
def _chk_discover(payload):
    errs = []
    if payload.get("order") != 720:
        errs.append("order=%r != 720（期望值源：experiments_p3.json → "
                    "recovery[n=6].auto_order）" % payload.get("order"))
    if payload.get("n_orbits") != 7:
        errs.append("n_orbits=%r != 7（期望值源：experiments_p3.json → "
                    "recovery[n=6].auto_orbits）" % payload.get("n_orbits"))
    if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
        errs.append("diagnostics.sentinel_ok=%r != True" %
                    payload.get("diagnostics", {}).get("sentinel_ok"))
    if payload.get("trivial") is not False:
        errs.append("trivial=%r != False" % payload.get("trivial"))
    # 完整性告警器：Q6 是已知完整环境（auto == 真群 S_6），
    # completeness 必须有字段且不告警（预期值源：experiments_completeness.json →
    # environments.q6_discover）
    c = payload.get("completeness")
    if not isinstance(c, dict):
        errs.append("completeness 字段缺失或不是对象")
    else:
        if c.get("alert") is not False:
            errs.append("completeness.alert=%r != False（Q6 已知完整，不应告警）"
                        % c.get("alert"))
        if c.get("n_certificates") != 0:
            errs.append("completeness.n_certificates=%r != 0（Q6 群外真对称应为 0）"
                        % c.get("n_certificates"))
    return errs


def _chk_verdict_pass(payload):
    return [] if payload.get("verdict") == "pass" else \
        ["verdict=%r != pass（reason=%r）" % (payload.get("verdict"), payload.get("reason"))]


def _chk_illegal(payload):
    errs = []
    if payload.get("verdict") != "reject":
        errs.append("verdict=%r != reject" % payload.get("verdict"))
    lt = payload.get("layer_transition", {})
    lr = payload.get("layer_reward_profile", {})
    if lt.get("passed") is not True:
        errs.append("layer_transition.passed=%r != True（XOR 平移应保转移概率，"
                    "worst_tv=%r）" % (lt.get("passed"), lt.get("worst_tv")))
    if lr.get("passed") is not False:
        errs.append("layer_reward_profile.passed=%r != False（奖励应不被保）" % lr.get("passed"))
    if not lr.get("n_bad", 0) > 0:
        errs.append("layer_reward_profile.n_bad=%r 应 > 0" % lr.get("n_bad"))
    return errs


def _chk_abstain(payload):
    errs = []
    if payload.get("verdict") != "abstain":
        errs.append("verdict=%r != abstain（reason=%r）" % (payload.get("verdict"), payload.get("reason")))
    return errs


def _chk_discover_canonize(p1):
    """分支 8 检查器：--canonize 标准环境。群阶/轨道数一致性的**硬断言**放在这里
    （一般输入不做硬断言、只如实报告 consistency；
    标准环境 Q₆ 双向一致 720/7 是本分支的验收口径）。p1 = 分支 1 不带标志的
    payload，供双向对照；p1 不可用时退回常量 720/7。"""
    def chk(payload):
        errs = []
        if payload.get("order") != 720:
            errs.append("order=%r != 720（--canonize 标准环境；与分支 1 同源期望）"
                        % payload.get("order"))
        if payload.get("n_orbits") != 7:
            errs.append("n_orbits=%r != 7（--canonize 标准环境；与分支 1 同源期望）"
                        % payload.get("n_orbits"))
        if payload.get("trivial") is not False:
            errs.append("trivial=%r != False" % payload.get("trivial"))
        if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
            errs.append("diagnostics.sentinel_ok=%r != True"
                        % payload.get("diagnostics", {}).get("sentinel_ok"))
        c = payload.get("canonize")
        if not isinstance(c, dict):
            errs.append("canonize 字段缺失或不是对象")
        else:
            if c.get("enabled") is not True:
                errs.append("canonize.enabled=%r != True" % c.get("enabled"))
            if not isinstance(c.get("mapping"), dict) or \
                    not isinstance(c["mapping"].get("is_identity"), bool):
                errs.append("canonize.mapping 缺失或无 is_identity 布尔")
            if not isinstance(c.get("canon_sec_magnitude"), str):
                errs.append("canonize.canon_sec_magnitude 缺失（应为期量级桶字符串）")
            cons = c.get("consistency")
            if not isinstance(cons, dict):
                errs.append("canonize.consistency 字段缺失或不是对象")
            else:
                for k in ("order_match", "n_orbits_match",
                          "elements_same_set_as_plain", "orbits_identical_as_sets"):
                    if cons.get(k) is not True:
                        errs.append("canonize.consistency.%s=%r != True（标准环境应双向一致）"
                                    % (k, cons.get(k)))
        if p1 is not None:
            if payload.get("order") != p1.get("order"):
                errs.append("--canonize 与不带标志群阶不一致：%r vs %r（标准环境硬断言）"
                            % (payload.get("order"), p1.get("order")))
            if payload.get("n_orbits") != p1.get("n_orbits"):
                errs.append("--canonize 与不带标志轨道数不一致：%r vs %r（标准环境硬断言）"
                            % (payload.get("n_orbits"), p1.get("n_orbits")))
        return errs
    return chk


def _step_discover_crippled(w, i, total, model_translated_path, rows):
    """分支 9（削弱环境，一命令双期望）：平移编号 Q₆ 上 --canonize 完整而
    plain 欠完整。本分支证明 --canonize 存在的理由——
    同一抽象环境换个编号，plain discover 找到的群显著变小（编号伪像），
    --canonize 恢复完整且退出码仍 0（绝不在这类环境报错）。
    只跑 --canonize 一条命令：run_discover 的 canonize 路径内部会跑 plain
    管线并把两侧群阶/轨道数写进 consistency（order_plain=6 / order_canon=720），
    双期望由同一 payload 覆盖（plain 侧数字与不带标志的 CLI 运行同一管线）。"""
    name = "discover --canonize 削弱环境（平移 Q₆：canon 720/7 完整、plain 6/32 欠完整）"
    t1 = time.time()
    errs = []
    try:
        p = _run_cli(["discover", "--trans", model_translated_path, "--canonize"])
    except subprocess.TimeoutExpired:
        rows.append((name, False, None, time.time() - t1))
        w.write("  [%d/%d] %-46s FAIL（子进程超时）\n" % (i, total, name))
        return
    try:
        payload = json.loads(p.stdout)
    except ValueError:
        payload = None
        errs.append("stdout 不是合法 JSON：%r" % p.stdout[:120])
    if payload is not None:
        if p.returncode != 0:
            errs.append("退出码 %d != 0（削弱环境上 --canonize 恢复完整群，必须放行）；"
                        "stderr 尾部：%s" % (p.returncode, p.stderr.strip()[-300:]))
        if payload.get("order") != 720:
            errs.append("order=%r != 720（canonize 侧期望完整群，期望源："
                        "demo_env.build_translated_standard 确定性构造 + 搜索固定种子，"
                        "可现算复验）" % payload.get("order"))
        if payload.get("n_orbits") != 7:
            errs.append("n_orbits=%r != 7（canonize 侧）" % payload.get("n_orbits"))
        if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
            errs.append("diagnostics.sentinel_ok=%r != True"
                        % payload.get("diagnostics", {}).get("sentinel_ok"))
        c = payload.get("canonize")
        cons = (c or {}).get("consistency") or {}
        if (c or {}).get("enabled") is not True:
            errs.append("canonize.enabled != True")
        if cons.get("order_plain") != 6 or cons.get("n_orbits_plain") != 32:
            errs.append("consistency plain 侧应欠完整（order_plain=6 / n_orbits_plain=32"
                        "——同构标准环境是 720/7），实得 %r/%r"
                        % (cons.get("order_plain"), cons.get("n_orbits_plain")))
        if cons.get("order_canon") != 720 or cons.get("n_orbits_canon") != 7:
            errs.append("consistency canonize 侧应为 720/7，实得 %r/%r"
                        % (cons.get("order_canon"), cons.get("n_orbits_canon")))
        if cons.get("order_match") is not False or cons.get("n_orbits_match") is not False:
            errs.append("consistency 应如实报告不一致（order_match/n_orbits_match=False），"
                        "实得 %r/%r" % (cons.get("order_match"), cons.get("n_orbits_match")))
        if cons.get("elements_same_set_as_plain") is not False:
            errs.append("consistency.elements_same_set_as_plain 应为 False（plain 欠完整），"
                        "实得 %r" % cons.get("elements_same_set_as_plain"))
    ok = not errs
    sec = time.time() - t1
    rows.append((name, ok, p.returncode if p else None, sec))
    w.write("  [%d/%d] %-46s %s（plain 6/32 → --canonize 720/7，%.1fs）\n"
            % (i, total, name, "PASS" if ok else "FAIL", sec))
    for e in errs:
        w.write("         ! %s\n" % e)


def _chk_discover_multilabel(payload):
    """分支 10 检查器：--multi-label 2 削弱环境（平移 Q₆，默认种子 20261025）。
    期望值 = 本分支同构造同种子确定性重跑的实测定值（order 120 / 12 轨道，
    两臂各 6，并集生成元去重 8，plain 侧 6/32）——multi_label.consistency
    只报告不报错（order_match False 如实）。"""
    errs = []
    if payload.get("order") != 120:
        errs.append("order=%r != 120（--multi-label 2 并集群，确定性实测定值）"
                    % payload.get("order"))
    if payload.get("n_orbits") != 12:
        errs.append("n_orbits=%r != 12" % payload.get("n_orbits"))
    if payload.get("trivial") is not False:
        errs.append("trivial=%r != False" % payload.get("trivial"))
    if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
        errs.append("diagnostics.sentinel_ok=%r != True"
                    % payload.get("diagnostics", {}).get("sentinel_ok"))
    m = payload.get("multi_label")
    if not isinstance(m, dict):
        errs.append("multi_label 字段缺失或不是对象")
        return errs
    if m.get("enabled") is not True:
        errs.append("multi_label.enabled=%r != True" % m.get("enabled"))
    if m.get("k") != 2:
        errs.append("multi_label.k=%r != 2" % m.get("k"))
    if m.get("seed") != 20261025:
        errs.append("multi_label.seed=%r != 20261025（默认种子）" % m.get("seed"))
    arms = m.get("arms")
    if not isinstance(arms, list) or len(arms) != 2:
        errs.append("multi_label.arms 应为 2 条逐臂记录，实得 %r" % (arms,))
    else:
        for i, a in enumerate(arms):
            if a.get("order") != 6 or a.get("n_pass") != 4:
                errs.append("multi_label.arms[%d] 应为 order=6 / n_pass=4，实得 %r"
                            % (i, a))
    if m.get("n_union_gens") != 8:
        errs.append("multi_label.n_union_gens=%r != 8（去重后并集生成元）"
                    % m.get("n_union_gens"))
    cons = m.get("consistency")
    if not isinstance(cons, dict):
        errs.append("multi_label.consistency 字段缺失或不是对象")
    else:
        if cons.get("order_plain") != 6 or cons.get("n_orbits_plain") != 32:
            errs.append("consistency plain 侧应欠完整（6/32），实得 %r/%r"
                        % (cons.get("order_plain"), cons.get("n_orbits_plain")))
        if cons.get("order_union") != 120 or cons.get("n_orbits_union") != 12:
            errs.append("consistency union 侧应为 120/12，实得 %r/%r"
                        % (cons.get("order_union"), cons.get("n_orbits_union")))
        if cons.get("order_match") is not False or cons.get("n_orbits_match") is not False:
            errs.append("consistency 应如实报告不一致（False），实得 %r/%r"
                        % (cons.get("order_match"), cons.get("n_orbits_match")))
        if cons.get("elements_same_set_as_plain") is not False:
            errs.append("consistency.elements_same_set_as_plain 应为 False，实得 %r"
                        % cons.get("elements_same_set_as_plain"))
    return errs


def _chk_discover_extra(payload):
    """分支 11 检查器：--extra-candidates 动作置换候选源（标准 Q₆ 环境）。
    标准环境目标态自环使动作映射非双射 ⇒ 零候选（保守性闸门），群与不带标志
    完全一致（720/7）。期望值 = 本分支同构造确定性重跑的实测定值；活火路径
    （候选真产出并全过的案例）在能量环境上实测为 6 候选 6 过、群 46080 零增量，
    因其 plain discover 本身耗时超出 selftest 预算而记于
    experiments_gua64_gapfix.json 与 README（分支 11 只走零候选分支）。"""
    errs = []
    if payload.get("order") != 720:
        errs.append("order=%r != 720（与分支 1 同源期望）" % payload.get("order"))
    if payload.get("n_orbits") != 7:
        errs.append("n_orbits=%r != 7" % payload.get("n_orbits"))
    if payload.get("trivial") is not False:
        errs.append("trivial=%r != False" % payload.get("trivial"))
    if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
        errs.append("diagnostics.sentinel_ok=%r != True"
                    % payload.get("diagnostics", {}).get("sentinel_ok"))
    c = payload.get("completeness")
    if not isinstance(c, dict):
        errs.append("completeness 字段缺失或不是对象")
    else:
        if c.get("alert") is not False:
            errs.append("completeness.alert=%r != False" % c.get("alert"))
        if c.get("n_certificates") != 0:
            errs.append("completeness.n_certificates=%r != 0" % c.get("n_certificates"))
    x = payload.get("extra_candidates")
    if not isinstance(x, dict):
        errs.append("extra_candidates 字段缺失或不是对象")
        return errs
    if x.get("enabled") is not True:
        errs.append("extra_candidates.enabled=%r != True" % x.get("enabled"))
    if x.get("n_candidates") != 0 or x.get("n_pass") != 0:
        errs.append("extra_candidates 应 0 候选（吸收态目标使动作映射非双射，"
                    "保守性闸门），实得 %r/%r"
                    % (x.get("n_candidates"), x.get("n_pass")))
    cons = x.get("consistency")
    if not isinstance(cons, dict):
        errs.append("extra_candidates.consistency 字段缺失或不是对象")
    else:
        if cons.get("order_plain") != 720 or cons.get("order_extra") != 720:
            errs.append("consistency 两侧群阶应均 720，实得 %r/%r"
                        % (cons.get("order_plain"), cons.get("order_extra")))
        for k in ("order_match", "n_orbits_match", "elements_same_set_as_plain",
                  "orbits_identical_as_sets"):
            if cons.get(k) is not True:
                errs.append("extra_candidates.consistency.%s=%r != True（零候选"
                            "应与不带标志完全一致）" % (k, cons.get(k)))
    return errs


def _build_preset_fixture(out_dir):
    """分支 12 夹具：16 状态能量环境 Q₄（双射动作 mini，preset 分支）。
    demo_env.build_popcount(4)：无吸收态 ⇒ 4 个动作的 δ_a 全为双射（双射动作
    环境，gua64 类——extra 候选真产出并全过）；soft 真群 384 = 2⁴·4!（n=6 同
    构造实测 46080 = 2⁶·6!，experiments_gua64_gapfix.json / README「--extra-
    candidates」一节；本构造全部臂一致 384 + completeness 零证书）。确定性
    可重建（build_popcount 为 n 的确定函数）。"""
    trans, n, goals = demo_env.build_popcount(4)
    p = os.path.join(out_dir, "model_popcount_q4.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(demo_env.model_payload(trans, n, goals), f, ensure_ascii=False, indent=1)
    return p


def _chk_discover_preset(payload):
    """分支 12 检查器：--preset robust 单命令达真群（soft 口径）。期望值 = 本分支
    同构造同种子确定性重跑的实测定值（order 384 / 并集生成元 369 / 逐臂全 384 /
    extra 4 候选 4 过 / consistency 与 plain 全一致）。组合 payload 契约逐字段核对：
    config（preset/三标志/k=8/seed）、arms（plain 对照 + canonical + 8 随机臂）、
    并集闭包、哨兵、completeness。"""
    errs = []
    if payload.get("order") != 384:
        errs.append("order=%r != 384（--preset robust 并集群 = soft 真群 2⁴·4!，"
                    "确定性实测定值）" % payload.get("order"))
    if payload.get("n_orbits") != 1:
        errs.append("n_orbits=%r != 1" % payload.get("n_orbits"))
    if payload.get("trivial") is not False:
        errs.append("trivial=%r != False" % payload.get("trivial"))
    if payload.get("diagnostics", {}).get("sentinel_ok") is not True:
        errs.append("diagnostics.sentinel_ok=%r != True"
                    % payload.get("diagnostics", {}).get("sentinel_ok"))
    c = payload.get("completeness")
    if not isinstance(c, dict):
        errs.append("completeness 字段缺失或不是对象")
    else:
        if c.get("alert") is not False:
            errs.append("completeness.alert=%r != False（已达真群，不应告警）"
                        % c.get("alert"))
        if c.get("n_certificates") != 0:
            errs.append("completeness.n_certificates=%r != 0" % c.get("n_certificates"))
    cb = payload.get("combination")
    if not isinstance(cb, dict):
        return errs + ["combination 字段缺失或不是对象"]
    if cb.get("enabled") is not True:
        errs.append("combination.enabled != True")
    cfg = cb.get("config")
    if not isinstance(cfg, dict):
        errs.append("combination.config 缺失")
    else:
        if cfg.get("preset") != "robust":
            errs.append("config.preset=%r != 'robust'" % cfg.get("preset"))
        if cfg.get("canonize") is not True or cfg.get("extra_candidates") is not True:
            errs.append("config 三标志应全开，实得 canonize=%r extra=%r"
                        % (cfg.get("canonize"), cfg.get("extra_candidates")))
        if cfg.get("multi_label") != 8:
            errs.append("config.multi_label=%r != 8（--preset robust 默认 k）"
                        % cfg.get("multi_label"))
        if cfg.get("seed") != 20261025:
            errs.append("config.seed=%r != 20261025（默认种子）" % cfg.get("seed"))
    arms = cb.get("arms")
    if not isinstance(arms, list) or len(arms) != 10:
        errs.append("arms 应为 10 条（plain 对照 + canonical + 8 随机臂），实得 %r 条"
                    % (len(arms) if isinstance(arms, list) else arms,))
    else:
        kinds = [a.get("kind") for a in arms]
        if kinds[0] != "plain(consistency-baseline)" or kinds[1] != "canonical" or \
                kinds[2:] != [("random") for _ in range(8)]:
            errs.append("arms 编排应为 plain 对照 + canonical + 8 random，实得 %r"
                        % kinds)
        for i, a in enumerate(arms):
            if a.get("order") != 384:
                errs.append("arms[%d].order=%r != 384（全部臂一致达真）"
                            % (i, a.get("order")))
            if a.get("sentinel_ok") is not True:
                errs.append("arms[%d].sentinel_ok=%r != True" % (i, a.get("sentinel_ok")))
            n_extra_exp = 0 if i == 0 else 4
            if a.get("n_extra_candidates") != n_extra_exp or a.get("n_extra_pass") != n_extra_exp:
                errs.append("arms[%d] extra 应 %d 候选 %d 过（plain 对照臂 0），实得 "
                            "%r/%r" % (i, n_extra_exp, n_extra_exp,
                                       a.get("n_extra_candidates"), a.get("n_extra_pass")))
        if [a.get("i") for a in arms[2:]] != list(range(8)):
            errs.append("随机臂编号应为 0..7，实得 %r" % [a.get("i") for a in arms[2:]])
    if cb.get("n_union_gens") != 369:
        errs.append("n_union_gens=%r != 369（去重后并集生成元，确定性实测定值）"
                    % cb.get("n_union_gens"))
    ci = cb.get("canonize_info")
    if not isinstance(ci, dict) or not isinstance(ci.get("mapping"), dict):
        errs.append("canonize_info.mapping 缺失")
    if not isinstance(cb.get("sec_magnitudes"), dict):
        errs.append("sec_magnitudes 缺失（应为期量级桶字符串表）")
    cons = cb.get("consistency")
    if not isinstance(cons, dict):
        errs.append("combination.consistency 字段缺失或不是对象")
    else:
        if cons.get("order_plain") != 384 or cons.get("order_union") != 384:
            errs.append("consistency 两侧群阶应均 384，实得 %r/%r"
                        % (cons.get("order_plain"), cons.get("order_union")))
        for k in ("order_match", "n_orbits_match", "elements_same_set_as_plain",
                  "orbits_identical_as_sets"):
            if cons.get(k) is not True:
                errs.append("combination.consistency.%s=%r != True（Q₄ 能量环境"
                            "plain 已达真群，preset 应与之全一致）" % (k, cons.get(k)))
    return errs


def _chk_confidence_no_evidence(payload):
    """分支 13 检查器 ①：标准 Q₆ --report-confidence。三配置臂全 720 同阶、
    wl_gap=7/7=1 ⇒ 无漏找证据（弱证据档；不是找全的证明——note 必含边界三句）。"""
    errs = []
    if payload.get("confidence") is None:
        return ["confidence 块缺失（--report-confidence 未生效）"]
    c = payload["confidence"]
    if c.get("verdict") != "no_evidence_of_missing":
        errs.append("confidence.verdict=%r != no_evidence_of_missing（三臂同阶 720、"
                    "wl_gap=1，应无漏找证据）" % c.get("verdict"))
    if c.get("proof_miss") is not False:
        errs.append("confidence.proof_miss=%r != False（三臂同阶不应有证明）"
                    % c.get("proof_miss"))
    if c.get("w3d_score") != 0.0:
        errs.append("confidence.w3d_score=%r != 0.0" % c.get("w3d_score"))
    if c.get("wl_gap") != 1.0:
        errs.append("confidence.wl_gap=%r != 1.0（720 阶群 7 轨道 / 7 WL 色类）"
                    % c.get("wl_gap"))
    arms = c.get("arm_orders") or {}
    for k in ("plain", "canonize", "extra"):
        if arms.get(k) != 720:
            errs.append("arm_orders.%s=%r != 720（标准 Q₆ 三臂均达真群）"
                        % (k, arms.get(k)))
    note = c.get("note") or ""
    for kw in ("不是数学保证", "≠ 找全的证明", "一致漏找"):
        if kw not in note:
            errs.append("confidence.note 缺边界句：%r" % kw)
    return errs


def _chk_confidence_proved(payload):
    """分支 13 检查器 ②：平移 Q₆ --report-confidence。plain 6 vs canonize 720
    （CLI 行为源 experiments_discover_labeling.json → bridge_cli.q6_translated_cli）
    ⇒ 证明层触发：当前群 ⊊ Aut 被证明；退出码仍 0（只读诊断不改语义）。"""
    errs = []
    if payload.get("confidence") is None:
        return ["confidence 块缺失（--report-confidence 未生效）"]
    c = payload["confidence"]
    if c.get("verdict") != "proved_incomplete":
        errs.append("confidence.verdict=%r != proved_incomplete（canonize 臂 720 > "
                    "plain 6，漏找应被证明）" % c.get("verdict"))
    if c.get("proof_miss") is not True:
        errs.append("confidence.proof_miss=%r != True" % c.get("proof_miss"))
    if c.get("peers_max") != 720 or c.get("order_current") != 6:
        errs.append("peers_max/order_current=%r/%r 应为 720/6"
                    % (c.get("peers_max"), c.get("order_current")))
    if c.get("w3d_score") != 1.0:
        errs.append("confidence.w3d_score=%r != 1.0（证明层满格）" % c.get("w3d_score"))
    arms = c.get("arm_orders") or {}
    if arms.get("canonize") != 720:
        errs.append("arm_orders.canonize=%r != 720" % arms.get("canonize"))
    if arms.get("extra") != 6:
        errs.append("arm_orders.extra=%r != 6（平移 Q₆ 吸收态使动作映射非双射 ⇒ "
                    "extra = plain 同代码路径，期望源 bridge/s9 同构造）"
                    % arms.get("extra"))
    return errs


def _step_confidence(w, i, total, fx, rows):
    """分支 13（校准判别分）：--report-confidence 单分支双子命令——
    ①标准 Q₆（三臂全 720、wl_gap=1）→ no_evidence_of_missing；②平移 Q₆
    （plain 6 vs canonize 720，CLI 行为源 labeling json → bridge_cli）→
    proved_incomplete（证明层）。两例退出码均 0：confidence 是只读诊断，
    不改变 discover 的退出码语义（预注册口径）。"""
    name = "discover --report-confidence（标准=无证据档；平移=证明档）"
    t1 = time.time()
    errs = []
    results = []
    for tag, model_key, checker in (
            ("标准 Q₆", "model_standard", _chk_confidence_no_evidence),
            ("平移 Q₆", "model_translated", _chk_confidence_proved)):
        try:
            p = _run_cli(["discover", "--trans", fx[model_key],
                          "--report-confidence"])
        except subprocess.TimeoutExpired:
            errs.append("%s 子进程超时" % tag)
            continue
        try:
            payload = json.loads(p.stdout)
        except ValueError:
            errs.append("%s stdout 不是合法 JSON：%r" % (tag, p.stdout[:120]))
            continue
        if p.returncode != 0:
            errs.append("%s 退出码 %d != 0（confidence 只读诊断不得改变退出码）"
                        % (tag, p.returncode))
        sub = checker(payload)
        errs.extend("%s：%s" % (tag, e) for e in sub)
        results.append((tag, (payload.get("confidence") or {}).get("verdict")))
    ok = not errs
    sec = time.time() - t1
    rows.append((name, ok, 0, sec))
    w.write("  [%d/%d] %-46s %s（%s，%.1fs）\n"
            % (i, total, name, "PASS" if ok else "FAIL",
               "；".join("%s→%s" % r for r in results) or "无输出", sec))
    for e in errs:
        w.write("         ! %s\n" % e)


def _write_discovered_group_file(tmp, disc_payload):
    p = os.path.join(tmp, "group_discovered.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"n_states": disc_payload["n_states"],
                   "elements": disc_payload["elements"]}, f)
    return p


# ---------------------------------------------------------------- 主流程
def run(out=None):
    w = out or sys.stdout
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="wuxing_gua_selftest_")
    rows = []           # (name, ok, exit, sec)
    hard_fail = []
    try:
        fx = demo_env.write_fixtures(tmp)
        w.write("selftest：夹具目录 %s\n" % tmp)
        w.write("selftest：判据 = 黑盒转移数据上、压缩之前，先判对称群能不能用；"
                "不能用就拒答\n")

        # 分支 1 先跑（discover），其输出供分支 3 复用
        def step(i, total, name, argv, expect_exit, checker):
            t1 = time.time()
            errs = []
            payload = None
            try:
                p = _run_cli(argv)
            except subprocess.TimeoutExpired:
                p = None
                errs.append("子进程超时（>%gs）" % PER_BRANCH_TIMEOUT)
            if p is not None:
                if p.returncode != expect_exit:
                    errs.append("退出码 %d != 预期 %d；stderr 尾部：%s"
                                % (p.returncode, expect_exit, p.stderr.strip()[-300:]))
                try:
                    payload = json.loads(p.stdout)
                except ValueError:
                    errs.append("stdout 不是合法 JSON：%r" % p.stdout[:120])
                if payload is not None and checker:
                    errs.extend(checker(payload))
            ok = not errs
            sec = time.time() - t1
            rows.append((name, ok, None if p is None else p.returncode, sec))
            w.write("  [%d/%d] %-46s %s（exit=%s，%.1fs）\n"
                    % (i, total, name, "PASS" if ok else "FAIL",
                       rows[-1][2], sec))
            for e in errs:
                w.write("         ! %s\n" % e)
            return payload, errs

        fxn = len(fx)
        w.write("selftest：夹具 %d 个（model/group/samples，确定性重建）\n" % fxn)

        total = N_BRANCHES
        p1, e1 = step(1, total, "discover 真群发现（Q6 标准环境）",
                      ["discover", "--trans", fx["model_standard"]], 0, _chk_discover)
        step(2, total, "check 真群放行（S6，退出码 0）",
             ["check", "--trans", fx["model_standard"], "--group", fx["group_true"]],
             0, _chk_verdict_pass)
        if p1 is not None and not e1:
            gp = _write_discovered_group_file(tmp, p1)
            step(3, total, "check 发现群复核（discover→check 全链）",
                 ["check", "--trans", fx["model_standard"], "--group", gp],
                 0, _chk_verdict_pass)
        else:
            rows.append(("check 发现群复核（discover→check 全链）", False, None, 0.0))
            hard_fail.append("分支 1 失败，分支 3 无法执行")
            w.write("  [3/%d] %-46s FAIL（分支 1 失败，无法执行）\n" % (total, "check 发现群复核"))
        step(4, total, "check-sample 达门槛放行（B=10000，退出码 0）",
             ["check-sample", "--samples", fx["samples_10000"], "--group", fx["group_true"],
              "--trans", fx["model_standard"]], 0, _chk_verdict_pass)
        step(5, total, "check 非法群拒答（保转移概率不保奖励，退出码 1）",
             ["check", "--trans", fx["model_popcount"], "--group", fx["group_xor"]],
             1, _chk_illegal)
        step(6, total, "check 能量环境真群仍放行（S6，退出码 0）",
             ["check", "--trans", fx["model_popcount"], "--group", fx["group_true"]],
             0, _chk_verdict_pass)
        step(7, total, "check-sample 样本不足（B=100，退出码 2）",
             ["check-sample", "--samples", fx["samples_100"], "--group", fx["group_true"],
              "--trans", fx["model_standard"]], 2, _chk_abstain)
        # 分支 8：--canonize 标准环境，与分支 1 双向一致（硬断言在此）
        step(8, total, "discover --canonize 标准环境（与分支 1 双向一致）",
             ["discover", "--trans", fx["model_standard"], "--canonize"],
             0, _chk_discover_canonize(p1))
        # 分支 9：削弱环境（平移 Q₆）——plain 欠完整 vs --canonize 完整
        _step_discover_crippled(w, 9, total, fx["model_translated"], rows)
        # 分支 10：--multi-label 2 削弱环境——并集恢复 120 > plain 6
        step(10, total, "discover --multi-label 2 削弱环境（并集 120 > plain 6）",
             ["discover", "--trans", fx["model_translated"], "--multi-label", "2"],
             0, _chk_discover_multilabel)
        # 分支 11：--extra-candidates 动作置换候选源——标准环境吸收态
        # 使动作映射非双射 ⇒ 零候选，群与不带标志完全一致（保守性 + 一致性）
        step(11, total, "discover --extra-candidates（动作置换源，零候选不误报）",
             ["discover", "--trans", fx["model_standard"], "--extra-candidates"],
             0, _chk_discover_extra)
        # 分支 12：--preset robust 一键推荐配置——16 状态能量
        # 环境 Q₄（双射动作 mini）上单命令达真群（soft 口径 384），退出码 0
        m_preset = _build_preset_fixture(tmp)
        step(12, total, "discover --preset robust（三开一键达真群，退出码 0）",
             ["discover", "--trans", m_preset, "--preset", "robust"],
             0, _chk_discover_preset)
        # 分支 13（校准判别分）：--report-confidence 双期望——
        # 标准 Q₆ 无漏找证据 / 平移 Q₆ 证明层触发；两例退出码均 0（只读诊断）
        _step_confidence(w, 13, total, fx, rows)

        total_sec = time.time() - t0
        n_ok = sum(1 for r in rows if r[1])
        all_ok = (n_ok == len(rows)) and not hard_fail and total_sec <= TOTAL_SEC_LIMIT
        w.write("-" * 78 + "\n")
        w.write("selftest 汇总：%d/%d 分支 PASS，总耗时 %.1fs（上限 %.0fs）→ 退出码 %d\n"
                % (n_ok, len(rows), total_sec, TOTAL_SEC_LIMIT,
                   0 if all_ok else 3))
        if not all_ok:
            for m in hard_fail:
                w.write("  ! %s\n" % m)
            if total_sec > TOTAL_SEC_LIMIT:
                w.write("  ! 总耗时超过 %.0fs 上限\n" % TOTAL_SEC_LIMIT)
        return 0 if all_ok else 3
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
