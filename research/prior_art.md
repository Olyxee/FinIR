# Prior art and positioning

> Goal: find the **strongest defensible** statement of FinIR's contribution by
> comparing it honestly against established work — not to prove novelty. Where prior
> work already contains a mechanism FinIR uses, this document says so and narrows
> the claim.
>
> Method caveat: this is an **architectural** comparison from general knowledge of
> these fields, without a formal cited literature search. Treat it as a positioning
> hypothesis to validate against the literature before any public novelty claim.

For each area: what it solves · overlap with FinIR · how FinIR differs · **does
novelty survive?**

---

### Spreadsheets (Excel, Google Sheets)
- **Solves:** cell dependency graphs with incremental recalculation; the most widely
  used financial computation tool on earth.
- **Overlap:** dependency tracking + recompute-only-what-changed is the spreadsheet
  calc engine's core, and FinIR's too.
- **Different:** spreadsheets are cell/grid-oriented, weakly typed (a cell is a
  number or a string), and not designed as a *programmatic execution target* for AI
  agents or for vectorized batch/GPU execution. FinIR is a typed IR with a finance
  type system, serialization, compiler passes, and pluggable backends.
- **Novelty survives?** **Not for incremental recomputation** — spreadsheets have
  done that for 40 years, and we must credit them. Survives only as: a *typed,
  serializable, backend-dispatched IR* rather than a grid UI.

### Excel calculation engine / calc chains
- **Solves:** a sophisticated dirty-marking + calc-chain engine at scale.
- **Overlap:** essentially the same incremental algorithm class.
- **Different:** closed, embedded in a product, not a library/IR.
- **Novelty survives?** No for the algorithm. FinIR's contribution is packaging and
  typing, not the recompute technique.

### Incremental computation systems (self-adjusting computation, Adapton, Salsa, incremental λ-calculus, build systems like Bazel)
- **Solves:** the general theory and practice of recomputing only what changed as
  inputs change — often far more sophisticated than FinIR (fine-grained change
  propagation, memoization, provenance).
- **Overlap:** FinIR's dirty-set propagation is a basic instance of this.
- **Different:** these are general frameworks; FinIR applies the idea to a
  finance-typed graph with domain kernels and a scenario/agent API.
- **Novelty survives?** **No for the incremental mechanism** — this field owns it,
  and more deeply than FinIR implements. Survives only as a domain specialization.

### Financial modeling DSLs (e.g. Modelica-style, actuarial/insurance DSLs, proprietary FP&A modeling languages)
- **Solves:** declarative financial/actuarial models with typed quantities.
- **Overlap:** a finance-specific language with typed metrics.
- **Different:** most are product- or domain-locked, not open, and not aimed at
  being an *execution target for AI-generated intent* with incremental+GPU backends.
- **Novelty survives?** Partially — the AI-intent-boundary framing and open IR are
  the differentiators; a finance DSL per se is not new.

### QuantLib / quant libraries
- **Solves:** deep, correct financial instrument pricing and risk analytics.
- **Overlap:** FinIR has a small kernel set (NPV/IRR/risk).
- **Different:** QuantLib is a *library of computations*; FinIR is a *representation
  and runtime* for composing and incrementally executing computations. FinIR is
  deliberately **not** a quant library and defers depth to them.
- **Novelty survives?** Yes at the layer level — different concern (IR/runtime vs.
  analytics library). No competition on kernel breadth (we are far shallower).

### JAX / autograd / computational graphs
- **Solves:** define-by-run/define-then-run numeric graphs, JIT via XLA,
  vectorization (vmap), GPU/TPU execution, autodiff.
- **Overlap:** a computation graph compiled and dispatched to hardware — conceptually
  close to FinIR's execute path, and technically far more advanced.
- **Different:** JAX is domain-agnostic tensors with **no finance type system**, no
  finance kernels, and no first-class *incremental single-input update* across
  interactive turns (its strength is batch/JIT, not "recompute one changed input").
  FinIR adds finance typing, a scenario/agent API, and interactive incrementality.
- **Novelty survives?** **Not for graph compilation, fusion, or GPU dispatch** — JAX
  and XLA do these far better. Survives only as: a finance-typed front-end with
  interactive incremental reuse, potentially *targeting* something like XLA later.

### GPU quant libraries / NVIDIA gQuant (RAPIDS)
- **Solves:** GPU-accelerated financial/dataframe pipelines.
- **Overlap:** scenario batches on GPU.
- **Different:** those are pipeline/dataframe tools; FinIR is a typed IR with
  incremental reuse and a dispatch planner. FinIR's GPU path is optional and shallow.
- **Novelty survives?** Not for GPU finance compute (they are ahead). Survives as the
  IR/incremental framing.

### Differentiable finance
- **Solves:** gradients of financial models for calibration/sensitivities.
- **Overlap:** both build financial computation graphs.
- **Different:** FinIR does not (yet) do autodiff; its focus is incremental reuse and
  typing, not gradients.
- **Novelty survives?** Orthogonal; not competing. Autodiff is a candidate future
  feature, not a current claim.

### MLIR / XLA / LLVM / tensor compilers (TVM)
- **Solves:** the compiler-infrastructure state of the art — typed IRs, pass
  pipelines, fusion, lowering, multi-backend codegen.
- **Overlap:** FinIR borrows the *shape* of this (typed IR + passes + backends) and
  even the "IR" in its name.
- **Different:** these are general-purpose compiler frameworks for tensors/programs;
  FinIR is tiny, finance-specific, interpreted (not lowered to machine code), and
  interactive. FinIR could in principle be *lowered onto* MLIR/XLA rather than
  competing with them.
- **Novelty survives?** **Absolutely not for compiler infrastructure** — MLIR/LLVM
  are vastly more capable and we must not imply otherwise. FinIR's only claim here is
  the *domain* (finance) and the *use case* (an execution boundary for AI financial
  intent), not compiler technology.

### Financial digital twins / enterprise planning engines (Anaplan, Pigment, Adaptive, etc.)
- **Solves:** large connected planning models with dependency recalculation and
  scenario planning — commercially, at enterprise scale.
- **Overlap:** connected financial graphs with incremental recalculation and
  scenarios — conceptually the closest *product* category.
- **Different:** these are closed products with UIs, governance, and data
  integration; FinIR is an open, embeddable library/runtime with a typed IR meant to
  be an execution target for code/agents, not an application.
- **Novelty survives?** The *open-IR-as-execution-target* framing differs from a
  closed planning product, but the underlying "connected model + incremental recalc +
  scenarios" is well-established commercially. We must not claim that as new.

---

## Synthesis: what survives

Every **mechanism** in FinIR is well-established, several for decades:

- dependency-graph incremental recomputation → **spreadsheets, self-adjusting
  computation, build systems**
- typed IR + pass pipeline + backend dispatch → **MLIR / XLA / LLVM / TVM**
- graph compilation + vectorization + GPU → **JAX / XLA / RAPIDS**
- finance kernels → **QuantLib and quant libraries**
- connected financial models + scenarios → **enterprise planning engines**

So FinIR's contribution is **not** any mechanism. The only defensible claim is
about a **specific composition and interface**:

> An **open, finance-typed intermediate representation** positioned as the
> **execution boundary** between AI-generated financial *intent* (structured, not
> arbitrary code) and **incremental, dependency-aware, backend-dispatched**
> financial computation — small, embeddable, CPU-first.

Each adjective removes a body of prior art from direct competition; only the
combination — *finance-typed IR + AI-intent boundary + interactive incrementality*,
packaged as open infrastructure — is distinctive.

## Novelty hypothesis (explicitly a hypothesis)

> There does not appear to be a **widely adopted, open, finance-specific
> intermediate representation** designed as an execution boundary between
> AI-generated financial intent and optimized incremental financial computation.

This must remain a **hypothesis** until a formal prior-art/literature review is
done. It is entirely possible that a closed product, an internal system, or an
academic project already occupies this exact niche. Nothing in this repository
should claim "first", "novel", or "breakthrough" until that review is complete.

## What must be verified before any stronger claim

1. A formal, cited literature and product search against every category above,
   especially enterprise planning engines and financial DSLs.
2. Evidence that AI agents actually benefit from a *structured intent boundary* vs.
   generating code — on real agent traces, not synthetic ones.
3. Larger, realistic financial models where the incremental win is material.
4. A GPU crossover measured on real hardware (Experiment 002 is unverified locally).
