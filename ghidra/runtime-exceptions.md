# IL2CPP Type and Exception Helpers

Read this file only after [helpers.md](helpers.md) classifies an unknown helper as a type check or automatic exception path. Identify the current binary's behavior; do not transfer example addresses between builds.

## Automatic Null and Bounds Throws

Null-reference and index-out-of-range helpers are commonly no-argument, non-returning functions that construct an exception and enter a shared raise path.

- Omit a null helper reached only from the compiler-inserted null-dereference path.
- Omit an index helper reached only from an array bounds check.
- Preserve explicit source checks, custom messages, catches, or surrounding side effects.

Do not classify two no-argument throw helpers by shape alone; use the branch context or resolved exception type.

## Invalid Cast

Signals:

- reached after class-depth, parent, interface, or assignability checks fail;
- may receive the object/class and target TypeInfo;
- constructs a cast message and never returns.

Restore the source cast. The automatic `InvalidCastException` path disappears. Preserve an explicit `throw` only when source-visible evidence exists beyond runtime cast enforcement.

## Runtime Type Check

Signals:

- receives an object and target TypeInfo;
- returns the object on assignability and null otherwise;
- calls `il2cpp_class_is_assignable_from` or performs interface checks.

Restore `as T`, `is T`, or a pattern match according to how the returned pointer and following branch are used. The helper body alone does not distinguish them.

## Array Type Mismatch

Signals:

- reached from an array covariance store check;
- resolves/constructs `ArrayTypeMismatchException` and enters a shared throw path;
- may contain `Il2CppExceptionWrapper`.

Omit the automatic throw path and preserve the array assignment. Do not remove a user-written catch or explicit throw.

## Shared Throw Infrastructure

`Il2CppExceptionWrapper`, exception-object construction, and common raise helpers indicate native exception transport. They do not by themselves prove which C# exception or whether the throw was compiler-inserted.

Trace one level upward to the failed check and use metadata/type evidence. Preserve business code inside any helper rather than deleting the entire function because it eventually throws.

## Safety Check

Remove only the automatic enforcement path. Preserve:

- explicit source validation;
- custom exception messages or exception subclasses confirmed by stubs;
- logging, cleanup, mutation, or callbacks before the throw;
- catch/finally behavior visible in the caller.
