# wuxing_gua —— 对称群能不能用？判据 CLI

**一句话定位**：在**黑盒转移数据**上、**状态压缩之前**，先判这个对称群**能不能用**；**不能用就拒答**。
（口径：黑盒、压缩前、可拒答。）

- **黑盒**：只需要转移表或 `(s,a,s',r)` 采样轨迹，不看模型内部结构（采样版连完整转移表都不要）
- **压缩前**：判据是轨道压缩的前置门禁——先裁决，后压缩
- **可拒答**：三态结论——**放行 / 拒答 / 样本不足**；样本不足时只说样本不足，绝不因为"没看出差异"而放行

---

## 环境要求

- Python ≥ 3.10（实测 3.12.10），**零第三方依赖**（纯标准库）
- 判据核心 **import 自本项目研究代码，未复制、未改写**（`experiments_p3` / `experiments_p4` / `cheap_check_sample` / `experiments_e1`，各自均纯标准库、import 无副作用），出处逐文件注明在模块文件头——因此本工具需在**本项目树内**运行
- 所有命令在**项目根目录**执行（或设 `PYTHONPATH` 指向项目根）
- 文件读写一律显式 `encoding='utf-8'`

## 快速开始（可复制）

**60 秒内最短路径**：先生成演示夹具——`demo` 一条命令秒级量级跑完（确定性可重建，
同一 `--n` 重复运行逐字节一致）：

```bash
python -X utf8 -m wuxing_gua demo --out demo_fixtures
```

然后跑端到端自检（13 个分支，实测总耗时两分钟量级、上限 180 s——分支数与上限随
版本演进，以输出汇总行为准；当前为 13 分支口径）：

```bash
python -X utf8 -m wuxing_gua selftest
```

期望输出：13 个分支全 PASS、退出码 0。

想逐条命令体验，直接用上面生成的演示夹具。共 7 个文件：`model_q6.json`（标准 Q₆ 环境：目标=全阳、奖励 R_GOAL/R_STEP）、
`model_popcount_q6.json`（能量环境：无吸收态、奖励=-0.02+0.05·popcount(后继)，用于非法群演示）、
`model_translated_q6.json`（平移编号环境：与标准环境同构、仅状态编号不同，用于
`--canonize` 编号伪像演示，见下文）、
`group_true_s6.json`（真群 S₆，阶 720）、`group_xor_z2n.json`（XOR 平移群，阶 64）、
`samples_10000.jsonl` / `samples_100.jsonl`（采样轨迹，种子公式与
`src/experiments_cheap_sample.py` 一致：`random.Random(101*7919+B)`）。

### discover：自动找群

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json
```

输出 JSON 到 stdout（stdout 一律可解析，进度/诊断走 stderr）。Q₆ 标准环境实测：
阶 720、7 轨道、压缩 9.1429×，`sentinel_ok=true`（与 `experiments_p3.json →
recovery[n=6].auto_order=720 / auto_orbits=7` 一致）。
**stdout 的 JSON 本身就是合法的 group.json**（含 `n_states` 与 `elements`），可直接落盘复用：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json > group_discovered.json
python -X utf8 -m wuxing_gua check --trans demo_fixtures/model_q6.json --group group_discovered.json
```

退出码：`0` = 找到非平凡对称群（可用）；`1` = 只找到平凡群（阶 1，按「群不可用」拒答，JSON 仍输出）。

#### discover 输出的 generators 顶层字段

输出 JSON 顶层带 **`generators`** 字段：输出群的一组**不冗余生成元**（试点反馈
"生成元混在 elements 里需自行识别"的修复）。口径：`elements` 是闭包全群，
`generators` 是从中贪心抽取的紧凑表示——**生成元闭包 == elements 全集**由实现内
assert 硬保证（`core_discover._compact_generators`：按元素序扫描，不在当前子群就
收进生成元集并增量闭包；确定性无随机源，同一输出必得同一生成元集；平凡群为空表
`[]`）。全部 discover 臂（plain / 三单标志 / 组合 / preset）统一带此字段。成本：
编排层一次增量闭包复算，demo 规模（≤720 阶）亚秒级；大群（六十四卦机器群
294,912 阶 / 真群 589,824 阶量级）与命令本身已做的闭包同量级（实测数字以
`experiments_fullflags.json` → environments.gua64 各 sec 字段为准）。判据与退出码
零改动——`generators` 只是 `elements` 的紧凑视图，不参与任何裁决。

### discover 的「标志 × judge」对照表

判据代码一行未改；本表把两个等变判据的**实际生效路径**按 `wuxing_gua/core_discover.py`
现读核对写成速查（回应试点反馈：写预注册需通读 `src/experiments_p3.py::equiv_error`
与 `src/experiments_gua64.py::equiv_error_gua` 两处源码，才能确定"置位型动作"会不会
被位串判据误杀）。**位串条件**（即已知限制 1）：`n_states = 2**n_bits` 且动作
a = 翻转第 a 位。

- **位串判据 `equiv_error`**（`src/experiments_p3.py`）：动作硬编码为"a = 翻转
  第 a 位"——对每个 (s,a) 要求 π(s⊕2^a)⊕π(s) 恰好翻一位（否则判 inf）。只对满足
  位串条件的模型语义成立。
- **泛化判据 `equiv_error_gua`**（`src/experiments_gua64.py`）：动作对应关系不硬编码，
  从 trans 数据现取（每个 (s,a) 取概率最大后继，在 π(s) 的动作里搜"接得住 π(后继)"
  的动作 b），接不住才判 inf。为任意动作集设计（六十四卦错/综/互即其诞生场景）。

| discover 臂 | 等变裁决 judge（实际生效路径） | 置位型动作模型（满足位串条件） | 非位串动作模型（错/综/互、业务动作集等） |
|---|---|---|---|
| plain（不带标志） | 位串 `equiv_error`（`experiments_p3.discover`，`labelings="plain"`、`equiv_fn=None`） | 安全 | **不适用**：可能误杀真自同构（判 inf）或报内部错误（gua64 现跑实测退出码 3：动作下标越界），绝不误放行 |
| `--canonize` 单标志 | 位串 `equiv_error`（`core_discover._discover_canonized`：候选映射回原编号后过同一裁决） | 安全 | 同上（canonize 只规范**搜索编号**，不改判据口径） |
| `--multi-label K` 单标志 | 位串 `equiv_error`（`core_discover._discover_multilabel`：K 臂候选均回原编号裁决） | 安全 | 同上 |
| `--extra-candidates` 单标志 | 位串 `equiv_error`（`core_discover._discover_extra`：δ_a 候选与三路候选同裁决） | 安全 | 同上 |
| 组合（≥2 标志同给）/ `--preset robust` | **泛化 `equiv_error_gua`**（`core_discover._discover_combined`：全部臂含 plain 对照臂统一用泛化判据） | 安全（位串实例上与位串版判定等价，`experiments_discover_labeling.json` → bridge） | 安全（gua64 上 C6 三开达真群 589,824，`experiments_fullflags.json` → judgment） |

注：`--pad-aware`（哑态商图臂）单标志走专用路径
（`core_discover._discover_padaware`），商图候选哑态定点回填后过**泛化判据
`equiv_error_gua`**（位串判据对 pad 定点回填结构性不适用，探针实测 bit=inf×4）；与其他标志同给时并入组合路径（同一泛化判据）。本行
不入上表（对照表按落盘时 5 臂口径锁定），
详见「--pad-aware」一节。

实操结论：

1. **模型动作 = 翻位**（满足位串条件）：任何臂都安全——两个判据在位串实例上判定
   等价（bridge 实证），选臂只看修复力对照（见「三标志怎么选」表），不必担心判据。
2. **模型动作不是翻位**：只有**组合路径**（`--preset robust` 一键，或任意两标志
   同给）走泛化判据；plain 与三个单标志臂的位串判据对此类模型不适用（不会被误
   放行——已知限制 1 的"如实拒答"语义——但会误杀/搜不到、甚至内部错误）。
3. **completeness 字段的 judge 同源**：plain/单标志路径用 `standard_equiv_fn`
   （= `equiv_error` 位串包装，`experiments_completeness.py`）；组合路径在位串模型
   上用 `equiv_error_gua`、非位串动作模型上如实跳过（`completeness.skipped=true`，
   见已知限制 8）。`--report-confidence` 的补臂（plain/canonize/extra）复用同三内核
   = 位串判据（`confidence._arm_orders`）。

### discover 的 completeness 字段（群完整性告警）

discover 在回答"找到什么群"之外，还回答**"这个群可能没找全吗"**——stdout JSON 里
附加 `completeness` 字段（判据实现在 `src/experiments_completeness.py`，阈值事前定死）：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json
# → "completeness": {
#      "n_certificates": 0, "completeness_score": 1.0,
#      "alert": false, "verdict": "probe_exhausted_no_certificate",
#      "reasons": ["重启搜索探针 3 批（候选 112 个，其中 112 个通过等变检验）+ …"], ... }
```

**判据口径（证书优先）**：探针找到一个置换 π，它 (a) 通过链路自己的等变检验
（max TV=0 零容忍口径）却 (b) 不在已得群中 ⇒ π 是「群没找全」的**证书**（被证明的
事实，非猜测）。两个探针：**动作置换探针**（动作的最优后继映射若是双射，整体检验）
与**重启搜索探针**（把链路主搜索路线换新种子 101+ 独立重跑 3 批，末批并入 MRV，
出证书即早停）。`completeness_score`：证书 ≥1 → 0.0（已证不完整）；否则 = 1 −
结构疑点分（疑点 = WL 色类数与群轨道数的落差，封顶 0.45 < 0.5 告警线 ⇒ 结构疑点
永不单独触发告警）。`alert=true` 时 `reasons` 给出可读证据与并集闭包增长。

- **阈值口径**：常量写死在 `src/experiments_completeness.py` 顶部（`ALERT_CERT_MIN=1`、
  `SCORE_ALERT_LINE=0.5`、`SUSPICION_CAP=0.45`、`WL_GAP_SCALE=10.0`、探针 3 批、
  种子基 101），在 7 个已知真群校准环境实例（4 正例 / 3 反例：SYS-2 n=4/5/6 喂
  D_n seed 与 SYS-3 A 为正例——SYS-3 A 经裁决由反例改判正例、阈值数值未动；
  SYS-2 n=6 喂 S_n seed、Q6、Q8 为反例）上复核，7/7 符合预期、逐环境误报 0 /
  漏报 0（gua64 无完整 ground truth，仅作展示、不参与标定）；取值依据与局限见
  仓库 docs/evidence.md（锚点 E50）。**告警器是启发式评估：证书是证明，
  但"探针穷尽无证书"≠"群已找全的证明"。**
- **退出码不受影响**：completeness 只是 discover 输出里的附加评估字段，告警不改变
  本命令的 0/1 退出码语义。
- **成本**：探针 ≈ 把 discover 主搜索再跑一遍。json 实测耗时只给量级（单次运行计时
  必然漂移，精确值以 `experiments_completeness.json → environments.*.chain_sec /
  assess_sec` 为准）：Q6 评估亚秒级（约 0.3 s，含探针；selftest 分支 1 实测全程秒级）；
  gua64 规模评估约 49 s（大头是证书并入后的并集闭包）。
- **实测行为**：Q6 标准环境不告警（score 1.0）；能量环境（popcount）上 discover 的
  对合路线已把群找满（阶 46080，含 XOR 平移），同样不告警——告警器只在它**抓到
  群外真对称**时才说话。

### discover 的 --report-confidence 标志（校准判别分）

completeness 解决「能证不完整」；`--report-confidence` 补另一半——**证书静默时给
可校准的可信度**（预注册与矩阵校准口径见下；实现在
`wuxing_gua/confidence.py`，阈值事前定死）：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json --report-confidence
# → "confidence": {
#      "proof_miss": false, "peers_max": 720, "order_current": 720,
#      "wl_gap": 1.0, "w3d_score": 0.0,
#      "verdict": "no_evidence_of_missing",      # 或 proved_incomplete / statistical_suspicion
#      "arm_orders": {"canonize": 720, "extra": 720, "plain": 720},
#      "basis": "…", "note": "…不是数学保证…≠ 找全的证明…一致漏找型…不触发…" }
```

**分布外提示**：`verdict=statistical_suspicion` 时输出块强制
附 `ood_hint` 固定文案——「分布外环境提示：统计层阈值（wl_gap 分界 1.5/满格 2.0）
在 9 个研究环境×13 编号矩阵上标定，真实业务 FSM 等分布外环境不保证——请以
completeness 证书/独立验证为准，不要单凭本统计判读下结论」。出处 = ticketfsm 试点实锤
统计层分布外假阳性（wl_gap=6.0 满格 vs 独立暴力验证 |Aut|=2，`pilot/aut_bruteforce.json`）；**只加提示、不在单点假阳性上改阈值**（重新标定等新环境数据另立
预注册），证明层/无证据档不附（不依赖统计阈值），退出码不受影响。

**判据（两层，全部使用者可见信息，不知真群）**：
- **证明层**：开启时自动补跑缺失配置臂（plain / canonize / extra，同模型），任何一臂
  群阶 **严格大于** 当前输出 ⇒ 当前群 ⊊ Aut **被证明**（各臂输出都逐元素过
  max TV=0 等变检验 ⇒ 都是 Aut 的子群，而 Aut 唯一）；
- **统计层**（全部重测同阶时）：`wl_gap = 当前群轨道数 / WL 色类数`，
  `判别分 = min(1, wl_gap−1)`；判读线 0.5（⇔ wl_gap 1.5）、满格线 2.0。

**校准**：9 环境 ×13 编号矩阵 115 实例上 AUC=1.0、两端错误率 0（达真 69 / 未达真
46 全部分对；`experiments_w3_discriminator.json`）；挑战集 SYS-1/SYS-2 重编号 31 臂
全对。**边界（note 三句必带）**：统计层阈值是矩阵经验值不是数学保证；「无漏找
证据」≠ 找全的证明；**一致漏找型**（SYS-1 n=6 随机重编号：全部配置全部编号一致
漏到同一真子群）在无分歧时不触发。

- **退出码不受影响**；默认关闭、关闭时输出逐字节不变；成本最高约 3 次 discover
  级搜索 + 一次 canonize（补臂）。并集型输出（`--multi-label` / 组合 / preset）上
  证明层静默属预期（并集阶 ≥ 各单臂）——并集自身的漏找看 completeness 证书与
  wl_gap 统计层。
- selftest 分支 13 双期望实测：标准 Q₆ → `no_evidence_of_missing`；平移 Q₆
  （plain 6 vs canonize 720）→ `proved_incomplete`，退出码均 0。

### discover 的 --canonize 标志（规范编号搜索）

**为什么**：ovh 审查链证明搜索统计量有**编号伪像**——同一张图只换顶点编号，
ovh 相对极差可达 336.4%（判决「实现伪像」，`experiments_ovh_relabel.json` →
per_graph_verdict）；先做规范化重编号（canonize）再跑同一搜索器，三图相对极差
全部降为 0.0%（判决「消除」，`experiments_canonical_search.json` → per_graph；
「canonize 后仍有结构解释」的残余候选亦被 29 图扩展否定）。本 CLI 里同一伪像更强：**discover 的发现结果本身
随编号变**——平移编号 Q₆（夹具 `model_translated_q6.json`，与标准环境同构、
仅状态编号不同）上不带标志群阶 6、轨道 32（欠完整），`--canonize` 群阶 720、
轨道 7（恢复完整，与标准编号一致）。这正是 `--canonize` 存在的理由。

**用法**：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json --canonize
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_translated_q6.json --canonize
```

Q₆ 标准环境实测：群阶 720、轨道 7，与不带标志双向一致（elements 同集合、
orbits 全同）。输出 JSON 附加 `canonize` 字段：

- `canon_sec_magnitude`：canonize 用时，**量级口径**（单次运行计时必然漂移，
  不报精确值；另有 `canon_search_nodes` 搜索树节点数，确定性可复现）
- `mapping`：重编号映射摘要（`is_identity` 是否恒等 / `n_fixed_points` 不动点数）
- `consistency`：与不带标志的对照——`order_plain` / `order_canon`、
  `n_orbits_plain` / `n_orbits_canon`、`order_match` / `n_orbits_match` /
  `elements_same_set_as_plain` / `orbits_identical_as_sets`

**一致性语义**：`consistency` 只报告、不报错——两侧不一致 = plain 发现被编号
伪像削弱，canonize 结果更可信（哨兵复检与 max TV=0 等变裁决照常执行）；退出码
只由 canonize 结果本身决定（非平凡群 = 0，绝不在这类环境报错）。双向一致的
**硬断言**在 selftest 分支 8（Q₆ 标准环境 720/7）；削弱环境（平移 Q₆，plain
6/32 → --canonize 720/7）是 selftest 分支 9 与本节实测的固定案例。

**口径**（结构图规范化）：canonize 在**骨干图**上判定（与 discover 内部同一张
骨干图；实现 import 复用 `src/experiments_canonical_search.py` 的 canonize——
规范 WL + 个体化-细化树 + lex-min 证书，未复制改写），**不重排整张转移表**：
等变裁决沿用研究实现的位串口径（动作 a = 翻转第 a 位），对状态任意重编号会
破坏该口径。因此三路图搜索（确定性/随机重启/对合/MRV fallback，编排与超参
照抄原 discover）在规范编号骨干图上跑，候选生成元映射回原编号后过等变裁决
与闭包，判据数据自始至终是原编号。canonize 映射经 `isom_map_ok` 硬校验必是
骨干图同构；搜索树节点上限 400000（源常量 `CANON_NODE_CAP`，超限报错、
退出码 3，不静默截断）。

**默认关**：不带 `--canonize` 的行为与本节加入前逐位一致（向后兼容）。
**成本**：约 2× discover + 一次 canonize，标准环境（64 状态）合计秒级量级；
完整性探针评估的成本本身也有编号依赖（同构的标准环境亚秒级 → 平移编号环境
数十秒量级——探针内部搜索的树规模随编号变，同一伪像的另一面），故削弱环境
上单条 discover 命令实测数十秒量级。
**系统化依据**（编号伪像矩阵）：7 环境 × 13 编号 × plain/--canonize 两臂的分布数字（plain 完全丢失率 0.4066、canonize 修复率 0.8571、canonize 残余伪像 13 个，全局口径）以 `experiments_discover_labeling.json` 为准，判读规则与逐环境分布见仓库 docs/evidence.md。

### discover 的 --multi-label K 标志（随机重编号生成元并集）

**为什么**：`--canonize` 依赖「规范编号存在且良定」，但编号扫描钉死它有 13 个
残余伪像（全部 gua64：canon 臂 0/13，全部 294,912 < 真群 589,824，
`experiments_discover_labeling.json`），汉诺塔 n=8 上 canonize 更是 suppress
到阶 1（`experiments_sys4_n8.json` → n8.canon）。`--multi-label K` 走另一条
不依赖任何编号假设的修复路径：把骨干图按 **K 个随机重编号**（固定种子流的
均匀随机置换）各跑一遍同一套三路搜索，K 臂幸存生成元**并集去重取闭包**——
候选生成元全部映射回原编号过等变裁决（max TV=0 零容忍），哨兵复检照常；
判据数据自始至终是原编号。并集只增不减（闭包单调，k 曲线实测零违规）。

**用法**：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_translated_q6.json --multi-label 2
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_translated_q6.json --multi-label 8 --seed 20261025
```

平移编号 Q₆（削弱环境，plain 6/32）实测：`--multi-label 2` 并集群阶 120、
12 轨道（两臂各找到阶 6，并集去重 8 生成元闭包成 120）——显著大于 plain；
同命令在标准环境（plain 已是 720）上 union@2 = 120 **低于** plain——K 较小时
并集在幸运编号上会回落，`multi_label.consistency` 如实报告、退出码不变。
退出码：`0` = 并集群非平凡；`1` = 并集群平凡（K 臂全空，如汉诺塔类环境在
部分随机编号上搜索树爆炸零收获）。

输出 JSON 附加 `multi_label` 字段：`k` / `seed`（默认 20261025，同种子同
编号批、结果确定可复现）/ `arms`（逐臂 n_candidates/n_pass/n_mrv/order）/
`n_union_gens`（去重后并集生成元数）/ `consistency`（与不带标志的对照，
`order_plain` / `order_union` / `order_match` / 轨道与元素集合一致性——语义
与 `--canonize.consistency` 同款：只报告、不报错、不改变退出码）。可与其他
标志自由组合（组合语义见「--preset robust」一节）；
`--multi-label 0`/负数报输入错误。

**口径与成本**：每臂 = 一次三路图搜索（编排与超参照抄 discover，只是骨干图
换随机编号）⇒ 成本 ≈ K× discover + 一次 plain（consistency 对照）+ 完整性
探针；demo 规模（64 状态）K=2 全命令数十秒量级。搜索重编号只动骨干图，
与 `_discover_canonized` 同构（规范形换成随机置换）；两条管线（重编号整张
转移表 + 泛化 judge vs 只重编号骨干图 + 位串 judge）在位串模型上收获相同
候选，逐元素集合相等实证见 `experiments_multilabel_union.json` →
`pipeline_checks.judge_equivalence_random_instance`（Q6 随机实例 arm(a) 阶 6
== arm(b) 阶 6，sets_equal=true）。

**k 曲线证据**（预注册判读，规则先落盘；9 环境 × k∈{1,2,4,8,13}，编号批
seed=1..13，全部数字以 `experiments_multilabel_union.json` 为准）：

- 判读**成立**：k=4 达真群环境数 6 ≥ canonize 达真群环境数 6，单调性零违规；
  饱和点 k=8（达真环境数 8/9：7 扫描环境 + 汉诺塔 n=7/n=8）。
- k 曲线逐环境（→ 为达真）：Q4/K44/Heawood 全 k 达真；Q5 k=2；Q6/Q7 k=8
  （plain 在随机编号上 0/13 幸运的全灭环境，并集 8 个随机编号即恢复
  S₆/S₇ 全群）；汉诺塔 n=7 k=2、n=8 k=1（10/13 随机编号 MRV 收获完整 S₃）；
  **gua64 全 k 不达真**（k=13 并集 294,912，与 std 机器群**同一集合**——
  随机编号并集与 canonize 同样卡在机器群天花板，错/综那一半不随编号变）。
- K 取值建议：默认档 K=4（判读成立的比较点，修复率已持平 canonize）；
  追求恢复上限用 K=8（饱和点）；K=13 无额外环境收益（8→8）。

#### 三标志怎么选（--canonize / --multi-label K / --extra-candidates，全局对照版）

三修复路径全局对照（同一 9 环境 × 13 编号矩阵量齐四配置，预注册判读先落盘；复用列与既有 json 逐位一致由脚本硬 assert；
全部数字以 `experiments_threefix_global.json` → judgment 为准）：

| 配置 | 达真环境数（/9） | 实例级完全丢失率 | 残余伪像实例 | 一句话 |
|---|---|---|---|---|
| C1 plain（不带标志） | 3 | 0.3162（37/117） | 46 | 编号伪像基线 |
| C2 `--canonize` | 6 | 0.0（0/93） | 15 | 修 6 环境，汉诺塔 suppress、gua64 无效 |
| C3 `--extra-candidates` 单次 | 3 | 0.3162（37/117） | 44 | 只修 gua64 有利编号（std/反转 2/13 达 589,824），其余环境与 plain 逐位相同（零双射动作） |
| C4 extra+multi k=8（实验层组合） | **8** | 0（9 环境 Union） | 1 | 旧推荐；gua64 147,456→294,912=机器群，仍不破 M 天花板 |
| C5 canonize+extra（实验层组合，2026-10-25 全开测试） | 7 | 0（单实例口径） | 2 | **gua64 589,824 达真**（canonical 收获 294,912 + 错/综候选补 τ 陪集），唯一单次型在 gua64 达真且编号鲁棒；汉诺塔仍 suppress 阶 1 |
| **C6 全开 canonize+extra+multi(k=8)**（实验层组合） | **9** | 0（9 环境 Union） | 0 | **翻案：鲁棒 9/9 配置存在**；canonical 收获 ∪ k=8 随机编号收获互补 |
| 参考：multi k=8（`--multi-label 8`） | 8 | — | — | 既有最好（CLI 可达）；C4 与之并列且 gua64 上严格更强 |

关键机理（`experiments_threefix_global.json` + `experiments_fullflags.json`
→ environments.gua64）：9 环境中只有 gua64 有双射动作（错/综 2 个）——其余
环境 extra 候选恒空、C3 与 plain 同代码路径逐位相同（脚本逐实例 assert）；
随机编号把共轭候选 σ̃=πσπ⁻¹ 送进机器群 M（294,912）内，k=8 并集只到
294,912；而 **canonize 自造的 canonical 编号在 gua64 上恰好是「有利编号」**：
三路收获补满 294,912 子群，extra 候选（σ,τ 回搬 = std 的 δ_a，脚本 assert）
补上 τ 所在陪集 ⇒ C5 单次即达真群 589,824；再并 k=8 随机编号收获兜住汉诺塔
suppress ⇒ **C6 全开 9/9——「不存在鲁棒 9/9 配置」被翻案**（预注册判读；C1-C4 复用列同流硬 assert，停查 F1-F8 全过）。

实操建议（按输入情形）：
1. **推荐入口**：`--preset robust`（= C6 全开 canonize+extra+multi k=8，达真
   9/9；对输入编号鲁棒、并集只增不减）——一条命令替代手工组合三标志，k 默认 8
   可由 `--multi-label` 覆盖（见下文「--preset robust」一节）。
2. 已知环境形态的省成本选择：`--canonize`（6/9、成本恒定，suppress/无效双刃
   并写）→ `--multi-label 8`（8/9）；gua64 类自然编号输入（动作本身是对称双射）
   加/先 `--extra-candidates` 单次（std 编号口径唯一把 gua64 修到真群 589,824）；
   汉诺塔类 suppress 环境（`--canonize` 后阶 1）必须换 `--multi-label`。
3. 自由组合：`--canonize --extra-candidates` = C5 语义
   （7/9，gua64 单次即真群 589,824）、`--multi-label K --extra-candidates` =
   C4 语义（8/9）、`--canonize --multi-label K` = canonical 臂与随机臂并集；
   组合 payload 均带 `combination` 字段（配置/逐臂群阶/并集群阶/consistency
   对照/耗时量级），见「--preset robust」一节。

三标志组合关系（原互斥检查已删）：`--canonize` /
`--multi-label K` / `--extra-candidates` 可任意组合，组合语义 = 实验层
C5/C6 同口径（每臂三路搜索 + 双射动作候选，幸存生成元并集闭包，见
「--preset robust」一节）；判据（等变裁决 + 哨兵 + check 两层）在所有路径上
完全一致，都不放伪群。全开组合在实验层验证达真 7/9（C5 canonize×extra）、
9/9（C6 三开，`experiments_fullflags.json` → judgment：推荐配置 C6、翻案
「不存在鲁棒 9/9」）。

### discover 的 --preset robust 标志（推荐配置一键）

**为什么**：三修复标志单独用各有短板（全局对照 C1 plain 3/9、C2 canonize 6/9、
C3 extra 3/9、C4 extra+multi 8/9、C5 canonize+extra 7/9），实验层全开测试证明
**组合**才是鲁棒解——C6 三开 canonize+extra+multi(k=8) 达真 **9/9**，翻案
「不存在鲁棒 9/9 配置」（预注册口径；全部数字以
`experiments_fullflags.json` → judgment 为准）。本开关把该推荐配置原样送进
工具层：一条命令 = 三标志全开。

**用法**：

```bash
python -X utf8 -m wuxing_gua discover --trans model.json --preset robust
# 等价于 --canonize --extra-candidates --multi-label 8；k 可覆盖：
python -X utf8 -m wuxing_gua discover --trans model.json --preset robust --multi-label 4
# 随机编号种子由 --seed 控制（默认 20261025，同种子同编号批、结果确定可复现）
```

六十四卦环境（64 状态、错/综/互 3 动作，构造 = `src/experiments_gua64.py::
build_gua64`）实测：`--preset robust` 单命令达真群（soft 口径）**589,824**、
退出码 0（与 `experiments_fullflags.json` → environments.gua64.C6_full_flags.
order 一致；C5 部分 canonical 三路收获 294,912 + 错/综双射动作候选补 τ 陪集
= 单次即真群，k=8 随机编号臂在汉诺塔类环境兜底 suppress）。

**语义（实验层 C6 同口径）**：canonize 臂在规范编号骨干图上搜索（多分量骨干图
逐分量 canonize + 按分量证书拼接——gua64 必需，整图 canonize 超
`CANON_NODE_CAP`；单分量骨干图即 `--canonize` 同一路径）+ K 个随机重编号臂
（`--multi-label` 同款种子流）+ 双射动作 δ_a 候选追加进每臂候选集；幸存生成元
逐臂累计并集去重取闭包（canonize 臂恒在池内，增量捷径 + 单调 assert）。判据
数据自始至终原编号；等变裁决 = 泛化版 max TV=0 零容忍（位串实例上与位串版
判定等价，`experiments_discover_labeling.json` → bridge）。三标志自由组合
（不带 preset）走同一管线：canonize+extra = C5 语义、multi+extra = C4 语义、
canonize+multi = 对应两臂并集；并集不含 plain 臂收获（C4/C6 同口径——K 较小时
并集可能低于幸运编号上的 plain，`combination.consistency` 如实报告、不改变
退出码）。

**输出**：`combination` 字段——`config`（preset/标志组合/k/seed）、`arms`
（每编号群阶：plain 对照 + canonical + K 随机臂，逐臂候选/过关数/sentinel）、
`n_union_gens`（并集生成元数）、`consistency`（与单次 plain 的对照，语义沿用
`--canonize` 版口径）、`sec_magnitudes`（各阶段耗时量级桶——单次运行计时必然
漂移，只给量级）；顶层 `order`/`elements` 即并集群（原编号，可直接当
group.json 用）。**completeness 适用域**：非位串动作模型（n_actions ≠ n_bits，
如六十四卦 3 动作 64 状态）上 completeness 评估器如实跳过（其仿射探针按
n_states = 2^n_actions 位串口径构造），输出 `completeness.skipped=true` 与
原因；判据本身（等变裁决/闭包/哨兵复检）不受影响。

**成本**：≈ 1 次 plain 对照 + 1 次 canonize + canonical 臂搜索 + K 臂搜索 +
并集闭包；计时只给量级：六十四卦规模分钟量级（以 `experiments_fullflags.json`
→ environments.gua64 各 sec 字段为准），demo 规模（≤64 状态、群阶 ≤ 数千）
秒级到数十秒量级。selftest 分支 12 用 16 状态能量环境 Q₄（双射动作 mini，
`demo_env.build_popcount(4)`）验证单命令达真群 **384**（= 2⁴·4!，n=6 同构造
实测 46080 = 2⁶·6! 的降维同构型；期望值 = 同构造确定性重跑的实测定值）——
为守 selftest 120 s 总上限不跑大环境（32 状态同构 mini 单命令实测数十秒量级，
六十四卦数字以上述 json 为准）。

### discover 的 --extra-candidates 标志（动作置换候选源）

**为什么**：discover 的候选**只来自三路图搜索器**（骨干图确定性回溯 / 随机重启 /
对合搜索，`experiments_p3.py`），环境**自身的动作置换**（动作 a 的后继映射
δ_a 为双射时）从不进候选集——它们只以「等变裁决参照物」身份出现。gua64 上
这一盲区被钉死：机器群 294,912 卡在真群（soft 口径 589,824）的指数-2 对角子群
里，缺口恰是综卦 τ 所在陪集；k=13 随机编号并集与 canonize 全部 13/13 不达
（`experiments_multilabel_union.json` / `experiments_discover_labeling.json`）。
诊断（`experiments_gua64_gapfix.json` → diagnosis）：对合路只产出不动点=0 的
对合而 τ-陪集含 0 个不动点=0 元素（结构排除）；确定性路预算内只走到支集 ≤8
的解而陪集最小支集 32（首个陪集解 ~3.4M 节点，默认 node_cap=4000）；随机重启
路默认 40 次重启采样量不足且在重编号图上存活率为 0。修法 = 补上缺失的候选源。

**是什么**：`--extra-candidates` 把每个动作 a 的最优后继映射 δ_a（与完整性
告警器「动作置换探针」同口径，`experiments_completeness._action_candidates`）
在**双射**时追加为候选生成元，与三路图搜索候选一起过**同一个** max TV=0
零容忍等变裁决；超参与编排（含 MRV fallback 触发条件）一字不动，闭包负责
复合。**只增候选、不减裁决** ⇒ 不可能引入伪自同构；群阶只可能不变或增大。

**用法**：

```bash
python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_popcount_q6.json --extra-candidates
```

能量环境（popcount Q₆，无吸收态、动作=位翻转双射）实测：6 个动作候选全部
产出、全部过裁决，群阶 46080 / 1 轨道与不带标志**完全一致**（plain 已达全
自同构群 ⇒ 零增量、不误报——selftest 分支 11 的固定案例）。吸收态环境
（model_q6：目标态自环使动作映射非双射）自动零候选，行为与不带标志逐位一致。
gua64 类环境上同一开关把 294,912 修到 589,824 = 真群（全量 589,824 元素独立
零容忍复检 0 失败，`experiments_gua64_gapfix.json` → fix/verdict）。

**口径与成本**：≈2× discover（内部重跑一次 plain 做一致性对照）+ 完整性
探针。输出 JSON 附加 `extra_candidates` 字段：`actions`（双射动作下标）/
`n_candidates` / `n_pass` / `consistency`（与不带标志的对照，语义与
`--canonize.consistency` 同款：只报告、不报错、不改变退出码）。可与其他
标志自由组合（组合语义见「--preset robust」一节）。
默认关；不带标志行为与旧版逐位一致。11 环境（Q4-Q8 / K44 / Heawood / sys3a /
gua64 / 汉诺塔 n=7/n=8）回归「群阶不减、不误报」逐环境结果以
`experiments_gua64_gapfix.json` → regression_rows 为准。

### discover 的 --pad-aware 标志（哑态商图臂）

**为什么**（判决 = 生成侧隔离，`pilot/s47_blindspot_v2.json`）：含 **pad 哑态**
（全动作单后继自环 r=0 的行）的模型上，四路候选（确定性 / 随机重启 / 对合 /
MRV fallback）系统性漏掉跨哑态-真态的对称元素——512 GameWXXX 模型池普查
real_touch_pass=0：det 的 48 个候选全 pad-only（pad 色类 47 元在回溯枚举序里
先耗尽 max_gens=48）、rr 0 个（node_cap 死区）、对合 0 个（全部 WL 色类大小
15/47/75 皆奇数 ⇒ 配对结构性无解）、MRV 4 个仍全 pad-only（DFS 回溯末位类
先变体 ⇒ pad-only 完成式淹没 max_gens=4）。σ 本体双口径 TV=0 但进不了候选池
⇒ discover 阶 1 拒答。

**是什么**：`--pad-aware` 追加一路「哑态商图臂」——检测 pad 哑态后，在**真态
商图**（删 pad 行、压缩重编号；真实行引用 pad 时收缩不保结构，如实跳过不冒进）
上跑**同款**三路搜索（超参与编排一字不动：det max_gens=48 → rr 40 次 seed=7 →
对合 → 全空时 MRV fallback），候选**哑态定点回填**全空间（真态按商图映射、
pad 逐点不动）后过**同一个** max TV=0 零容忍等变裁决。判据零改动：零容忍语义、
退出码语义一字不动，不可能引入伪自同构。

**判据口径**：pad 臂用泛化判据 `equiv_error_gua`（组合路径同款）。原因（探针
实测，`pilot/_w5_padprobe.py`）：位串判据「动作 = 翻第 a 位」口径对 pad 定点
回填结构性不适用（512 商图候选回填后 4 个全部 bit=inf——pad 定点破坏位翻结构，
与 75→5 可见群机理同源），泛化判据从 trans 现取动作像、对回填候选判定正常。
无 pad 哑态的模型上新臂如实空转（`skipped="no_pad_states"`），行为不受影响。

**用法**：

```bash
python -X utf8 -m wuxing_gua discover --trans <model.json> --pad-aware
# 与其他标志自由组合（哑态商图臂追加进并集）：
python -X utf8 -m wuxing_gua discover --trans <model.json> --pad-aware --preset robust
```

**验收**（预注册 `pilot/gw_padaware_run.json`，先落盘后实现）：512 GameWXXX
模型 --pad-aware plain 在 900s 预算内从阶 1 拒答修到**发现非平凡群阶 5**
（=H，与 S47 四臂对账一致），全部元素 ⊆ 抽象 Aut=75（⟨σ,π⟩=C5×C15 重建
逐元素核对）、pad 全定点、哨兵 ok；回归：selftest 13 分支、默认/单标志路径
逐位 diff 全等（剥离计时字段口径）、C1-C6 矩阵抽 3 环境（Q4/K44/Heawood）
复跑达真 18/18 不降、ticketfsm 复跑阶 2 不变——逐项数字以 `gw_padaware_run.json`
的 stage_main / stage_regress 为准，判据文件 sha256 before/after 相等（判据
与搜索器一行未动）。完整记录见仓库 docs/evidence.md。

### check：完整转移表版判定（两层零容忍）

```bash
python -X utf8 -m wuxing_gua check --trans demo_fixtures/model_q6.json --group demo_fixtures/group_true_s6.json
```

- 真群 S₆（阶 720）：`verdict=pass`，退出码 0
- 非法群演示（**保转移概率但不保奖励**：能量环境 + XOR 平移群）：

```bash
python -X utf8 -m wuxing_gua check --trans demo_fixtures/model_popcount_q6.json --group demo_fixtures/group_xor_z2n.json
```

输出 `layer_transition.passed=true`（转移等变，max TV=0.0——"保转移概率"）
而 `layer_reward_profile.passed=false`（同轨道奖励剖面不同 1586/2016 对——"不保奖励"），
`verdict=reject`，退出码 1。这说明两层缺一不可：只查转移会放走它。

### check-sample：纯采样版判定（三态）

```bash
# 达门槛（10⁴ 条）→ 与完整表版一致：放行
python -X utf8 -m wuxing_gua check-sample --samples demo_fixtures/samples_10000.jsonl --group demo_fixtures/group_true_s6.json --trans demo_fixtures/model_q6.json

# 样本不足 → 只说样本不足（退出码 2），不下其他结论
python -X utf8 -m wuxing_gua check-sample --samples demo_fixtures/samples_100.jsonl --group demo_fixtures/group_true_s6.json --trans demo_fixtures/model_q6.json
```

`--trans` 推荐始终提供（读 goals 与 n_actions）；不提供时 group.json 须含 `n_actions`
（goals 可选，缺省空集并打 stderr 提醒——见"已知限制"第 5 条）。

---

## 退出码表

| 退出码 | 含义 | discover | check | check-sample |
|---|---|---|---|---|
| **0** | 放行可用 | 找到非平凡群（阶>1） | 两层判据均通过 | `verdict=pass`（两层无报警且功效达标） |
| **1** | 拒答（群不可用/非法） | 只找到平凡群 | 任一层报警 / 群内容非法 | `verdict=reject`（有可认证的不等变证据）/ 群内容非法 |
| **2** | 样本不足 | —（不适用） | —（不适用） | `verdict=abstain`（只说样本不足，绝不放行） |
| **3** | 输入或内部错误 | 文件缺失 / JSON 解析失败 / 模型不合格式 | 同左 / 模型与群规模不一致 | 同左 / 样本行越界 |

细分约定：**文件读不了**（缺失、JSON 坏、顶层结构不对）= 输入错误 = 3；
**群文件读得进来但内容不成立**（元素不是双射、长度不一）= 群非法 = 1。
argparse 用法错误也被改为退出码 3（argparse 缺省的 2 与"样本不足"冲突）。

## 输入 JSON 格式

### model.json（discover / check / check-sample 的 `--trans`）

```json
{
  "n_bits": 6,
  "n_actions": 6,
  "n_states": 64,
  "goals": [63],
  "trans": [
    [                              ← 状态 s=0
      [[0.004, 0, -0.02], ...],   ← 动作 a=0：[[p, u, r], ...]（p=概率, u=后继, r=奖励）
      ...
    ],
    ...
  ]
}
```

- `n_states` 必须 = `2**n_bits`（位串口径）；`1 ≤ n_actions ≤ n_bits`；**动作 a = 翻转第 a 位**（研究口径，等变裁决依赖它推断动作映射）
- `trans[s][a]` 非空，`p ≥ 0` 且 `Σp` 与 1 偏差 ≤ 1e-6，`u ∈ [0, n_states)`，r 有限数
- `goals`（可选）：吸收态列表（研究环境中目标态自环、奖励 0）。check-sample 的 L1 奖励层用它排除吸收态发出的样本；discover/check 不使用

### group.json（`--group`）

```json
{
  "n_states": 64,
  "elements": [[0, 1, 2, ...], ...],
  "n_actions": 6,
  "goals": [63]
}
```

- `elements`：置换列表，每个是 `0..n_states-1` 的双射；**允许只给生成集**——工具自动取闭包并在输出的 `group.input_was_closed_group` / `elements_added_by_closure` 里如实注明
- `discover` 的 stdout 直接可当作 group.json 用（多余字段被忽略）
- `n_actions` / `goals` 仅 check-sample 在缺 `--trans` 时使用（可选字段）

### samples.jsonl（check-sample 的 `--samples`）

每行一个 JSON，二选一：数组 `[s, a, u, r]` 或对象 `{"s": .., "a": .., "u": .., "r": ..}`（u = 后继状态）。

## 判据口径（照抄原实现，未放宽）

**check = 完整转移表版，两层都要过，都零容忍：**

1. **转移等变层**：每个群元素 π 过 `equiv_error`（`src/experiments_p3.py`，discover 的最终裁决；
   「max TV = 0 才放行」），容忍度 `TV_TOL = 1e-9`（与 discover 缺省 `tol` 一致）。
   |G| ≤ 5000 逐元素全查；更大时按 discover 的哨兵口径抽查（贪心生成元 + 头 64 / 中 64 / 尾 32），
   依据「等变关于复合封闭」的数学论证——demo 规模（≤64 状态）内不会触发。
2. **奖励剖面层**：`cheap_check`（`src/experiments_p4.py` 完整转移表版）——对每个状态把
   (概率, 奖励) 多重集按轨道代表元聚合为「奖励剖面」，同轨道剖面全同 ⇔ 等变；
   `n_bad = 0` 零容忍。它抓的正是「保转移概率但不保奖励」的群。

**check-sample = 纯采样版（`src/cheap_check_sample.py`，判据逻辑与参数逐字照抄）：**

- L1 奖励层：非吸收源样本中，同一后继轨道上的奖励必须恒定
- L2 齐性层：同轨道状态的后继-轨道分布 Pearson χ² 齐性检验（动作维池化）
- 三态：`pass`（两层无报警且每轨道功效达标）/ `reject`（可认证报警）/ `abstain`（其余——**样本不足绝不放行**）
- 参数（事前定死）：α=0.05（Bonferroni 分摊）、β=0.20、d_detect=0.20、min_exp=5.0、tail=0.01
  （`src/cheap_check_sample.py` 常量区）
- **采样门槛 10⁴ 条**：来自 `experiments_cheap_sample.json → threshold.overall_min_budget = 10000`
  （4 场景 × 3 种子与完整表版 100% 一致的最小预算档）；低于门槛时工具报
  abstain，不会靠放宽判据凑放行

## 已知限制

1. **位串口径**：等变裁决沿用研究实现，要求 `n_states = 2**n_bits` 且动作 a = 翻转第 a 位。
   不满足的模型不会被误放行——会在转移等变层如实拒答（元素推不出合法动作映射），
   discover 则可能只找到平凡群。
2. **平凡群恒放行**：check 回答"合法性"，不回答"有用性"。阶 1 的群两层判据真空通过
   （输出里带 note 说明压缩比 1.00×）；找群请用 discover。
3. **discover 只看转移、不看奖励**：奖励破坏对称时（如能量环境上的 S₆ 之外的更大群），
   discover 找到的群可能过不了 check 的奖励剖面层——这正是"发现→校验"两段式的设计，
   请始终把 discover 的输出过一遍 check 再用。
4. **采样门槛是经验标定**（与完整表版 100% 一致的实测最小预算），不是理论保证；
   d_detect 锚定在本环境单步随机性（P_PERT=0.12 / P_NOOP=0.10）上，换环境需重新标定。
5. **check-sample 的 goals 口径**：模型有吸收态时必须提供 goals（`--trans` 或 group.json），
   否则 L1 可能把吸收自环奖励误判为"奖励不恒定"（宁可误报、不放行，但结论不对）。
6. **性能**：demo 规模（64 状态、群阶 ≤720）单命令秒级；更大状态数/群阶耗时按
   状态数 × 群阶增长，未做优化。|G| > 5000 时转移层自动切换哨兵抽查（见上）。
7. **sys.path 副作用**：本包 import 时把 `<项目根>/src` 插到 `sys.path[0]`
   （模块名 `core`/`tests` 等以 src 版为准），并设 `sys.dont_write_bytecode=True`
   以免运行时向 `src/__pycache__` 写字节码。
8. **completeness 适用域（组合路径）**：`--preset robust` / 三标志组合
   在非位串动作模型（n_actions ≠ n_bits，如六十四卦错/综/互 3 动作 64 状态）上
   如实跳过 completeness 评估（其仿射探针按 n_states = 2^n_actions 位串口径
   构造，`src/experiments_completeness.py::_bit_perm_maps`），输出
   `completeness.skipped=true` 与原因；判据本身（max TV=0 等变裁决、闭包、
   哨兵复检）不受影响。

## 文件结构与出处

| 文件 | 出处 |
|---|---|
| `core_discover.py` | 包装 import `src/experiments_p3.py` 的 discover 全链（backbone+WL+三路候选+等变裁决+闭包+哨兵）；`--extra-candidates` 路径（`_discover_extra`：动作置换候选源 = experiments_completeness._action_candidates 同口径追加进候选集，编排/超参照抄 discover，见 README「--extra-candidates」一节）；completeness 字段 import `src/experiments_completeness.py`（完整性告警器，只附加输出、不改退出码）；`--canonize` 路径 import `src/experiments_canonical_search.py` 的 canonize + `src/experiments_ovh_relabel.py` 的 relabel/isom_map_ok（结构图规范化口径，见 README「--canonize」一节）；`--multi-label` 路径（`_discover_multilabel`，随机重编号骨干图 + 生成元并集闭包，编排/超参照抄 discover，见 README「--multi-label」一节）；组合路径（`_discover_combined`：`--preset robust` / 三标志任意组合 = 实验层 C5/C6 同口径——canonize 臂 import `experiments_discover_labeling.canonize_model_generic`（多分量骨干图逐分量拼接）∪ K 随机重编号臂 ∪ 双射动作候选，幸存生成元并集闭包（copy 自 experiments_fullflags.c6_union_curve），judge = `experiments_gua64.equiv_error_gua` 泛化版零容忍，见 README「--preset robust」一节）；输出层：`_compact_generators`（从已得群抽不冗余生成元，顶层 `generators` 字段，闭包==elements 由 assert 硬保证，不做任何裁决）+ 「标志 × judge」对照表的代码事实核对（见 README 同名一节） |
| `core_check.py` | 判据 import `src/experiments_p3.py: equiv_error` + `src/experiments_p4.py: cheap_check` + `src/experiments_e1.py: orbits_of`；新增装载/校验/闭包/两层编排 |
| `core_sample.py` | 判据 import `src/cheap_check_sample.py`（cheap_check_sample/make_sampler/sample_from_model）；新增 samples.jsonl 装载 |
| `demo_env.py` | 环境与真群 import `src/experiments_e1.py: build_model_n`、`src/experiments_cheap_sample.py: swap_gen`；能量环境（build_popcount）与平移编号环境（build_translated_standard，削弱案例）为新增构造（文件头说明用途） |
| `selftest.py` / `cli.py` / `errors.py` / `__init__.py` / `__main__.py` | 新写（编排层） |
| `confidence.py` | `--report-confidence`（校准判别分）只读诊断块：指标公式/阈值与研究侧 `src/experiments_w3_discriminator.py` 同源（预注册口径）；补臂复用 `core_discover.py` 的 `_discover` / `_canonize_model`+`_discover_canonized` / `_discover_extra`（同超参，不重写搜索），见 README「--report-confidence」一节）；`statistical_suspicion` 分支输出块强制附分布外提示 `ood_hint`（常量 `_OOD_HINT`，ticketfsm 试点反馈；阈值/退出码零改动） |

## 安装

- **主形态**（Python ≥ 3.10、纯标准库；作者验证环境 Python 3.12 实测通过）：

```bash
python -m pip install . --target <任意目录> --no-build-isolation
cd <任意目录>
python -X utf8 -m wuxing_gua selftest
```

  期望：selftest 13/13 分支 PASS、退出码 0（实测两分钟量级，上限 180 s，以输出汇总
  行为准）。安装树会同时含
  `wuxing_gua/` 与 `src/` 两个顶层目录——判据核心 import 自 src（见上文
  「文件结构与出处」表），只装 `wuxing_gua` 单包会在 import 时报错，这是设计使然；
  `pyproject.toml` 头注有完整说明。
- **无 pip 的环境**：把本仓库整树复制到任意目录后运行同上命令。
- **zipapp 不可自包含（实测，不提供 .pyz）**：`python -m zipapp wuxing_gua
  --main "wuxing_gua.cli:main"` 构建即报 `ZipAppError: Cannot specify entry point
  if the source has __main__.py`（包自带 `python -m` 入口）；即便改用 staging 绕开
  构建限制，`<pyz>/src` 也不是真实目录，import 时的 isdir 守卫（本文件第 7 条
  已知限制的 sys.path 机制）照样失败。实测记录由发布方留存。
- **版本口径**：发行版 `wuxing-gua 0.1.0`（pyproject.toml）；包内 `__version__`
  = 1.0.0——两者不同源，发行版口径以 pyproject 为准。
- 验证细节与形态取舍：见仓库根 `README.md` 与 `docs/evidence.md`。

## 许可与联系

- **许可**：MIT（见仓库根 `LICENSE`）；如需亦可采用 Apache-2.0（全文随附
  `licenses/LICENSE-Apache-2.0.txt`）。
- **联系**：欢迎通过 issue 反馈缺陷与负结果（请附命令、输入与完整输出）。
  维护现状如实声明：单维护者（bus factor = 1），无响应时效承诺。
