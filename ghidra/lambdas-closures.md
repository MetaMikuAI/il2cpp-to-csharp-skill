# Lambdas, Closures, and Local Functions

Read this file when the current method contains `__c`, `__9__N_M`, `b__`, `DisplayClass`, or `g__` symbols. Use only names and addresses from the current build.

## Workflow

1. Restore the outer method's guards, branches, loops, delegate construction, and higher-order calls.
2. Identify every delegate target from MethodInfo labels, delegate TypeInfo, `script.json`, and exact RVAs.
3. Decompile each target before deciding whether it is a lambda, local function, or business helper.
4. Record each helper's parameters, captures, result, and side effects.
5. Inline only short single-use helpers. Keep shared, named, complex, or side-effecting helpers as local functions or private methods.

Prefer `scripts/ghidra_query.py query ... info` and `decompile` for exact RVAs. Use xrefs when ownership remains unclear.

## Symbol Map

| Symbol | Meaning | Restore as |
|---|---|---|
| `Type.__c` and `__9` | Singleton target for no-capture lambdas | Compiler cache; omit |
| `__9__N_M` | Cached no-capture delegate | Decompile `b__N_M` |
| `<Outer>b__N_M` | Anonymous delegate body | Lambda or anonymous delegate |
| `DisplayClassN_M` | Closure object | Captured locals and outer `this` |
| `<Outer>g__Name\|N_M` | Named local function | Prefer a named local function |

Use numeric suffixes only to correlate symbols. Do not infer behavior from them.

## No-Capture Lambdas

The native pattern commonly loads `__9__N_M`, constructs a delegate targeting `__c.__9` when null, stores it with a write barrier, and passes it to a higher-order method.

Recover it by:

1. Reading the delegate TypeInfo to establish `Func<T,...>` or `Action<T,...>` shape.
2. Decompiling the referenced `b__N_M` body.
3. Confirming fields and enum values from stubs.
4. Omitting singleton and cache initialization from final C#.

Do not infer a predicate from `Func<T,bool>` alone.

## Capturing Lambdas

A capturing lambda allocates a `DisplayClass` and assigns captured values before delegate construction. Treat those assignments as the capture list:

- `__4__this` is the outer instance.
- Other fields are captured parameters, locals, or cached delegates.
- Fields that store delegate caches are compiler machinery, not business fields.

Decompile every `DisplayClass...b__` or `g__` target and replace its field reads with the corresponding captured values. Preserve mutations of captured collections, queues, counters, and flags.

Do not remove capture semantics or invent semantic names without stub or assignment evidence.

## Named Local Functions

`<Outer>g__Name|N_M` preserves the source name. Prefer:

```csharp
void Name(Arg value)
{
    // reconstructed body
}
```

If one local function registers another as a callback, preserve named method-group flow when signatures agree. If a local function returns `IEnumerator`, its business body is normally in a nested `_g__Name_..._d$$MoveNext`; read [coroutines.md](coroutines.md).

## Large Helper Sets

For a method containing many `b__`, `g__`, or `DisplayClass` references, build a helper table before writing C#:

```text
helper RVA | delegate type | captures | result | side effects | callers
```

Restore the outer skeleton first, then helpers. A call list can locate candidates but cannot replace helper decompilation.

## Failure Checks

- Missing exact name: search `script.json` by helper fragment, then query its RVA.
- Multiple aliases at one entry: treat it as possible ICF and match the requested stub to the shared body.
- Helper decompile incomplete: retry once, then use the GUI; do not infer the body.
- Generic helper shown as `object` or `undefined8`: preserve source generic types from stubs and call sites.
