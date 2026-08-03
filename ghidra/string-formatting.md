# IL2CPP String Formatting Recovery

Read this file only when resolved literals participate in `String.Concat`, `String.Format`, boxing, or interpolation-like lowering.

## Preserve Semantics First

Follow native argument order and the exact resolved format string. Do not reorder values because variable names suggest a nicer sentence.

| Native shape | Likely C# restoration |
|---|---|
| `String.Concat(a, b)` | `a + b` or `$"{a}{b}"` |
| Four-argument `String.Concat` | Often lowered interpolation; preserve all four operands |
| `String.Format(fmt, args...)` | Interpolation when the format is static and semantics remain exact |
| Dynamic format string | Keep `String.Format` when interpolation cannot express it directly |

## `String.Format` Mapping

Map `{0}`, `{1}`, and later placeholders to native argument order. When IL2CPP boxes value types, the first boxed argument passed to `String.Format` is `{0}`, the next is `{1}`, and so on.

Preserve:

- repeated or reordered placeholders;
- alignment and format specifiers such as `{0,8}` or `{0:0.00}`;
- escaped braces;
- culture/provider overloads;
- dynamic format strings.

Example:

```csharp
String.Format("{1}: {0:0.00}", value, label)
```

may restore as:

```csharp
$"{label}: {value:0.00}"
```

## Boxing

Remove `il2cpp_value_box` when C# formatting, concatenation, or an `object` parameter naturally boxes the value. Do not erase an explicit object conversion when it affects overload resolution.

## Style

Prefer interpolation for a static, readable format. Keep `String.Format` or concatenation when converting would obscure evaluation order, culture, dynamic formatting, or exact behavior.
