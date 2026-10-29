# Revision log: teaching-ladder pass (docs/revision-log-w29.md)

- 审校日期：2026-10-28
- 审校视角：「第一次接触对称群概念的学习者」——沿 `examples/` 目录从上往下读，能否在纸上**看见**一次对称性、亲手**触发**一次拒答、并逐行读懂两种输出。
- 修订原则：
  1. **数字零编造**：本轮新增样例的群阶/轨道/退出码/违约对数全部来自当日对在盘文件的真实命令运行，机器可读记录落在 `examples/expected/`；
  2. **既有样例一字未动**：三个真实案例的模型与群文件（`ticketfsm_milestones_model.json` / `gw_chainrot_*` / `gw_teambattle_*`）不移动、不改内容（既有 sha 断言继续钉住）；案例 1–3 的 README 段落原文保留；
  3. **双语同步**：根 README 双语指针若提及新样例则两版同步（数字 token 集合逐节保持相等）；
  4. **黑话零泄漏**：新增文件全部过现行泄漏 grep 口径（大小写敏感票据 token 含大写 W/P+数字——本文件因此以小写 `w1` 作节标记）。

## 教学阶梯重审（标记 w1，先行审读）

以教学视角通读 `examples/README.md` 既有三案例，结论：**规模阶梯成立（32 → 512 → 16,384 态），教学阶梯缺两块**。

**断档一：起步台阶缺失。** 三个案例全部是真实系统的转录模型，最小的也有 32 态与业务语义（派单/接单/在途/……）。对称性在其中是「工具找到的结论」，不是「读者能自己看见的起点」——32 态的位交换对称画不出来，512/16,384 态更不可能。「肉眼看图 → 跑命令 → 读懂输出」这条最小学习闭环缺第一环：需要一个 ≤16 态、对称性能画在纸上、`discover` 秒级、输出字段少到能逐行读完的最小样例。

**断档二：拒答展示缺失。** 本工具的招牌能力是三态结论（放行 / 拒答 / 样本不足），但三个案例从头到尾全是 exit 0 放行；案例 3 提到一个 125 元素候选被拒（100/125 元素违约），那是叙述，不是读者可复跑的样例。拒答路径目前只能靠先跑 `demo` 生成沙盒夹具来体验（quickstart §4 的能量环境命令依赖 `demo --out` 先落盘）。按 `examples/` 路径走完全程的读者见不到一次 exit 1，也就学不会「拒答输出的违约读数怎么读」。

**断档三（连带）：两层判据缺一不可，无可跑入门实例。** 「保转移概率但不保奖励」的拒答演示在沙盒夹具里（能量环境 + XOR 平移群），但 examples 目录内没有任何可复跑的拒答实例；「为什么只查转移会放走坏群」只能听叙述。

**补法（本轮实施，全部实跑闭环：制作 → 真跑 → 读数落 `examples/expected/` → 审计断言钉住）：**

1. **一阶教学样例（tier-1 starter）**：`tier1_starter_model.json` —— 8 态「立方体登山」模型（3 bit 立方体顶点、动作 = 翻一位、goal 111 吸收、上坡 +1 / 下坡 −1），由随仓生成器 `make_tier1_samples.py` 确定性生成（重复运行逐字节一致）。对称性肉眼可画：绕 000–111 主对角线的 6 个旋转（三条轴的全部换序），轨道 = 立方体的 4 层「壳」。实跑（2026-10-28，github_release 根目录）：
   - `discover`：exit 0、群阶 6、4 轨道、压缩 2.0×、`trivial=false`、`completeness` 无告警（`probe_exhausted_no_certificate`、score 1.0）；两次独立运行 stdout 除计时字段（`assess_sec`）外逐字节一致——计时按量级口径处理，不落数字；发现群已存为 `tier1_starter_group.json`（= discover stdout 原样）。
   - `check`（发现群）：exit 0、`pass`、6/6 元素 `worst_tv` 0.0、奖励剖面 6 对 0 坏。
   - 读数记录：`examples/expected/tier1_starter_expected.json`。
2. **拒答配套样例（refusal demo）**：`tier1_xor_goalswap_group.json` —— 同一模型上「看似合法实则非法」的 2 阶群：非单位元 = XOR 001，把每个顶点与 bit-0 方向的邻居配对，**恰好把吸收 goal 态 7 与 6 换位**（裸立方体图上它边对边映射，所以「看似合法」）。README 让读者先猜再跑。实跑：
   - `check`：exit 1、`reject`、**两层都报警**——转移层 1/2 个元素不过（`worst_tv` 1.0，`first_bad` = 受检第 2 个元素），奖励剖面层 4 对全坏（4/4）；4 对违约对均可按 expected 内的手查注释逐对验算。
   - 读数记录：`examples/expected/tier1_xor_goalswap_expected.json`。
3. **文档面**：`examples/README.md` 重写为五样例教学阶梯（新增阶梯总表、starter 三步走查、拒答先猜再跑两节；案例 1–3 原文保留）；`docs/quickstart.md` 与双语根 README 各补一条指针（双语同步）。原有「本文件数字都有机器可读出处」的声明相应收窄：三个真实案例的数字仍由 `docs/evidence.md` 锚定，两个教学样例的数字改由 `examples/expected/` 直接承载（`docs/evidence.md` 本轮未动——不在本波工作面）。
4. **审计**：主项目 `src/audit_consistency.py` 纯追加 6 条 relw5 断言（模型与生成器在盘及形状、starter 群阶/轨道/退出码钉住、拒答 exit 1 与 1/2 元素及 4/4 违约对钉住、README 提及计数、quickstart 与双语指针同步、本修订清单在盘）。

**新文件清单（7 个，全部新增）**：`examples/make_tier1_samples.py`、`examples/tier1_starter_model.json`、`examples/tier1_starter_group.json`、`examples/tier1_xor_goalswap_group.json`、`examples/expected/tier1_starter_expected.json`、`examples/expected/tier1_xor_goalswap_expected.json`、`docs/revision-log-w29.md`（本文件）。**改动面声明**：既有 5 样例文件（三模型 + 两群）一字未动；docs 既有文档中仅 `docs/quickstart.md`（三处指针句）与双语根 README（§2 一句、§7 示例条目，双语同步）被追加/改写；`docs/evidence.md` 等其余文档一字未动。

复核口径（供审计）：新样例 2 个（各含模型/群/expected 三件套，拒答样例复用 starter 模型）；实跑退出码 = discover 0 / check 0 / check 1；starter 读数 = 阶 6、4 轨道、压缩 2.0×、6 对 0 坏；拒答读数 = 1/2 元素 `worst_tv` 1.0、4/4 对坏；生成器重复运行逐字节一致（`--check` 自校验）；全部新文件过黑话泄漏 grep 零命中。收尾复验：CLI selftest 13/13 PASS（98 s 量级，上限 180 s 口径）；本波追加 6 条 relw5 断言单跑 6/6 PASS；全量审计在本波收尾时点的快照为 588 条全 PASS（随后队友并级追加与 relw4 口径演进落地，最终数字以收编轮重跑的汇总行为准）。运维注意：在发布仓根目录跑 CLI（含 selftest 子进程）会写 `wuxing_gua/__pycache__` 字节码缓存，而 relw1.closure 钉住 `wuxing_gua/` 文件面——**跑完 CLI 后、跑审计前**需清一次 `__pycache__`（本波实测两次踩中、两次清理后复验通过；本波追加的 relw5 现跑断言已带 `PYTHONDONTWRITEBYTECODE=1` 自不留痕）。

跨写者备注（2026-10-28 收尾时在案）：同波并行队友在 `examples/README.md` 追加了 control-pair 小节与 Rung S（采样）级并在其中使用「What you'll see / What it means」两行串 6 次，使既有断言 relw4.examples.twoliner 的「各恰 3 次」口径变为 9/9——该钉的演进已有裁决授权（改为 `n_see==n_mean 且 ≥3` 下限式 + 按落盘计数重钉），由队友面处置，本波未动其内容、未动既有断言；本波自有断言以 `relw5.*` 为前缀，后续追加者留意 ID 撞车（撞者改名并报备）。

---

## 追加节：采样档波（Rung S 采样三件套 + ticketfsm 控制对 + 边界演示；只追加本节，上文一字未动）

- 视角：「手上只有 `(s,a,s',r)` 日志、没有完整转移表」的使用者——`check-sample` 三态判定在既有示例无在盘样例，本节补齐采样档（Rung S）并入六级阶梯；与上文教学波互不动对方产物（其 7 文件与两节原文保留，`make_tier1_samples.py --check` 复验一致）。
- 数字零编造：本节全部读数来自 2026-10-28 对在盘文件的实跑，逐项记录于 `examples/expected/` 6 件；`n_req_total=375.547…` 直接取自工具输出（README 行文用 ≈376），不经手算。

**新增文件 14 个（全部只新增）**：`examples/sampling_tiny_model.json`（4 态双开关采样宿主：奖励只依赖后继态，满足采样层 L1 前提——构造规则在 meta）、`examples/sampling_tiny_group.json`（discover stdout 逐字节存盘）、`examples/make_samples.py`（确定性轨迹生成器：均匀随机策略、种子 20261028、`--check` 三份在盘样本逐字节复生）、`examples/samples_tiny_10000.jsonl`、`examples/samples_tiny_100.jsonl`（= 前者前 100 行）、`examples/samples_ticketfsm_50000.jsonl`、`examples/ticketfsm_group_found.json`（discover stdout 存盘，控制对与边界共用）、`examples/ticketfsm_wrong_swap_group.json`（换 dispatched/accepted 两里程碑位的错误候选，meta 记成因）、`examples/expected/` 6 件（ticketfsm 控制对两件 + 采样三件 + 边界一件）。

**修订处 6**：`examples/README.md` 引言（Five→Six 及构成句）、阶梯总表插 S 行（5→6 行）、案例 1 末追加「The control pair」小节、新增 `## Rung S` 整节、File sizes 表补 14 行 + Where-the-numbers 补 6 件 expected、`docs/quickstart.md` §5/§8 采样指针；另有双语根 README §7 示例条目同步（five-rung→six-rung / 五级→六级，双语对等）。

**实跑退出码（github_release 根目录，python -B -X utf8 -m wuxing_gua）**：check-sample(100) → **exit 2** abstain（n_req_total=375.5，工具自报需求量）；check-sample(10000) → **exit 0** pass；宿主完整表 check → exit 0 pass（采样判定与完整表版判定一致）；ticketfsm 发现群 check → exit 0 pass（2/2 元素 tv 0.0、0/8 对）；ticketfsm 错候选 check → **exit 1** reject（1/2 元素 tv 1.0、7/8 对）；ticketfsm 50,000 条采样对同一合法群 → **exit 1** reject（L1 奖励层 11/24 轨道报警）。

**边界发现（如实记录）**：ticketfsm 与 tier1-cube 两模型的奖励属「动作/移动」（+1 合法推进或上坡 / −1 非法尝试或下坡）而非后继态，采样层廉价奖励检查的 r=f(s') 前提不满足——两模型上 check-sample 在任意样本量都 exit 1，而完整表版 check 对同一群通过。采样 pass 一致性演示因此改在 4 态宿主模型上做；ticketfsm 50,000 条实测作为**边界演示**入盘（expected 内含用户侧前提说明），Rung S 与 quickstart §5 各用两句人话写明适用前提。此为给用户的诚实提示，非缺陷遮掩。

**主项目断言报备（审计核对用）**：①relw4.examples.twoliner 与 ②relw5.examples.readme 两处按 2026-10-28 裁决授权（断言演进判例第五次适用）改为下限式（两行配对计数相等且 ≥3 / 阶梯表 ≥5 行，改动处代码注释留痕）——原「恰 3+3 / 恰 5 行」与采样档每命令两行格式、阶梯并级直接冲突；③本波新增 **relw6** 断言 7 条（三件套在盘与字节复生、采样双演示退出码 2/0 与完整表一致性、边界 11/24 钉住、控制对 0/1 与错群 elements 现算重建、阶梯表 6 行与两行解读 **9+9** 重钉、双语 quickstart 指针同步、本节在盘）。ID 备案：relw5 前缀归教学波，本波用 relw6，后继追加者顺延。

复核口径（供审计）：新增 14 个文件；修订处 6 + 双语一对；两行解读计数 9+9（relw6.examples.readme 钉死）；阶梯表 6 行（relw6 钉死）；既有样例与教学波文件未动（既有 sha 断言与 `make_tier1_samples.py --check` 复验）。
