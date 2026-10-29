# -*- coding: utf-8 -*-
"""
cheap_check_sample.py —— 纯采样版「廉价合法性校验器」

━━ 与 experiments_p4.cheap_check 的关系 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

p4 版（要改我的请去看 experiments_p4.py，那个留作对照，不许动）：
    输入完整转移表 trans[s][a] = [(p, u, r), ...]
    对每个状态 s 把 (概率, 奖励) 多重集按轨道代表元 canon(u) 聚合 ⇒ 该状态的
    「奖励剖面」；同轨道内剖面全同 ⇔ 群等变。
    问题：要精确概率。真实场景只有轨迹，拿不到。

本版：
    只给 (s, a, s', r) 采样，把「剖面全同」改写成**后继-轨道分布齐性检验**。

━━ 统计量 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  对状态 s，把它的样本按 key = (后继的轨道代表元 canon(s'), 奖励 r) 归成直方图
      ν_s(k) = #{样本 (s,·,u,r) : (canon(u), r) = k} / n_s

  **动作维被池化**：若 G 是等变的，它同时置换动作指标（a ↦ σ(a)），
  于是「均匀混合动作」得到的边际分布在群作用下不变：
      ν_{g(s)}(·) = (1/|A|)Σ_a P(g(s), g(a), ·) = (1/|A|)Σ_a P(s, a, ·) = ν_s(·)
  池化换来 |A| 倍的样本效率；代价是只检验了等变的**必要条件**
  （p4 版比的是逐动作剖面的多重集，更强，但要 |A| 倍样本）。见文末「局限」。

  H0（可放行）：同一轨道 O 内所有 s 的后继分布 ν_s 共同服从某个 p
  H1（应拒答）：存在 s≠t∈O 与 key k 使 |p_s(k) - p_t(k)| 显著非零

  检验统计量为该 (状态 × key) 列联表的 Pearson X²，
  非中心参数 λ = Σ_s n_s·χ²(p_s‖p̄)，并用它定义效应尺度
      d = sqrt( mean_s χ²(p_s‖p̄) )           （RMS χ² 散度，d/2 ≈ 总变差距离）

━━ 为什么必须三态（放行 / 拒答 / 样本不足）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  「没检验出差异」≠「没有差异」。样本太少时检验功效不足，
  非法群也会因为看不出差异而被放行 —— 那就是谎报，比拒答坏得多。
  所以本校验器**只在功效达标时才敢放行**：

    放行 = 两层都没报警 且 每个受检轨道的样本量都 ≥ 功效门槛 N_req
    拒答 = 任一层报警（且该层判据在此样本量下可认证）
    不足 = 其余：包括「看到了偏差但样本不够、不足以认证」

━━ 判据（事前定死，不按结果调）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  显著性 α（经轨道数 Bonferroni 分摊 → α_B），置信水平 1-α。
  功效门槛：给定「要能检出的最小差异」d_detect 与目标功效 1-β，
      λ_req = 使 P(χ²_df(λ) > 临界值) ≥ 1-β 的最小非中心参数
      N_req = λ_req / d_detect²
  d_detect 的默认 0.20（≈ 总变差 10%）锚定在**环境自身的单步随机性**上
  （本环境 P_PERT=0.12、P_NOOP=0.10）：比环境噪声还小的差异，
  既检不出也不影响可用性与否。改 d_detect 则 N_req 按 1/d² 缩放。

运行（自检）：python src/cheap_check_sample.py
"""
import math
import time

# ---- 事前定死的判据 --------------------------------------------------------
ALPHA = 0.05        # 显著性水平（家族wise，经轨道数 Bonferroni 分摊）
BETA = 0.20         # 二类错误 ⇒ 功效 1-β = 80%
D_DETECT = 0.20     # 要求能检出的最小差异（RMS χ² 散度，≈ 2×总变差）
MIN_EXP = 5.0       # 卡方近似可用性的最低平均期望频数（Cochran 准则）
TAIL = 0.01         # 稀有 key 合并阈值（低于此占比的 key 并进 OTHER）

_OTHER = "__OTHER__"


# ===========================================================================
# 0. 数值工具（纯 Python，无 scipy）
# ===========================================================================

def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p):
    lo, hi = -40.0, 40.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if _norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _chi2_ppf(p, df):
    """Wilson–Hilferty 近似：df≥3、上尾时相对误差 <1%"""
    t = 2.0 / (9.0 * df)
    return df * max(0.0, (1.0 - t + _norm_ppf(p) * math.sqrt(t))) ** 3


def _chi2_sf(x, df):
    """P(χ²_df > x)，Wilson–Hilferty 近似"""
    t = 2.0 / (9.0 * df)
    z = ((max(x, 1e-12) / df) ** (1.0 / 3.0) - (1.0 - t)) / math.sqrt(t)
    return 1.0 - _norm_cdf(z)


def _lambda_bounds(x, df, z):
    """
    非中心 χ² 的正态近似 X² ≈ N(df+λ, 2(df+2λ))。
    由观测 X² 反解 λ 的 (下界, 上界)（z=1.96 ⇒ 双侧 95%）。
    """
    disc = 4.0 * z * z - 2.0 * df + 4.0 * max(x, 0.0)
    disc = max(disc, 0.0)
    r = math.sqrt(disc)
    w_hi = 2.0 * z + r
    w_lo = -2.0 * z + r
    lam_hi = w_hi * w_hi / 4.0 - df / 2.0
    lam_lo = w_lo * w_lo / 4.0 - df / 2.0
    return max(0.0, lam_lo), max(0.0, lam_hi)


def _lambda_req(df, crit, zbeta):
    """使 P(χ²_df(λ) > crit) ≥ 1-β 的最小 λ（二分求根）"""
    def g(lam):
        return df + lam - zbeta * math.sqrt(2.0 * (df + 2.0 * lam)) - crit
    if g(0.0) >= 0.0:
        return 0.0
    lo, hi = 0.0, 1.0
    while g(hi) < 0.0:
        hi *= 2.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if g(mid) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ===========================================================================
# 1. 离线采样器（只有它碰模型；校验器本体只碰 samples）
# ===========================================================================

def make_sampler(trans, n_acts):
    """预累积分布，返回 cum[s][a] = [(c,u,r)...]"""
    cum = []
    for s in range(len(trans)):
        row = []
        for a in range(n_acts):
            c, cs = 0.0, []
            for (p, u, r) in trans[s][a]:
                c += p
                cs.append((c, u, r))
            row.append(cs)
        cum.append(row)
    return cum


def sample_from_model(cum, n_acts, n_samples, rng):
    """均匀抽 (s,a)，再按 P(·|s,a) 抽后继 ⇒ [(s, a, s', r)]"""
    NS = len(cum)
    out = []
    for _ in range(n_samples):
        s = rng.randrange(NS)
        a = rng.randrange(n_acts)
        x = rng.random()
        u, r = cum[s][a][-1][1], cum[s][a][-1][2]
        for (c, uu, rr) in cum[s][a]:
            if x <= c:
                u, r = uu, rr
                break
        out.append((s, a, u, r))
    return out


# ===========================================================================
# 2. 直方图整理
# ===========================================================================

def _hist(states, cnt, tail):
    """
    把 states 的 key 计数合并稀有键 ⇒ (C, keys, col, n_vec, N)
    稀有键：总占比 < tail 的丢进 OTHER（OTHER 总数 <2 则整桶丢弃，
    否则 OTHER 列会成为"期望频数≈0"的噪声放大器）。
    """
    tot = {}
    for s in states:
        for k, c in cnt[s].items():
            tot[k] = tot.get(k, 0) + c
    N = sum(tot.values())
    thr = max(2, int(tail * N))
    keep = [k for k, v in tot.items() if v >= thr]
    merged = N - sum(tot[k] for k in keep)
    use_other = merged >= 2
    keys = sorted(keep) + ([_OTHER] if use_other else [])
    idx = {k: i for i, k in enumerate(keys)}
    K = len(keys)
    oi = K - 1 if use_other else None
    C, col = [], [0] * K
    for s in states:
        row = [0] * K
        for k, c in cnt[s].items():
            j = idx[k] if k in idx else oi
            if j is not None:
                row[j] += c
        C.append(row)
    for row in C:
        for j in range(K):
            col[j] += row[j]
    n_vec = [sum(row) for row in C]
    return C, keys, col, n_vec


def _pearson(C, col, n_vec):
    N = float(sum(col))
    p = [c / N for c in col]
    K = len(col)
    X2 = 0.0
    for i, row in enumerate(C):
        for j in range(K):
            e = n_vec[i] * p[j]
            if e > 0.0:
                X2 += (row[j] - e) ** 2 / e
    return X2, p


# ===========================================================================
# 3. 主体：纯采样版廉价校验
# ===========================================================================

def cheap_check_sample(samples, goals, orbits, n_acts,
                       alpha=ALPHA, beta=BETA, d_detect=D_DETECT,
                       min_exp=MIN_EXP, tail=TAIL):
    """
    输入
      samples : [(s, a, s', r), ...]   纯采样数据，不要转移表
      goals   : 目标状态集合（用于区分吸收态的自环奖励）
      orbits  : 候选群的轨道划分 [[s...], ...]
      n_acts  : 动作数
    输出
      (放行?, diag)

    diag["verdict"] ∈ {"pass", "reject", "abstain"}
      pass    —— 两层都没报警，且每个受检轨道的功效都达标
      reject  —— 有可认证的证据表明该群不等变 ⇒ 不许用
      abstain —— 样本不足，不敢给结论（**绝不因为"没看出差异"就放行**）
    """
    t0 = time.time()
    canon = {}
    for ob in orbits:
        rep = min(ob)
        for s in ob:
            canon[s] = rep
    NS = sum(len(ob) for ob in orbits)

    # ---- 归桶：源状态 → key 计数 ----------------------------------------
    cnt = {}
    saw_sa = set()
    for (s, a, u, r) in samples:
        k = (canon.get(u, u), round(float(r), 9))
        d = cnt.setdefault(s, {})
        d[k] = d.get(k, 0) + 1
        saw_sa.add((s, a))

    # ---- 第 1 层：奖励在轨道上必须恒定（等变的极廉价必要条件）------------
    # r = f(s') 时，等变 ⇒ r(g·u) = r(u) ⇒ 奖励在轨道上恒定。
    # 只用「源状态非目标」的样本：目标状态的自环奖励是吸收约定，不是 f(s')。
    rwd = {}
    for (s, a, u, r) in samples:
        if s in goals:
            continue
        rwd.setdefault(canon.get(u, u), set()).add(round(float(r), 9))
    l1_bad = [c for c, vs in rwd.items() if len(vs) > 1]
    l1 = {"n_orbit_checked": len(rwd), "n_bad": len(l1_bad),
          "bad_canons": sorted(l1_bad)[:20]}

    # ---- 第 2 层：后继-轨道分布的齐性 χ² 检验 ---------------------------
    testable = [ob for ob in orbits if len(ob) >= 2]
    alpha_b = alpha / max(1, len(testable))
    zbeta = _norm_ppf(1.0 - beta)
    zci = _norm_ppf(1.0 - alpha / 2.0)

    per_ob = []
    n_req_total = 0.0
    for ob in testable:
        states = [s for s in ob if cnt.get(s)]
        m_eff = len(states)
        rec = {"orbit_size": len(ob), "states_with_samples": m_eff}
        if m_eff < 2:
            rec.update(tested=False, reason="轨道内被采样到的状态 <2")
            per_ob.append(rec)
            continue
        C, keys, col, n_vec = _hist(states, cnt, tail)
        K = len(keys)
        if K < 2:
            # 结构退化：该轨道内所有状态在观测上无可分辨差异（典型是"全是吸收态"，
            # 每个动作都回到自己、奖励恒为 0）。此时逐动作剖面也一样逐个相同，
            # p4 表版同样判它们相同 —— 不是"没看到差异"，而是"没有差异可看"。
            # 只有在该轨道样本足够多（每状态 ≥10 条）时才敢这么认定，
            # 否则就是被样本稀缺掩盖，仍按"未检验"处理。
            degen = min(n_vec) >= 10
            rec.update(tested=False, degenerate=degen,
                       reason=("结构退化：全体成员观测上相同（如吸收态），"
                               "本轨不提供证据" if degen
                               else "样本太稀疏，合并后只剩 1 个 key"))
            per_ob.append(rec)
            continue
        X2, p_hat = _pearson(C, col, n_vec)
        df = (m_eff - 1) * (K - 1)
        N_O = float(sum(col))
        crit = _chi2_ppf(1.0 - alpha_b, df)
        pval = _chi2_sf(X2, df)
        lam_lo, lam_hi = _lambda_bounds(X2, df, zci)
        lam_req = _lambda_req(df, crit, zbeta)
        N_req = lam_req / (d_detect * d_detect)
        avg_exp = N_O / (m_eff * K)
        rec.update(tested=True, K=K, df=df, X2=X2, crit=crit, p=pval,
                   N_orbit=N_O, avg_exp=avg_exp,
                   reliable=(avg_exp >= min_exp),
                   d_hat=math.sqrt(max(0.0, X2 - df) / N_O),
                   d_lo=math.sqrt(lam_lo / N_O), d_hi=math.sqrt(lam_hi / N_O),
                   lam_req=lam_req, N_req=N_req,
                   powered=(N_O >= N_req),
                   significant=(pval < alpha_b))
        # 换算：该轨道要拿到 N_req，总量得抽多少
        n_req_total = max(n_req_total, N_req * NS / float(m_eff))
        per_ob.append(rec)

    # ---- 汇总裁决 -------------------------------------------------------
    reasons = []
    if l1["n_bad"] > 0:
        verdict = "reject"
        reasons.append("L1 奖励在轨道上不恒定（%d 个轨道）" % l1["n_bad"])
    else:
        rejected = [r for r in per_ob
                    if r.get("tested") and r["significant"] and r["reliable"]]
        suspect = [r for r in per_ob
                   if r.get("tested") and r["significant"] and not r["reliable"]]
        # 结构退化轨道既不提供证据、也不构成"没证据"，不参与放行/拒答的表决
        untested = [r for r in per_ob
                    if not r.get("tested") and not r.get("degenerate")]
        weak = [r for r in per_ob if r.get("tested") and not r["powered"]]
        n_degen = sum(1 for r in per_ob if r.get("degenerate"))
        if rejected:
            verdict = "reject"
            reasons.append("L2 后继分布不齐（%d/%d 轨道，p<%.2g）"
                           % (len(rejected), len(per_ob), alpha_b))
        elif untested or weak:
            verdict = "abstain"
            if untested:
                reasons.append("有 %d 个轨道未被采样覆盖" % len(untested))
            if weak:
                reasons.append("有 %d 个轨道样本量低于功效门槛" % len(weak))
            if suspect:
                reasons.append("另有 %d 个轨道观察到偏差但样本量不足以认证"
                               % len(suspect))
        else:
            verdict = "pass"
            reasons.append("两层均无报警，且 %d 个轨道功效均达标%s"
                           % (len(per_ob),
                              "（另有 %d 个结构退化轨道不提供证据）" % n_degen
                              if n_degen else ""))

    ns_list = sorted(len(v) for v in cnt.values())
    med = ns_list[len(ns_list) // 2] if ns_list else 0
    diag = {
        "verdict": verdict,
        "reason": "；".join(reasons),
        "layer1_reward": l1,
        "orbits": per_ob,
        "thresholds": {"alpha": alpha, "alpha_bonf": alpha_b, "beta": beta,
                       "d_detect": d_detect, "min_exp": min_exp, "tail": tail,
                       "z_beta": zbeta, "n_req_total": n_req_total},
        "coverage": {
            "n_samples": len(samples),
            "n_states": NS,
            "states_covered": len(cnt),
            "coverage_state": len(cnt) / float(NS) if NS else 0.0,
            "min_per_state": ns_list[0] if ns_list else 0,
            "median_per_state": med,
            "per_sa": len(samples) / float(NS * n_acts) if NS else 0.0,
            "cells_covered": len(saw_sa),
            "cells_total": NS * n_acts,
            "coverage_sa": len(saw_sa) / float(NS * n_acts) if NS else 0.0,
        },
        "sec": time.time() - t0,
    }
    return (verdict == "pass"), diag


# ===========================================================================
# 4. 用真实模型算「人群差异度」（只用于实验标注信号强弱，不属于校验器）
# ===========================================================================

def population_d(trans, orbits, n_acts, tail=TAIL):
    """
    用精确转移表算每个轨道的 d（RMS χ² 散度）—— 这是「信号真实大小」。
    校验器看不到它；实验用它解释"为什么这个预算检不出"。
    返回 (每轨道 dict 列表, 最大 d)
    """
    canon = {}
    for ob in orbits:
        rep = min(ob)
        for s in ob:
            canon[s] = rep
    out = []
    for ob in orbits:
        if len(ob) < 2:
            continue
        prof = []
        for s in ob:
            d = {}
            for a in range(n_acts):
                for (p, u, r) in trans[s][a]:
                    k = (canon.get(u, u), round(r, 9))
                    d[k] = d.get(k, 0.0) + p / float(n_acts)
            prof.append(d)
        tot = {}
        for d in prof:
            for k, v in d.items():
                tot[k] = tot.get(k, 0.0) + v
        N = sum(tot.values())
        keys = sorted(k for k, v in tot.items() if v >= tail * N)
        pbar = [tot[k] / N for k in keys]
        oth = 1.0 - sum(pbar)
        s2 = 0.0
        for d in prof:
            row = [d.get(k, 0.0) for k in keys]
            s2 += sum((row[j] - pbar[j]) ** 2 / pbar[j] for j in range(len(keys)))
            if oth > 1e-12:
                s2 += (1.0 - sum(row) - oth) ** 2 / oth
        d2 = s2 / len(prof)
        out.append({"orbit_size": len(ob), "K": len(keys),
                    "d": math.sqrt(max(0.0, d2))})
    return out, max([o["d"] for o in out], default=0.0)


# ===========================================================================
# 5. 自检
# ===========================================================================

if __name__ == "__main__":
    import os
    import random
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from experiments_e1 import build_model_n, orbits_of, closure

    NS = 64
    n = 6
    goals = {NS - 1}
    tr = build_model_n(n, goals)
    cum = make_sampler(tr, n)
    G = closure([[s ^ (1 << j) for s in range(NS)] for j in range(n)])
    ob_xor = orbits_of(G, NS)
    print("XOR 群 轨道数 =", len(ob_xor), "（应为 1）")

    rng = random.Random(1)
    for B in (100, 2000, 50000):
        smp = sample_from_model(cum, n, B, rng)
        ok, dg = cheap_check_sample(smp, goals, ob_xor, n)
        print("  B=%-6d verdict=%-8s %s | 覆盖 %d/%d 状态, 每(s,a) %.2f 个样本"
              % (B, dg["verdict"], dg["reason"],
                 dg["coverage"]["states_covered"], NS,
                 dg["coverage"]["per_sa"]))
    # 近似自检
    print("χ² 近似自检: sf(6, 12.59)=%.4f (应≈0.05)  ppf(0.95,6)=%.3f (应≈12.59)"
          % (_chi2_sf(12.592, 6), _chi2_ppf(0.95, 6)))
    print("            ppf(0.95,30)=%.2f (应≈43.8)  sf(30,43.77)=%.4f"
          % (_chi2_ppf(0.95, 30), _chi2_sf(43.773, 30)))
