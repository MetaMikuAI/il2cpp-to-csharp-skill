# Ghidra Project Setup

Read this file only when creating a Ghidra project, importing an image, or reapplying Il2CppDumper symbols and signatures. All names and paths are examples.

## Launchers and Project Identity

On Homebrew macOS installations:

```bash
ghidraRun
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless"
```

`analyzeHeadless` requires the project-location directory to exist. Address a local program as:

```text
<project-location> <project-name> -process <program-name>
```

The project name and imported program name are independent. If the binary was imported as `UnityFramework`, use `-process UnityFramework` even when the project is named `game`.

Use `-readOnly` for queries. Omit it only for changes that must be saved, such as symbol or type import.

## Initial Import

Create a project and import the native image:

```bash
mkdir -p /path/to/ghidra-projects
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless" \
  /path/to/ghidra-projects game \
  -import /path/to/UnityFramework \
  -scriptPath /path/to/skill/scripts \
  -postScript ApplyIl2CppSymbols.java /path/to/script.json
```

Verify the loader and processor in the analysis log:

- PE: normally `x86:LE:64` for Windows x64.
- ELF: the matching x86-64 or AArch64 language.
- Mach-O: normally `AARCH64:LE:64:AppleSilicon:default` for modern iOS ARM64.

If Ghidra proposes raw-binary import for a normal PE, ELF, or Mach-O file, stop and check whether the image is packed, encrypted, truncated, or the wrong bundle member.

## Reapply Symbols

For an existing project:

```bash
"$(brew --prefix ghidra)/libexec/support/analyzeHeadless" \
  /path/to/ghidra-projects game \
  -process UnityFramework \
  -scriptPath /path/to/skill/scripts \
  -postScript ApplyIl2CppSymbols.java /path/to/script.json
```

The importer adds function starts, method aliases, string-literal labels, metadata labels, and MethodInfo labels from `script.json`. Supply `--signatures` only after the matching C types have been imported.

Multiple C# methods may share one function address. Ghidra retains their labels but displays only one primary function name; use `ghidra_query.py query ... info` to inspect aliases.

