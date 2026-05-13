# il2cpp-to-csharp-skill

[中文](README.zh-CN.md)

A Codex skill for restoring readable C# from Unity IL2CPP binaries with IDA Pro MCP, Il2CppDumper output, DummyDll stubs, and `stringliteral.json`.

This is not a one-click decompiler. It helps an agent analyze user-provided VAs or function names and reconstruct C# while preserving strings, switch branches, lambdas, LINQ, async/coroutine state machines, and IL2CPP-specific quirks.

Output quality depends on the AI model and the available context. Restored code is for reference only and should be manually reviewed against IDA, DummyDll stubs, and runtime behavior.

## Requirements

- IDA Pro with IDA Pro MCP enabled
- Il2CppDumper output: `script.json`, `stringliteral.json`, and `DummyDll/`
- Python 3 for bundled helper scripts

## Preparation

1. Open the IL2CPP binary, usually `GameAssembly.dll`, in IDA Pro and wait for initial analysis to finish.
2. Run Il2CppDumper's IDA processing script, usually `ida_with_struct_py3.py`, inside IDA on the current database.
3. Open `DummyDll/Assembly-CSharp.dll` in dnSpy and export it as a C# project. This gives the agent readable class, method, field, enum, generic, and `[FieldOffset]` stubs.
4. Keep `stringliteral.json` available and provide its local path when string resolution is needed.

## Usage

Install or copy this folder as a Codex skill named `il2cpp-to-csharp-skill`, then ask Codex to restore one function at a time:

```text
Use $il2cpp-to-csharp-skill to restore 0x180000000.
IDA Pro MCP is ready. The dnSpy-exported stub project from DummyDll/Assembly-CSharp.dll is at C:\path\to\DummyDllExport, and stringliteral.json is at C:\path\to\stringliteral.json.
```

## Example

### example 1

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

DeepSeek v4 pro (Claude Code) 1 retry

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

### example 2

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

