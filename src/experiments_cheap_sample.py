# -*- coding: utf-8 -*-
"""
experiments_cheap_sample.py —— 纯采样版廉价校验器：采样预算扫描

回答一个产品化问题：**拿到多少条 (s,a,s',r) 采样，采样版才能和完整转移表版
判得一样准？** 少于这个数时必须报"样本不足"，不许靠放宽判据凑好看。

场景（n=6，|S|=64，|A|=6）
  ① Q_6 真群 S_6      —— 目标 = 全阳，真对称群 = S_6（阶 720，7 轨道，按 popcount）
                          表版应放行；采样版在样本够时应放行
  ② SYS-3 B 部分对称  —— 目标 = {位0=位1=1}，真群 = S_2×S_{n-2}×(Z_2)^{n-2}
                          （阶 768，3 轨道 = 16/32/16）；表版应放行
  ③ 非法群·XOR 平移   —— (Z_2)^6 作用在超立方体上，全体 64 态合成 1 个轨道。
                          目标 {63} 不是轨道的并 ⇒ 破坏奖励结构；表版应拒答
  ④ 非法群·隐蔽 GL    —— 一个固定 63 的非坐标置换（x ↦ x^(e_0·(v·x))，
                          对偶转置，阶 2）。它保住目标集、保住奖励，
                          **奖励层查不出来**，只能靠后继分布层 ⇒ 用来测功效上限

扫描：预算 [100, 500, 2000, 10000, 50000] × 种子 3 个

主指标
  与表版一致率 = 判断与完整转移表版完全一致的占比
      （"样本不足"既不等于放行也不等于拒答，一律记为不一致 —— 
       这是对本版最苛刻的口径，避免用"拒答"浑水摸鱼）
  真群放行率 / 非法群拒答率 / 非法群不谎报率(=拒答+不足) / 误通过率

运行：python src/experiments_cheap_sample.py
"""
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import (build_model_n, orbits_of, closure,  # noqa: E402
                            tables)
from experiments_p4 import cheap_check                          # noqa: E402
from experiments_sys3 import free_sym_gens                      # noqa: E402
from cheap_check_sample import (cheap_check_sample,             # noqa: E402
                                make_sampler, sample_from_model,
                                population_d)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BUDGETS = [100, 500, 2000, 10000, 50000]
SEEDS = (101, 202, 303)
N = 6


def swap_gen(NS, i, j):
    """坐标对换 i<->j 作为状态置换表"""
    pi = list(range(NS))
    for s in range(NS):
        a, b = (s >> i) & 1, (s >> j) & 1
        if a == 0 and b == 1:
            pi[s] = (s | (1 << i)) & ~(1 << j)
        elif a == 1 and b == 0:
            pi[s] = (s | (1 << j)) & ~(1 << i)
    return pi


def invol_gen(NS):
    """
    隐蔽的非法置换：x ↦ x ^ e_0·(v·x mod 2)，v = 位1..位4。
    保住全阳状态（v·全阳 = 0 偶）⇒ 奖励在轨道上恒定 ⇒ 第 1 层查不出。
    但它把"翻一位"送到"翻两位"，不属于动作集 ⇒ 不等变 ⇒ 第 2 层该抓。
    """
    v = 0b011110
    return [s ^ 1 if (bin(s & v).count("1") % 2) else s for s in range(NS)]


def build_scenarios(n=N):
    NS = 1 << n
    out = []

    # ① Q_n 真群 S_n
    tr = build_model_n(n, {NS - 1})
    G = closure([swap_gen(NS, i, i + 1) for i in range(n - 1)])
    out.append(dict(key="S6", name="Q_6 真群 S_6", kind="真群",
                    trans=tr, goals={NS - 1}, orbits=orbits_of(G, NS),
                    order=len(G)))

    # ② SYS-3 B 部分对称
    gb = set(s for s in range(NS) if (s & 3) == 3)
    trb = build_model_n(n, gb)
    Gb = closure(free_sym_gens(n))
    out.append(dict(key="SYS3B", name="SYS-3 B 部分对称", kind="部分对称",
                    trans=trb, goals=gb, orbits=orbits_of(Gb, NS),
                    order=len(Gb)))

    # ③ 非法·XOR 平移
    Gx = closure([[s ^ (1 << j) for s in range(NS)] for j in range(n)])
    out.append(dict(key="XOR", name="非法群·XOR 平移", kind="非法",
                    trans=tr, goals={NS - 1}, orbits=orbits_of(Gx, NS),
                    order=len(Gx)))

    # ④ 非法·隐蔽（GL 型对偶转置）
    Gm = closure([invol_gen(NS)])
    out.append(dict(key="GL", name="非法群·隐蔽(GL 对偶转置)", kind="非法·隐蔽",
                    trans=tr, goals={NS - 1}, orbits=orbits_of(Gm, NS),
                    order=len(Gm)))
    return out


def main():
    t0 = time.time()
    print("=" * 100)
    print("纯采样版廉价校验 · 采样预算扫描（n=6, |S|=64, |A|=6）")
    print("  三态裁决：pass 放行 / reject 拒答 / abstain 样本不足"
          "（样本不足**绝不放行**）")
    print("  与表版一致率口径：abstain 一律算不一致（最苛刻）")
    print("=" * 100)

    scs = build_scenarios(N)
    NS = 1 << N

    # ---- 表版真值 + 人群信号大小 ---------------------------------------
    for sc in scs:
        ok, dg = cheap_check(sc["trans"], sc["goals"], sc["orbits"], N)
        sc["table_pass"] = ok
        sc["table_diag"] = {"n_pair": dg["n_pair"], "n_bad": dg["n_bad"]}
        _, sc["pop_d_max"] = population_d(sc["trans"], sc["orbits"], N)
        sc["n_orbits"] = len(sc["orbits"])
        sc["cum"] = make_sampler(sc["trans"], N)
    print("\n  [0] 基线（完整转移表版 + 人群信号）")
    print("      %-24s %-8s %-6s %-10s %-10s %-12s"
          % ("场景", "群阶", "轨道", "表版", "剖面不同", "人群 d_max"))
    for sc in scs:
        print("      %-24s %-8d %-6d %-10s %-10s %.4f"
              % (sc["name"], sc["order"], sc["n_orbits"],
                 "放行" if sc["table_pass"] else "拒答",
                 "%d/%d" % (sc["table_diag"]["n_bad"], sc["table_diag"]["n_pair"]),
                 sc["pop_d_max"]))

    # ---- 预算扫描 -------------------------------------------------------
    res = {}
    for sc in scs:
        per = {}
        for B in BUDGETS:
            vs, dhis, nreqs, secs, cov = [], [], [], [], []
            for sd in SEEDS:
                rng = random.Random(sd * 7919 + B)
                smp = sample_from_model(sc["cum"], N, B, rng)
                ok, dg = cheap_check_sample(smp, sc["goals"], sc["orbits"], N)
                vs.append(dg["verdict"])
                testeds = [o for o in dg["orbits"] if o.get("tested")]
                dhis.append(max([o["d_hi"] for o in testeds], default=0.0))
                nreqs.append(dg["thresholds"]["n_req_total"])
                secs.append(dg["sec"])
                cov.append(dg["coverage"]["coverage_state"])
            want = "pass" if sc["table_pass"] else "reject"
            agree = sum(1 for v in vs if v == want) / len(vs)
            per[str(B)] = {
                "verdicts": vs,
                "n_pass": sum(1 for v in vs if v == "pass"),
                "n_reject": sum(1 for v in vs if v == "reject"),
                "n_abstain": sum(1 for v in vs if v == "abstain"),
                "agree": agree,
                "d_hi_mean": sum(dhis) / len(dhis),
                "d_hi_max": max(dhis),
                "n_req_mean": sum(nreqs) / len(nreqs),
                "cov_state": sum(cov) / len(cov),
                "sec": sum(secs) / len(secs),
            }
            print("      %-24s B=%-6d %s  一致 %.2f  d_hi≤%.3f  需 N≥%.0f"
                  % (sc["name"], B,
                     "/".join(v[:4] for v in vs), agree,
                     per[str(B)]["d_hi_max"], per[str(B)]["n_req_mean"]))
        sc["per_budget"] = per
        res[sc["key"]] = sc

    # ---- 汇总曲线 -------------------------------------------------------
    print("\n  [2] 采样量 → 与表版一致率 曲线")
    print("      %-8s %-10s %-10s %-10s %-10s %-10s %-10s"
          % ("预算", "一致率", "波动", "真群放行", "非法拒答", "不谎报", "误通过"))
    curve = []
    for B in BUDGETS:
        ag, ps, rj, gd, fp, ab = [], [], [], [], [], []
        for sc in scs:
            p = sc["per_budget"][str(B)]
            ag.append(p["agree"])
            if sc["kind"] == "真群" or sc["kind"] == "部分对称":
                ps.append(p["n_pass"] / len(SEEDS))
            else:
                rj.append(p["n_reject"] / len(SEEDS))
                gd.append((p["n_reject"] + p["n_abstain"]) / len(SEEDS))
                fp.append(p["n_pass"] / len(SEEDS))
            ab.append(p["n_abstain"] / len(SEEDS))
        m = sum(ag) / len(ag)
        sd = (sum((x - m) ** 2 for x in ag) / (len(ag) - 1)) ** 0.5
        curve.append({"budget": B,
                      "agree_mean": m, "agree_sd": sd,
                      "agree_per_scenario": {sc["key"]:
                                             sc["per_budget"][str(B)]["agree"]
                                             for sc in scs},
                      "true_pass_rate": sum(ps) / len(ps),
                      "illegal_reject_rate": sum(rj) / len(rj),
                      "illegal_guard_rate": sum(gd) / len(gd),
                      "false_pass_rate": sum(fp) / len(fp),
                      "abstain_rate": sum(ab) / len(ab),
                      "per_sa": B / float(NS * N)})
        print("      %-8d %-10.3f %-10.3f %-10.2f %-10.2f %-10.2f %-10.2f"
              % (B, m, sd, sum(ps) / len(ps), sum(rj) / len(rj),
                 sum(gd) / len(gd), sum(fp) / len(fp)))

    # ---- 门槛 -----------------------------------------------------------
    thr = {}
    for sc in scs:
        need = None
        for B in BUDGETS:
            if sc["per_budget"][str(B)]["agree"] >= 1.0:
                need = B
                break
        thr[sc["key"]] = {"agree_at_budget": need,
                          "n_req_total": sc["per_budget"][
                              str(BUDGETS[-1])]["n_req_mean"],
                          "pop_d_max": sc["pop_d_max"]}
    ok_budget = [B for B in BUDGETS
                 if all(res[k]["per_budget"][str(B)]["agree"] >= 1.0
                        for k in ("S6", "SYS3B", "XOR"))]
    # 人群 d 反推：要检出 d 需 N ≈ λ_req/d²（用最后档的 λ_req 量级）
    print("\n  [3] 门槛：与表版 4 个场景全一致的**最小**采样量 = %s"
          % (min(ok_budget) if ok_budget else "未在扫描范围内达到"))
    for k in ("S6", "SYS3B", "XOR", "GL"):
        print("      %-6s  达标预算=%-7s  功效门槛 N_req≈%.0f（每(s,a) %.1f 个）"
              "  人群 d=%.4f"
              % (k, thr[k]["agree_at_budget"], thr[k]["n_req_total"],
                 thr[k]["n_req_total"] / (NS * N), thr[k]["pop_d_max"]))

    out = {
        "meta": {"n": N, "NS": NS, "n_acts": N,
                 "budgets": BUDGETS, "seeds": list(SEEDS),
                 "alpha": 0.05, "beta": 0.20, "d_detect": 0.20,
                 "min_exp": 5.0, "tail": 0.01,
                 "verdict_meaning": {"pass": "放行", "reject": "拒答",
                                     "abstain": "样本不足(不放行)"},
                 "agree_rule": "abstain 计为与表版不一致（最苛刻口径）",
                 "sec": time.time() - t0},
        "scenarios": {k: {"name": res[k]["name"], "kind": res[k]["kind"],
                          "order": res[k]["order"],
                          "n_orbits": res[k]["n_orbits"],
                          "table_pass": res[k]["table_pass"],
                          "table_n_bad": res[k]["table_diag"]["n_bad"],
                          "table_n_pair": res[k]["table_diag"]["n_pair"],
                          "pop_d_max": res[k]["pop_d_max"],
                          "per_budget": res[k]["per_budget"]}
                      for k in res},
        "curve": curve,
        "threshold": {"overall_min_budget": (min(ok_budget) if ok_budget
                                             else None),
                      "per_scenario": thr},
    }
    with open(os.path.join(ROOT, "experiments_cheap_sample.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_cheap_sample.json（总耗时 %.1fs）"
          % (time.time() - t0))


if __name__ == "__main__":
    main()
