#!/bin/bash
set -x
export NEO4J_URI="$1"
export CODESTORY_NEO4J__URI="$1"
export CODESTORY_CONFIG_FILE="$2"
echo "[run_query_cypher.sh] NEO4J_URI=$NEO4J_URI" >&2
echo "[run_query_cypher.sh] CODESTORY_NEO4J__URI=$CODESTORY_NEO4J__URI" >&2
echo "[run_query_cypher.sh] CODESTORY_CONFIG_FILE=$CODESTORY_CONFIG_FILE" >&2
exit 1
python src/codestory/cli/main.py query run "MATCH (n) RETURN count(n) as count LIMIT 5"