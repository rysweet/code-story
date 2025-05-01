#!/usr/bin/env bash
set -euo pipefail
ROOT="code-story/specs"

write () { mkdir -p "$(dirname "$1")"; cat >"$1"; echo "✓ $1"; }

##############################################################################
# P4 – DAG & Summariser micro-specs
##############################################################################
mkdir -p "$ROOT/P4_dag_summariser"

write "$ROOT/P4_dag_summariser/00_dag_builder_spec.md" <<'EOF'
### P4-00 DAGBuilder Internal Logic
*(full content from canvas)*
EOF

write "$ROOT/P4_dag_summariser/01_topic_aggregation.md" <<'EOF'
### P4-01 Topic Aggregation Helper
*(full content)*
EOF

##############################################################################
# P5 – MCP Adapter micro-specs
##############################################################################
mkdir -p "$ROOT/P5_mcp_adapter"

write "$ROOT/P5_mcp_adapter/00_tool_handlers.md" <<'EOF'
### P5-00 MCP Tool Handlers
*(full content)*
EOF

write "$ROOT/P5_mcp_adapter/01_auth_module.md" <<'EOF'
### P5-01 Entra ID Auth Module
*(full content)*
EOF

##############################################################################
# P6 – CLI micro-specs
##############################################################################
mkdir -p "$ROOT/P6_cli"

write "$ROOT/P6_cli/00_cli_core.md" <<'EOF'
### P6-00 CLI Core
*(full content)*
EOF

write "$ROOT/P6_cli/01_ingest_command.md" <<'EOF'
### P6-01 ingest Command
*(full content)*
EOF

write "$ROOT/P6_cli/02_query_command.md" <<'EOF'
### P6-02 query Command
*(full content)*
EOF

##############################################################################
# P7 – GUI micro-specs
##############################################################################
mkdir -p "$ROOT/P7_gui"

write "$ROOT/P7_gui/00_gui_bootstrap.md" <<'EOF'
### P7-00 GUI Bootstrap
*(full content)*
EOF

write "$ROOT/P7_gui/01_graph_viewer.md" <<'EOF'
### P7-01 GraphViewer Component
*(full content)*
EOF

write "$ROOT/P7_gui/02_ingest_dashboard.md" <<'EOF'
### P7-02 Ingestion Dashboard
*(full content)*
EOF

echo "Batch 2 specs written."