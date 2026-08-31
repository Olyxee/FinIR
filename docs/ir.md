# The Financial IR

A FinIR **module** is a typed computation graph: named nodes (inputs, constants,
computed) plus declared outputs. It is pure data — the compiler and runtime operate
over it without mutating it.

## Textual form (`.finir`)

```
model company {
  input revenue: money[ZAR]
  input cogs: money[ZAR]
  input opex: money[ZAR]

  gross_profit = revenue - cogs
  gross_margin = gross_profit / revenue
  ebitda       = gross_profit - opex

  output gross_margin
  output ebitda
}
```

Bare-line form (no `model { }` wrapper) also parses, and `name = input money[ZAR]`
is accepted as an alternate input declaration.

## Expressions

Computed nodes hold an expression AST (`finir.ir.expr`): `Ref` (node reference),
`Lit` (numeric or `N%` percentage literal), `Bin` (`+ - * /`), and `Call` (a kernel
invocation like `npv(rate, cashflows)`). The parser is a small precedence-climbing
parser; `4%` becomes a percentage literal `0.04`.

## Programmatic construction

```python
import finir

module = finir.parse("""
revenue = input money[ZAR]
cogs    = input money[ZAR]
gross_profit = revenue - cogs
""")
```

## Serialization (JSON) — the interchange format

`module_to_json` / `module_from_json` round-trip a module losslessly. JSON is the
**stable, language-neutral** interchange format: other languages (TypeScript, Rust,
Java, ...) can consume FinIR without a Python parser. Types round-trip via their
textual form; expressions round-trip structurally.

## Queries

`module.dependencies(name)`, `module.topo_order()`,
`module.transitive_dependents({...})` power dependency analysis, and are the basis
for the runtime's dirty-set propagation.

## Validation

`validate_module` checks that references resolve, outputs exist, no node references
itself, and there are no cycles — raising `ValidationError` on the first problem.
