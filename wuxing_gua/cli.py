# -*- coding: utf-8 -*-
"""
cli.py —— wuxing_gua 命令行接口

退出码约定（全命令统一）：
  0 = 放行可用（check/check-sample 判据通过；discover 找到非平凡群）
  1 = 拒答（群不可用/非法；discover 只找到平凡群）
  2 = 样本不足（仅 check-sample：三态中的 abstain，只说样本不足，不下其他结论）
  3 = 输入或内部错误

子命令：
  discover      --trans model.json [--preset robust]               自动找群（JSON →
                 [--canonize] [--multi-label K [--seed S]]          stdout）；
                 [--extra-candidates] [--report-confidence]         三标志可自由组合
                                                                 （组合放开，
                                                                 组合语义 = 实验层
                                                                 C5/C6 同口径）；
                                                                 --preset robust =
                                                                 三标志全开（k=8）；
                                                                 --report-confidence
                                                                 附加校准判别分
                                                                 只读诊断块
  check         --trans model.json --group group.json     完整转移表版两层判定
  check-sample  --samples samples.jsonl --group group.json [--trans model.json]
                                                          采样版三态判定
  selftest                                                端到端自检（15 分支，约 2 分钟）
  demo          --out DIR [--n 6]                         辅助：生成 README 示例夹具

stdout 一律是可解析 JSON（demo/selftest 除外：它们输出人读进度）；
诊断与错误信息走 stderr。
"""
import argparse
import json
import math
import sys

from . import PROJECT_ROOT, __version__
from . import confidence as _confidence
from . import core_check, core_discover, core_sample, demo_env   # noqa: F401
from . import selftest as _selftest
from .errors import GroupInvalid, InputError

EXIT_PASS = 0
EXIT_REJECT = 1
EXIT_ABSTAIN = 2
EXIT_ERROR = 3


class _ArgParser(argparse.ArgumentParser):
    """argparse 缺省把用法错误以退出码 2 结束——与本工具的 2=样本不足冲突，改为 3。"""

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: 错误：%s\n" % (self.prog, message))
        raise SystemExit(EXIT_ERROR)


def _json_safe(v):
    """inf/nan 不是合法 JSON，映射为 null（判据输出里不应出现，兜底）。"""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: _json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    return v


def _emit(payload):
    sys.stdout.write(json.dumps(_json_safe(payload), ensure_ascii=False, indent=1))
    sys.stdout.write("\n")


# ---------------------------------------------------------------- 子命令
def cmd_discover(args):
    model = core_check.load_model(args.trans)
    if args.multi_label is not None and args.multi_label < 1:
        raise InputError("--multi-label 需要 K ≥ 1（随机重编号臂数），实得 %r"
                         % args.multi_label)
    # --preset robust（组合放开）= 三标志全开：canonize + extra +
    # multi（k 默认 8，--multi-label 可覆盖；种子由 --seed 控制可复现）。
    # 语义 = 实验层 C6 同口径（experiments_fullflags.json → judgment：
    # C6 三开达真 9/9 = 推荐配置）；不带 preset 时三标志自由组合。
    preset = args.preset
    if preset == "robust":
        canonize, extra = True, True
        multi = args.multi_label if args.multi_label is not None else 8
    else:
        canonize, extra = bool(args.canonize), bool(args.extra_candidates)
        multi = args.multi_label
    payload = core_discover.run_discover(
        model, canonize=canonize,
        multi_label=multi,
        multi_label_seed=args.seed,
        extra_candidates=extra,
        preset=preset,
        pad_aware=bool(getattr(args, "pad_aware", False)))
    # discover 产出的群自动标注动作语义：discover 的搜索与裁决在 relabel 口径
    # （动作可随状态换名，开关/里程碑位类正确）下进行——落盘复用时该标注随之
    # 带走并保持 assumed=true，直到模型作者改成自己的显式声明。
    payload["semantics"] = {
        "action": "relabel", "assumed": True,
        "note": ("discover 的搜索与等变裁决在 relabel 口径（动作可随状态换名）下"
                 "进行；事件驱动系统（动作=外部事件）请把本块改声明为 \"fixed\""
                 "——对照与自判指引见 docs/judge-semantics.md")}
    # --report-confidence：只读诊断块，默认关闭、
    # 关闭时输出逐字节不变；不改变退出码语义（预注册口径）。
    if args.report_confidence:
        if args.pad_aware or preset == "robust" or \
                (canonize and (multi is not None or extra)) or \
                (multi is not None and extra):
            current_kind = "combined"
        elif canonize:
            current_kind = "canonize"
        elif extra:
            current_kind = "extra"
        elif multi is not None:
            current_kind = "multi"
        else:
            current_kind = "plain"
        payload["confidence"] = _confidence.build_confidence_block(
            model, payload, current_kind)
    _emit(payload)
    return EXIT_REJECT if payload["trivial"] else EXIT_PASS


def cmd_check(args):
    model = core_check.load_model(args.trans)
    group = core_check.load_group(args.group)
    payload = core_check.run_check(model, group, strict=getattr(args, "strict", False))
    if payload.get("semantics_assumed"):
        # 宽容默认必须显眼：群文件未声明动作语义时按 relabel 判读，
        # 结论以该口径为条件——事件类系统在此口径下会被误放行（TCP 教训）。
        sys.stderr.write(
            "[口径警示] 群文件未声明动作语义（semantics 块）：按 relabel（动作可随"
            "状态换名）判读，本结论以该口径为条件。事件驱动系统（动作=外部事件，"
            "如协议报文）应把群文件里的 semantics 块声明为 \"fixed\"——"
            "两类系统的对照与自判指引见 docs/judge-semantics.md\n")
    _emit(payload)
    return EXIT_PASS if payload["verdict"] == "pass" else EXIT_REJECT


def cmd_check_sample(args):
    group = core_check.load_group(args.group)
    if args.trans:
        model = core_check.load_model(args.trans)
        if model["n_states"] != group["n_states"]:
            raise InputError("模型 n_states=%d 与群 n_states=%d 不一致"
                             % (model["n_states"], group["n_states"]))
        goals, n_actions = model["goals"], model["n_actions"]
        goals_source = "model"
    else:
        n_actions = group["n_actions"]
        if n_actions is None:
            raise InputError("check-sample 需要知道动作数：请加 --trans <model.json>，"
                             "或在 group.json 里给出 n_actions")
        goals = group["goals"] if group["goals"] is not None else set()
        goals_source = "group_file" if group["goals"] is not None else "none"
        if goals_source == "none":
            sys.stderr.write("[提醒] 未提供 goals：若模型有吸收态（目标自环奖励特殊），"
                             "L1 奖励层可能误判，建议始终带 --trans\n")
    samples = core_sample.load_samples(args.samples, group["n_states"], n_actions)
    orbits = core_check.orbits_of_group(group)
    payload = core_sample.run_check_sample(samples, goals, orbits, n_actions)
    payload["goals_source"] = goals_source
    payload["n_goals"] = len(goals)
    payload["group"] = {
        "n_states": group["n_states"],
        "order": len(group["elements"]),
        "n_orbits": len(orbits),
    }
    _emit(payload)
    return core_sample.VERDICT_EXIT[payload["verdict"]]


def cmd_selftest(args):
    return _selftest.run()


def cmd_demo(args):
    try:
        paths = demo_env.write_fixtures(args.out, n=args.n)
    except ValueError as e:
        raise InputError(str(e))
    sys.stdout.write("夹具已写入 %s（确定性可重建，重复运行逐字节一致）：\n" % args.out)
    for name in sorted(paths):
        sys.stdout.write("  %-16s %s\n" % (name, paths[name]))
    sys.stdout.write("用法示例见 wuxing_gua/README.md\n")
    return EXIT_PASS


# ---------------------------------------------------------------- 入口
def build_parser():
    ap = _ArgParser(prog="wuxing_gua",
                    description="黑盒转移数据上、压缩之前，判这个对称群能不能用；不能用就拒答")
    ap.add_argument("--version", action="version", version="wuxing_gua %s" % __version__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover", help="自动找群（三路候选+等变裁决+闭包，JSON → stdout）")
    p.add_argument("--trans", required=True, metavar="MODEL_JSON",
                   help="模型文件（README 输入格式：n_bits/n_actions/trans[/goals]）")
    p.add_argument("--preset", default=None, choices=["robust"],
                   help="预设配置一键（组合放开）：robust = --canonize "
                        "--extra-candidates --multi-label 8 三标志全开（k 可由 "
                        "--multi-label 覆盖）。语义 = 实验层 C6 同口径"
                        "（experiments_fullflags.json → judgment：C6 三开达真 "
                        "9/9 = 推荐配置；canonize 臂规范编号搜索 + 随机重编号臂 "
                        "+ 双射动作候选，幸存生成元并集闭包）。推荐入口，见 "
                        "README「--preset robust」一节")
    p.add_argument("--canonize", action="store_true", default=False,
                   help="先做规范化重编号（canonize）再跑同一搜索："
                        "消除 discover 发现结果的编号伪像；输出附加 canonize 字段"
                        "（用时量级/映射摘要/与不带标志的一致性对照）。默认关，"
                        "不带标志行为与旧版逐位一致（README「--canonize」一节）。"
                        "与其他标志可自由组合（组合语义见 "
                        "README「--preset robust」）")
    p.add_argument("--multi-label", type=int, default=None, metavar="K",
                   help="K 个随机重编号骨干图搜索的生成元并集取闭包："
                        "不依赖任何编号假设的替代修复路径；种子由 --seed 控制；"
                        "输出附加 multi_label 字段（k/种子/逐臂记录/与不带标志的"
                        "一致性对照，语义与 --canonize 同款）。与其他标志可自由"
                        "组合。默认关；k 曲线证据见 "
                        "experiments_multilabel_union.json 与 README"
                        "「三标志怎么选」一节")
    p.add_argument("--seed", type=int, default=20261025, metavar="SEED",
                   help="--multi-label（及 --preset robust 的 multi 臂）的随机编号"
                        "种子（默认 20261025；同种子同编号批，结果确定可复现）")
    p.add_argument("--extra-candidates", action="store_true", default=False,
                   help="追加动作置换候选源（生成器盲区修复）：每个动作的"
                        "最优后继映射为双射时作为候选生成元，与三路图搜索候选一起"
                        "过同一个 max TV=0 零容忍等变裁决（裁决口径与超参不变，"
                        "不可能引入伪自同构）。修「环境动作本身是对称却进不了"
                        "候选集」的盲区（gua64 实证：294,912→589,824，"
                        "experiments_gua64_gapfix.json）。默认关，不带标志行为与"
                        "旧版逐位一致；与其他标志可自由组合")
    p.add_argument("--pad-aware", action="store_true", default=False,
                   help="追加哑态商图臂（pad 感知候选生成修复）：检测 pad 哑态"
                        "（全动作单后继自环 r=0 行）后，在真态商图（哑态折叠、压缩"
                        "重编号）上跑同款三路图搜索（确定性/重启/对合/MRV fallback，"
                        "超参不变），候选哑态定点回填全空间后过同一个 max TV=0 零容忍"
                        "等变裁决（泛化判据 equiv_error_gua 口径，零容忍语义零改动，"
                        "不可能引入伪自同构）。修 S47 判决的「生成侧隔离」：含 pad "
                        "哑态时四路候选系统性漏掉跨哑态-真态对称元素（512 模型池普查"
                        " real_touch_pass=0，s47_blindspot_v2.json）。无 pad 哑态或"
                        "真实行引用 pad 时新臂如实跳过（不冒进）。默认关，不带标志"
                        "行为与旧版逐位一致；与其他标志可自由组合（哑态商图臂追加进"
                        "并集）；验收见 pilot/gw_padaware_run.json（回源索引"
                        " docs/evidence.md 锚点 E12）")
    p.add_argument("--report-confidence", action="store_true", default=False,
                   help="附加只读诊断块 confidence（校准判别分）：在"
                        "completeness 证书静默时给「这个群找全了吗」的可校准判读"
                        "（proved_incomplete / statistical_suspicion / "
                        "no_evidence_of_missing）。判据 = 同模型重测自一致性：证明层"
                        "（任一配置臂群阶 > 当前 ⇒ 当前漏找被证明）+ 统计层（wl_gap"
                        "轨道/色类比，阈值预注册事前定死）。矩阵校准 AUC=1.0、两端"
                        "错误率 0（experiments_w3_discriminator.json；预注册口径，"
                        "阈值事前定死——「无漏找证据」不是找全的证明）。开启时"
                        "自动补跑缺失配置臂（成本最高约 3 次 discover 级搜索 + 一次"
                        "canonize）；默认关闭、关闭时输出逐字节不变；**不改变退出码"
                        "语义**")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("check", help="完整转移表版判定（转移等变 + 奖励剖面，均零容忍）")
    p.add_argument("--trans", required=True, metavar="MODEL_JSON")
    p.add_argument("--group", required=True, metavar="GROUP_JSON")
    p.add_argument("--strict", action="store_true",
                   help="覆盖群声明为 fixed 口径：动作名必须原样对应，不得随状态"
                        "换名（事件驱动系统——动作=外部事件——的正确口径；开关/"
                        "里程碑位类系统请不要用本标志，改在群文件里声明 "
                        "semantics.action=\"relabel\"，两类系统的对照与自判指引见"
                        " docs/judge-semantics.md。不带本标志且群文件已声明时，"
                        "按声明分派")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("check-sample", help="采样版判定（三态：pass/reject/abstain）")
    p.add_argument("--samples", required=True, metavar="SAMPLES_JSONL",
                   help="逐行 [s, a, u, r]（或对象 {s,a,u,r}），u=后继")
    p.add_argument("--group", required=True, metavar="GROUP_JSON")
    p.add_argument("--trans", required=False, default=None, metavar="MODEL_JSON",
                   help="推荐提供：读 goals（吸收态口径）与 n_actions")
    p.set_defaults(func=cmd_check_sample)

    p = sub.add_parser("selftest", help="端到端自检（15 分支，约 2 分钟）")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("demo", help="辅助：生成 README 示例与 selftest 共用的夹具文件")
    p.add_argument("--out", required=True, metavar="DIR")
    p.add_argument("--n", type=int, default=6, metavar="N",
                   help="演示环境位数（1..6，默认 6 ⇒ 64 状态）")
    p.set_defaults(func=cmd_demo)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except InputError as e:
        sys.stderr.write("[输入错误（退出码 3）] %s\n" % e)
        return EXIT_ERROR
    except GroupInvalid as e:
        sys.stderr.write("[群非法（退出码 1：拒答）] %s\n" % e)
        return EXIT_REJECT
    except Exception as e:                       # noqa: BLE001 内部错误兜底
        sys.stderr.write("[内部错误（退出码 3）] %r\n" % e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return EXIT_ERROR
