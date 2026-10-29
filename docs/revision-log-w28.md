# Revision log: readability & usability pass (docs/revision-log-w28.md)

- 审校日期：2026-10-28
- 审校视角：「第一次见到本仓库的研究者/工程师」——三屏可懂（这是什么/为何在乎/怎么用）与五分钟可用（真实用户能跑通并看懂输出拿到价值）。
- 修订原则：**表达层修订**——
  1. 数字零变更：修订前后全部数字逐个一致（审后复核：五个被改文件数字 token 与修订前快照比对，唯一新增 token 为锚点编号 E17，属回源指针非数据，且双语同现）；
  2. 双语逐节对等：README.md ↔ README.zh-CN.md 同步改（编号节 1..7 对齐、数字 token 集合全等、新增图结构逐线同构）；
  3. 黑话零泄漏：改后全树 51 文件复扫零命中（词表沿用现行审计口径）；
  4. 裁剪树 selftest 13/13 收尾复验通过（文档层改动不触及代码）。

**修订处数：23**（下列 1–23，按改动位点计）。另有**新增文件 2 个**（不计入修订处）：`docs/glossary.md`（15 个核心术语，英文，一句人话 + 一例）、`docs/revision-log-w28.md`（本清单）。

1. 位置：README.md §1。问题：首屏说了「检查对称群是否安全」，但从未具体说明「对称群」在这个语境里是什么，30 秒内说不出它判的对象。改法：§1 首段后新增一段具体化说明——对称群 = 保持系统行为不变的状态置换集合；轨道 = 群的置换能互达的状态；压缩 = 每轨道留一个代表态。
2. 位置：README.md §1 末。问题：核心流程（黑盒数据 + 候选群 → 门 → 三判决）纯文字，一图胜千言缺失。改法：新增 Mermaid 流程图（GitHub 原生渲染）：输入（转移表或采样轨迹 + 候选群）→ 准入门 → 放行（exit 0）/ 拒答（exit 1）/ 不下结论（exit 2，仅 check-sample）。
3. 位置：README.md §1 末。问题：orbit / equivariance / total variation / generator / padding states 等术语使用前无解释、无查询入口。改法：加一句指向 docs/glossary.md 的术语表指针。
4. 位置：README.md §2 末。问题：quickstart 没说工具吃什么输入、去哪查文件格式——真实用户在「跑自己的系统」这一步会卡住。改法：加一句：输入 = 符合位串口径（n_states = 2**n_bits、动作 a = 翻第 a 位）的 JSON 转移模型，model / group / samples 格式见 wuxing_gua/README.md。
5. 位置：README.md §4。问题：证据表「Preregistered verdict」列的「primary prediction hit / repair loop closed」标签无可读解释，新读者无法复原判定含义。改法：表下新增脚注：预注册 = 结局档与判定规则在运行前先写死；两类标签各是什么意思；规则原文见 docs/evidence.md（锚点 E6、E17）。
6. 位置：README.md §7。问题：文档列表无术语表入口。改法：Docs 列表在 evidence.md 后插入 docs/glossary.md 条目（注明 plain-language definitions of the core terms）。
7. 位置：README.zh-CN.md §1。问题：同 #1（中文版）。改法：新增对等的中文具体化段落（对称群 / 轨道 / 每轨道留一代表）。
8. 位置：README.zh-CN.md §1 末。问题：同 #2（双语对等）。改法：新增同构 Mermaid 图，节点/边结构逐线一致，标签为中文（放行 / 拒答 / 不下结论）。
9. 位置：README.zh-CN.md §1 末。问题：同 #3（双语对等）。改法：加中文指向句（注明术语表为英文）。
10. 位置：README.zh-CN.md §2 末。问题：同 #4（双语对等）。改法：加位串口径输入说明 + wuxing_gua/README.md 指针。
11. 位置：README.zh-CN.md §4。问题：同 #5（双语对等）。改法：新增「预注册判定」列怎么读的脚注（含 E6、E17 锚点指引）。
12. 位置：README.zh-CN.md §7。问题：同 #6（双语对等）。改法：文档列表插入 docs/glossary.md 条目（标注「英文」）。
13. 位置：README.zh-CN.md §2。问题：「判据核心 import 自同树的 src/」是英文直译腔，不合中文技术写作习惯。改法：改「判据核心从同一目录树的 src/ 导入」（数字与节结构不动）。
14. 位置：README.zh-CN.md §4。问题：「可回源」非常用词（「回源」是 CDN 术语，中文技术写作惯用「溯源」）。改法：改「关键读数全部可溯源」。
15. 位置：README.zh-CN.md §6。问题：「这是口径限制」对应英文 protocol limitation，「口径」在此处易误读为统计口径。改法：改「这是协议设计的限制」。
16. 位置：README.zh-CN.md §7。问题：「回源索引」同 #14。改法：改「溯源索引」。
17. 位置：docs/quickstart.md 开头。问题：全文术语门槛高而无术语表入口。改法：引言区加一句指向 docs/glossary.md。
18. 位置：docs/quickstart.md §1。问题：安装命令中的 `--no-build-isolation` 对新手是无来由的咒语。改法：命令块下加括注：用环境内已有构建工具完成构建、安装自包含。
19. 位置：docs/quickstart.md §8。问题：「接下来去哪」列表缺两份对新用户最关键的文档：输入文件格式与术语表。改法：列表补 `wuxing_gua/README.md`（输入格式 + 全标志参考）与 `docs/glossary.md` 两条。
20. 位置：docs/boundaries.md 开头。问题：全文行话密度最高却无术语表入口。改法：首段加半句指向 docs/glossary.md。
21. 位置：examples/README.md 开头。问题：下文使用 orbit / order / generator 无定义入口。改法：引言末加一句指向 docs/glossary.md。
22. 位置：examples/README.md 案例 3。问题：「C5 x C5」群论记号未解释。改法：改为「两个 5 元循环群的直积，C5 x C5（25 元素）」（数字不变）。
23. 位置：RELEASE-CHECK.md 末。问题：预检完成后文档层又有表达层修订，原预检报告（49 文件口径）不反映现状。改法：末尾新增「追记」节，记录本轮修订概要与复验结果（数字零变更、黑话零命中、selftest 13/13、审计断言追加）。

复核口径（供审计）：修订处计数 = 23；新增术语表条目 = 15；新增图 = 1（双语一对，结构同构）。主项目 src/audit_consistency.py 同步追加 3 条 relw3 断言（术语表在盘与条数、修订清单在盘与修订处计数自洽、双语节结构含表行数与图对等）。

---

## 追加节：实用性审校（2026-10-28 同日第二审校轮；只追加本节，上文一字未动）

- 审校视角：「手里有个状态机/调度系统、想试试这工具能不能用」的真实用户——五分钟内跑通并看懂输出拿到价值；与上节（易懂性审校）互不动对方产物。
- 审校方式：先真跑再动笔——把整树复制到系统临时目录（模拟 clone），从零开始把上手路径完整跑一遍并逐步计时（单机量级口径，精确值不落入文档、以结果记录为准）。实测：零安装从仓库根直跑可行（`--help` 亚秒）；`discover` examples 工单模型（32 态）约 3 秒出真实系统结果（exit 0、order=2、24 轨道）；`check` 512 态亚秒、16,384 态约 12 秒（均 exit 0，读数与 examples/README 逐项一致）；demo 亚秒、demo Q6 discover 约 2 秒（720/7）；check-sample 10,000 条 pass（exit 0）、100 条 abstain（exit 2）；`--report-confidence` 在 ticketfsm 上复现 `statistical_suspicion`（wl_gap 6.0）、在平移夹具上复现 `proved_incomplete`（阶 6 vs 臂最大 720）；pip 安装约 8 秒、装后异目录可跑；selftest 约 2 分钟 13/13（与锚 E41 量级一致）。
- 上手路径结论（据此优化步序）：安装不是第一价值的前提——零安装从仓库根直跑最快；第一价值优先打 examples 真实系统（秒级），demo 是安全触发拒答路径的沙盒，selftest 是信任步而非前置步。

**本节修订处数：14**（位点计）：

- 修订 ①（位置：docs/quickstart.md 引言末）：问题：最快价值路径（零安装 + examples 直跑）在全文没有任何入口，新手默认从安装起步。改法：引言末加「In a hurry?」块——零安装 examples discover 命令 + 秒级预期读数 + 输出解读指针。
- 修订 ②（位置：docs/quickstart.md §1）：问题：节名「Install」让安装看起来是必经第一步，零安装事实藏在 README 的附注里。改法：节名改「Install (optional — every command also runs without it)」，节首补零安装直跑说明段（安装动机改为「想在其他目录用命令时才需要」）。
- 修订 ③（位置：docs/quickstart.md §2）：问题：tour 直接进 demo 沙盒，没说 examples 更快、selftest 非前置。改法：§2 节首补一段（examples 三系统秒级单命令、demo 用于自己触发拒答路径、selftest 是一次性信任步）。
- 修订 ④（位置：docs/quickstart.md §3）：问题：discover 输出 JSON 字段多而无解读入口。改法：字段列表后补一句指向 docs/interpreting-output.md。
- 修订 ⑤（位置：docs/quickstart.md §8）：问题：「接下来去哪」缺输出解读与 FAQ 两条最常用入口。改法：列表补 docs/interpreting-output.md 与 docs/faq.md 两条。
- 修订 ⑥（位置：docs/boundaries.md「Verified scale bands」节后）：问题：既有边界是研究口径（规模带/局限），缺「我的系统该走哪条命令」的决策入口，也没有明确的「什么情况别用」。改法：新增「A user decision table」节——六行「系统特征 → 推荐路径」表（双候选直验/自动发现/采样判定/哑态模型/不确定形态/大规模）+ 五条明确劝退清单，数字全部沿用本文既有锚定读数。
- 修订 ⑦（位置：examples/README.md 引言）：问题：三案例定位（不重不漏各覆盖什么）无说明，输出 JSON 无解读入口。改法：引言补 docs/interpreting-output.md 链接 + 一段三案例定位说明（1=自动找群最小系统、2=哑态带手工候选验证、3=规模上限处验证廉价/发现让位）。
- 修订 ⑧（位置：examples/README.md 案例 1）：问题：命令后只有字段清单，没有「你会看到什么 + 它说明什么」。改法：命令后补 What you'll see / What it means 两行（order=2/24 轨道即「只有这一个非平凡对称」的完整答案）。
- 修订 ⑨（位置：examples/README.md 案例 2）：问题：同 ⑧。改法：补两行（两层零容忍全过 = 手工候选可安全依赖；4.0× 是结构读数非收益承诺）。
- 修订 ⑩（位置：examples/README.md 案例 3）：问题：同 ⑧。改法：补两行（16,384 态上验证仍秒级 = 验证才是该规模的承载路径，撞预算墙的是自动发现）。
- 修订 ⑪（位置：README.md §2）：问题：安装块在首屏第一位，零安装直跑与 examples 首值路径靠后。改法：§2 重排——「Fastest first value — no install step」（examples discover 命令 + exit 0/群阶 2/24 轨道）提前，安装块降为可选项，demo 示例段与输入格式段保留，段末补 interpreting-output 与 faq 双链接。
- 修订 ⑫（位置：README.md §7）：问题：文档列表缺两份新文档。改法：Docs 列表在 glossary 后插入 interpreting-output（what every output field means, with real values）与 faq（the questions that come up first）两条。
- 修订 ⑬（位置：README.zh-CN.md §2）：问题：同 ⑪（双语对等）。改法：同构重排——「最快的第一份价值——无需安装」提前，安装降为可选项，段末补两文档中文指针句。
- 修订 ⑭（位置：README.zh-CN.md §7）：问题：同 ⑫（双语对等）。改法：文档列表同步插入两条（标注输出解读为实跑值、FAQ 为英文）。

**新增文件 2 个**（不计入修订处）：`docs/interpreting-output.md`（三个命令的输出逐字段人话解读：字段含义/典型值/下一步动作；全部字段与数值取自当日对在盘 fixtures 与 examples 的实跑输出，量级口径不落精确计时）、`docs/faq.md`（10 问：非位串系统/输入格式/样本量/exit 1 是否错误/拒答后下一步/统计疑点是否=群错/能否加速训练/哑态模型/大模型发现慢/中英混排与脚本化）。

复核口径（供审计）：本节修订处计数 = 14（修订 ①..⑭）；新增文件 2；主项目 src/audit_consistency.py 追加 6 条 relw4 断言（FAQ 条数与门槛回源、输出解读字段覆盖与读数回源、决策表行数与劝退条数、examples 两行解读计数、quickstart 路径要素、双语 README 双链接）。数字零变更自查：本节修订新增表述中的数字（order=2、24 轨道、32 态、512、16,384、720/7、10,000、176,640、4.0×、6.0、9/9、3,600、75→5、375→25）全部取自上节修订后文本已在盘的锚定读数或当日实跑复核值，未引入新数据口径；双语 README 逐节 token 集合仍全等。
