# -*- coding: utf-8 -*-
"""
wuxing_guard.py -- 压缩前的守门人（最小可用版）

用法（在仓库根目录）：
    python -X utf8 wuxing_guard.py --model examples/ticketfsm_milestones_model.json

它做三件事，你不需要懂任何术语：
  1. 自动搜一遍这个系统里「哪些状态其实只是名字不同」
  2. 把搜到的结果老老实实验一遍（不合格就说不合格）
  3. 给你一句结论：能压 / 不能压 / 压了不划算

输出只有人话，没有 JSON。要 JSON 请直接用 wuxing_gua 本体。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

LINE = "=" * 66


def _run(args, timeout=None):
    """跑 wuxing_gua 本体，返回 (退出码, stdout 解析后的 dict 或 None, 是否超时)"""
    try:
        p = subprocess.run([sys.executable, "-X", "utf8", "-m", "wuxing_gua"] + args,
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, True
    try:
        return p.returncode, json.loads(p.stdout), False
    except Exception:
        return p.returncode, None, False


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="压缩前先问一句：这份「哪些状态能互换」的清单，靠得住吗？")
    ap.add_argument("--model", required=True, help="你的系统模型文件（json）")
    ap.add_argument("--min-ratio", type=float, default=2.0,
                    help="压缩比低于这个数就判定不划算（默认 2.0，经验值）")
    ap.add_argument("--timeout", type=int, default=180,
                    help="自动搜索最多等多少秒（默认 180；大模型会超时，这是正常的）")
    args = ap.parse_args(argv)

    if not os.path.exists(args.model):
        print("找不到模型文件：%s" % args.model)
        return 3

    try:
        with open(args.model, encoding="utf-8") as f:
            model = json.load(f)
    except Exception as e:
        print("模型文件读不了（%s）：%s" % (type(e).__name__, e))
        return 3
    n_states = model.get("n_states")
    n_actions = model.get("n_actions")
    if not isinstance(n_states, int) or not isinstance(n_actions, int):
        print("模型格式不对：缺少整数类型的 n_states / n_actions 字段"
              "（本体命令会报 exit 3，请先查文件格式）。")
        return 3
    name = model.get("meta", {}).get("source_system", os.path.basename(args.model))

    print(LINE)
    print("模型：%s" % name)
    print("规模：%d 个状态 · %d 个动作" % (n_states, n_actions))
    print(LINE)
    print()

    # ---- 第一步：搜 ----
    print("[1/3] 自动搜「哪些状态其实只是名字不同」……")
    rc, d, timed_out = _run(["discover", "--trans", args.model], timeout=args.timeout)
    if timed_out:
        print("     搜了 %d 秒还没结果——这个规模自动搜不完。" % args.timeout)
        print()
        print(LINE)
        print("结论：自动搜索在这个规模上不可用（不是失败，是边界）。")
        print("      如果你已经人工推导出候选，直接用 wuxing_gua check 验证：")
        print("      python -X utf8 -m wuxing_gua check --trans %s --group 你的候选.json" % args.model)
        print(LINE)
        return 0
    if d is None:
        print("     搜索失败（退出码 %s），先看看模型格式对不对。" % rc)
        return 3

    order = d.get("order", 1)
    orbits = d.get("n_orbits", n_states)
    alert = d.get("completeness", {}).get("alert", False)
    cverdict = d.get("completeness", {}).get("verdict", "")

    if rc == 1 or order <= 1:
        print("     结果：没找到任何可用的替换关系。")
        print()
        print(LINE)
        print("结论：别压了。")
        print("      这个系统里没有可利用的对称性。强行压缩只会让结果算错，")
        print("      而且不会报错——你未必发现得了。")
        print(LINE)
        return 0

    print("     结果：找到 %d 种换法，能把 %d 个状态归成 %d 类。"
          % (order, n_states, orbits))

    if alert:
        print("     ⚠ 但它自己承认：这个结果可能没找全（%s）。" % cverdict)
        print()
        print("     换更保守的搜法再搜一遍……")
        rc2, d2, to2 = _run(["discover", "--preset", "robust", "--trans", args.model],
                            timeout=args.timeout)
        if d2 is not None and d2.get("order", 0) > order:
            d = d2
            order = d2["order"]
            orbits = d2.get("n_orbits", n_states)
            print("     这次找到 %d 种换法，归成 %d 类。" % (order, orbits))
        else:
            print("     重搜没有改善，先按当前结果往下验。")

    # ---- 第二步：验 ----
    print()
    print("[2/3] 把搜到的结果逐条验一遍（这一步不能省）……")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
        gpath = f.name
    try:
        rc3, c, to3 = _run(["check", "--trans", args.model, "--group", gpath],
                           timeout=args.timeout)
    finally:
        os.unlink(gpath)

    if c is None:
        print("     验证没跑完（退出码 %s）。" % rc3)
        return 3

    if c.get("verdict") != "pass":
        print("     结果：没通过。")
        print("     原因：%s" % c.get("reason", ""))
        print()
        print(LINE)
        print("结论：别用这份清单。")
        print("      搜索给出来的东西过不了验证——要么加参数重搜，")
        print("      要么人工推导候选之后再验。")
        print(LINE)
        return 0

    lt = c.get("layer_transition", {})
    lr = c.get("layer_reward_profile", {})
    print("     结果：通过。%d 种换法全部核对过，%d 对回报全部对得上。"
          % (lt.get("n_checked", 0), lr.get("n_pair", 0)))
    if c.get("semantics_assumed"):
        print("     ⚠ 口径提醒：你没声明动作语义，按「动作可随状态换名」判读的。")
        print("       动作是外部事件（协议报文、用户操作）的系统请改用群文件声明，")
        print("       见 docs/judge-semantics.md。")

    # ---- 第三步：算账 ----
    ratio = (n_states / orbits) if orbits else 0
    print()
    print("[3/3] 算一下值不值得压……")
    print("     压缩前 %d 个状态 → 压缩后 %d 个（%.2f 倍）"
          % (n_states, orbits, ratio))
    print()
    print(LINE)
    if ratio >= args.min_ratio:
        print("结论：能压，而且值得压。")
        print("      %.0f 倍这个量级，省下来的计算是实打实的。" % ratio)
    else:
        print("结论：能压，但不划算。")
        print("      只有 %.2f 倍——省下来的还不够你改代码的功夫。" % ratio)
        print("      这个工具在这里的作用，是让你确定它不划算，别再纠结。")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
