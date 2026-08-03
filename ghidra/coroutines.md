# Coroutine and Iterator Recovery

Read this file for methods returning `IEnumerator` or `IEnumerable<T>`, `_d__N` types, `__2__current`, or boolean `MoveNext` bodies.

## Find the Business Body

The outer wrapper normally allocates a state-machine object, records `__4__this` and arguments, sets an initial state, and returns it. Treat this as ownership evidence; business logic lives in `_d__N$$MoveNext`.

Locate `MoveNext` by:

1. Reading the state-machine TypeInfo from the wrapper.
2. Searching `script.json` for the exact `_d__N$$MoveNext` name.
3. Querying the matched RVA with the artifact-first wrapper.
4. Using bounded xrefs on the exact TypeInfo only when metadata search is insufficient.

Do not enumerate all `MoveNext` functions.

## Core Fields

| Field | Meaning |
|---|---|
| `__1__state` | Continuation state; `-1` running and `-2` completed are common |
| `__2__current` | Value returned by the current `yield` |
| `__4__this` | Captured outer instance |
| argument fields | Parameters copied by the wrapper |
| `__8__N` | Closure or local that survives a yield |
| `_local_5__N` | Ordinary local promoted across yields |

`MoveNext` returning true means it yielded and paused. Returning false means completion or `yield break`.

## Recover Yields

An assignment to `__2__current`, followed by a non-negative state assignment and `return true`, is a yield point. Continue reconstruction from the matching resume-state branch.

- `__2__current = null` normally means `yield return null`.
- A named static wait object should remain that named object.
- An `IEnumerator` result stored as current normally means `yield return OtherCoroutine(...)`.
- A sequence of state cases writing tuple values commonly restores to sequential `yield return (...)` statements.

Do not expose the state switch as business logic. It represents continuation points.

## Loops and Iterators

When resuming from a yield re-enters the same condition and body, restore a loop rather than a one-shot `if`.

An `IEnumerable<T>` wrapper commonly starts at state `-2` and records a thread ID. Preserve it as an iterator; do not replace it with collection construction unless the source explicitly materialized a collection.

## Closures and Nested Coroutines

A state-machine field holding a `DisplayClass` is a closure local that must survive a yield. Map its fields from outer assignments and decompile its lambda/local-function helpers using [lambdas-closures.md](lambdas-closures.md).

If a named local function returns `IEnumerator`, locate its nested `_g__Name_..._d$$MoveNext`. Build this map before assembling C#:

```text
outer state machine
closure fields
ordinary lambda helpers
named local functions
nested coroutine state machines
```

Keep LINQ inside the scope where its native calls occur. Read [linq-generics.md](linq-generics.md) when a coroutine contains LINQ callbacks.

## Completeness

For a large `MoveNext`, use the artifact index to locate state branches, then read all behavior-relevant slices. The index and callees are navigation only. If any state region is missing or decompilation fails after one retry, use the GUI and obtain complete C.
