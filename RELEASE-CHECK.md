# 发布预检报告（RELEASE-CHECK）

- 预检对象：本目录（`github_release/`）整树，49 个文件。
- 预检方式：以「第一次见到本仓库的外来用户」视角，五步全部实际执行（命令与退出码均在预检当日实跑取得，非转抄）。
- 预检日期：2026-10-28。
- 本文件是发布流程产物：可随仓库一起发布，也可在发布前删除；删除与否不影响工具与文档。

## 结论

**五步预检全部通过。** 预检中发现 15 处问题，已当场修复并复验（修复后重新做了完整隔离自跑，13/13 分支 PASS、退出码 0）。无阻断项。

## 五步预检逐项结果

### 第 1 步：隔离自跑（把整树复制到系统临时目录后运行）

| 检查 | 命令 | 结果 |
|---|---|---|
| 隔离自检 | `python -X utf8 -m wuxing_gua selftest`（临时副本内） | **13/13 分支 PASS，退出码 0**（90.6 s，上限 180 s） |
| 演示夹具 | `python -X utf8 -m wuxing_gua demo --out demo_fixtures` | 退出码 0，7 个文件；另做**两次生成逐字节一致**比对（确定性主张成立） |
| 示例 1（32 态工单模型） | `python -X utf8 -m wuxing_gua discover --trans examples/ticketfsm_milestones_model.json` | 退出码 0；order=2、n_orbits=24、compression=1.3333…、completeness 无告警——与 `examples/README.md` 预期逐项一致 |
| 示例 2（512 态模型） | `python -X utf8 -m wuxing_gua check --trans examples/gw_chainrot_model.json --group examples/gw_chainrot_group_h.json` | 退出码 0；verdict=pass、5/5 元素 worst_tv=0.0、奖励层 0/960、4.0×——与预期一致 |
| 示例 3（16,384 态模型） | `python -X utf8 -m wuxing_gua check --trans examples/gw_teambattle_model.json --group examples/gw_teambattle_group_h.json` | 退出码 0；verdict=pass、25/25 元素 TV=0.0、奖励层 0/176,640、1,024 轨道、16.0×，墙钟 8 s（秒级量级主张成立） |
| README 快速上手示例 | `python -X utf8 -m wuxing_gua discover --trans demo_fixtures/model_q6.json` | 退出码 0；order=720、n_orbits=7，输出含 `completeness` 与 `generators` 字段——与 README §2 一致 |
| 安装冒烟（离线） | `python -m pip install . --target <临时目录> --no-build-isolation --no-index` | 安装退出码 0（装出 `wuxing_gua/` + `src/` 两个顶层目录）；随后在安装目录 `python -X utf8 -m wuxing_gua selftest` → **13/13 PASS、退出码 0**（89.0 s） |

修复全部落盘后，另取全新临时副本**复跑了一轮完整隔离自检：13/13 PASS、退出码 0**，确认修复零行为影响。

### 第 2 步：黑话泄漏全仓 grep（词表全扫）

对 49 个文件全树扫描：中文内部术语（轮次编号类/项目代号/角色名/人名/内部账册类文档名/机器路径）、大小写敏感的票据编号 token（单字母加序数形式，词边界正则共 2 类）、以及内部轮次号与内部文档名专名。

- **预检时发现 11 处命中并全部修复**（见下节）：2 处内部轮次号（注释与出处表各 1）、9 处内部文档名引用（全部位于注释/帮助文本，含一处 `--help` 用户可见文本）。
- **修复后复扫零命中。** 该扫描已固化为可复跑断言（见「回归防线」一节），发布后每次运行一致性审计都会重扫。

### 第 3 步：双语一致性（README.md ↔ README.zh-CN.md）

- 标题结构：两版各 8 个标题（含文档名），编号节 1–7 一一对应、层级一致；
- 表格：逐节行数对齐（3/4/5 节分别为 6/5/8 行，两版全等，总 19/19）；
- 语言切换链接：两文件互链、文件名拼写正确、目标存在；两 README 的全部本地链接目标 0 缺失；
- **数字抽验 15 组，三方回源（英文书写 + 中文书写 + 主项目机器可读记录）全部一致**，包括：32 态×5 动作、群阶 2、轨道 24、1.333×、|Aut|=2、512=465+47、120,000 步 100.000%、75 vs 5、16,384=14,415+1,969、25/25 TV=0、0/176,640、1,024 轨道 16.0×、AUC=1.0×115 实例、0/100、order=720/n_orbits=7（另有 4 项由记录数据现算复核）。

### 第 4 步：README 主张 vs 工具实况

- **六标志逐一 `--help` 核对**：`--preset {robust}`、`--canonize`、`--multi-label K`、`--extra-candidates`、`--pad-aware`、`--report-confidence` 全部存在；`--seed` 默认 20261025、其余默认关——与 README §5「六标志速查」一致；`--preset robust` 帮助文本即「三标志全开」语义；五个子命令（discover/check/check-sample/selftest/demo）齐全。
- **退出码表逐档实测**：0（真群放行）/ 1（保转移不保奖励的非法群拒答）/ 2（check-sample 样本不足）/ 3（文件缺失、argparse 用法错误、模型与群规模不一致）全档吻合；`--help` 退出码 0。
- **关键常量对代码**：逐元素验证上限 5,000（`ELEM_VERIFY_CAP=5000`）、等变容忍 `tol=1e-9`、canonize 搜索树节点上限 `CANON_NODE_CAP=400000`、采样门槛 10,000（记录字段 `threshold.overall_min_budget=10000`）——与 README/文档主张一致。
- **证据索引（`docs/evidence.md`）**：50 个锚点全部有定义；全仓 markdown/yml/toml 引用的锚点零悬空；每个锚点引用的机器可读记录文件在主项目中全部存在；16,384 态 3,600 s 干净超时锚点（E48）的 `budget_sec=3600.0 / wall_sec=3600.2 / stdout 0 字节 / stderr 0 字节` 逐字段核对相符。
- **对外纪律口径**：组合式定位表述在两 README §1 在位；全仓无「首创/first/no prior/novel」式对标主张（"first public release" 系发行事实）；无「经真实系统验证」式主张（"Not production-hardened" 等均为免责声明）；压缩比全部以「读数、非收益主张」口径书写。

### 第 5 步：预检中发现并已修复的 15 处问题（含修复后复跑隔离自检）

| # | 文件 | 问题 | 修复 |
|---|---|---|---|
| 1 | `wuxing_gua/confidence.py` | 注释含内部轮次号 | 删除该编号，保留语义 |
| 2 | `wuxing_gua/core_discover.py` | 注释引用内部文档名（案例修复记录） | 改为中性描述 |
| 3 | `wuxing_gua/core_discover.py` | 注释引用内部文档名（并集策略） | 改为指向本包 README 对应小节 |
| 4 | `wuxing_gua/core_discover.py` | 注释含内部回归约束编号 | 删除编号 |
| 5 | `wuxing_gua/cli.py` | `--pad-aware` 帮助文本引用内部文档名（用户可见） | 改为引用结果记录 + 证据索引锚点 E12 |
| 6 | `wuxing_gua/cli.py` | `--multi-label` 帮助文本指向 README 已不存在的小节名 + 一个多余右括号 | 改指现行小节「三标志怎么选」，修掉括号 |
| 7 | `src/experiments_completeness.py` | 头注引用内部文档名；校准环境计数 6 与记录的 7 不符；预期表标注为裁决改判前旧口径 | 改为引用结果记录与锚点 E50，改为「7 个校准环境实例（首版预期表）」并保留裁决更正注记 |
| 8 | `src/experiments_completeness.py` | 常量区注释引用内部文档名 | 改为引用结果记录 `meta.constants` 与锚点 E50 |
| 9 | `src/experiments_completeness.py` | 注释引用内部文档名 | 中性化 |
| 10 | `src/experiments_p3.py` | 注释引用内部文档名 | 中性化 |
| 11 | `src/experiments_p3.py` | 实测注引用内部文档名 | 保留量级口径数字、删除文档指引 |
| 12 | `src/experiments_discover_labeling.py` | 注释引用内部文档名 | 中性化 |
| 13 | `wuxing_gua/README.md` | 完整性告警器校准标注过时：写「6 案例/7 实例」且把 SYS-3 A 标为反例（裁决改判前旧预期），与记录的 4 正例/3 反例、7/7 符合矛盾 | 按 `experiments_completeness.json → calibration_summary` 现读改写（4 正例/3 反例、7/7 符合、0 误报/0 漏报、gua64 无 ground truth 仅展示），指向锚点 E50 |
| 14 | `wuxing_gua/README.md` | 出处表含内部轮次号 | 删除编号 |
| 15 | `docs/evidence.md` | 完整性告警器阈值标定无锚点（`wuxing_gua/README.md` 原有「见 evidence.md」指针悬空） | 新增锚点 **E50**（6 个阈值常量 + 校准表 4/3/7-7/0/0 + 修复前后对照记录），指针全部落到实锚 |

注：对 `src/` 研究代码的修复全部为**注释级**（判据逻辑零改动），修复后做了语法编译检查并重跑完整隔离自检（13/13 PASS）。

## 回归防线（发布后仍会自动复查）

主项目的数字一致性审计（`src/audit_consistency.py`，纯标准库）在原有 569 条断言基础上新增 4 条可复跑断言，本次预检的三类关键结果已固化进去：

1. **隔离实跑**：整树复制到临时目录后现跑 `--help` / demo 双跑逐字节一致 / 示例 1 discover（退出码 0、order=2、n_orbits=24）/ selftest 13 分支口径在盘；
2. **黑话泄漏 v2 扫描**：20 个中文黑话词 + 大小写敏感票据 token 正则（2 类），全树零命中；
3. **双语数字三方回源**：13 组数字（json 现读 ↔ 英文书写 ↔ 中文书写）+ 4 项现算复核 + Q6 示例 720/7；
4. **证据锚点卫生**：锚点引用零悬空、引用源文件全部在盘、E50 常量与校准表现读相符。

追加后全量审计实测：**573 条断言 PASS 573 / FAIL 0 / MISSING 0，退出码 0**（57.7 s）。

## 遗留风险清单（发布前知悉，无阻断项）

1. **豁免类标识符**：随附 `src/` 研究代码的文件名（如 `experiments_p3.py`、`experiments_p4.py`）与 `docs/evidence.md` 引用的记录文件名/字段名中，不可避免地含有内部系列号片段（`p3`/`p4`/`w3`/`sys3` 等）。这是两条更高优先级约束的共同结果——「判据核心 import 自研究代码，未复制、未改写」（改文件名即破坏该主张）与「每个数字的回源路径必须真实」（引用即须逐字）。大写票据编号 token（单字母加序数形式，两类正则）在全仓为零命中；CLI 输出字段 `w3d_score` 保留原名，以与证据索引 E19/E20 引用的校准记录字段保持同名可对照，改名将造成工具输出与引用记录脱钩。
2. **单维护者、无第三方复现**：`docs/boundaries.md` 限制 11 已如实声明；发布本身不改变该状态。
3. **大文件**：`examples/gw_teambattle_model.json`（约 11.1 MB）与 `examples/gw_teambattle_group_h.json`（约 4.2 MB）远低于 GitHub 单文件 50 MB 告警线，`examples/README.md` 已说明。
4. **并发修改风险**：预检期间对每个被改文件均先核对修改时间（mtime）再动笔，预检窗口内未观察到并发写入；若此后仓库仍有其他会话在写，请重跑本预检（五步均可照抄重做）。
5. **`__version__` 双口径**：包内 `__version__ = 1.0.0` 与发行版 `pyproject.toml` 的 `0.1.0` 不同源，`wuxing_gua/README.md`「安装」一节已声明以 pyproject 为准。
6. **zipapp 形态不可用**：`wuxing_gua/README.md` 已声明实测原因（`ZipAppError` + `<pyz>/src` 非真实目录），不提供 `.pyz`。
7. **耗时口径**：selftest 两分钟量级（90 s 上下的实测带），CI 超时 10 分钟内充足（`.github/workflows/ci.yml` 已按此配置）。

## 发布三行命令（git init / add / commit / push）

在本目录（`github_release/`）下执行：

```bash
git init && git add . && git commit -m "wuxing-gua 0.1.0 — initial public release"
git branch -M main && git remote add origin <你的仓库URL>
git push -u origin main
```

- 第 1 行：初始化仓库并完成首次提交（`.gitignore` 已覆盖 `__pycache__/`、`demo_fixtures/` 等运行产物，不会误提交）；
- 第 2 行：主分支命名并绑定远端（把 `<你的仓库URL>` 换成实际地址）；
- 第 3 行：首次推送。推送后 `.github/workflows/ci.yml` 会在每次 push / PR 上自动跑 `--help` 冒烟 + 全量 selftest（13 分支）。
- 提交前建议确认：`git status` 里没有意外文件（尤其本地生成的 `demo_fixtures/`、`group_discovered.json`，均已被忽略规则覆盖）。
- 预检方仅验证到「可以发布」为止，**未执行任何 git 操作**（init/add/commit/push 均由发布者执行）。

## 复验方式（任何人可照做）

```bash
# 隔离自跑
cp -r github_release /tmp/wx && cd /tmp/wx
python -X utf8 -m wuxing_gua demo --out demo_fixtures
python -X utf8 -m wuxing_gua selftest          # 期望 13/13 PASS、退出码 0
# 示例复跑（退出码与读数见 examples/README.md）
python -X utf8 -m wuxing_gua discover --trans examples/ticketfsm_milestones_model.json
python -X utf8 -m wuxing_gua check --trans examples/gw_chainrot_model.json --group examples/gw_chainrot_group_h.json
python -X utf8 -m wuxing_gua check --trans examples/gw_teambattle_model.json --group examples/gw_teambattle_group_h.json
```

每个引用数字的原始记录路径见 `docs/evidence.md`（一行一锚点）。

## 追记：易懂性审校（2026-10-28，预检完成后）

预检之后，同日另做一轮「新手视角」易懂性/实用性审校（三屏可懂：这是什么/为何在乎/怎么用；五分钟可用：真实用户能跑通并看懂输出）。修订全部为**表达层**，逐条清单见 `docs/revision-log-w28.md`（23 处修订，另新增文件 2 个）：

- 新增 `docs/glossary.md`（15 个核心术语，一句人话 + 一例，英文）与 `docs/revision-log-w28.md`（本审校新增 2 个文件；追记写入时同波并行任务另新增 `docs/faq.md`、`docs/interpreting-output.md`，属外部产物、本审校未改动其内容）；
- README×2 同步新增：§1 具体化背景段 + Mermaid 准入流程图（双语各一、去标签结构逐线同构）+ 术语表指针，§2 输入格式指针，§4「预注册判定」列脚注，§7 术语表链接；中文版另做直译腔润色（回源→溯源等 4 处，数字与节结构不动）；
- `docs/quickstart.md`（术语表入口、`--no-build-isolation` 括注、「接下来去哪」补输入格式与术语表两条）、`docs/boundaries.md`（术语表入口）、`examples/README.md`（术语表入口、C5 x C5 记号解释）各做小幅修订；
- 复验（全部实跑，非转抄）：五个被改文件修订前后数字 token 逐个比对零漂移（唯一新增 token 为锚点编号 E17，属回源指针非数据，且双语同现）；黑话泄漏全树复扫零命中（最近一次现扫覆盖全部 54 个在盘文件，含同波并行任务新增 2 个）；整树临时副本隔离实跑 `python -X utf8 -m wuxing_gua demo` + `selftest`：**13/13 分支 PASS、退出码 0**（131.2 s，上限 180 s）；主项目 `src/audit_consistency.py` 追加 3 条 relw3 断言（术语表在盘与条数、修订清单自洽、双语结构含表行数与图同构），追加后全量审计 **576 条断言 PASS 576 / FAIL 0 / MISSING 0，退出码 0**。

## 2026-10-28 终检节（三波演进后对现役全树复跑五步预检）

- 终检对象：本目录整树**现役状态**（包装波 → 审校波 → 样例波三波演进之后），在盘实数 **75 个文件**（前文各节的 49 / 54 为其当时口径，纯追加不改旧文）。
- 终检执行：2026-10-29；五步全部当日实跑（命令与退出码均为现跑取得，非转抄）。五步全过，无阻断项；新发现 5 处问题，已当场修复并复验。

### 第 1 步：隔离自跑（整树复制系统临时目录后现跑）

| 检查 | 命令 | 结果 |
|---|---|---|
| 隔离自检 | `python -X utf8 -m wuxing_gua selftest`（临时副本内） | **13/13 分支 PASS，退出码 0**（101.4 s，上限 180 s） |
| 六级阶梯端到端 | 12 条主命令（下表）逐一现跑 | **12/12 退出码与关键读数全部相符** |
| 安装冒烟（离线） | `python -m pip install . --target <临时目录> --no-build-isolation --no-index` | 安装退出码 0；装出 `wuxing_gua/`+`src/`+dist-info；随后在安装目录 `selftest` → **13/13 PASS、退出码 0**（105.4 s） |

12 条阶梯命令与读数核对口径（退出码逐条与 `examples/expected/` 及 `examples/README.md` 预期一致）：

| 阶梯 | 命令 | 退出码 | 关键读数（现跑 = 预期） |
|---|---|---|---|
| Rung 0 | `discover --trans examples/tier1_starter_model.json` | 0 | order 6、4 轨道、compression 2.0、trivial=false、无告警（对 expected/tier1_starter_expected.json 逐项符） |
| Rung 0 | `check --trans examples/tier1_starter_model.json --group examples/tier1_starter_group.json` | 0 | pass、2/2 元素 worst_tv 0.0、6 对 0 坏、order 6 / 4 轨道 / 2.0 |
| Rung R | `check --trans examples/tier1_starter_model.json --group examples/tier1_xor_goalswap_group.json` | 1 | reject、转移层 1/2 元素 worst_tv 1.0、奖励层 4/4 对全坏 |
| Rung 1 | `discover --trans examples/ticketfsm_milestones_model.json` | 0 | order 2、24 轨道、1.3333…、trivial=false、无告警 |
| 控制对 | `check --trans examples/ticketfsm_milestones_model.json --group examples/ticketfsm_group_found.json` | 0 | pass、2/2 元素 tv 0.0、0/8 对坏 |
| 控制对 | `check --trans examples/ticketfsm_milestones_model.json --group examples/ticketfsm_wrong_swap_group.json` | 1 | reject、1/2 元素 tv 1.0、7/8 对坏 |
| Rung S | `check-sample --samples examples/samples_tiny_100.jsonl --group examples/sampling_tiny_group.json --trans examples/sampling_tiny_model.json` | 2 | abstain、n_req_total=375.5474…（expected 原值逐位一致） |
| Rung S | `check-sample --samples examples/samples_tiny_10000.jsonl …` | 0 | pass、n_samples=10000 |
| Rung S | `check --trans examples/sampling_tiny_model.json --group examples/sampling_tiny_group.json` | 0 | pass、完整表与采样判定一致 |
| Rung S | `check-sample --samples examples/samples_ticketfsm_50000.jsonl --group examples/ticketfsm_group_found.json --trans examples/ticketfsm_milestones_model.json` | 1 | reject、L1 奖励层 11/24 轨道报警（边界演示如实拒答） |
| Rung 2 | `check --trans examples/gw_chainrot_model.json --group examples/gw_chainrot_group_h.json` | 0 | pass、5/5 元素 tv 0.0、0/960 对坏、order 5 / 128 轨道 / 4.0× |
| Rung 3 | `check --trans examples/gw_teambattle_model.json --group examples/gw_teambattle_group_h.json` | 0 | pass、25/25 元素 tv 0.0、0/176,640 对坏、order 25 / 1,024 轨道 / 16.0× |

其中 8 条构成**六级阶梯退出码矩阵**（Rung 0 的 0,0 + Rung R 的 1 + Rung 1 的 0 + Rung S 的 2,0,1 + 控制对的 0,1），已固化为审计断言 `relw7.ladder.matrix`（对 expected 记录与 `examples/README.md` 阶梯表现算比对；本节所列 12 命令为终检当日隔离实跑）。

### 第 2 步：黑话泄漏全仓 grep 复扫（v3 词表 = 既有词表 + 终检自补变体）

- 词表：relw1 全部 11 条正则 + relw2 全部 20 中文子串与 2 条大小写敏感票据 token 正则，另自补英文/中文变体（大写票据 token `W[0-9]+`、英文 wave、内部计划文档「roadmap」加小节号的相邻引用形态、内部流程词、波序编号类中文变体等）。
- **新发现并修复 5 处**：`src/` 研究代码注释以内部计划文档「roadmap」加小节号（§9 / §11.1 / §12 / §12.1 / §12.5）的形式引用该文档（4 个文件、5 处；包装波词表只查该文档名后跟斜杠的路径形态，未覆盖「文档名+小节号」相邻形态）。修复为中性描述（预注册记录在案口径），**判据逻辑零改动**：4 文件语法编译检查通过，修复后整树复跑 12 条阶梯命令 12/12 相符。详见下节修复清单。
- 修复后复扫：扩展词表全树零命中。其余原始命中逐条分诊为正当用法并记录在案：`internal error`（退出码 3 语义，5 处）、"wave through"（动词短语，4 处）、CONTRIBUTING/boundaries 的 "internal consistency"（自述其一致性审计）、RELEASE-CHECK/revision-log 两份发布过程日志对审计链的如实自述（relw6.revision.log 断言反而要求其中 relw5/relw6 标识在位）。历史标识符豁免沿用包装波口径（src 文件名 p3/p4 等系列号片段、小写 w28/w29 日志文件名、`w3d_score` 输出字段名）。
- 对外主张红线（N5/N6 双语）：「首创/前所未有/经真实系统验证/生产验证/first/novel/unprecedented/no prior/validated on production」全树扫描，33 处原始命中逐条分诊为零违规（时序用法如 "guess first"、免责声明 "Not production-hardened"、发行事实 "first public release"、规则自引）。

### 第 3 步：双语一致性（README.md ↔ README.zh-CN.md ↔ quickstart ↔ examples）

- 结构：编号节 1..7 一一对应、逐节数字 token 集合与表行数相等、各含 1 个 mermaid 准入流程图且去标签结构 12 行逐线同构、语言互链在位；
- 六级阶梯同步：`examples/README.md` 阶梯表恰 6 行（六档文件名全在表）；quickstart §8 六档实质条目齐（starter cube / refusal / control pair / abstain / 512 / 16,384）；双语根 README 六级表述同步（EN six-rung / ZH 六级，check-sample 与 examples 提及计数两版相等）；
- **数字抽验 15 组三方回源全部一致**（英文书写 + 中文书写 + 主项目机器记录现读）：32 态×5 动作、阶 2/轨道 24、1.333×、512=465+47、75 vs 5、120,000 步 0 偏差、16,384=14,415+1,969、25/25 与 0/176,640、1,024 轨道 16.0×、AUC=1.0/115 实例、0/100、门槛 10,000、Q6 720/7，另样例波自证数字 2 组（n_req_total≈376、starter 阶 6/4 轨道/2.0，机读记录在发布仓 `examples/expected/`）。

### 第 4 步：主张 vs 实况

- **五子命令 + 六标志逐一 `--help` 复对**：discover/check/check-sample/selftest/demo 齐全；`--preset {robust}` 帮助文本明写「robust = --canonize --extra-candidates --multi-label 8 三标志全开」；`--seed` 默认 20261025；三份文档（README×2/quickstart）18 行标志表全部与 `--help` 相符；check/--group、check-sample/--samples/--group/--trans、demo/--out 参数齐；
- **证据索引（docs/evidence.md）：锚点恰为 E1..E50 共 50 个**；锚点引用的 21 个机器记录文件全部在盘（pilot/ 与 experiments_*.json 对主项目根、examples/ 三模型对发布仓）；
- **CI（.github/workflows/ci.yml）**：触发器 push+pull_request、ubuntu-latest、timeout-minutes 10、Python 3.12、`--help` 冒烟 + 13 分支 selftest 两步齐全；
- **残留检查：全树无 .git / __pycache__ / *.pyc / egg-info，文件数 75**。

### 第 5 步：终检发现并已修复的 5 处问题（修复后复跑）

| # | 文件 | 问题 | 修复 |
|---|---|---|---|
| 1 | `src/experiments_c_attribution.py` | 注释以内部计划文档「roadmap」+小节号 §12 相邻形态引用该文档 | 改为「各 scan 结果记录的 structure_evidence 块」中性指称 |
| 2 | `src/experiments_restart_scan3.py` | 注释以同形态引用该文档小节 §9 | 改为「判据本身随预注册记录落盘」 |
| 3 | `src/experiments_restart_scan5.py` | 注释以同形态引用该文档小节 §11.1（「逐字对应」） | 改为「预注册逐字在案」 |
| 4 | `src/experiments_restart_scan6.py` | 模块头注以同形态引用该文档小节 §12.1 / §12.5 | 改为「预注册与可行性记录」 |
| 5 | `src/experiments_restart_scan6.py` | 注释以同形态引用该文档小节 §12.1（「逐字对应」） | 改为「预注册逐字在案」 |

修复全部为**注释级**（判据逻辑零改动）：4 文件 `py_compile` 通过；隔离副本同步修复件后复跑 12 条阶梯命令 12/12 相符；扩展词表复扫（含「文档名+小节号」相邻形态禁令）零命中。本节五步结果已固化为审计断言 4 条：`relw7.ladder.matrix`（六级阶梯 8 命令退出码矩阵现算比对）、`relw7.finalcheck.section`（本节在盘且要素自洽）、`relw7.release.count`（文件计数 75 及分目录构成）、`relw7.jargon.v3`（扩展词表全树零命中）。追加后全量审计实测：**599 条断言 PASS 599 / FAIL 0 / MISSING 0，退出码 0**。

### 与包装波预检（上文）的差异说明

1. **检查面扩容**：包装波预检时 `examples/` 为三案例样例；现役树为六级阶梯（新增 8 条 expected 记录、2 个生成器、采样三件套、控制对），本轮新增 12 命令端到端矩阵与 Rung S 退出码档位（2/0/1）的现跑复核——包装波预检无此面。
2. **文件计数演进**：49（包装波）→ 54（审校波追记口径）→ **75（现役实数）**；其中 `docs/` 9、`examples/` 26（含 expected/ 8 件）、`src/` 19、`wuxing_gua/` 11、`licenses/` 1、根级 9（含 .github/workflows/ci.yml）——分桶求和 = 75（2026-10-29 审计订正：原枚举漏 licenses/ 一桶）。
3. **词表演进**：本轮 v3 词表在 relw1+relw2 之上补内部计划文档「roadmap」+小节号相邻形态的禁令，并首次把 N5/N6 对标主张红线做成双语显式扫描；据此新发现 5 处注释级泄漏并修复（包装波 15 处、审校波 23 处修订之外的增量）。
4. **expected 断言体系**：8 件 expected 记录由 relw5/relw6 断言在链钉住；本轮以隔离实跑 12/12 独立复核其与现役 CLI 行为一致，两道防线并行。
5. **行为零漂移确认**：修复仅注释级；隔离自跑、安装冒烟、阶梯矩阵三道复验与包装波结论一致（13/13、安装后 13/13、退出码矩阵不变）。
