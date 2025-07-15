# Documentation Workflow Specification

## Overview

This document defines the documentation workflow for the CodeStory project, enabling:
- Automated API reference generation from Python docstrings
- Narrative documentation (overview, quickstart, CLI usage, configuration, contributing, etc.)
- Seamless integration with existing Python tooling (uv, pre-commit, CI)
- Minimal ongoing maintenance

---

## 1. Static Site Generator Selection

**Chosen Tool:** [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)

**Rationale:**
- Widely adopted in the Python ecosystem
- Excellent support for code reference via [mkdocstrings-python](https://mkdocstrings.github.io/python/)
- Modern, responsive UI with built-in search and versioning support
- Easy local preview and CI/CD integration
- Active community and plugin ecosystem

---

## 2. Plugin List

- **mkdocstrings[python]**: Auto-generates API reference from docstrings, supports type hints, cross-references, and configuration.
- **mike**: Versioned documentation deployment (for GH Pages).
- **mkdocs-material**: Enhanced theme and features.
- **mkdocs-git-revision-date-localized-plugin**: Shows last updated date on pages.
- **mkdocs-section-index**: Clean section landing pages.
- **mkdocs-literate-nav**: Markdown-based navigation.
- **mkdocs-link-checker**: Validates internal/external links (for pre-commit/CI).
- **Optional**: mkdocs-gen-files, mkdocs-awesome-pages-plugin (for advanced structure).

---

## 3. Folder Structure

```
docs/
  index.md                # Project overview/landing page
  quickstart.md           # Quickstart guide
  cli.md                  # CLI usage and examples
  config.md               # Configuration reference
  contributing.md         # Contribution guidelines
  guides/
    ingestion.md
    graph.md
    ai.md
    ...                   # Additional guides as needed
  reference/
    codestory.md          # API reference (auto-generated)
    ...                   # Submodules as needed
  assets/
    images/
    diagrams/
  specs/                  # (symlink or copy from project/specs if needed)
  changelog.md            # Project changelog (optional)
  ...
mkdocs.yml                # MkDocs configuration
```

---

## 4. Commands

**Install dependencies (using uv):**
```sh
uv pip install mkdocs-material mkdocstrings[python] mike mkdocs-git-revision-date-localized-plugin mkdocs-section-index mkdocs-literate-nav mkdocs-link-checker
```

**Local preview:**
```sh
uv run mkdocs serve
```

**Build static site:**
```sh
uv run mkdocs build
```

**Check links (pre-commit/CI):**
```sh
uv run mkdocs link-checker
```

**Deploy versioned docs (mike):**
```sh
uv run mike deploy --update-aliases latest
```

---

## 5. Pre-commit and CI Integration

- **Pre-commit:** Add a hook to run `mkdocs build` and `mkdocs link-checker` to ensure docs build and all links are valid before commit.
- **CI:** Add a job to build docs and check links on every PR and push to main.
- **All commands must use `uv run` to comply with Python environment rules.**

---

## 6. GitHub Pages Deployment (Outline)

- Use `mike` to manage versioned docs on the `gh-pages` branch.
- Configure GitHub Pages to serve from `/docs` or `/` on the `gh-pages` branch.
- Add a CI workflow to deploy docs on release or main branch update.
- Document the deployment process in `docs/contributing.md`.

---

## 7. Implementation & Test Task Breakdown

**Implementation Tasks:**
1. Add `mkdocs.yml` and initial `docs/` structure.
2. Add and configure required plugins in `mkdocs.yml`.
3. Write/port narrative docs: overview, quickstart, CLI, config, contributing.
4. Set up `mkdocstrings` for API reference (pointing to `codestory` package).
5. Add pre-commit hook for `mkdocs build` and `mkdocs link-checker`.
6. Add CI job for docs build and link check.
7. Set up `mike` for versioned deployment and document the process.
8. (Optional) Symlink or copy `specs/` into `docs/` for design doc visibility.

**Test Strategy:**
- Validate that `uv run mkdocs build` and `uv run mkdocs serve` work locally.
- Ensure API reference updates automatically with code changes.
- Confirm pre-commit and CI block on broken links or build errors.
- Test versioned deployment to GH Pages (dry run, then real).
- Review rendered site for navigation, search, and content accuracy.

---

## 8. Mermaid Diagram: Documentation Workflow

```mermaid
flowchart TD
    A[Write/Update Code & Docstrings] --> B[Run mkdocstrings]
    B --> C[API Reference in docs/reference/]
    D[Write/Update Narrative Docs] --> E[docs/*.md, guides/, etc.]
    C & E --> F[mkdocs build]
    F --> G[Static Site Output (site/)]
    G --> H[Preview Locally or Deploy to GH Pages]
    F --> I[Pre-commit/CI: Link Check, Build Check]
```

---

## 9. Maintenance Guidelines

- Keep docstrings up to date in code for API reference.
- Update narrative docs as features evolve.
- Use pre-commit and CI to catch issues early.
- Review docs on PRs as part of code review.

---

## 10. References

- [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
- [mkdocstrings-python](https://mkdocstrings.github.io/python/)
- [mike](https://github.com/jimporter/mike)
- [MkDocs Plugins List](https://github.com/mkdocs/catalog)
