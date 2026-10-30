# Judging action semantics: `relabel` vs `fixed`

`check` verifies that a candidate group preserves the system's behavior. For the
transition layer that raises one question the mathematics alone cannot answer:
**when a renaming carries state `s` to `s'`, may action names travel with it?**
Both answers are legitimate — for *different kinds of systems* — and they can
disagree so sharply that the same candidate group passes under one and is
refused under the other. This page explains the two readings, how to tell which
one your system needs, and how to declare it so the tool never has to guess.

The judge math is the same in every case (zero-tolerance max TV = 0, unchanged
since the first release). What the declaration controls is **dispatch**: which
equivalence reading the transition layer applies.

## The two system classes

| | Switch / milestone class | Event-driven class |
|---|---|---|
| What an action is | A state bit being set: "open switch A", "dispatch ticket", "mark milestone accepted" | An external input with its own name: "receive FIN", "customer cancels", "sensor fires" |
| Action ↔ state link | An action is *defined by* the bit it flips — renaming the bits necessarily renames the actions | An action exists *independently* of states — its name is part of the protocol, not of the naming |
| When states are renamed | Actions must follow (the right reading) | Actions must stay put (the right reading) |
| Reading name | `relabel` | `fixed` |
| Where you have seen it | the starter cube, the two-channel sample, the work-order model, the 512- and 16,384-state cases | a TCP-shaped close handshake: rung 1c (`examples/eventfsm_*`) |
| Failure if you pick wrong | `fixed` rejects every real symmetry (TV 1.0 on the swapped bits) — formally strict, business-wrong | `relabel` admits permutations that merge distinct events — e.g. "the peer's FIN arrived" read as "the peer acknowledged": structure lines up, protocol breaks |

The second failure is not hypothetical. An external spot-check against the TCP
state diagram (RFC 9293) found two states (CLOSING and FIN-WAIT-2) that are
structurally identical but whose outgoing events differ (`rcv FIN` vs
`rcv ACK of FIN`): under `relabel` the tool admits their swap, with event names
pinned it refuses — and refusing is correct there. Rung 1c rebuilds that shape
as a minimal runnable example.

## The declaration

A group file may carry an optional top-level block:

```json
{
  "n_states": 8,
  "elements": [[0, 1, 2, ...], ...],
  "semantics": {"action": "relabel" | "fixed" | "explicit"}
}
```

| Value | Meaning | Transition-layer judge |
|---|---|---|
| `"relabel"` | Actions may be renamed along with the states. Correct for switch/milestone systems; the tool's historical default. | `bitstring` (when `n_actions <= n_bits`), else `generalized` |
| `"fixed"` | Event names are pinned: state renaming must preserve behavior with the *same* action names. Correct for event-driven systems. | `strict` |
| `"explicit"` | You spell out the action renaming yourself: add `"action_map": [ρ(0), ρ(1), ...]` (a bijection of the action indices). | `explicit` |

Rules the loader enforces:

- The block is optional. A group file without it still runs — see the warning
  below.
- `action_map` is only allowed with `"explicit"` and must be a bijection of
  `0..n_actions-1` whose length equals the model's `n_actions`.
- Any additional keys inside the block (e.g. a `note`) are ignored, so a saved
  `discover` stdout remains directly usable as a group file.

## What `check` does with it

The check output carries the resolution explicitly:

```json
"semantics": {"action": "fixed", "judge": "strict",
              "declared": true, "assumed": false, "source": "group_file"},
"semantics_assumed": false
```

- `judge` — which judge the transition layer actually ran (`bitstring` /
  `generalized` / `strict` / `explicit`); mirrored in `layer_transition.judge`.
- `declared` / `source` — whether the reading came from the group file, from
  the `--strict` flag (`source: "flag_strict"`, which overrides any
  declaration), or was the un-declared default.
- `semantics_assumed: true` — **the dangerous case, made loud**: the reading was
  not explicitly declared by the model author — either no semantics block at all
  (and no `--strict`), or only `discover`'s stamp on the group file (see below).
  The verdict is then computed under `relabel` and
  is *conditional on that reading*; the tool prints a warning on stderr and
  marks the payload. An admission tool with a permissive silent default is the
  wrong direction — the default still exists (historic outputs stay valid), but
  it is never silent.

`discover` stamps its own output with
`"semantics": {"action": "relabel", "assumed": true, "note": ...}`: its search
and its judge operate under the relabel reading, and a group file saved from
that stdout carries the stamp until the model author replaces it with an
explicit declaration. A stamped file keeps `semantics_assumed: true` in `check`
— assumed until *you* say otherwise.

`check-sample` is unaffected: it tests the reward layer on logs and never runs
the transition-equivalence judge.

## Deciding which your system is — three questions

1. **Can you say what the action *is* without pointing at a state?**
   "Receive FIN" makes sense without mentioning a state → event → `fixed`.
   "Open switch A" is *defined by* which bit moves → switch → `relabel`.
2. **If two states swap names, would the events around them still mean the
   same thing?** If yes (the events belong to the outside world) → `fixed`.
   If the events would have to swap too (the event is the bit) → `relabel`.
3. **Would merging two differently-named events be a bug in your domain?**
   Protocol events, UI events, customer actions: yes → `fixed`. Internal
   counter/milestone operations that exist only relative to the state layout:
   no → `relabel`.

When in doubt, run the candidate under both declarations and read the
difference: rung 1c is exactly that comparison, committed and reproducible
(`examples/expected/eventfsm_expected.json` records both readings of the same
elements side by side).

## Boundaries

- `discover`'s candidate search is built on the bit-string action convention
  (`n_actions <= n_bits`). Event-driven models with more events than state
  bits are outside its domain; the command refuses at the entry gate (exit 3)
  instead of crashing. Derive candidates by hand and judge them with `check` —
  rung 1c shows the full flow.
- The declaration changes the *transition layer* only. The reward layer
  compares reward profiles as sorted per-action multisets and is intentionally
  blind to action renamings; rung 1c's refused candidate passes the reward
  layer under both readings, which is why the transition layer exists.
- A single declared `action_map` is one global renaming applied to every group
  element. Per-element action renamings (the general relabel reading) remain
  the `relabel` judges' own derivation, unchanged.

## 中文速览

**两类系统**：动作 = 状态位（开关/里程碑位类）→ 换状态名必须连带换动作名 →
声明 `relabel`；动作 = 外部事件（协议报文、用户操作）→ 动作名独立于状态 →
声明 `fixed`。选错口径的代价：开关类选 `fixed` 会把真对称全拒（形式严格、
业务判错）；事件类选 `relabel` 会把"收到 FIN"当"收到 ACK"合并放行（协议错）。

**声明写法**（group.json 可选块，缺省时按 relabel 判读但输出
`semantics_assumed: true` 并在 stderr 显眼警示）：

```json
"semantics": {"action": "relabel"}      // 开关/里程碑位类（历史默认口径）
"semantics": {"action": "fixed"}        // 事件驱动类（= 旧 --strict）
"semantics": {"action": "explicit",     // 逐动作映射（自定动作改名）
              "action_map": [1, 0, 2]}
```

**自判三问**：①动作能否不指着状态说清自己是什么（能 → fixed）；②两状态换名
后周围事件含义是否不变（不变 → fixed）；③合并两个不同名事件算不算你领域的
bug（算 → fixed）。拿不准就把同一候选群按两种声明各跑一遍 `check`，对照读数
差——rung 1c 就是这套对照的可复现实例。

**注意**：`--strict` 是覆盖一切的 fixed（事件类快捷方式）；`discover` 按位串
动作约定搜索（n_actions > n_bits 时入口即拒、退出码 3）；奖励层对动作改名
天然不敏感，拦事件错位的是 `fixed` 口径下的转移层。
