# -*- coding: utf-8 -*-
"""
experiments_gua64_aut.py —— 六十四卦转移系统真群定论

【问题】experiments_gua64.json 给出的 64 卦转移系统（状态=6 爻位串、动作=错/综/互、
假设奖励=上卦后天五行标量）上，机器群（discover 单次）294,912 阶、并集群
（discover 生成元 ∪ {错,综}）589,824 阶都只是「Aut(转移系统)」的下界。
本脚本用结构分割 + 精确回溯穷举，把真群从「下界」做成 ground truth。

【三个口径，全部精确计数】（预注册口径与 json 口径不完全一致，如实分列）
  soft        : Aut(无标签后继图 D)，D 的边集 E = {(s, δ_a(s))}（动作标签不区分）。
                这正是 experiments_gua64.py::equiv_error_gua 的等变语义
                （∀(s,a): π(δ_a(s)) = δ_b(π(s)) 对某个 b），机器群/并集群数字属于此口径。
  strict      : 保动作标签：π∘δ_a = δ_a∘π 对 a=错/综/互 分别成立（预注册「保动作标签」
                的字面读法）。并集群生成元中有不满足者，589,824 对此口径不是下界，
                真实下界由并集内 strict 子集给出（本脚本全量扫描定量）。
  *_rw        : 再加保奖励 f(π(s)) = f(s)（预注册「保奖励」）。
                错卦把坤土4↔乾金0、离火3↔坎水2 翻转，含错卦的群不可能保奖励——
                这是 experiments_gua64.json cheap_check 双拒答的定量版。

【方法】（结构分割先于穷举；不依赖任何自写 Schreier-Sims，全部用显式闭包对拍）
  1) 无标签图 D 的弱连通分量是 Aut 不变量 ⟹ |Aut| = Π 分量自同构群阶之积
     （两分量去重出边数不同 ⟹ 不同构 ⟹ 无分量互换因子，纯直积）。
  2) 每分量内：静态 WL 染色先切分，再回溯穷举：候选按 WL 色/奖励/一致性过滤
     （strict 侧对单射动作做强制造传），叶点全量验证。数学完备性：所有过滤
     条件都是自同构的必要条件，每个自同构对应唯一搜索路径 ⟹ 叶数 = |Aut|。
  3) 交叉验证（全部机器可查）：
     a) 每分量 ⟨全部叶⟩ 显式闭包阶 == 叶数（⟨叶⟩⊇叶 且同阶 ⟹ 叶集=子群，闭包 0 失败）；
     b) 闭包抽查：叶集内随机 2000 对乘积仍在叶集；
     c) discover 重跑（seed=7 确定性）重构机器群/并集群，显式闭包阶必须 =
        experiments_gua64.json 的 294,912 / 589,824；
     d) 并集群生成元逐一分量限制后哈希查表 ∈ 对应叶群（直积成员检验），
        且 |并集群| = |Aut_soft| ⟹ 并集群 = Aut_soft（outcome a 时）；
     e) 并集群全量扫描：strict / 保奖励 / strict∧保奖励 元素计数，
        与对应口径 |Aut| 相等性检验。

运行：python -X utf8 src/experiments_gua64_aut.py
输出：experiments_gua64_aut.json（项目根）+ 终端人话摘要
"""
import json
import os
import random
import sys
import time
from collections import Counter, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from experiments_gua64 import build_gua64, discover_gua, WUXING   # noqa: E402
from experiments_p3 import closure_perms                          # noqa: E402

NS = 64
N_ACT = 3

# ---------------------------------------------------------------- 转移系统（口径同 experiments_gua64.py）
trans, actions, sigma, tau = build_gua64()
nu = actions[2]
ACTS = [sigma, tau, nu]
ACT_NAMES = ["cuo(错卦)", "zong(综卦)", "hu(互卦)"]


def reward(u):
    """假设奖励：上卦后天五行标量（金0木1水2火3土4），同 experiments_gua64.py。"""
    return WUXING[(u >> 3) & 7]


# ---------------------------------------------------------------- 显式闭包（bytes，确定性 BFS）
def closure_bytes(gens, n):
    """⟨gens⟩ 的全部元素（bytes 长度 n）。单向右乘 BFS：
    从 {id} 出发反复乘生成元得到生成半群；有限群中生成半群 = 生成子群。"""
    ident = bytes(range(n))
    gs = [bytes(g) for g in gens if bytes(g) != ident]
    S = {ident}
    frontier = [ident]
    while frontier:
        nxt = []
        for x in frontier:
            for g in gs:
                y = bytes(g[x[i]] for i in range(n))
                if y not in S:
                    S.add(y)
                    nxt.append(y)
        frontier = nxt
    return S


def restrict(g, states, pos):
    """全 64 态置换在分量 states（全局编号列表）上的限制（局部 bytes：
    局部下标 i ↦ g[states[i]] 在分量内的局部下标）。"""
    return bytes(pos[g[states[i]]] for i in range(len(states)))


# ---------------------------------------------------------------- 图结构
OUT = [tuple(sorted({sigma[s], tau[s], nu[s]})) for s in range(NS)]
OUTSET = [set(o) for o in OUT]
UND = [[] for _ in range(NS)]
for s in range(NS):
    for y in OUT[s]:
        UND[s].append(y)
        UND[y].append(s)
UND = [sorted(set(v)) for v in UND]


def weak_components():
    comps, seen = [], [False] * NS
    for s in range(NS):
        if seen[s]:
            continue
        c, q = [], deque([s])
        seen[s] = True
        while q:
            x = q.popleft()
            c.append(x)
            for y in UND[x]:
                if not seen[y]:
                    seen[y] = True
                    q.append(y)
        comps.append(sorted(c))
    return comps


# ---------------------------------------------------------------- 静态 WL 染色
IN = [[] for _ in range(NS)]
for s in range(NS):
    for y in OUT[s]:
        IN[y].append(s)
IN = [tuple(sorted(set(v))) for v in IN]


def wl_strict(initial):
    """逐动作后继色（保标签口径的不变量细化）。"""
    col = list(initial)
    while True:
        sig, new = {}, [0] * NS
        for s in range(NS):
            key = (col[s], col[sigma[s]], col[tau[s]], col[nu[s]])
            sig.setdefault(key, len(sig))
            new[s] = sig[key]
        if len(set(new)) == len(set(col)):
            return col
        col = new


def wl_soft(initial):
    """无标签出/入邻域色（soft 口径的不变量细化）。"""
    col = list(initial)
    while True:
        sig, new = {}, [0] * NS
        for s in range(NS):
            key = (col[s], tuple(sorted({col[y] for y in OUT[s]})),
                   tuple(sorted({col[y] for y in IN[s]})))
            sig.setdefault(key, len(sig))
            new[s] = sig[key]
        if len(set(new)) == len(set(col)):
            return col
        col = new


# ---------------------------------------------------------------- 每分量精确回溯
def search_component(kind, states, col_global, use_reward):
    """单分量 |Aut| 精确计数。kind: 'strict'|'soft'。
    返回 (叶数, 节点数, 全部叶置换 list[bytes 局部])。
    完备性：候选过滤（WL 色∧分量∧奖励∧一致性）均为自同构必要条件，
    每个自同构对应唯一路径 ⟹ 叶数 = |Aut(分量)| 精确。"""
    states = list(states)
    n = len(states)
    col = [col_global[s] for s in states]
    rwd = [reward(s) for s in states]
    if kind == "soft":
        pos = {s: i for i, s in enumerate(states)}
        outl = [[pos[y] for y in OUT[s]] for s in states]
        outm = [0] * n
        for i in range(n):
            m = 0
            for y in outl[i]:
                m |= 1 << y
            outm[i] = m
    else:
        pos = {s: i for i, s in enumerate(states)}
        act_local = [[pos[a[s]] for s in states] for a in ACTS]
        nu_local = act_local[2]
        nu_pre_local = [[] for _ in range(n)]
        for i in range(n):
            nu_pre_local[nu_local[i]].append(i)

    img = [-1] * n
    used = [False] * n
    stats = {"leaves": 0, "nodes": 0}
    leaves_list = []

    def leaf_verify(pi):
        if kind == "strict":
            for k in range(3):
                al = act_local[k]
                for i in range(n):
                    if pi[al[i]] != al[pi[i]]:
                        return False
        else:
            # π(E)⊆E 逐边查；π 单射 ⟹ |π(E)|=|E| ⟹ π(E)=E
            for i in range(n):
                wi = outm[pi[i]]
                for j in outl[i]:
                    if not (wi >> pi[j]) & 1:
                        return False
        if use_reward:
            for i in range(n):
                if rwd[pi[i]] != rwd[i]:
                    return False
        return True

    def consistent(i, c):
        if kind == "strict":
            for k in range(3):
                al = act_local[k]
                w = img[al[i]]
                if w != -1 and al[c] != w:
                    return False
            # 互卦非单射反向：z 满足 ν(z)=s_i 且已赋值 ⟹ ν(π(z)) == c
            for z in nu_pre_local[i]:
                wz = img[z]
                if wz != -1 and nu_local[wz] != c:
                    return False
            return True
        for j in range(n):
            w = img[j]
            if w == -1:
                continue
            # (j,i)∈E ⟺ (w,c)∈E；(i,j)∈E ⟺ (c,w)∈E
            if ((outm[j] >> i) & 1) != ((outm[w] >> c) & 1):
                return False
            if ((outm[i] >> j) & 1) != ((outm[c] >> w) & 1):
                return False
        return True

    def rec():
        stats["nodes"] += 1
        best_i, best_c = -1, None
        for i in range(n):
            if img[i] != -1:
                continue
            cands = []
            ci = col[i]
            ri = rwd[i]
            for c in range(n):
                if used[c] or col[c] != ci:
                    continue
                if use_reward and rwd[c] != ri:
                    continue
                if consistent(i, c):
                    cands.append(c)
            if best_c is None or len(cands) < len(best_c):
                best_i, best_c = i, cands
                if not cands:
                    return
                if len(cands) == 1:
                    break
        if best_i == -1:
            pi = bytes(img)
            assert leaf_verify(pi), "叶点验证失败（搜索一致性 bug）"
            stats["leaves"] += 1
            leaves_list.append(pi)
            return
        for c in best_c:
            new_assigned = []
            ok = True
            img[best_i] = c
            used[c] = True
            new_assigned.append((best_i, c))
            if kind == "strict":
                q = deque([(best_i, c)])
                while ok and q:
                    i1, c1 = q.popleft()
                    for k in range(3):
                        al = act_local[k]
                        t, w = al[i1], al[c1]
                        if img[t] == -1:
                            if used[w]:
                                ok = False
                                break
                            img[t] = w
                            used[w] = True
                            new_assigned.append((t, w))
                            q.append((t, w))
                        elif img[t] != w:
                            ok = False
                            break
                    if ok:
                        for z in nu_pre_local[i1]:
                            wz = img[z]
                            if wz != -1 and nu_local[wz] != c1:
                                ok = False
                                break
                if ok:
                    rec()
            else:
                rec()
            for (sp, cp) in reversed(new_assigned):
                img[sp] = -1
                used[cp] = False
        return

    rec()
    return stats["leaves"], stats["nodes"], leaves_list


# ---------------------------------------------------------------- 判定谓词（独立实现）
def soft_ok(g):
    """discover 等变语义的独立实现：∀(s,a): g[δ_a(s)] ∈ {δ_b(g[s]): b}。"""
    for s in range(NS):
        gt = OUTSET[g[s]]
        for a in ACTS:
            if g[a[s]] not in gt:
                return False
    return True


def strict_ok(g):
    return all(g[a[s]] == a[g[s]] for s in range(NS) for a in ACTS)


def rw_ok(g):
    return all(reward(g[s]) == reward(s) for s in range(NS))


# ---------------------------------------------------------------- 主流程
def main():
    t_total = time.time()
    print("=" * 96)
    print("六十四卦真群定论：结构分割 + 精确回溯穷举，三口径全算")
    print("  口径：soft=无标签后继图 Aut（discover/并集群口径）；strict=保动作标签；")
    print("        *_rw=再加保奖励 f(π(s))==f(s)（金0木1水2火3土4，上卦后天五行）")
    print("=" * 96)

    checks = []   # 逐条交叉 assert 记录

    def check(name, ok, got, expect):
        checks.append({"name": name, "ok": bool(ok), "got": got, "expect": expect})
        print("  [assert] %-56s %s（实测 %s / 期望 %s）"
              % (name, "PASS" if ok else "FAIL", got, expect))
        if not ok:
            raise AssertionError("交叉 assert 失败：%s" % name)

    # ---------- 0. 结构自证（每个不变量进判据前先自证） ----------
    assert all(sigma[sigma[x]] == x for x in range(NS)), "错卦非对合"
    assert all(tau[tau[x]] == x for x in range(NS)), "综卦非对合"
    assert all(sigma[tau[x]] == tau[sigma[x]] for x in range(NS)), "错综不交换"
    assert all(tau[nu[x]] == nu[tau[x]] for x in range(NS)), "综互不交换"
    assert all(sigma[nu[x]] == nu[sigma[x]] for x in range(NS)), "错互不交换"
    imgset = set(nu)
    Jset = set(nu[y] for y in imgset)
    assert len(imgset) == 16 and len(Jset) == 4
    assert all(1 <= len(OUT[s]) <= 3 for s in range(NS))
    sigma_cert = next(s for s in range(NS) if reward(sigma[s]) != reward(s))
    tau_certs = [s for s in range(NS) if reward(tau[s]) != reward(s)]
    print("[0] 结构自证：错/综对合、两两交换、互像集 16、交替集 4；")
    print("    奖励证书：σ 在 s=%d 处 reward %d→%d；τ 在 %d/64 个状态挪动奖励"
          % (sigma_cert, reward(sigma_cert), reward(sigma[sigma_cert]), len(tau_certs)))

    # ---------- 1. 分量分解 ----------
    comps = weak_components()
    comp_edge_cnt = [len({(s, y) for s in c for y in OUT[s]}) for c in comps]
    print("[1] 无标签图 D 弱分量：%d 个，尺寸 %s，去重出边数 %s"
          % (len(comps), [len(c) for c in comps], comp_edge_cnt))
    check("分量去重出边数两两不同 ⇒ 不同构 ⇒ 无分量互换因子",
          len(set(comp_edge_cnt)) == len(comps), comp_edge_cnt, "两两不同")
    comp_of = {}
    for i, c in enumerate(comps):
        for x in c:
            comp_of[x] = i
    for i, c in enumerate(comps):
        assert all(comp_of[a[s]] == i for s in c for a in ACTS), "分量对动作不封闭"

    # ---------- 2. WL 稳定分割（口径各一套；奖励版各一套） ----------
    inI = [1 if x in imgset else 0 for x in range(NS)]
    col_soft = wl_soft([0] * NS)
    col_strict = wl_strict([(inI[x],) for x in range(NS)])
    col_soft_rw = wl_soft([reward(x) for x in range(NS)])
    col_strict_rw = wl_strict([(reward(x), inI[x]) for x in range(NS)])
    wl_info = {
        "soft": {"n_blocks": len(set(col_soft)),
                 "sizes": sorted(Counter(col_soft).values())},
        "strict": {"n_blocks": len(set(col_strict)),
                   "sizes": sorted(Counter(col_strict).values())},
        "soft_rw": {"n_blocks": len(set(col_soft_rw)),
                    "sizes": sorted(Counter(col_soft_rw).values())},
        "strict_rw": {"n_blocks": len(set(col_strict_rw)),
                      "sizes": sorted(Counter(col_strict_rw).values())},
    }
    print("[2] WL 稳定块数：soft=%d 尺寸%s | strict=%d 尺寸%s"
          % (wl_info["soft"]["n_blocks"], wl_info["soft"]["sizes"],
             wl_info["strict"]["n_blocks"], wl_info["strict"]["sizes"]))
    print("    加奖励后：soft_rw=%d 尺寸%s | strict_rw=%d 尺寸%s"
          % (wl_info["soft_rw"]["n_blocks"], wl_info["soft_rw"]["sizes"],
             wl_info["strict_rw"]["n_blocks"], wl_info["strict_rw"]["sizes"]))

    # ---------- 3. discover 重跑（确定性 seed=7）+ 两群显式闭包重构 ----------
    print("[3] discover 重跑（seed=7，与 experiments_gua64.json 同默认参数）…")
    t0 = time.time()
    M, diag = discover_gua(trans, N_ACT, verbose=False)
    good = [tuple(g) for g in diag["good_gens"]]
    t_disc = time.time() - t0
    print("    discover 生成元 %d 个（%.1fs）" % (len(good), t_disc))
    union_gens = good + [tuple(sigma), tuple(tau)]

    t0 = time.time()
    Mset = closure_bytes(good, NS)
    o_machine = len(Mset)
    print("    机器群显式闭包 |M| = %d（%.1fs）" % (o_machine, time.time() - t0))
    check("机器群阶 = experiments_gua64.json auto_group.order",
          o_machine == 294912, o_machine, 294912)

    t0 = time.time()
    Uset = closure_bytes(union_gens, NS)
    o_union = len(Uset)
    print("    并集群显式闭包 |U| = %d（%.1fs）" % (o_union, time.time() - t0))
    check("并集群阶 = experiments_gua64.json comparison.union_group_order",
          o_union == 589824, o_union, 589824)
    check("机器群生成元 ∈ 并集群（生成关系平凡）",
          all(bytes(g) in Uset for g in good), True, True)

    # ---------- 4. 四口径每分量精确计数 ----------
    rng = random.Random(11)
    results = {}
    leafsets = {}     # kind -> [每分量叶集（局部 bytes）]
    for kind, col_g, rw in [("soft", col_soft, False), ("strict", col_strict, False),
                            ("soft_rw", col_soft_rw, True),
                            ("strict_rw", col_strict_rw, True)]:
        base_kind = "strict" if kind.startswith("strict") else "soft"
        tot, nodes_tot = 1, 0
        per_comp = []
        leafsets[kind] = []
        for i, c in enumerate(comps):
            t0 = time.time()
            lv, nd, leaves_list = search_component(base_kind, c, col_g, rw)
            n_c = len(c)
            # 显式闭包验证：⟨全部叶⟩ 阶 == 叶数 ⟹ 叶集本身是群（闭包 0 失败）
            leaf_closure = closure_bytes(leaves_list, n_c)
            check("%s C%d：⟨全部叶⟩显式闭包阶 == 叶数" % (kind, i),
                  len(leaf_closure) == lv, len(leaf_closure), lv)
            # 闭包封闭性抽查：随机 2000 对乘积仍在叶集（0 失败）
            leafset = set(leaves_list)
            n_pair = 2000
            viol = 0
            for _ in range(n_pair):
                a = leaves_list[rng.randrange(lv)]
                b = leaves_list[rng.randrange(lv)]
                if bytes(a[b[x]] for x in range(n_c)) not in leafset:
                    viol += 1
                    break
            check("%s C%d：闭包抽查 %d 对乘积 0 失败" % (kind, i, n_pair),
                  viol == 0, viol, 0)
            # 贪心小生成集（叶集已是群，贪心必张成全群；仅记录用）
            ident_c = bytes(range(n_c))
            gset = {ident_c}
            gens = []
            for g in leaves_list:
                if g in gset:
                    continue
                gens.append(g)
                frontier = [g]
                while frontier:
                    nxt = []
                    for x in frontier:
                        for h in gens:
                            y = bytes(h[x[k]] for k in range(n_c))
                            if y not in gset:
                                gset.add(y)
                                nxt.append(y)
                    frontier = nxt
                if len(gset) == lv:
                    break
            assert len(gset) == lv, "贪心生成集未张成全群"
            per_comp.append({"component": i, "size": n_c, "order": lv,
                             "nodes": nd, "sec": time.time() - t0,
                             "n_gens": len(gens)})
            leafsets[kind].append(leafset)
            tot *= lv
            nodes_tot += nd
            print("    %-10s C%d（%d 态）：|Aut|=%d（闭包验证 %d，生成元 %d，%.1fs）"
                  % (kind, i, n_c, lv, len(leaf_closure), len(gens),
                     time.time() - t0))
        results[kind] = {"order": tot, "per_component": per_comp,
                         "nodes": nodes_tot}
        print("    ⇒ |Aut_%s| = Π 分量 = %d" % (kind, tot))

    # ---------- 5. 与机器群/并集群的包含关系（直积成员检验，哈希查表） ----------
    gens_soft = sum(1 for g in union_gens if soft_ok(g))
    gens_strict = sum(1 for g in union_gens if strict_ok(g))
    print("[5] 并集群 %d 个生成元：独立实现 soft 全量判定通过 %d，strict 通过 %d"
          % (len(union_gens), gens_soft, gens_strict))
    check("并集群生成元全部通过 soft 全量判定（独立实现）",
          gens_soft == len(union_gens), gens_soft, len(union_gens))

    comp_pos = [{s: i for i, s in enumerate(c)} for c in comps]

    def member_of_product(kind, g):
        """g 是否 ∈ Π 分量叶群：先验地要求 g 保分量，再逐分量限制查表。"""
        for i, c in enumerate(comps):
            if {g[x] for x in c} != set(c):
                return False
            if restrict(g, c, comp_pos[i]) not in leafsets[kind][i]:
                return False
        return True

    memb_soft = [g for g in union_gens if member_of_product("soft", g)]
    check("并集群生成元全部 ∈ Aut_soft（直积分量限制查表）",
          len(memb_soft) == len(union_gens), len(memb_soft), len(union_gens))
    strict_gens = [g for g in union_gens if strict_ok(g)]
    memb_strict = [g for g in union_gens if member_of_product("strict", g)]
    check("并集群 strict 生成元 ∈ Aut_strict；非 strict 生成元 ∉ Aut_strict",
          len(memb_strict) == len(strict_gens), len(memb_strict), len(strict_gens))
    check("机器群生成元 ∈ Aut_soft", all(member_of_product("soft", g) for g in good),
          True, True)
    check("机器群阶 ≤ |Aut_soft|", o_machine <= results["soft"]["order"],
          o_machine, "<= %d" % results["soft"]["order"])
    check("并集群阶 ≤ |Aut_soft|", o_union <= results["soft"]["order"],
          o_union, "<= %d" % results["soft"]["order"])

    # ---------- 6. 并集群全量扫描：strict / 奖励保持元素计数（口径差异定量） ----------
    print("[6] 并集群全量 %d 元素扫描（口径差异定量）…" % o_union)
    t0 = time.time()
    n_strict = n_rw = n_strict_rw = 0
    for gb in Uset:
        g = list(gb)
        so = strict_ok(g)
        ro = rw_ok(g)
        if so:
            n_strict += 1
        if ro:
            n_rw += 1
        if so and ro:
            n_strict_rw += 1
    t_scan = time.time() - t0
    print("    strict %d / %d，保奖励 %d / %d，strict∧保奖励 %d / %d（%.1fs）"
          % (n_strict, o_union, n_rw, o_union, n_strict_rw, o_union, t_scan))
    check("并集群 strict 元素数 == |Aut_strict|（并集内 strict 部分即全群）",
          n_strict == results["strict"]["order"], n_strict,
          results["strict"]["order"])
    check("并集群保奖励元素数 == |Aut_soft_rw|",
          n_rw == results["soft_rw"]["order"], n_rw, results["soft_rw"]["order"])
    check("并集群 strict∧保奖励元素数 == |Aut_strict_rw|",
          n_strict_rw == results["strict_rw"]["order"], n_strict_rw,
          results["strict_rw"]["order"])

    # ---------- 7. 三态定论 ----------
    o_soft = results["soft"]["order"]
    if o_soft == 589824:
        verdict = ("(a) 真群(soft 口径) = 589,824 = 并集群 ⟹ "
                   "并集群升格为完整 Aut(转移系统)")
    elif o_soft > 589824:
        verdict = "(b) 真群(soft 口径) = %d > 589,824 ⟹ 完整性告警器活案例" % o_soft
    else:
        verdict = "(x) 异常：|Aut_soft| = %d < 并集群 589,824（不可能，检查搜索）" % o_soft
        raise AssertionError(verdict)
    print("[7] 定论：%s" % verdict)

    # ---------- 8. 输出 json ----------
    out = {
        "meta": {
            "task": "六十四卦真群定论：把冠名实例 Aut 从下界做成 ground truth",
            "assumption_rule": "口径同 experiments_gua64.json（编码=初爻bit0上爻bit5、"
                               "1=阳爻；动作=错(全爻取反)/综(爻序颠倒)/互(新1..6爻=旧2,3,4,3,4,5爻)；"
                               "奖励=上卦后天五行标量金0木1水2火3土4）",
            "notions": {
                "soft": "Aut(无标签后继图 D)，E={(s,δ_a(s))} 去重；等价于 discover 的"
                        " equiv_error_gua 等变语义（∀(s,a): π(δ_a(s))=δ_b(π(s)) 某个 b）；"
                        "机器群/并集群数字属于此口径",
                "strict": "保动作标签：π∘δ_a=δ_a∘π 对 a=错/综/互 分别成立",
                "_rw": "再加保奖励 f(π(s))==f(s)",
            },
            "method": "弱分量分解（2 个 32 态分量，去重出边数不同⇒不同构⇒纯直积）+ 每分量"
                      "WL 染色 + 回溯穷举（候选=WL色∧分量∧奖励∧一致性，叶点全量验证）+ "
                      "显式闭包对拍（不自写 Schreier-Sims）；discover 重跑 seed=7 确定性",
            "determinism": "全程无随机（闭包抽查 rng seed=11）；discover 随机重启/对合"
                           "搜索 seed=7（同原版默认）",
        },
        "components": {
            "n": len(comps), "sizes": [len(c) for c in comps],
            "dedup_out_edges": comp_edge_cnt,
            "states": comps,
            "note": "弱分量是无标签图 Aut 不变量；两分量去重出边数不同⇒不同构，"
                    "故各口径 |Aut| = 两分量自同构群阶直接相乘（无 k! 互换因子）",
        },
        "wl": wl_info,
        "aut": {k: {"order": v["order"], "nodes": v["nodes"],
                    "per_component": v["per_component"]}
                for k, v in results.items()},
        "cross_check": {
            "machine_order_closure": o_machine,
            "union_order_closure": o_union,
            "union_gens_soft_pass": gens_soft,
            "union_gens_strict_pass": gens_strict,
            "union_gens_total": len(union_gens),
            "strict_gens_in_union": len(strict_gens),
            "union_scan": {"total": o_union, "strict": n_strict,
                           "reward_preserving": n_rw,
                           "strict_and_reward": n_strict_rw},
            "equalities": {
                "union_eq_aut_soft": o_union == results["soft"]["order"],
                "union_scan_strict_eq_aut_strict": n_strict == results["strict"]["order"],
                "union_scan_reward_eq_aut_soft_rw": n_rw == results["soft_rw"]["order"],
                "union_scan_strict_rw_eq_aut_strict_rw":
                    n_strict_rw == results["strict_rw"]["order"],
            },
            "reward_certificates": {
                "sigma_moves_reward_at": sigma_cert,
                "sigma_reward_from": reward(sigma_cert),
                "sigma_reward_to": reward(sigma[sigma_cert]),
                "tau_moves_reward_count": len(tau_certs),
            },
        },
        "verdict": {
            "code": "a" if o_soft == 589824 else ("b" if o_soft > 589824 else "c"),
            "text": verdict,
            "aut_soft_order": o_soft,
            "union_order": o_union,
            "machine_order": o_machine,
        },
        "asserts": checks,
        "timing": {"discover_sec": t_disc, "union_scan_sec": t_scan,
                   "total_sec": time.time() - t_total},
    }
    with open(os.path.join(ROOT, "experiments_gua64_aut.json"), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---------- 人话摘要 ----------
    print("\n" + "=" * 96)
    print("人话摘要")
    print("  ① 真群（soft 口径 = discover/并集群口径）|Aut| = %d，与并集群 %d %s。"
          % (o_soft, o_union, "相等" if o_soft == o_union else "不等"))
    print("  ② 保动作标签口径 |Aut_strict| = %d（并集群里恰有 %d 个元素满足此口径）。"
          % (results["strict"]["order"], n_strict))
    print("  ③ 保奖励口径：|Aut_soft_rw| = %d，|Aut_strict_rw| = %d"
          "（并集群里保奖励的恰 %d 个——cheap_check 双拒答的定量版）。"
          % (results["soft_rw"]["order"], results["strict_rw"]["order"], n_rw))
    print("  ④ 分量分解：2 个 32 态弱分量（出边 %s 不同构），WL 稳定块 soft=%d、"
          "strict=%d、soft_rw=%d、strict_rw=%d。"
          % (comp_edge_cnt, wl_info["soft"]["n_blocks"],
             wl_info["strict"]["n_blocks"], wl_info["soft_rw"]["n_blocks"],
             wl_info["strict_rw"]["n_blocks"]))
    print("  结果已写入 experiments_gua64_aut.json")


if __name__ == "__main__":
    main()
