# -*- coding: utf-8 -*-
"""
core_sample.py —— 纯采样版判定（三态：pass / reject / abstain）

━━ 出处（import 复用，未复制、未改写判据逻辑）━━━━━━━━━━━━━━━━━━━━━━━━━
  cheap_check_sample / make_sampler / sample_from_model
      ← src/cheap_check_sample.py。判据参数照抄原实现（事前定死，不按结果调）：
        ALPHA=0.05（家族wise，经轨道数 Bonferroni 分摊）、BETA=0.20（功效 80%）、
        D_DETECT=0.20（≈总变差 10%）、MIN_EXP=5.0（Cochran 准则）、TAIL=0.01
        （见 src/cheap_check_sample.py 常量区）。
  采样门槛 10⁴ 条：experiments_cheap_sample.json → threshold.overall_min_budget
  = 10000（4 个场景 × 3 种子与完整转移表版 100% 一致的最小预算档）。

本文件新增的只有 samples.jsonl 装载与输入校验（load_samples）与输出编排。
三态语义（照抄原实现）：
  pass    两层都没报警，且每个受检轨道的功效都达标
  reject  有可认证的证据表明该群不等变 ⇒ 不许用
  abstain 样本不足，不敢给结论——绝不因为"没看出差异"就放行
"""
import json
import os

from cheap_check_sample import (cheap_check_sample as _cheap_check_sample,   # noqa: F401
                                make_sampler, sample_from_model)             # noqa: F401

from .errors import InputError

VERDICT_EXIT = {"pass": 0, "reject": 1, "abstain": 2}


def load_samples(path, n_states, n_actions):
    """
    装载 samples.jsonl：每行一个 JSON，[s, a, u, r] 数组或 {"s","a","u","r"} 对象
    （u = 后继状态）。越界/缺键/非 JSON → InputError（退出码 3）。
    """
    if not os.path.isfile(path):
        raise InputError("样本文件不存在：%s" % path)
    samples = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError as e:
                    raise InputError("samples 第 %d 行不是合法 JSON：%s" % (lineno, e))
                if isinstance(obj, list) and len(obj) == 4:
                    s, a, u, r = obj
                elif isinstance(obj, dict):
                    if not {"s", "a", "u", "r"} <= set(obj):
                        raise InputError("samples 第 %d 行对象形式需含 s/a/u/r 四个键" % lineno)
                    s, a, u, r = obj["s"], obj["a"], obj["u"], obj["r"]
                else:
                    raise InputError("samples 第 %d 行必须是 [s,a,u,r] 数组或含这四个键的对象" % lineno)
                if not (_is_int(s) and 0 <= s < n_states):
                    raise InputError("samples 第 %d 行 s=%r 越界（应为 0..%d）" % (lineno, s, n_states - 1))
                if not (_is_int(a) and 0 <= a < n_actions):
                    raise InputError("samples 第 %d 行 a=%r 越界（应为 0..%d）" % (lineno, a, n_actions - 1))
                if not (_is_int(u) and 0 <= u < n_states):
                    raise InputError("samples 第 %d 行 u=%r 越界（应为 0..%d）" % (lineno, u, n_states - 1))
                if not (isinstance(r, (int, float)) and not isinstance(r, bool)):
                    raise InputError("samples 第 %d 行 r=%r 必须是数值" % (lineno, r))
                samples.append((s, a, u, float(r)))
    except OSError as e:
        raise InputError("样本文件读取失败：%s" % e)
    if not samples:
        raise InputError("样本文件为空（%s）" % path)
    return samples


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def run_check_sample(samples, goals, orbits, n_actions):
    """
    调 src/cheap_check_sample.py 的 cheap_check_sample（判据本体），
    编排成 stdout JSON payload。退出码由 verdict 映射：
    pass→0 / reject→1 / abstain→2。
    """
    ok, diag = _cheap_check_sample(samples, set(goals), orbits, n_actions)   # noqa: F841 ok 由 verdict 决定
    verdict = diag["verdict"]
    return {
        "command": "check-sample",
        "verdict": verdict,
        "exit_code": VERDICT_EXIT[verdict],
        "reason": diag["reason"],
        "n_samples": len(samples),
        "abstain_note": ("样本不足：只说明样本不足，不下其他结论（绝不放行）"
                         if verdict == "abstain" else None),
        "diagnostics": diag,
    }
