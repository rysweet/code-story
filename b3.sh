#!/usr/bin/env bash
set -euo pipefail
ROOT="code-story/specs"

write () { mkdir -p "$(dirname "$1")"; cat >"$1"; echo "✓ $1"; }

##############################################################################
# P8 – Infra micro-spec (combined compose + Bicep)
##############################################################################
mkdir -p "$ROOT/P8_infra"

write "$ROOT/P8_infra/00_compose_and_deploy.md" <<'EOF'
### P8-00 Docker-Compose & Bicep Deployment
*(full content copied from canvas)*
EOF

##############################################################################
# P9 – Docs & Prompts micro-specs
##############################################################################
mkdir -p "$ROOT/P9_docs_prompts"

write "$ROOT/P9_docs_prompts/00_mkdocs_site.md" <<'EOF'
### P9-00 MkDocs Site
*(full content)*
EOF

write "$ROOT/P9_docs_prompts/01_prompt_templates.md" <<'EOF'
### P9-01 Prompt Templates
*(full content)*
EOF

##############################################################################
# Coding-agent micro-specs (CA-00..03)
##############################################################################
mkdir -p "$ROOT/coding-agent"

write "$ROOT/coding-agent/00_core_loop.md" <<'EOF'
### CA-00 Core Generation Loop
*(full content)*
EOF

write "$ROOT/coding-agent/01_decomposer.md" <<'EOF'
### CA-01 Micro-Spec Decomposer
*(full content)*
EOF

write "$ROOT/coding-agent/02_static_analysis.md" <<'EOF'
### CA-02 Static Analysis Pre-check
*(full content)*
EOF

write "$ROOT/coding-agent/03_git_integration.md" <<'EOF'
### CA-03 Git & PR Automation
*(full content)*
EOF

##############################################################################
# Supporting docs (decomposer plan & backlog)
##############################################################################
write "$ROOT/decomposer_plan.md" <<'EOF'
# Component Sub-Spec Decomposition Plan
*(full content)*
EOF

write "$ROOT/coding-agent-backlog.md" <<'EOF'
# Coding Agent Improvement Backlog
*(full content)*
EOF

echo "Batch 3 specs written."