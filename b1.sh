#!/usr/bin/env bash
set -euo pipefail
ROOT="code-story"
mkdir -p "$ROOT/specs"

write() {                   # write <file> <<'EOF'  …  EOF
  mkdir -p "$(dirname "$1")"
  cat >"$1"
  echo "✓ ${1}"
}

##############################################################################
# Root-level specs
##############################################################################
write "$ROOT/specs/00_overview.md" <<'EOF'
# code-story – Overview & Architecture
*(identical content to canvas `00_overview.md`)*
EOF

write "$ROOT/specs/01_scaffolding.md" <<'EOF'
## 00 Scaffolding (P0)
*(full content from canvas – purpose, layout, toolchain, MIT license, …)*
EOF

write "$ROOT/specs/coding-guidelines.md" <<'EOF'
# Coding Guidelines (CG)
*(full guidelines: Python PEP 8+type-hints, ESLint rules, docstrings, …)*
EOF

write "$ROOT/specs/methodology.md" <<'EOF'
# Iterative Spec-First Development Method
*(playbook + detailed deliverables matrix + prompt snippets)*
EOF

##############################################################################
# P1 – Graph Service micro-specs
##############################################################################
mkdir -p "$ROOT/specs/P1_graph_service"
write "$ROOT/specs/P1_graph_service/00_schema.md" <<'EOF'
### P1-00 Schema & Migration Runner
*(exact content from canvas)*
EOF
write "$ROOT/specs/P1_graph_service/01_service_class.md" <<'EOF'
### P1-01 GraphService Class
*(exact content)*
EOF
write "$ROOT/specs/P1_graph_service/02_rest_router.md" <<'EOF'
### P1-02 Optional REST Router
*(exact content)*
EOF

##############################################################################
# P2 – OpenAI Client micro-specs
##############################################################################
mkdir -p "$ROOT/specs/P2_openai_client"
write "$ROOT/specs/P2_openai_client/00_client_core.md" <<'EOF'
### P2-00 OpenAI Client Core
*(exact content)*
EOF
write "$ROOT/specs/P2_openai_client/01_retry_backoff.md" <<'EOF'
### P2-01 Retry & Back-off Decorator
*(exact content)*
EOF
write "$ROOT/specs/P2_openai_client/02_metrics.md" <<'EOF'
### P2-02 Metrics & Tracing
*(exact content)*
EOF

##############################################################################
# P3 – Ingestion Pipeline micro-specs
##############################################################################
mkdir -p "$ROOT/specs/P3_ingestion_pipeline"
write "$ROOT/specs/P3_ingestion_pipeline/00_pipeline_core.md" <<'EOF'
### P3-00 Pipeline Core
*(exact content)*
EOF
write "$ROOT/specs/P3_ingestion_pipeline/01_blarify_step.md" <<'EOF'
### P3-01 BlarifyStep
*(exact content)*
EOF
write "$ROOT/specs/P3_ingestion_pipeline/02_fs_linker_step.md" <<'EOF'
### P3-02 FilesystemGraphStep
*(exact content)*
EOF
write "$ROOT/specs/P3_ingestion_pipeline/03_dag_builder_step.md" <<'EOF'
### P3-03 DAGBuilderStep
*(exact content)*
EOF
write "$ROOT/specs/P3_ingestion_pipeline/04_doc_graph_step.md" <<'EOF'
### P3-04 DocumentationGraphStep
*(exact content)*
EOF
write "$ROOT/specs/P3_ingestion_pipeline/05_summariser_step.md" <<'EOF'
### P3-05 SummariserGraphStep
*(exact content)*
EOF

echo "Batch 1 files created under $ROOT/specs"