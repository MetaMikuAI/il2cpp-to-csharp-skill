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

## 用法

将本目录安装或复制为名为 `il2cpp-to-csharp-skill` 的 skill，然后让 agent 每次恢复一个函数。分发器会根据你说明的环境选择后端：

```text
使用 $il2cpp-to-csharp-skill 来恢复 0x180000000.
IDA Pro MCP 已就绪。由 DummyDll/Assembly-CSharp.dll 通过 dnSpy 导出的桩代码项目位于 C:\path\to\DummyDllExport，stringliteral.json 位于 C:\path\to\stringliteral.json。
```

```text
使用 $il2cpp-to-csharp-skill 来恢复 rva:0x123456.
Ghidra 已就绪。项目位于 /path/to/ghidra-projects/game，程序为 UnityFramework，stringliteral.json 位于 /path/to/stringliteral.json。
```

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
