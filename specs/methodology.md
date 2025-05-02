# Iterative Spec‑First Development Method

This playbook abstracts the process we just used into a reusable recipe for *any* green‑field project.

## Phases

| Phase                   | Goal                                                                                  | Typical Prompts                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **1. Rough Sketch**     | Capture vision, major components, constraints.                                        | “I’d like to build X; the service will have A, B, C … Specs in Markdown please.” |
| **2. Overall Spec**     | Produce a single high‑level specification (responsibilities, architecture, stack).    | “Generate an overall specification; include components, data flow.”              |
| **3. Refinement Loop**  | Ask clarifying questions; patch spec until stakeholder signs off.                     | “Please add unit‑test plan; remove Typer; use MIT license.”                      |
| **4. Component Specs**  | Break overall spec into one doc per component.                                        | “Create detailed specs for each component, step‑by‑step.”                        |
| **5. Micro‑Specs**      | Decompose each component into micro‑specs—one implementable unit per LLM inference.   | “Make a sub‑spec for schema, another for service class.”                         |
| **6. Backlog / Review** | Record pending edits, feature backlog, consistency review.                            | “Add these issues to backlog.md; review contracts.”                              |
| **7. Code Generation**  | Feed micro‑specs to an agent that iterates (generate → test → iterate) until passing. | “Run coding‑agent on P3/00\_pipeline\_core.md.”                                  |

## Key Practices

* **Markdown specs** with “One‑Shot Code Generation Instructions”.
* **Artifacts panel** (or Git) to store every spec and generated file.
* **Backlog file** to track remaining tasks and spec diffs.
* **Micro‑spec granularity** small enough for ≈8 k‑token context.
* **Iterative agent loop**: generate → lint/typecheck → tests → regenerate on failure.

---

*Use this checklist to replicate the process for any new project.*
