# -*- coding: utf-8 -*-
"""
core.py —— 五行 / 六十四卦 的形式化核心（纯标准库，零第三方依赖）

设计原则：
  只保留可被形式化、可被计算、可被证伪的结构。
  不含任何命理/风水/占卜语义：五行 = Z5 上的两个循环算子；
  六十四卦 = 2^6 位串上的一组位运算与对称群。
"""

import cmath
import itertools
import math

# ===========================================================================
# 第一部分：五行 = Z5 上的二元关系代数
# ===========================================================================

PHASES = ["木", "火", "土", "金", "水"]   # 按"相生"次序排列
N5 = 5


def sheng(i):
    """i 所生者：木生火，火生土，土生金，金生水，水生木 —— 步长 +1"""
    return (i + 1) % N5


def ke(i):
    """i 所克者：木克土，土克水，水克火，火克金，金克木 —— 步长 +2"""
    return (i + 2) % N5


def sheng_of(i):
    """生我者（母）"""
    return (i - 1) % N5


def ke_of(i):
    """克我者（所不胜）"""
    return (i - 2) % N5


def circulant(shift, n=N5):
    """
    循环移位矩阵 C，满足 (Cx)_i = x_{i-shift}。
    第一行 c 定义为 c[(i-j) mod n] = A[i][j]。
    """
    return [[1 if (i - j) % n == shift else 0 for j in range(n)] for i in range(n)]


def matvec(A, x):
    return [sum(A[i][j] * x[j] for j in range(len(x))) for i in range(len(A))]


def circulant_eigs(first_row):
    """
    循环矩阵 A[i][j] = first_row[(i-j) mod n] 的特征值。
    特征向量为 Fourier 基 v_k(i) = exp(2*pi*i*k*i/n)，
    lambda_k = sum_m first_row[m] * omega^{-k m}
    """
    n = len(first_row)
    out = []
    for k in range(n):
        s = 0j
        for m in range(n):
            s += first_row[m] * cmath.exp(-2j * cmath.pi * k * m / n)
        out.append(s)
    return out


def dft(x, n=None):
    """长度 n 的离散 Fourier 变换（未归一化）：X[k] = sum_i x[i] e^{-2pi i k i/n}"""
    n = n or len(x)
    return [sum(x[i] * cmath.exp(-2j * cmath.pi * k * i / n) for i in range(n))
            for k in range(n)]


def five_phase_spectrum(alpha, beta, gamma, n=N5):
    """
    五行流网络 ẋ = A x + u 的谱，其中
        A = alpha*(S - I) - beta*K - gamma*I
        (Sx)_i = x_{i-1}   生 = 相邻守恒输运（步长 1）
        (Kx)_i = x_{i-2}   克 = 隔位抑制      （步长 2）
        gamma           耗散 / 完成 / 漏出
    返回 [(k, Re mu_k, Im mu_k, |mu_k|), ...]
    """
    eigs_S = circulant_eigs(circulant(1, n)[0])   # lambda_k(S) = omega^{-k}
    eigs_K = circulant_eigs(circulant(2, n)[0])   # lambda_k(K) = omega^{-2k}
    out = []
    for k in range(n):
        mu = alpha * (eigs_S[k] - 1) - beta * eigs_K[k] - gamma
        out.append((k, mu.real, mu.imag, abs(mu)))
    return out


def stability_margin(alpha, beta, gamma, n=N5):
    """max_k Re(mu_k)。< 0 渐近稳定；> 0 该模发散。"""
    return max(r for (_, r, _, _) in five_phase_spectrum(alpha, beta, gamma, n))


def critical_gamma(alpha, beta, n=N5):
    """
    临界耗散：使 max_k Re(mu_k) = 0 的 gamma。
    闭式：gamma* = max_k [ alpha*(cos(2*pi*k/n) - 1) - beta*cos(4*pi*k/n) ]
    """
    best = -1e18
    for k in range(n):
        v = alpha * (math.cos(2 * math.pi * k / n) - 1) - beta * math.cos(4 * math.pi * k / n)
        best = max(best, v)
    return best


def dominant_mode(alpha, beta, gamma, n=N5):
    """返回 (k*, Re, Im)：谱半径意义下最不稳的模"""
    spec = five_phase_spectrum(alpha, beta, gamma, n)
    return max(spec, key=lambda t: t[1])


def predicted_period(alpha, beta, gamma, n=N5):
    """最不稳模的预测振荡周期 T = 2*pi / |Im mu|（Im=0 时返回 inf）"""
    _, _, im, _ = dominant_mode(alpha, beta, gamma, n)
    return float("inf") if abs(im) < 1e-12 else 2 * math.pi / abs(im)


def is_ke_single_cycle(n):
    """克的步长 2 是否构成单一 Hamilton 环（gcd(2,n)==1）"""
    return math.gcd(2, n) == 1


def all_steps_hamiltonian(n):
    """n 为素数时，任意非平凡步长都构成单一 Hamilton 环（不会分裂成派系）"""
    return all(math.gcd(k, n) == 1 for k in range(1, n))


# --- 失衡度量（用于奖励塑形的势函数） -------------------------------------

def spec_potential(x, modes=None):
    """
    五行谱势：Phi(x) = - sum_{k in modes} |x_hat_k|^2
    modes=None 时取全部非直流模 {1..n-1}。
    由 Parseval：全模谱势 == -n * sum_i (x_i - x_bar)^2，即方差惩罚。
    """
    n = len(x)
    X = dft(x, n)
    if modes is None:
        modes = list(range(1, n))
    return -sum(abs(X[k]) ** 2 for k in modes)


def imbalance_l1(x):
    """L1 失衡度：sum |x_i - x_bar| —— 非谱的对照度量"""
    n = len(x)
    xb = sum(x) / n
    return sum(abs(v - xb) for v in x)


def cycle_gap(x):
    """
    "生克环流强度差"：相邻生边上的梯度范数 减 隔位克边上的抑制强度。
    用于判定系统处在"生主导"还是"克主导"的动力学区间。
    """
    n = len(x)
    s = sum(x[(i + 1) % n] - x[i] for i in range(n))
    k = sum(x[(i + 2) % n] - x[i] for i in range(n))
    return s, k


def simulate_flow(x0, alpha, beta, gamma, u=None, dt=0.01, steps=20000, clip=True):
    """
    显式 Euler 积分 ẋ = alpha*(S-I)x - beta*K x - gamma*x + u
    返回 (轨迹, 时间序列)。用于数值验证谱判据。
    """
    n = len(x0)
    u = u or [0.0] * n
    x = list(map(float, x0))
    traj = [list(x)]
    ts = [0.0]
    for t in range(steps):
        dx = [alpha * (x[(i - 1) % n] - x[i]) - beta * x[(i - 2) % n]
              - gamma * x[i] + u[i] for i in range(n)]
        x = [x[i] + dt * dx[i] for i in range(n)]
        if clip:
            x = [max(0.0, v) for v in x]
        traj.append(list(x))
        ts.append((t + 1) * dt)
    return ts, traj


def measure_oscillation(ts, traj, idx=0, tail_frac=0.6):
    """
    从后段轨迹估计主导振荡周期（峰值间距法）。
    峰值位置对指数增长/衰减的单调包络免疫 —— 包络只影响幅度，不影响峰的间距。
    返回 None 表示未检出振荡（峰少于 2 个，或后段根本没有起伏）。

    ⚠️ 阈值说明：原写法用 `amp < 1e-300`，太低 —— 全零序列上的浮点残差（~1e-18）
    会逃过该检查，被归一化后测出"周期"（E5 诊断时真实遇到过：
    clip=True 的轨迹后 60% 全是 0，却返回了 13.671 的假周期）。
    现改为绝对门槛 1e-9：低于它视为"没有振荡"，直接返回 None。
    """
    start = int(len(traj) * (1 - tail_frac))
    seg = [traj[t][idx] for t in range(start, len(traj))]
    tseg = [ts[t] for t in range(start, len(ts))]
    amp = max(abs(v) for v in seg)
    if amp < 1e-9 or amp == float("inf") or amp != amp:
        return None
    seg = [v / amp for v in seg]          # 归一化，避免量级问题
    peaks = []
    for i in range(1, len(seg) - 1):
        if seg[i] > seg[i - 1] and seg[i] >= seg[i + 1]:
            peaks.append(i)
    # 去掉相邻重复峰（数值噪声）
    dedup = [peaks[0]] if peaks else []
    for p in peaks[1:]:
        if p - dedup[-1] > 2:
            dedup.append(p)
    if len(dedup) < 2:
        return None
    pt = [tseg[p] for p in dedup]
    gaps = [pt[i + 1] - pt[i] for i in range(len(pt) - 1)]
    gaps.sort()
    gaps = gaps[len(gaps) // 4: len(gaps) - len(gaps) // 4] or gaps   # 去两端异常
    return sum(gaps) / len(gaps)


# ===========================================================================
# 第二部分：六十四卦 = 2^6 位串上的位运算与对称群
# ===========================================================================

NBITS = 6
NS = 1 << NBITS          # 64
FULL = NS - 1            # 0b111111 = 63

# 先天（伏羲/邵雍）二进制编码：1 = 阳爻，bit5 = 上爻，bit0 = 初爻
TRIGRAM = {"坤": 0b000, "艮": 0b001, "坎": 0b010, "巽": 0b011,
           "震": 0b100, "离": 0b101, "兑": 0b110, "乾": 0b111}
TRIGRAM_NAME = {v: k for k, v in TRIGRAM.items()}


def hex_code(upper, lower):
    """八卦名 -> 六爻码：(上卦 << 3) | 下卦"""
    return (TRIGRAM[upper] << 3) | TRIGRAM[lower]


def hex_str(h):
    return format(h, "06b")


def trigrams_of(h):
    return TRIGRAM_NAME[(h >> 3) & 7], TRIGRAM_NAME[h & 7]


def cuo(h):
    """错卦（旁通）：六爻全反 —— 位异或 111111"""
    return h ^ FULL


def zong(h):
    """综卦（反对/覆）：上下颠倒 —— 6 位反序"""
    r = 0
    for i in range(NBITS):
        r = (r << 1) | ((h >> i) & 1)
    return r


def hu(h):
    """
    互卦：新上卦 = 原 3,4,5 爻；新下卦 = 原 2,3,4 爻
    （bit5=上爻, bit0=初爻）=> new_up = (h>>2)&7, new_low = (h>>1)&7
    注意：互卦是投影（不可逆），不是群元素，只能作为"宏动作"使用。
    """
    return (((h >> 2) & 7) << 3) | ((h >> 1) & 7)


def swap_halves(h):
    """上下卦易位 —— 等价于循环左移 3 位"""
    return ((h & 7) << 3) | ((h >> 3) & 7)


def rotl(h, k):
    """爻位循环左移 k 位"""
    k %= NBITS
    return ((h << k) | (h >> (NBITS - k))) & FULL


def flip_yao(h, j):
    """爻变：第 j 爻阴阳互变（j=0 为初爻）"""
    return h ^ (1 << j)


def hamming(a, b):
    return bin(a ^ b).count("1")


def popcount(h):
    return bin(h).count("1")


# --- 文王卦序（通行本）----------------------------------------------------
# (卦名, 上卦, 下卦)
KING_WEN = [
    ("乾", "乾", "乾"), ("坤", "坤", "坤"), ("屯", "坎", "震"), ("蒙", "艮", "坎"),
    ("需", "坎", "乾"), ("讼", "乾", "坎"), ("师", "坤", "坎"), ("比", "坎", "坤"),
    ("小畜", "巽", "乾"), ("履", "乾", "兑"), ("泰", "坤", "乾"), ("否", "乾", "坤"),
    ("同人", "乾", "离"), ("大有", "离", "乾"), ("谦", "坤", "艮"), ("豫", "震", "坤"),
    ("随", "兑", "震"), ("蛊", "艮", "巽"), ("临", "坤", "兑"), ("观", "巽", "坤"),
    ("噬嗑", "离", "震"), ("贲", "艮", "离"), ("剥", "艮", "坤"), ("复", "坤", "震"),
    ("无妄", "乾", "震"), ("大畜", "艮", "乾"), ("颐", "艮", "震"), ("大过", "兑", "巽"),
    ("坎", "坎", "坎"), ("离", "离", "离"), ("咸", "兑", "艮"), ("恒", "震", "巽"),
    ("遁", "乾", "艮"), ("大壮", "震", "乾"), ("晋", "离", "坤"), ("明夷", "坤", "离"),
    ("家人", "巽", "离"), ("睽", "离", "兑"), ("蹇", "坎", "艮"), ("解", "震", "坎"),
    ("损", "艮", "兑"), ("益", "巽", "震"), ("夬", "兑", "乾"), ("姤", "乾", "巽"),
    ("萃", "兑", "坤"), ("升", "坤", "巽"), ("困", "兑", "坎"), ("井", "坎", "巽"),
    ("革", "兑", "离"), ("鼎", "离", "巽"), ("震", "震", "震"), ("艮", "艮", "艮"),
    ("渐", "巽", "艮"), ("归妹", "震", "兑"), ("丰", "震", "离"), ("旅", "离", "艮"),
    ("巽", "巽", "巽"), ("兑", "兑", "兑"), ("涣", "巽", "坎"), ("节", "坎", "兑"),
    ("中孚", "巽", "兑"), ("小过", "震", "艮"), ("既济", "坎", "离"), ("未济", "离", "坎"),
]


def king_wen_codes():
    return [hex_code(u, l) for (_, u, l) in KING_WEN]


def verify_king_wen():
    """
    验证文王卦序的结构定理：
      64 卦分为 32 对，相邻两卦（奇,偶）互为"综"（位反序）或"错"（位取反）。
    返回 dict：每对的关系、综对数、错对数、两者兼有的对数。
    """
    codes = king_wen_codes()
    assert len(set(codes)) == 64, "卦码必须互不相同"
    pairs = []
    n_zong = n_cuo = n_both = 0
    for i in range(0, 64, 2):
        a, b = codes[i], codes[i + 1]
        is_z = (zong(a) == b)
        is_c = (cuo(a) == b)
        assert is_z or is_c, "第 %d/%d 对（%s/%s）既非综也非错" % (
            i + 1, i + 2, KING_WEN[i][0], KING_WEN[i + 1][0])
        if is_z and is_c:
            n_both += 1
        elif is_z:
            n_zong += 1
        else:
            n_cuo += 1
        pairs.append((KING_WEN[i][0], KING_WEN[i + 1][0], a, b, is_z, is_c))
    return {"pairs": pairs, "n_zong_only": n_zong, "n_cuo_only": n_cuo,
            "n_both": n_both, "n_self_zong": sum(1 for c in codes if zong(c) == c)}


# --- 对称群与轨道 ---------------------------------------------------------

def compose(f, g):
    """复合：(f ∘ g)(x) = f(g(x))，f,g 为长度 N 的映射表（N 任意）"""
    return tuple(f[g[x]] for x in range(len(g)))


def closure(gens):
    """由生成元（N 长映射表）生成群的闭包"""
    ident = tuple(range(len(gens[0])))
    seen = {ident}
    frontier = [ident]
    while frontier:
        nxt = []
        for a in frontier:
            for g in gens:
                c = compose(g, a)
                if c not in seen:
                    seen.add(c)
                    nxt.append(c)
        frontier = nxt
    return sorted(seen)


def as_map(fn):
    return tuple(fn(x) for x in range(NS))


# 生成元
G_CUO = as_map(cuo)          # 错
G_ZONG = as_map(zong)        # 综
G_ROT1 = as_map(lambda h: rotl(h, 1))
G_SWAP = as_map(swap_halves)  # = ROT1^3


def group_from(names):
    """按名字取群：'CR' / 'CRS' / 'CRS1'（含全部循环移位 -> D6×Z2）"""
    gens = {"C": G_CUO, "R": G_ZONG, "S": G_SWAP, "1": G_ROT1}
    return closure([gens[c] for c in names])


def orbits(group):
    """群作用下的轨道划分"""
    parent = list(range(NS))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for g in group:
        for x in range(NS):
            ra, rb = find(x), find(g[x])
            if ra != rb:
                parent[ra] = rb
    buckets = {}
    for x in range(NS):
        buckets.setdefault(find(x), []).append(x)
    return list(buckets.values())


def burnside_count(group):
    """Burnside 引理校验轨道数：|X/G| = (1/|G|) sum_g |Fix(g)|"""
    tot = sum(1 for g in group for x in range(NS) if g[x] == x)
    return tot / len(group)


def canonical_and_perm(group):
    """
    对每个状态 s，返回 (canonical, g)：
      canonical = min{ g(s) : g in G }，g 是取到最小值的群元素。
    同时给出 g 的"位位置映射" posmap：posmap[j] = 输入第 j 位在输出中落到的位置。
    """
    info = {}
    for s in range(NS):
        best, bg = None, None
        for g in group:
            v = g[s]
            if best is None or v < best:
                best, bg = v, g
        posmap = [0] * NBITS
        base = bg[0]
        for j in range(NBITS):
            v = bg[1 << j] ^ base
            posmap[j] = v.bit_length() - 1
        info[s] = (best, posmap)
    return info


def orbit_table(group):
    """列出轨道：代表元、大小"""
    obs = orbits(group)
    obs.sort(key=lambda o: (-len(o), o[0]))
    return [(min(o), len(o), sorted(o)) for o in obs]
