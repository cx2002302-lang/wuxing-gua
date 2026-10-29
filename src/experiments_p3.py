# -*- coding: utf-8 -*-
"""
experiments_p3.py —— 自动找群：只给转移数据，机器自己发现对称性

前期阶段证明了抽象极强，但所有实验都有隐含前提：**群是人给的**。
本模块把这一步拿掉。

**判据（事前定死）**
  ① 恢复力：Q_n 上自动法找到的群，收益 ≥ 人工 D_n 的 90%
  ② 发现力：≥1 例在**非刻意对称**环境里发现有效抽象
  ③ kill：只能恢复出平凡群 ⇒ 承认「对称先验必须来自领域知识」，转工具化

**方法：骨干图 + WL refine + 等变检验（纯数据，不看模型）**
  第 1 步  提骨干：每个 (s,a) 取概率最大的后继（P_NOOP/P_PERT 只是包装），
           得到确定性状态转移图。对 Q_n 它就是 n-维超立方体。
  第 2 步  WL refine：用「邻居色序列」迭代染色（1-Weisfeiler-Lehman）。
           自同构必须保持颜色 ⇒ 只需在**同色类内**找映射，
           把 n! 的搜索空间压到可解。
  第 3 步  构造候选：每个色类内，把成员 m 与代表元对换。
  第 4 步  等变检验：equiv_error(π) = max TV(π_#P(·|s,a), P(·|π(s),a'))，
           = 0 才算真自同构（比"骨干图同构"更强：要求含噪声的完整转移也等变）。
  第 5 步  闭包 + 整体复检。

**为什么不用随机对换**：64 个状态里随机对换命中自同构的概率约 1/64²，
4000 个候选中 0 个通过（首版真实踩到）。必须用结构信息压搜索空间。

运行：python src/experiments_p3.py
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from experiments_e1 import (tables, group_dn, orbits_of,   # noqa: E402
                            build_model_n, vi_n, abstraction_loss)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------------------------------------------------------------- 基础工具
def tvd(p, q):
    """两个稀疏分布（dict）的全变差距离"""
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def dist_of(trans, s, a):
    d = {}
    for (p, u, _r) in trans[s][a]:
        d[u] = d.get(u, 0.0) + p
    return d


def equiv_error(trans, pi, n):
    """
    纯数据等变检验：pi 为状态映射表（list），返回 (最大 TV 误差, 检验过的 (s,a) 数）。
    动作像 a' 由「翻转 pi(s) 与 pi(s^(1<<a)) 不同的那位」推得。

    ⚠️ 2026-10-27 追加一道适用域守卫（游戏案例修复）：
    π 诱导出的动作标签 pa 必须**存在**（pa < n_actions），否则 trans[·][pa] 越界
    IndexError。历史全部环境满足 n_actions == n_bits（动作 a = 翻第 a 位，
    n_states = 2^n_bits）⇒ pa ∈ [0, n_bits-1] 恒落在动作域内，守卫永不触发、
    逐位行为不变。n_bits > n_actions 的模型（如 512 = 2^9 态 / 7 动作）上，
    π 若把某个动作位映到第 ≥ n_actions 位，说明该 π 在本口径下**诱导了一个不存在
    的动作** ⇒ 与既有的「不是位置置换」同档**结构性拒绝**（返回 inf），不崩。
    """
    NS = len(pi)
    worst, checked = 0.0, 0
    for s in range(NS):
        for a in range(n):
            ps = pi[s]
            d = pi[s ^ (1 << a)] ^ ps
            if bin(d).count("1") != 1:
                return float("inf"), 0      # 不是位置置换
            pa = d.bit_length() - 1
            if pa >= n:
                return float("inf"), 0      # π 诱导的动作标签不存在（结构性不可用）
            p1 = {pi[u]: v for u, v in dist_of(trans, s, a).items()}
            p2 = dist_of(trans, ps, pa)
            worst = max(worst, tvd(p1, p2))
            checked += 1
    return worst, checked


def closure_perms(gens, NS):
    """由生成元（list 形式映射表）求置换群闭包"""
    ident = list(range(NS))
    seen = {tuple(ident)}
    frontier = [ident]
    while frontier:
        nxt = []
        for a in frontier:
            for g in gens:
                c = [g[a[x]] for x in range(NS)]
                t = tuple(c)
                if t not in seen:
                    seen.add(t)
                    nxt.append(c)
        frontier = nxt
    return [list(t) for t in seen]


# ---------------------------------------------------------------- 骨干图 + WL
def backbone_adj(trans, n):
    """
    骨干图：每个 (s,a) 取概率最大的后继，构成状态转移图。

    ⚠️ 2026-10-16 改为**无向化**（原为单向/有向）。改因是一次真实失败：

    有向版只写 `adj[s].add(后继)`，吸收态（目标态）的出邻接就只剩自环 {s}，
    「谁指向我」这些入边全部丢失 ⇒ 目标态在骨干图里彼此不可区分。
    实测后果（SYS-3 B，目标={位0=位1=1}）：真对称群阶 768，
    有向骨干图让 discover 只返回平凡群（阶 1），**一个真对称都没找到**。
    无向化后 n=6 完全恢复 768。

    安全性（改前已用 `src/_audit_backbone.py` 三点验证）：
      · SYS-3 B  n=6：群阶 1 → 768（= 真群 2·(n-2)!·2^(n-2)）✅ 修复
      · 自动找群 Q_n n=6/8：仍 720 / 40320 ✅ 未破坏
      · SYS-3 A  n=6/8：仍阶 1（无对称系统不谎报）✅ 未引入假阳性
    且无向化只影响**候选生成**，`equiv_error` 的最终裁决一步未松，
    所以不可能把伪自同构放进来。
    """
    NS = len(trans)
    adj = [set() for _ in range(NS)]
    for s in range(NS):
        for a in range(n):
            best = max(trans[s][a], key=lambda x: x[0])
            adj[s].add(best[1])
            adj[best[1]].add(s)      # 无向化：把入边也写进邻接
    return adj


def wl_refine(adj, rounds=None):
    """
    1-Weisfeiler-Lehman 迭代染色，返回每个节点的最终颜色。
    自同构必须保持颜色 ⇒ 只在同色类内搜映射，把搜索空间压下来。
    """
    NS = len(adj)
    if rounds is None:
        rounds = NS
    color = {s: len(adj[s]) for s in range(NS)}
    for _ in range(rounds):
        newc = {}
        for s in range(NS):
            newc[s] = (color[s], tuple(sorted(color[v] for v in adj[s])))
        uniq = {}
        for s in range(NS):
            if newc[s] not in uniq:
                uniq[newc[s]] = len(uniq)
            newc[s] = uniq[newc[s]]
        if len(set(newc.values())) == len(set(color.values())):
            color = newc
            break
        color = newc
    return color


def graph_automorphisms(adj, color, max_gens=64, node_cap=4000):
    """
    回溯搜索保色图自同构，返回生成元列表。

    为什么不能用「色类内对换」：自同构群常常由**非对换**生成
    （如 Q_n 的旋转是 6-循环，倒序是多个对换的乘积），只试对换会全部漏掉
    —— 前两版真实踩到：WL 分类正确、候选全在对换里，0 个通过。

    回溯：按色类分组的顺序，逐个给节点选像（必须是同色、且保邻接的未占用节点）。
    找到的第一个非平凡自同构即可作为生成元；继续搜索直到凑够 max_gens
    或搜索预算用尽。
    """
    NS = len(adj)
    order = sorted(range(NS), key=lambda s: (color[s], len(adj[s])))
    by_color = {}
    for s in range(NS):
        by_color.setdefault(color[s], []).append(s)
    pi = [None] * NS
    used = [False] * NS
    gens = []
    budget = [node_cap]

    def ok_map(s, t):
        # 保邻接：已映射的邻居，其像必须是 t 的邻居
        for v in adj[s]:
            if pi[v] is not None and pi[v] not in adj[t]:
                return False
        # 反向：t 的已映射邻居必须来自 s 的邻居
        for w in adj[t]:
            pv = None
            for u in range(NS):
                if pi[u] == w:
                    pv = u
                    break
            if pv is not None and pv not in adj[s]:
                return False
        return True

    def bt(i):
        if budget[0] <= 0:
            return False
        budget[0] -= 1
        if i == NS:
            if pi != list(range(NS)):
                gens.append(pi[:])
            return len(gens) >= max_gens
        s = order[i]
        for t in by_color[color[s]]:
            if used[t]:
                continue
            if not ok_map(s, t):
                continue
            pi[s] = t
            used[t] = True
            if bt(i + 1):
                return True
            pi[s] = None
            used[t] = False
        return False

    bt(0)
    return gens


def graph_automorphisms_rr(adj, color, n_restarts=40, max_gens=64,
                           node_cap=8000, seed=0):
    """
    多次随机重启的图自同构搜索（第三版）。

    为什么需要随机重启：确定性回溯每次都从同一 order / 同一候选顺序出发，
    会卡在**同一个陪集区域的子群**里出不来。

    ⚠️ 定量口径已于 2026-10-14 修正（见 experiments_restart_scan.py）：
    早期注释称「node_cap 4000→80000 闭包阶都停在 120」，那是把 **max_gens
    （输出上限）截断**误读成了搜索预算不足的结果。受控重测（放开 max_gens）显示：
        node_cap 4000/16000/64000/250000 → 闭包阶 24 / 120 / 720 / 5040
        node_cap 1000000                 → 闭包阶仍 5040（生成元虚增 1000→4003）
    即预算在到达 **5040 = S_7 = S_8 的点稳定子** 之前是有效的，
    只有到这之后才真正停滞（再也跨不到其余 7 个陪集），而随机重启直达 40320。

    修法：每次重启随机打乱「同色类内的候选顺序」与「节点处理顺序」，
    让搜索落在不同陪集上，合并去重后取闭包。
    """
    NS = len(adj)
    rng = random.Random(seed)
    all_gens = []

    for _r in range(n_restarts):
        # 随机化节点处理顺序（同色类内打乱）
        order = list(range(NS))
        rng.shuffle(order)
        order.sort(key=lambda s: color[s])
        by_color = {}
        for s in range(NS):
            by_color.setdefault(color[s], []).append(s)
        for c in by_color:
            rng.shuffle(by_color[c])

        pi = [None] * NS
        used = [False] * NS
        budget = [node_cap]
        found = []

        def ok_map(s, t):
            for v in adj[s]:
                if pi[v] is not None and pi[v] not in adj[t]:
                    return False
            for w in adj[t]:
                pv = None
                for u in range(NS):
                    if pi[u] == w:
                        pv = u
                        break
                if pv is not None and pv not in adj[s]:
                    return False
            return True

        def bt(i):
            if budget[0] <= 0:
                return False
            budget[0] -= 1
            if i == NS:
                if pi != list(range(NS)):
                    found.append(pi[:])
                return len(found) >= 2
            s = order[i]
            for t in by_color[color[s]]:
                if used[t] or not ok_map(s, t):
                    continue
                pi[s], used[t] = t, True
                if bt(i + 1):
                    return True
                pi[s], used[t] = None, False
            return False

        bt(0)
        all_gens.extend(found)
    return all_gens


def involution_automorphisms(adj, color, n_restarts=24, node_cap=60000,
                             max_gens=6, seed=7):
    """
    搜**对合**自同构（π² = id），返回生成元列表。

    ## 为什么需要这个（2026-10-16，一个结构性盲区的修复）
    种子判别实验（`src/_audit_seed.py`）证实：上面的逐点回溯 + 随机重启，
    **结构上产生不了 XOR 平移类对称** —— 喂全部坐标置换种子也只到 1440/92160，
    必须显式喂 XOR 生成元才满。

    根因：回溯是**逐点贪心**构造映射，天然只产出「保位置」类置换；
    XOR 平移是「整体位移」（s -> s^c），要同时决定所有点的像，
    贪心早期选错就永远构造不出。⇒ **不是预算问题，重启也救不了**
    （与「陪集陷阱」是两种不同的病：那个加预算有硬顶，这个是候选根本不生成）。

    ## 修法
    改搜**对合**：π² = id ⟺ 把顶点两两配对，搜索空间从「排列」降到「配对方案」。
    XOR 平移（c≠0）正是无固定点对合，坐标置换群里的对合同样能搜到（不丢原有能力）。
    按色类顺序处理，每个未配对顶点选配偶（同色 + 保邻接），强制 π(w)=v。

    ## 安全性
    只影响**候选生成**；每个候选仍要过 `equiv_error` 完整转移等变检验，
    所以不可能引入伪自同构（实测 16 个候选全过、闭包抽查 0 个不过）。
    """
    import random
    NS = len(adj)
    rng = random.Random(seed)
    order_base = list(range(NS))
    by_color = {}
    for s in range(NS):
        by_color.setdefault(color[s], []).append(s)

    found = []
    for _ in range(n_restarts):
        pi = [None] * NS
        budget = [node_cap]
        rng.shuffle(order_base)
        order = sorted(order_base, key=lambda s: color[s])

        def ok_pair(v, w):
            for x in adj[v]:
                if pi[x] is not None and pi[x] not in adj[w]:
                    return False
            for y in adj[w]:
                px = None
                for u in range(NS):
                    if pi[u] == y:
                        px = u
                        break
                if px is not None and px not in adj[v]:
                    return False
            return True

        def bt(i):
            if budget[0] <= 0:
                return False
            budget[0] -= 1
            while i < NS and pi[order[i]] is not None:
                i += 1
            if i >= NS:
                if pi != list(range(NS)):
                    found.append(pi[:])
                return len(found) >= max_gens
            v = order[i]
            cands = [w for w in by_color[color[v]]
                     if pi[w] is None and w != v and ok_pair(v, w)]
            rng.shuffle(cands)
            for w in cands:
                pi[v], pi[w] = w, v
                if bt(i + 1):
                    return True
                pi[v], pi[w] = None, None
            return False

        bt(0)

    uniq, seen = [], set()
    for g in found:
        t = tuple(g)
        if t not in seen:
            seen.add(t)
            uniq.append(g)
    return uniq


def graph_automorphisms_mrv(adj, color, max_gens=4, budget=200000):
    """
    MRV（最小剩余值）启发式的自同构回溯 —— 治「搜索树指数爆炸」这一种失败模式。

    ## 为什么需要（2026-10-16，第三种失败模式）
    汉诺塔（SYS-4）上实测：S_3 确是骨干图自同构、WL 色类闭合于轨道、
    `ok_map` 对真解一步都没误杀，但固定顺序的回溯在 node_cap 4000 → 2,000,000
    （放大 500 倍）全程找到 **0** 个生成元。实测搜索树规模 **10^46.3**，
    2e6 只覆盖其中 9.7e-41 —— 加预算在本模式下属杯水车薪。

    根因：`ok_map` 只做**局部**剪枝（检查已映射邻居），固定变量顺序让 DFS
    在错误子树里打转。而该实例 155/243 个 depth 其实只有 1 个合法候选
    （约束极强），少数 depth 却有 47 个 —— 先处理强约束变量，弱变量的候选
    会被 used / 邻接约束自然消掉。

    MRV 正是这个思想：每一层动态选「当前合法候选最少」的顶点。
    实测 n=5 汉诺塔 36.7s 找到完整 S_3（6/6 命中），而固定顺序 500 倍预算为 0。

    ## 代价与定位
    每层要重算所有未处理顶点的候选集，开销远大于固定顺序。
    所以**不作为默认路径**，只在 discover 里做 fallback：
    普通搜索 + 对合搜索都没找到非平凡群时，才启用 MRV。
    """
    NS = len(adj)
    by_color = {}
    for s in range(NS):
        by_color.setdefault(color[s], []).append(s)

    pi = [None] * NS
    used = [False] * NS
    inv = [None] * NS          # inv[t] = s 表示 pi[s] = t，供反向查询 O(1)
    cnt = [budget]
    gens = []

    def ok_map(s, t):
        for v in adj[s]:
            if pi[v] is not None and pi[v] not in adj[t]:
                return False
        for w in adj[t]:
            pv = inv[w]        # 原写法是线性扫全表找 pi[u]==w，O(NS)；改为 O(1)
            if pv is not None and pv not in adj[s]:
                return False
        return True

    def bt(remaining):
        if not remaining:
            if pi != list(range(NS)):
                gens.append(pi[:])
            return len(gens) >= max_gens
        if cnt[0] <= 0:
            return False
        cnt[0] -= 1
        # MRV：选合法候选最少的顶点（候选为 0 立即剪枝；为 1 可提前锁定）
        best_s, best_c = None, None
        for s in remaining:
            c = [t for t in by_color[color[s]]
                 if not used[t] and ok_map(s, t)]
            if best_c is None or len(c) < len(best_c):
                best_s, best_c = s, c
                if len(c) <= 1:
                    break
        if not best_c:
            return False
        for t in best_c:
            pi[best_s], used[t], inv[t] = t, True, best_s
            if bt(remaining - {best_s}):
                return True
            pi[best_s], used[t], inv[t] = None, False, None
        return False

    bt(set(range(NS)))
    return gens


def graph_automorphisms_mrv_fast(adj, color, max_gens=4, budget=200000):
    """
    MRV 自同构回溯的**加速版** —— 与 graph_automorphisms_mrv 结果逐元素一致，
    但把「每层重算所有剩余顶点的候选集」改为**增量候选维护**（位掩码）。

    ## 为什么可以等价加速（不变式）
    原版每层对每个剩余顶点 s 重算候选
        C(s) = { t 同色 : 未用 且 ok_map(s, t) }
    ok_map 的两条检查都是**只减不增**的约束：
      正向：已映射邻居 v（pi[v]=t_v）必须满足 t_v ∈ adj[t'']
      反向：t'' 的已映射邻居（inv[w]=s'）必须满足 s' ∈ adj[s]
    用大整数位掩码 cand[s] 维护（第 t 位为 1 ⟺ t 是 s 的当前合法候选）：
      · 初始 cand[s] = 同色类位掩码；
      · 赋值 pi[s']=t 时，对每个剩余 u（无向图 t''∈adj[t] ⟺ t∈adj[t'']）：
          s' ∈ adj[u] ⇒ 新正向约束 t ∈ adj[t''] ⇒ cand[u] &= adj[t] \\ {t}
          s' ∉ adj[u] ⇒ 新反向约束 t ∉ adj[t''] ⇒ cand[u] &= ~(adj[t] ∪ {t})
        （t 已用，两个掩码都已剔除 bit t；used 的剔除随之折叠进更新）
    不变式：对任意剩余 s，cand[s] 的置位集合 == 原版 C(s)。
    证明：每条约束都是单调 AND，且赋值只引入上述两类新约束（其余约束不变），
    初始两者相同（同色类、无已映射点）⇒ 归纳可得始终相同。

    ## 三项加速（对应优化方向 1/2/3）
    1. 增量候选维护：一次赋值只做 O(|remaining|) 次大整数 AND（平均 35 个机器字），
       取代原版每层 O(NS × 类大小 × 度数) 的 ok_map 重算 —— 这是主要瓶颈。
    2. 邻接倒排：adj[t] 预计算为位掩码；原版反向检查要线性扫全表找 pi[u]==w
       （O(NS)），现在 O(1)；ok_map 整体被位运算取代。
    3. 前向检查：候选数 = bit_count()，MRV 扫描 O(1) 取得；候选为 0 的顶点
       在 MRV 选点时立即剪枝（与原版同点剪枝，不改变搜索树）。
    未做 AC-3：前三项已够用；且任何额外剪枝都会改变搜索树与预算消耗，
    有破坏「结果逐元素一致」的风险，故不做。

    ## 语义保持（硬约束）
    MRV 选点规则（set 迭代序、严格小于才更新、首个 ≤1 即停）、候选顺序
    （by_color 即顶点编号升序）、剪枝点、预算计数、单位元排除全部照搬原版
    ⇒ 搜索树逐节点一致 ⇒ 生成元列表逐元素一致（n=5 汉诺塔已断言验证）。

    实测（量级口径）：n=5 汉诺塔 ~20s → ~1s 量级；n=7（2187 状态）
    从「40 分钟未出结果」变为分钟级完成。
    """
    NS = len(adj)
    by_color = {}
    for s in range(NS):
        by_color.setdefault(color[s], []).append(s)

    # ---- 预计算：邻接位掩码 / 色类位掩码（优化方向 2：邻接倒排）----
    adj_mask = [0] * NS
    for s in range(NS):
        m = 0
        for v in adj[s]:
            m |= 1 << v
        adj_mask[s] = m
    color_mask = {}
    for c, members in by_color.items():
        m = 0
        for s in members:
            m |= 1 << s
        color_mask[c] = m
    full = (1 << NS) - 1

    pi = [None] * NS
    cand = [color_mask[color[s]] for s in range(NS)]   # 增量候选（位掩码）
    cnt = [budget]
    gens = []

    def bt(remaining):
        if not remaining:
            if pi != list(range(NS)):
                gens.append(pi[:])
            return len(gens) >= max_gens
        if cnt[0] <= 0:
            return False
        cnt[0] -= 1
        # MRV 选点：与原版同一规则（set 迭代序、严格小于才更新、首个 ≤1 即停）
        best_s, best_n = None, None
        for s in remaining:
            n = cand[s].bit_count()
            if best_n is None or n < best_n:
                best_s, best_n = s, n
                if n <= 1:
                    break
        if best_n == 0:          # 候选为 0：剪枝（原版 not best_c）
            return False
        cs = color[best_s]
        cm = cand[best_s]
        saved = cand[:]          # 撤销快照（大整数不可变，浅拷贝即正确）
        adj_s = adj[best_s]
        for t in by_color[cs]:   # 候选顺序 = 顶点编号升序，与原版一致
            if not (cm >> t) & 1:
                continue
            pi[best_s] = t
            # 增量更新：只做位运算（优化方向 1）
            bit_t = 1 << t
            keep = adj_mask[t] & (full ^ bit_t)        # t 的邻居（去 t）
            drop = full ^ (adj_mask[t] | bit_t)        # 非 t 的邻居（去 t）
            for u in remaining:
                cand[u] &= keep if u in adj_s else drop
            if bt(remaining - {best_s}):
                return True
            cand[:] = saved
            pi[best_s] = None
        return False

    bt(set(range(NS)))
    return gens


# ---------------------------------------------------------------- canonize（可选前置）
def canonical_relabel(adj, variant="min_smallest"):
    """
    规范重编号（canonize）：把邻接表搬到规范编号下。
    返回 (规范编号下的邻接表, 旧→新映射 old2new)，其中 old2new[旧顶点] = 新 id。

    ⚠️ 可选前置：默认不启用，因为会改变历史结果的可比性。

    为什么有用：归因分析证明 ovh 是**实现伪像**——同一个图只换
    顶点编号，ovh 相对极差可达 336.4%；§16 证明 canonize 后该值降到 **0.0%**。
    为什么仍不设默认：canonize 会把历史实例的**自然编号**换掉，而既有文档里的
    ovh / c 全是在自然编号下测的，两者不可比（§16.5：Heawood 的 c 190.48 → 5.95）。
    ⇒ 只在「需要跨实例比较 ovh/c」时显式打开，历史实验一律保持关闭。

    算法不在本文件实现：`canonize` 直接 import 自 `experiments_canonical_search`
    （§16 的规范 WL + 个体化-细化树 + lex-min 证书），本函数只做「搬边 + 出映射」，
    不复制第二份。用**函数内延迟 import** 的原因：那个模块反过来 import 本模块的
    `wl_refine`，放到模块顶层就是循环 import。
    """
    from experiments_canonical_search import canonize     # 延迟：避免循环 import

    NS = len(adj)
    order, _cert, _nodes = canonize([set(a) for a in adj],  # order[新 id] = 旧顶点
                                    variant=variant)
    old2new = [0] * NS
    for new, old in enumerate(order):
        old2new[old] = new
    new_adj = [set() for _ in range(NS)]
    for new in range(NS):
        old = order[new]
        new_adj[new] = {old2new[v] for v in adj[old]}
    return new_adj, old2new


def random_relabels(NS, k, seed=20261025):
    """
    K 个**可复现**的随机重编号（约定 `rho[旧顶点] = 新 id`）。

    固定种子 ⇒ 同一 (NS, k, seed) 每次给出逐条相同的编号序列（并集口径要能复跑）。
    与 `experiments_multi_labeling_union.make_rhos` 同一约定（shuffle 取一个、
    不去重、不排序），故默认种子下的 rnd01.. 与该实验的同名口径是同一批编号。
    """
    rng = random.Random(seed)
    rhos = []
    for _i in range(k):
        rho = list(range(NS))
        rng.shuffle(rho)
        rhos.append(rho)
    return rhos


def _discover_one_labeling(trans, n, adj, back, tol=1e-9, verbose=False,
                           max_gens=48, use_involution=True,
                           use_mrv_fallback=True, equiv_fn=None):
    """
    在**一个编号口径**上跑一次完整 discover 管线，返回该口径的幸存生成元（原编号）。

      adj  : 该口径编号下的骨干图
      back : 该口径下的置换 → 原编号下的置换（plain 口径时为恒等）
      equiv_fn: 自定义等变判据 `pi -> 误差`；None 时用 `equiv_error`（位串口径）

    ⚠️ 判据数据 trans 自始至终是原编号：候选一律先 `back()` 搬回原编号再裁决，
    所以并集里每个生成元都是**在原编号口径下验证过的**（不是"某口径自己说自己对"）。
    """
    NS = len(trans)

    def err(pi):
        return equiv_error(trans, pi, n)[0] if equiv_fn is None else equiv_fn(pi)

    color = wl_refine(adj)
    classes = {}
    for s in range(NS):
        classes.setdefault(color[s], []).append(s)
    if verbose:
        print("      WL 色类大小：%s" % sorted(len(v) for v in classes.values()))

    # 先确定性跑一轮，再随机重启补充（第三版：随机重启是上规模的关键）
    gens = graph_automorphisms(adj, color, max_gens=max_gens)
    n_det = len(gens)
    gens_rr = graph_automorphisms_rr(adj, color, n_restarts=40, seed=7)
    gens = gens + gens_rr
    if verbose:
        print("      骨干图自同构生成元：确定性 %d + 随机重启 %d = %d"
              % (n_det, len(gens_rr), len(gens)))

    # 阶段 2：对合搜索 —— 补 XOR 平移类盲区（详见 involution_automorphisms 文档字符串）
    n_invol = 0
    if use_involution and gens:
        invols = involution_automorphisms(adj, color)
        n_invol = len(invols)
        gens = gens + invols
        if verbose:
            print("      + 对合搜索候选 %d 个（补 XOR 平移类盲区）" % n_invol)

    # 候选一律搬回原编号后再过等变裁决（plain 口径下 back 是恒等，零行为变化）
    gens = [back(g) for g in gens]

    # ⚠️ 不要在这里对 gens 空早退：三路候选全 0 也可能是「搜索树指数爆炸」的
    # 特征（汉诺塔实测：固定顺序 500 倍预算 0 候选，MRV 却能找到完整群）。
    # 故一律往下走到 good 判定与阶段3 MRV fallback。
    good, worst = [], 0.0
    for g in gens:
        e = err(g)
        worst = max(worst, e)
        if e <= tol:
            good.append(g)
    if verbose:
        print("      其中通过完整等变检验 %d 个（最大 TV 误差 %.2e）"
              % (len(good), worst))
    n_mrv = 0
    if not good:
        # 阶段 3：MRV fallback —— 前两条路都没找到非平凡群时启用。
        # 治「搜索树指数爆炸」这一失败模式（详见 graph_automorphisms_mrv 文档）：
        # 解存在、剪枝不误杀、加预算也无效，但 MRV 靠约束排序能走出来。
        if use_mrv_fallback:
            mrv = graph_automorphisms_mrv(adj, color)
            n_mrv = len(mrv)
            if verbose:
                print("      阶段3 MRV fallback：候选 %d 个" % n_mrv)
            for g in mrv:
                gg = back(g)
                if err(gg) <= tol:
                    good.append(gg)
    return {"good": good, "n_gens": len(gens), "n_classes": len(classes),
            "n_involution": n_invol, "n_mrv": n_mrv, "worst": worst}


def discover(trans, n, tol=1e-9, verbose=False, max_gens=48,
             use_involution=True, use_mrv_fallback=True, canonize=False,
             labelings="plain", n_rand=3, seed=20261025, equiv_fn=None):
    """
    自动找群。返回 (群[list of perm], 诊断 dict)。

    canonize（默认 False，可选前置，见 `canonical_relabel` 的文档）：
      True 时三路图搜索（确定性 / 随机重启 / 对合 / MRV）都在**规范重编号后的骨干图**
      上跑——搜索器的全部 id 依赖（变量序 = id 序、候选枚举序 = id 序）因此作用在
      规范编号上；候选生成元随即搬回原编号，再交给 `equiv_error`。
      **判据数据 trans 自始至终是原编号**：`equiv_error` 的位串动作口径
      （动作 a = 翻转第 a 位）依赖状态编号，重排 trans 会破坏它。
      返回值与 diag 的群一律是原编号下的群，可直接与不 canonize 的结果对照。
      diag 仅在 canonize=True 时附 `canonized: true`；默认关闭时不写该字段，
      以保证历史输出（`experiments_p3.json`）逐字不变。

    labelings（默认 **'plain'**）—— 编号口径模式，依据并集策略预注册：
      'plain' 只跑自然编号（本次改动前的默认行为，**逐字不变**）；
      'canon' 只跑 canonize 口径（与 `canonize=True` 同一口径）；
      'union' 跑 plain + canon + `n_rand` 个随机编号（默认 3），
             各口径幸存生成元**取并集后闭包**。
      ⚠️ 默认必须是 'plain'：并集 = 跑 (2+K) 遍搜索，会拖慢所有实验；
         想用并集要显式传 `labelings='union'`。
      ⚠️ 并集**不是**完备性保证，只是"把各口径的长处都收下"（见文档 §5 边界）。
      随机编号由 `seed` 固定（默认 20261025）⇒ 可复现；`n_rand=0` 即 plain∪canon。
      `labelings != 'plain'` 与 `canonize=True` 互斥（后者是前者的旧写法），同传报错。

    equiv_fn：自定义等变判据 `pi -> 误差`，None 时用 `equiv_error`。
      SYS-1 这类「动作标签随位置一起换」的场景需传自己的联合判据
      （`experiments_sys1.equiv_error_joint` 经 `_induced_sigma`），
      否则 `equiv_error` 的位串口径（动作 a = 翻第 a 位）会把它判成平凡群。

    diag 的新字段（**仅非 plain 口径时**附加，以保证 plain 的 diag 与历史逐字一致）：
      `labelings`、`per_labeling_orders`（各口径各自的闭包阶）、`union_order`。
    """
    NS = len(trans)
    if labelings not in ("plain", "canon", "union"):
        raise ValueError("labelings 必须是 'plain'/'canon'/'union'，收到 %r"
                         % (labelings,))
    if labelings != "plain" and canonize:
        raise ValueError("labelings=%r 已含 canonize 语义，不要再传 canonize=True"
                         % (labelings,))
    # 旧写法 canonize=True == 只跑 canon 口径（同一条代码路径，不留第二份）
    mode = "canon" if canonize else labelings
    adj0 = backbone_adj(trans, n)

    # ---- 口径清单 [(tag, adj(该口径编号), back(该口径置换 -> 原编号置换))] ----
    def _plain():
        return adj0, (lambda pi: pi)

    def _canon():
        adj, old2new = canonical_relabel(adj0)
        new2old = [0] * NS
        for old, new in enumerate(old2new):
            new2old[new] = old
        return adj, (lambda pi, o2n=old2new, n2o=new2old:
                     [n2o[pi[o2n[s]]] for s in range(NS)])

    if mode == "plain":
        plan = [("plain", _plain())]
    elif mode == "canon":
        plan = [("canon", _canon())]
    else:
        plan = [("plain", _plain()), ("canon", _canon())]
        for i, rho in enumerate(random_relabels(NS, n_rand, seed)):
            new2old = [0] * NS
            for old, new in enumerate(rho):
                new2old[new] = old
            adj_r = [set() for _ in range(NS)]        # rho[旧] = 新
            for old in range(NS):
                adj_r[rho[old]] = {rho[v] for v in adj0[old]}
            plan.append(("rnd%02d" % (i + 1),
                         (adj_r, (lambda pi, r=rho, n2o=new2old:
                                  [n2o[pi[r[s]]] for s in range(NS)]))))

    runs = []
    for tag, (adj, back) in plan:
        if verbose and len(plan) > 1:
            print("      [口径 %s]" % tag)
        runs.append((tag, _discover_one_labeling(
            trans, n, adj, back, tol=tol, verbose=verbose, max_gens=max_gens,
            use_involution=use_involution, use_mrv_fallback=use_mrv_fallback,
            equiv_fn=equiv_fn)))

    good = [g for _t, r in runs for g in r["good"]]
    n_gens = sum(r["n_gens"] for _t, r in runs)
    n_invol = sum(r["n_involution"] for _t, r in runs)
    n_mrv = sum(r["n_mrv"] for _t, r in runs)
    n_classes = runs[0][1]["n_classes"]
    worst = max(r["worst"] for _t, r in runs) if runs else 0.0
    is_canon = bool(mode == "canon")

    def _closure_order(gs):
        return len(closure_perms(gs, NS)) if gs else 1

    if not good:
        d = {"n_gens": n_gens, "n_pass": 0, "n_classes": n_classes,
             "worst": worst, "n_involution": n_invol, "n_mrv": n_mrv}
        if is_canon:
            d["canonized"] = True
        if labelings != "plain":
            d["labelings"] = labelings
            d["per_labeling_orders"] = {t: 1 for t, _r in runs}
            d["union_order"] = 1
        return [list(range(NS))], d

    # ---------------------------------------------------------------- 闭包 + 复检
    # 原写法只复检闭包里前 128 个元素 —— 群大时（S8=40320）等于没验完，
    # 且 worst2 算了也不用（不过滤、不报警）。这是 2026-10-14 审计记下的技术债。
    #
    # 正确的修法不是"把 128 改成全量"（40320 × 全转移等变检验太慢），
    # 而是用数学：**自同构关于复合封闭** ——
    #   若 π1、π2 都保持转移（equiv_error=0），则 π1∘π2 必然也保持。
    # 所以只要生成元全过等变，闭包内所有元素**必然**等变，逐元素复检是多余的。
    #
    # 但"多余"不等于"不该做"：仍保留**哨兵抽样**复检，用来抓
    # `closure_perms` 自身实现错误（复合顺序写反、漏元素等）。
    # 与原版的区别：哨兵结果现在会**参与判定**，失败即显式报警，不再静默通过。
    G = closure_perms(good, NS)
    sample = G[:64]
    if len(G) > 192:
        mid = len(G) // 2
        sample = sample + G[mid:mid + 64] + G[-32:]
    def err(pi):
        return equiv_error(trans, pi, n)[0] if equiv_fn is None else equiv_fn(pi)

    worst2 = 0.0
    for g in sample:
        e = err(g)
        worst2 = max(worst2, e)
    sentinel_ok = worst2 <= tol
    diag = {"n_gens": n_gens, "n_pass": len(good), "order": len(G),
            "worst_equiv": worst2, "sentinel_ok": sentinel_ok,
            "sentinel_n": len(sample), "n_classes": n_classes,
            "n_involution": n_invol}
    if is_canon:
        diag["canonized"] = True
    if labelings != "plain":
        diag["labelings"] = labelings
        diag["per_labeling_orders"] = {t: _closure_order(r["good"])
                                       for t, r in runs}
        diag["union_order"] = len(G)
    return G, diag


# ---------------------------------------------------------------- 主流程
def main():
    print("=" * 96)
    print("自动找群：只给转移数据，机器自己发现对称性")
    print("  方法：骨干图 -> WL refine 压搜索空间 -> 等变检验 -> 闭包")
    print("=" * 96)
    out = {}

    # ---------- ① 恢复力 ----------
    print("\n  [1] 恢复力：Q_n（目标全阳）上，自动群 vs 人工 D_n")
    rec = []
    for n in (6, 8):
        NS = 1 << n
        goals = {NS - 1}
        trans = build_model_n(n, goals)
        Gd = group_dn(n)
        od = orbits_of(Gd, NS)
        Gauto, diag = discover(trans, n, verbose=True)
        oa = orbits_of(Gauto, NS)
        rec.append({"n": n, "auto_order": len(Gauto), "auto_orbits": len(oa),
                    "manual_order": len(Gd), "manual_orbits": len(od),
                    "diag": diag})
        print("      n=%d：自动群 |G|=%d、轨道 %d（压缩 %.2f×）｜ 人工 D_n |G|=%d、轨道 %d（压缩 %.2f×）"
              % (n, len(Gauto), len(oa), NS / len(oa),
                 len(Gd), len(od), NS / len(od)))
    out["recovery"] = rec

    # ---------- ② 发现力 ----------
    print("\n  [2] 发现力：目标改为非 D_n 不动点（popcount=3 的状态）")
    n = 6
    NS = 1 << n
    goals = {0b000111}
    trans = build_model_n(n, goals)
    Gd = group_dn(n)
    od = orbits_of(Gd, NS)
    V, _ = vi_n(trans, n, NS)
    l_manual = abstraction_loss(V, od, NS)
    Gauto, diag = discover(trans, n, verbose=True)
    oa = orbits_of(Gauto, NS)
    l_auto = abstraction_loss(V, oa, NS)

    # ⚠️ 判据修正（2026-10-14 审计发现原写法有假阳性）：
    # 原判据 `len(oa) < len(od) or l_auto[0] < l_manual[0]` 会被**平凡群**骗过 ——
    # 平凡群(|G|=1) 每个状态自成轨道 ⇒ V* 极差恒为 0（"无损"），
    # 但它压缩比 = 1.00×，**根本不是抽象**，却被判 found_new=True。
    # 与早期规划结论「发现力 ❌ 未达成（返回平凡群）」长期矛盾，故修正为：
    #   ① 群非平凡(|G|>1) ② 真比人工群压得多 ③ 抽象本身无损
    TOL_LOSS = 1e-9
    found_new = bool(len(Gauto) > 1
                     and len(oa) < len(od)
                     and l_auto[0] <= TOL_LOSS)
    print("      判据复核：|G|=%d(>1? %s)｜轨道 %d < %d? %s｜无损? %s ⇒ found_new=%s"
          % (len(Gauto), len(Gauto) > 1, len(oa), len(od), len(oa) < len(od),
             l_auto[0] <= TOL_LOSS, found_new))
    print("      人工 D_n：轨道 %d，V* 极差 %.6f（%s）"
          % (len(od), l_manual[0], "精确" if l_manual[0] < 1e-9 else "有损"))
    print("      自动群  ：轨道 %d，V* 极差 %.6f（%s）"
          % (len(oa), l_auto[0], "精确" if l_auto[0] < 1e-9 else "有损"))
    print("      ⇒ %s" % ("发现了人工群之外的有效抽象 ✓" if found_new
                          else "未能超过人工群"))
    out["discovery"] = {"manual_orbits": len(od), "manual_loss": l_manual[0],
                        "auto_orbits": len(oa), "auto_loss": l_auto[0],
                        "auto_order": len(Gauto), "found_new": found_new,
                        "diag": diag}

    with open(os.path.join(ROOT, "experiments_p3.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\n结果已写入 experiments_p3.json")


if __name__ == "__main__":
    main()
