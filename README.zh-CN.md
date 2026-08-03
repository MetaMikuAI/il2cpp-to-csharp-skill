# il2cpp-to-csharp-skill

[English](README.md)

一个用于从 Unity IL2CPP 二进制中恢复可读 C# 的 skill。它内置**两个相互独立的后端**，目标相同，且使用相同的 Il2CppDumper 产物：

| 后端 | 环境 | 文档 |
|---|---|---|
| **IDA**（原版） | IDA Pro + IDA Pro MCP | [`ida/SKILL.md`](ida/SKILL.md) |
| **Ghidra**（自研） | Ghidra GUI 或 `analyzeHeadless` | [`ghidra/SKILL.md`](ghidra/SKILL.md) |

它不是一键反编译器，而是帮助 agent 分析用户给出的 VA 或函数名，并在恢复 C# 时保留字符串、switch 分支、lambda、LINQ、async/coroutine 状态机和 IL2CPP 特有噪音。

**后端选择：** 根目录 [`SKILL.md`](SKILL.md) 是一个精简分发器：当 IDA Pro MCP 工具可用时选择 IDA 后端，当 Ghidra 环境可用时选择 Ghidra 后端，然后完全遵循该后端自己的 `SKILL.md`。两个后端互不混用指令，因此任一工作流都不会被稀释。

输出质量取决于所使用的 AI 模型能力和可用上下文。恢复代码仅供参考，应结合反编译输出、DummyDll stub 和实际运行行为进行人工核对。

## 前置要求

- **IDA 后端：** 已启用 IDA Pro MCP 的 IDA Pro。
- **Ghidra 后端：** Ghidra（GUI 或 `analyzeHeadless`）。
- 两者通用：Il2CppDumper 输出 —— `script.json`、`stringliteral.json`、`DummyDll/` 或 `dump.cs` —— 以及用于运行内置辅助脚本的 Python 3。

## 安装

仓库同时包含两个后端。**安装时由你选择装哪个（哪些）**，因此单后端安装与原版 skill 逐字节一致：

```bash
./install.sh                      # 交互式：选 1) IDA，2) Ghidra，3) 两者都装
./install.sh --ida                # 只装 IDA 后端（默认目标：~/.claude/skills/il2cpp-to-csharp-skill）
./install.sh --ghidra ~/.codex/skills/il2cpp-to-csharp-skill
./install.sh --both ~/.dsh/skills/il2cpp-to-csharp-skill
```

- `--ida` 安装原版 IDA Pro MCP skill，内容不变。
- `--ghidra` 安装自研 Ghidra skill，内容不变。
- `--both` 安装双后端分发器版；agent 在运行时根据环境选择后端。

### 通过 agent 安装

`install.sh` 只在终端里交互提示；agent 安装时无法应答，所以 agent 需要**先问你要装哪个后端**，再带上对应参数执行。可直接复制的 prompt：

先问你，再安装（推荐）：

```text
把 /path/to/il2cpp-to-csharp-skill 的 il2cpp-to-csharp skill 安装到我的 skill 目录（~/.claude/skills/il2cpp-to-csharp-skill）。先问我要装哪个后端 —— 1) 仅 IDA，2) 仅 Ghidra，3) 两者都装 —— 然后用对应的参数运行 install.sh，并验证安装结果。
```

安装整个 skill（双后端分发器版）：

```text
把 /path/to/il2cpp-to-csharp-skill 的完整 il2cpp-to-csharp skill（双后端）安装到 ~/.dsh/skills/il2cpp-to-csharp-skill：运行 ./install.sh --both，并验证分发器布局（SKILL.md、ida/、ghidra/）。
```

只安装单个后端（换 `--ida` / `--ghidra` 即装另一个）：

```text
把 /path/to/il2cpp-to-csharp-skill 的 il2cpp-to-csharp skill 只安装 IDA 后端到 ~/.codex/skills/il2cpp-to-csharp-skill：运行 ./install.sh --ida，并确认装好的 SKILL.md 是 IDA 工作流。
```

## 准备

1. 在 IDA Pro 中打开 IL2CPP 二进制，通常是 `GameAssembly.dll`，并等待初始分析完成。
2. 在当前 IDA 数据库中运行 Il2CppDumper 的 IDA 处理脚本，通常是 `ida_with_struct_py3.py`。
3. 用 dnSpy 打开 `DummyDll/Assembly-CSharp.dll`，并将它导出为 C# 项目。这会给 agent 提供可读的类、方法、字段、枚举、泛型和 `[FieldOffset]` stub。
4. 保留 `stringliteral.json`，需要解析字符串时提供它的本地路径。

## 用法

将本目录安装或复制为名为 `il2cpp-to-csharp-skill` 的 skill，然后让 agent 每次恢复一个函数：

```text
使用 $il2cpp-to-csharp-skill 来恢复 0x180000000.
IDA Pro MCP 已就绪。由 DummyDll/Assembly-CSharp.dll 通过 dnSpy 导出的桩代码项目位于 C:\path\to\DummyDllExport，stringliteral.json 位于 C:\path\to\stringliteral.json。
```

Ghidra 后端调用示例（安装的是 Ghidra 后端或双后端时）：

```text
使用 $il2cpp-to-csharp-skill 来恢复 rva:0x123456.
Ghidra 已就绪。项目位于 /path/to/ghidra-projects/game，程序为 UnityFramework，stringliteral.json 位于 /path/to/stringliteral.json。
```

## 示例

### 例 1

IDA

```C#
// local variable allocation has failed, the output may be wrong!
Cysharp_Threading_Tasks_UniTaskVoid_o ResultScene_UI_ResultSceneSavePannel__OverrideSave(
        ResultScene_UI_ResultSceneSavePannel_o *this,
        int32_t index,
        const MethodInfo *method)
{
  ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16_o stateMachine; // [rsp+20h] [rbp-38h] BYREF

  if ( !byte_18440B475 )
  {
    sub_18033D260(
      &Method_Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_Start_ResultSceneSavePannel__OverrideSave_d__16___,
      *(_QWORD *)&index);
    byte_18440B475 = 1;
  }
  memset(&stateMachine.fields.__1__state + 1, 0, 44);
  sub_18033CD60(&stateMachine.fields.__t__builder, 0LL);
  stateMachine.fields.__4__this = this;
  sub_18033CD60(&stateMachine.fields.__4__this, this);
  stateMachine.fields.index = index;
  stateMachine.fields.__1__state = -1;
  Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder__Start_ResultSceneSavePannel__OverrideSave_d__16_(
    (Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_o)&stateMachine.fields.__t__builder,
    &stateMachine,
    Method_Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_Start_ResultSceneSavePannel__OverrideSave_d__16___);
  return 0;
}


void ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16__MoveNext(
        ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16_o *this,
        const MethodInfo *method)
{
  struct ResultScene_UI_ResultSceneSavePannel_o *_4__this; // rdi
  __int64 v4; // rdx
  __int64 v5; // rcx
  __int64 v6; // rdx
  struct Cysharp_Threading_Tasks_UniTask_Awaiter_o v7; // xmm6
  __int64 v8; // rdx
  __int64 v9; // rcx
  __int64 v10; // rsi
  __int64 v11; // rax
  struct Cysharp_Threading_Tasks_CompilerServices_IStateMachineRunner_o *runner; // r8
  __int64 v13; // rax
  Cysharp_Threading_Tasks_UniTask_o u__1; // [rsp+30h] [rbp-28h] BYREF

  if ( !byte_18440BEC7 )
  {
    sub_18033D260(
      &Method_Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_AwaitUnsafeOnCompleted_UniTask_Awaiter__ResultSceneSavePannel__OverrideSave_d__16___,
      method);
    byte_18440BEC7 = 1;
  }
  _4__this = this->fields.__4__this;
  if ( !this->fields.__1__state )
  {
    u__1 = (Cysharp_Threading_Tasks_UniTask_o)this->fields.__u__1;
    this->fields.__u__1 = 0LL;
    this->fields.__1__state = -1;
LABEL_5:
    sub_180406670(&u__1, 0LL);
    if ( !_4__this )
      sub_18033D420(v5, v4);
    DEYU_AdpUISystem_PanelCollection_UIPanelBaseImpl__ClosePanel(
      (DEYU_AdpUISystem_PanelCollection_UIPanelBaseImpl_o *)_4__this,
      0LL);
    this->fields.__1__state = -2;
    sub_1804065D0(&this->fields.__t__builder, 0LL);
    return;
  }
  if ( !_4__this )
    sub_18033D420(this, method);
  _4__this->fields.m_BlockSubPanelCommand = 1;
  DEYU_AdpUISystem_PanelCollection_UIPanelBaseImpl__HidePanel(
    (DEYU_AdpUISystem_PanelCollection_UIPanelBaseImpl_o *)_4__this,
    0LL);
  u__1 = *ResultScene_UI_ResultSceneSavePannel__SavePlayerDataCoreAsync(&u__1, _4__this, this->fields.index, 0LL);
  sub_18033CD60(&u__1, 0LL);
  v7 = (struct Cysharp_Threading_Tasks_UniTask_Awaiter_o)u__1;
  if ( !byte_18440B3D8 )
  {
    sub_18033D260(&Cysharp_Threading_Tasks_IUniTaskSource_TypeInfo, v6);
    byte_18440B3D8 = 1;
  }
  if ( !v7.fields.task.fields.source
    || (unsigned int)sub_180004110(
                       0LL,
                       Cysharp_Threading_Tasks_IUniTaskSource_TypeInfo,
                       v7.fields.task.fields.source,
                       (unsigned int)_mm_extract_epi16((__m128i)v7, 4)) )
  {
    goto LABEL_5;
  }
  this->fields.__1__state = 0;
  this->fields.__u__1 = v7;
  sub_18033CD60(&this->fields.__u__1, 0LL);
  v10 = Method_Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_AwaitUnsafeOnCompleted_UniTask_Awaiter__ResultSceneSavePannel__OverrideSave_d__16___;
  if ( !byte_18440BF77 )
  {
    sub_18033D260(&Cysharp_Threading_Tasks_CompilerServices_IStateMachineRunner_TypeInfo, v8);
    byte_18440BF77 = 1;
  }
  if ( !this->fields.__t__builder.fields.runner )
  {
    v11 = *(_QWORD *)(*(_QWORD *)(v10 + 56) + 8LL);
    if ( (*(_BYTE *)(v11 + 306) & 1) == 0 )
      v11 = sub_180365730(*(_QWORD *)(*(_QWORD *)(v10 + 56) + 8LL));
    if ( !*(_DWORD *)(v11 + 224) )
      il2cpp_runtime_class_init(v11);
    (*(void (__fastcall **)(ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16_o *, struct Cysharp_Threading_Tasks_CompilerServices_AsyncUniTaskVoidMethodBuilder_o *, _QWORD))(**(_QWORD **)(v10 + 56) + 8LL))(
      this,
      &this->fields.__t__builder,
      **(_QWORD **)(v10 + 56));
  }
  runner = this->fields.__t__builder.fields.runner;
  if ( !runner )
    sub_18033D420(v9, v8);
  v13 = sub_180002C50(0LL, Cysharp_Threading_Tasks_CompilerServices_IStateMachineRunner_TypeInfo, runner);
  sub_180406800(&u__1, v13, *(_QWORD *)(*(_QWORD *)(v10 + 56) + 24LL));
}
```

GPT 5.5 (Codex)

```C#
private async UniTaskVoid OverrideSave(int index)
{
    m_BlockSubPanelCommand = true;
    HidePanel();

    await SavePlayerDataCoreAsync(index);

    ClosePanel();
}
```

Opus 4.6 (Copilot)

```C#
private async UniTaskVoid OverrideSave(int index) // By Opus 4.7
{
    this.m_BlockSubPanelCommand = true;
    HidePanel();
    await SavePlayerDataCoreAsync(index);
    ClosePanel();
}
```

mimo-v2.5-pro (Claude Code)

```C#
// ResultScene.UI.ResultSceneSavePannel
public async UniTaskVoid OverrideSave(int index)
{
    m_BlockSubPanelCommand = true;
    HidePanel();

    await SavePlayerDataCoreAsync(index);

    ClosePanel();
}
```

DeepSeek v4 pro (Claude Code) 重试一次

```C#
async UniTaskVoid OverrideSave(int index)
{
    m_BlockSubPanelCommand = true;
    HidePanel();
    await SavePlayerDataCoreAsync(index);
    ClosePanel();
}
```

Gemini 3.1 Pro (Copilot)

```C#
private async UniTaskVoid OverrideSave(int index)
{
    this.m_BlockSubPanelCommand = true;
    base.HidePanel();
    await this.SavePlayerDataCoreAsync(index);
    base.ClosePanel();
}
```

### 例 2

GPT 5.5 (Codex)

```C#
protected override IEnumerator OnPositiveBuffExecute(SpellExecutionContext spellExecutionContext)
{
    List<int> targetSeats = EventManager.Instance
        .TargetTablesAny(1000)
        .Except(EventManager.Instance.TargetTablesGuests(1000))
        .ToList();

    if (targetSeats.Count <= 0)
        yield break;

    List<NormalGuest> allNGuests = DataBaseCharacter.GetAllNormalGuests()
        .Where(x => /* __c.<OnPositiveBuffExecute>b__15_0, predicate not resolved by IDA MCP */ true)
        .ToList();

    GuestsManager guestManager = GuestsManager.Instance;

    Vector3 guestPosition = spellExecutionContext.GuestPosition.Value;
    Vector3 tablePosition = spellExecutionContext.GuestsController.DeskCode == -1
        ? default
        : GetGuestTable(spellExecutionContext.GuestsController.DeskCode);

    Vector3 aliceHand = guestPosition + new Vector3(
        tablePosition.x > guestPosition.x ? handOffset.x : -handOffset.x,
        handOffset.y,
        0f);

    bool dollEnd = false;

    PlayAudio(rewardSFX);

    foreach (int seat in targetSeats)
    {
        GameObject doll = Instantiate(rewardDoll);
        doll.transform.position = aliceHand;

        UIElementCluster uiElementCluster = doll.GetComponent<UIElementCluster>();

        Vector3 targetPosition = GetGuestTable(seat) + new Vector3(0f, -0.75f, 0f);
        uiElementCluster.GetObject<SpriteRenderer>(0).flipX = targetPosition.x > aliceHand.x;

        EventManager.Instance.StartCoroutine(SetLinenear(doll, uiElementCluster, seat));
        EventManager.Instance.StartCoroutine(
            LerpPosition(doll.transform, () => targetPosition, 1f));
    }

    yield return UnityCoroutineExtension.OneSecondDelay;

    dollEnd = true;

    yield return UnityCoroutineExtension.OneSecondDelay;

    IEnumerator SetLinenear(GameObject doll, UIElementCluster uiElementCluster, int seat)
    {
        LineRenderer lineRenderer = uiElementCluster.GetObject<LineRenderer>(0);
        lineRenderer.SetPosition(1, aliceHand);

        while (!dollEnd)
        {
            Vector3 position = doll.transform.position;
            lineRenderer.SetPosition(0, position + new Vector3(0f, 0.5f, 0f));
            yield return null;
        }

        Animator animator = doll.GetComponent<Animator>();

        if (EventManager.Instance.ShouldSkip)
        {
            animator.Play("AliceRewardDoll2");
            yield return UnityCoroutineExtension.HalfSecondDelay;
        }
        else
        {
            animator.Play("AliceRewardDoll1");

            SpriteMask mask1 = uiElementCluster.GetObject<SpriteMask>(0);
            SpriteMask mask2 = uiElementCluster.GetObject<SpriteMask>(1);

            NormalGuest guest1 = allNGuests.RandomSelectOne();
            NormalGuest guest2 = allNGuests.RandomSelectOne();
            SpriteRenderer dollSprite = uiElementCluster.GetObject<SpriteRenderer>(0);

            mask1.sprite = guest1.CharacterPixel.m_AnimatedSprites[1];
            mask2.sprite = guest2.CharacterPixel.m_AnimatedSprites[1];

            yield return UnityCoroutineExtension.QuarterSecondDelay;

            dollSprite.maskInteraction = SpriteMaskInteraction.VisibleInsideMask;

            yield return UnityCoroutineExtension.HalfSecondDelay;

            guestManager.SpawnNormalGuestGroup(
                new[] { guest1, guest2 },
                doll.transform.position,
                GuestGroupController.LeaveType.Fading,
                seat,
                false);

            yield return UnityCoroutineExtension.QuarterSecondDelay;
        }

        Destroy(doll);
    }
}
```

Opus 4.7 (Copilot)

```C#
protected override IEnumerator OnPositiveBuffExecute(SpellExecutionContext spellExecutionContext) // By Opus 4.7
{
    // NOTE(By Opus 4.7): cached __c.<OnPositiveBuffExecute>b__15_0 - Where predicate body
    // not directly resolvable from IDA (Method$ pointer indirection); preserved as
    // a placeholder lambda. Heuristic: filters unsuitable guests for the reward duo.
    List<NormalGuest> allNGuests = DataBaseCharacter.GetAllNormalGuests()
        .Where(g => /* TODO(By Opus 4.7): unresolved __c.<OnPositiveBuffExecute>b__15_0 */ true)
        .ToList();
    GuestsManager guestManager = MonoSingleton<GuestsManager>.Instance;

    Vector3 guestPos = spellExecutionContext.GuestPosition.Value;
    float xOffset;
    SpecialGuestsController guestsController = spellExecutionContext.GuestsController;
    if (guestsController.DeskCode == -1
        || GetGuestTable(guestsController.DeskCode).x > spellExecutionContext.GuestPosition.Value.x)
    {
        xOffset = this.handOffset.x;
    }
    else
    {
        xOffset = -this.handOffset.x;
    }
    Vector3 aliceHand = new Vector3(
        guestPos.x + xOffset,
        guestPos.y + this.handOffset.y,
        guestPos.z + 0f);
    bool dollEnd = false;

    PlayAudio(this.rewardSFX);

    List<int> tablesToReward = EventManager.Instance.TargetTablesAny(1000)
        .Except(EventManager.Instance.TargetTablesGuests(1000))
        .ToList();
    if (tablesToReward.Count <= 0)
        yield break;

    foreach (int seat in tablesToReward)
    {
        int capturedSeat = seat;
        GameObject doll = Instantiate(this.rewardDoll);
        UIElementCluster uiElementCluster = doll.GetComponent<UIElementCluster>();
        doll.transform.position = aliceHand;

        Vector3 tablePos = GetGuestTable(capturedSeat);
        Vector3 capturedTarget = new Vector3(
            tablePos.x + 0f,
            tablePos.y - 0.75f,
            tablePos.z + 0f);

        uiElementCluster.GetObject<SpriteRenderer>(0).flipX = capturedTarget.x > aliceHand.x;

        EventManager.Instance.StartCoroutine(SetLinenear_1(doll, uiElementCluster, capturedSeat));
        // original: <>c__DisplayClass15_1.<OnPositiveBuffExecute>b__2 returns capturedTarget
        EventManager.Instance.StartCoroutine(
            LerpPosition(doll.transform, () => capturedTarget, 1f));
    }

    yield return UnityCoroutineExtension.OneSecondDelay;
    dollEnd = true;
    yield return UnityCoroutineExtension.OneSecondDelay;
    yield break;

    // original: <OnPositiveBuffExecute>g__SetLinenear_1|15_1 (iterator state machine)
    IEnumerator SetLinenear_1(GameObject doll, UIElementCluster uiElementCluster, int seat)
    {
        LineRenderer lineRenderer = uiElementCluster.GetObject<LineRenderer>(0);
        lineRenderer.SetPosition(1, aliceHand);

        while (!dollEnd)
        {
            Vector3 dollPos = doll.transform.position;
            lineRenderer.SetPosition(0, new Vector3(
                dollPos.x + 0f,
                dollPos.y + 0.5f,
                dollPos.z + 0f));
            yield return null;
        }

        Animator animator = doll.GetComponent<Animator>();
        // NOTE(By Opus 4.7): BYTE4(EventManager.Instance[40].monitor) - an unresolved
        // boolean field on EventManager that picks between the two reward animations.
        if (/* TODO(By Opus 4.7): unresolved EventManager flag */ false)
        {
            animator.Play("AliceRewardDoll2");
            yield return UnityCoroutineExtension.HalfSecondDelay;
        }
        else
        {
            animator.Play("AliceRewardDoll1");
            SpriteMask spriteMask1 = uiElementCluster.GetObject<SpriteMask>(0);
            SpriteMask spriteMask2 = uiElementCluster.GetObject<SpriteMask>(1);
            NormalGuest guest1 = allNGuests.RandomSelectOne();
            NormalGuest guest2 = allNGuests.RandomSelectOne();
            SpriteRenderer dollSprite = uiElementCluster.GetObject<SpriteRenderer>(0);

            // NOTE(By Opus 4.7): NormalGuest vtable slot 6 returning an object whose
            // field at +0x28 (relative to its Fields) is a Sprite. Mapped here as a
            // portrait-style accessor; concrete member name unresolved.
            spriteMask1.sprite = guest1.GetVisual()/* TODO(By Opus 4.7): vtable._6 */.Sprites[0];
            spriteMask2.sprite = guest2.GetVisual()/* TODO(By Opus 4.7): vtable._6 */.Sprites[0];

            yield return UnityCoroutineExtension.QuarterSecondDelay;
            dollSprite.maskInteraction = SpriteMaskInteraction.VisibleInsideMask;
            yield return UnityCoroutineExtension.HalfSecondDelay;

            guestManager.SpawnNormalGuestGroup(
                new NormalGuest[] { guest1, guest2 },
                doll.transform.position,
                true,
                seat,
                false);
            yield return UnityCoroutineExtension.QuarterSecondDelay;
        }

        UnityEngine.Object.Destroy(doll);
    }
}
```

mimo-v2.5-pro (Claude Code)

```C#
// GameData.Core.Collections.NightSceneUtility.SkillCollection.Spell_Alice
public override IEnumerator OnPositiveBuffExecute(SpellExecutionContext spellExecutionContext)
{
    // State machine: _OnPositiveBuffExecute_d__15
    // Captures: this, spellExecutionContext
    // (coroutine body below)
    yield return null; // placeholder — see MoveNext
}


// Spell_Alice.OnPositiveBuffExecute (coroutine body)
private IEnumerator OnPositiveBuffExecuteCoroutine(SpellExecutionContext spellExecutionContext)
{
    var closure = new DisplayClass15_0();
    closure._this = this;

    // Get empty tables (target tables minus occupied tables)
    var emptyTables = EventManager.Instance.TargetTablesAny(1000, null, null)
        .Except(EventManager.Instance.TargetTablesGuests(1000, null, null))
        .ToList();

    if (emptyTables.Count <= 0)
        yield break;

    // Get all normal guests and filter
    closure.allNGuests = DataBaseCharacter.GetAllNormalGuests()
        .Where(/* b__15_0: predicate — likely guest.IsNormal / guest.IsSeated check */)
        .ToList();

    closure.guestManager = GuestsManager.Instance;

    // Calculate Alice's hand position with directional offset
    var guestPos = spellExecutionContext.GuestPosition.Value;
    var deskCode = spellExecutionContext.GuestsController.DeskCode;

    float xOffset;
    if (deskCode == -1 || GetGuestTable(deskCode).x > guestPos.x)
        xOffset = this.offsetX;  // field at +0x28 (offset 10 from base)
    else
        xOffset = -this.offsetX;

    closure.aliceHand = new Vector3(
        guestPos.x + xOffset,
        guestPos.y + this.offsetY,  // field at +0x2C (offset 11 from base)
        guestPos.z);

    closure.dollEnd = false;

    PlayAudio(this.audioClip);  // field at +0x30 (offset 6 from base)

    foreach (var tableIndex in emptyTables)
    {
        // Spawn doll prefab at aliceHand position
        var doll = Instantiate(this.dollPrefab);  // field at +0x20 (offset 4 from base)
        doll.transform.position = closure.aliceHand;

        var uiCluster = doll.GetComponent<UIElementCluster>();
        var dollSprite = uiCluster.GetObject<SpriteRenderer>(0);
        var guestTablePos = GetGuestTable(tableIndex);
        var targetPos = new Vector3(guestTablePos.x, guestTablePos.y - 0.75f, guestTablePos.z);

        // Flip sprite based on direction
        dollSprite.flipX = targetPos.x > closure.aliceHand.x;

        // Start line-drawing coroutine
        EventManager.Instance.StartCoroutine(
            SetLinenear(closure, doll, uiCluster, tableIndex));

        // Start movement coroutine (LerpPosition)
        EventManager.Instance.StartCoroutine(
            LerpPosition(doll.transform, () => /* b__2: returns targetPos */));
    }

    yield return UnityCoroutineExtension.OneSecondDelay;

    closure.dollEnd = true;
    yield return UnityCoroutineExtension.OneSecondDelay;
}

// Spell_Alice.DisplayClass15_0.SetLinenear (local function / coroutine)
private IEnumerator SetLinenear(GameObject doll, UIElementCluster uiElementCluster, int seat)
{
    // State machine: _SetLinenear_1_d
    var lineRenderer = uiElementCluster.GetObject<LineRenderer>(0);
    lineRenderer.SetPosition(1, this.aliceHand);

    while (!this.dollEnd)
    {
        var dollPos = doll.transform.position;
        lineRenderer.SetPosition(0, new Vector3(dollPos.x, dollPos.y + 0.5f, dollPos.z));
        yield return null;
    }

    // Get animator and play appropriate animation
    var animator = doll.GetComponent<Animator>();

    if (/* game state condition — checks a boolean field on EventManager */)
    {
        animator.Play("w");  // StringLiteral_4133
        yield return UnityCoroutineExtension.HalfSecondDelay;
    }
    else
    {
        animator.Play("u");  // StringLiteral_4126

        // Set up sprite masks with random guest portraits
        var mask1 = uiElementCluster.GetObject<SpriteMask>(0);
        var mask2 = uiElementCluster.GetObject<SpriteMask>(1);

        var guest1 = allNGuests.RandomSelectOne();
        var guest2 = allNGuests.RandomSelectOne();

        var dollSprite = uiElementCluster.GetObject<SpriteRenderer>(0);

        // Access guest sprite via vtable slot 6
        var spriteData1 = guest1./* vtable._6 */();
        if (spriteData1 != null && spriteData1.Length > 1)
            mask1.sprite = spriteData1[1];

        var spriteData2 = guest2./* vtable._6 */();
        if (spriteData2 != null && spriteData2.Length > 1)
            mask2.sprite = spriteData2[1];

        yield return UnityCoroutineExtension.QuarterSecondDelay;

        // Set mask interaction and wait
        dollSprite.maskInteraction = SpriteMaskInteraction.VisibleInsideMask;
        yield return UnityCoroutineExtension.HalfSecondDelay;

        // Spawn guest group at doll position
        var guests = new NormalGuest[] { guest1, guest2 };
        var dollPosition = doll.transform.position;
        guestManager.SpawnNormalGuestGroup(guests, dollPosition, true, seat, false);

        yield return UnityCoroutineExtension.QuarterSecondDelay;
    }

    // Cleanup
    Destroy(doll);
}
```

### 例 3 — Ghidra 后端

用 Ghidra 后端查询例 1 的同一个 `OverrideSave` 方法（与 IDA 后端最终收敛到同一份源码）：

```bash
python3 scripts/ghidra_query.py query \
  --project-location /path/to/ghidra-projects \
  --project-name game \
  --program UnityFramework \
  decompile name:ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16__MoveNext
```

Ghidra 反编译 C（摘自完整 `decompile.c`，省略类初始化保护和 builder 脚手架）

```c
void ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16__MoveNext
          (ResultScene_UI_ResultSceneSavePannel__OverrideSave_d__16_o *this, MethodInfo *method)

{
  Cysharp_Threading_Tasks_UniTask_o u__1;

  if (this->fields.__1__state == 0) {
    u__1 = this->fields.__u__1;
    this->fields.__u__1 = 0;
    this->fields.__1__state = -1;
LAB_00123456:
    UniTask_Awaiter__GetResult(&u__1);
    ResultScene_UI_ResultSceneSavePannel__ClosePanel(this->fields.__4__this, 0);
    this->fields.__1__state = -2;
    return;
  }
  this->fields.__4__this->fields.m_BlockSubPanelCommand = 1;
  ResultScene_UI_ResultSceneSavePannel__HidePanel(this->fields.__4__this, 0);
  ResultScene_UI_ResultSceneSavePannel__SavePlayerDataCoreAsync
            (&u__1, this->fields.__4__this, this->fields.index, 0);
  if (UniTask_Awaiter__IsCompleted(&u__1) == 0) {
    this->fields.__1__state = 0;
    this->fields.__u__1 = u__1;
    AsyncUniTaskVoidMethodBuilder__AwaitUnsafeOnCompleted(&this->fields.__t__builder, &u__1, this);
    return;
  }
  goto LAB_00123456;
}
```

恢复结果（与例 1 相同 —— 两个后端收敛到同一份源码）：

```csharp
private async UniTaskVoid OverrideSave(int index)
{
    m_BlockSubPanelCommand = true;
    HidePanel();
    await SavePlayerDataCoreAsync(index);
    ClosePanel();
}
```

以上名称与地址仅为示例占位，与 skill 的约定一致；真实分析时以当前二进制的 Ghidra 输出为准。

## 仓库结构

```
SKILL.md               分发器：后端选择 + 共享规则（从这里开始）
ida/                   IDA 后端（原版 skill，未修改）
  SKILL.md             IDA 工作流：ida-usage.md、ida-quirks.md、strings.md、
                       helpers.md、compiler-patterns.md、scripts/
ghidra/                Ghidra 后端（自研 skill，未修改）
  SKILL.md             Ghidra 工作流：ghidra-setup.md、ghidra-query.md、
                       ghidra-quirks.md、strings.md、helpers.md、
                       string-formatting.md、lambdas-closures.md、linq-generics.md、
                       coroutines.md、async.md、runtime-exceptions.md、
                       runtime-memory.md、scripts/、agents/
```

每个后端的 `scripts/` 目录都是自包含的；请在该后端自己的目录内运行其脚本，以保证相对路径引用有效。
