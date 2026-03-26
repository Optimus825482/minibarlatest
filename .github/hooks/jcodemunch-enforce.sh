#!/bin/bash
set -e

INPUT=$(cat)

# Use Python for JSON parsing (jq not reliably available on Windows Git Bash)
parse_json() {
  python -c "import sys,json; d=json.loads(sys.argv[1]); print(d.get('$1',''))" "$INPUT" 2>/dev/null || echo ""
}

parse_nested() {
  python -c "
import sys, json
d = json.loads(sys.argv[1])
args = d.get('toolArgs', {})
if isinstance(args, str):
    import json as j2; args = j2.loads(args)
print(args.get('$1', args.get('$2', '')))
" "$INPUT" 2>/dev/null || echo ""
}

TOOL_NAME=$(parse_json toolName)
# Only intercept read/search tools used for code exploration
# VS Code Copilot actual tool names: read_file, grep_search, file_search, run_in_terminal, semantic_search, list_dir
case "$TOOL_NAME" in
  read_file|grep_search|file_search|semantic_search|list_dir|run_in_terminal)
    # Check if run_in_terminal is being used for code search (cat, grep, find, ls)
    if [ "$TOOL_NAME" = "run_in_terminal" ]; then
      COMMAND=$(parse_nested command command)
      if echo "$COMMAND" | grep -qE "^(cat |head |tail |grep |find |ls |rg |ag |ack )"; then
        echo '{"permissionDecision":"deny","permissionDecisionReason":"STOP: Use jCodemunch MCP tools for code exploration. Use mcp_jcodemunch_get_file_content/mcp_jcodemunch_get_file_outline instead of cat/head/tail, mcp_jcodemunch_search_symbols/mcp_jcodemunch_search_text instead of grep/rg, mcp_jcodemunch_get_file_tree instead of find/ls."}'
        exit 0
      fi
      # Allow other terminal commands (pip, pytest, flask, etc.)
      exit 0
    fi

    # For read_file/grep_search/file_search/semantic_search/list_dir, check if target is a code file
    FILE_PATH=$(parse_nested filePath path)
    if [ -n "$FILE_PATH" ]; then
      case "$FILE_PATH" in
        *.py|*.ts|*.tsx|*.js|*.jsx|*.css|*.vue|*.svelte|*.go|*.rs|*.java|*.rb)
          echo '{"permissionDecision":"deny","permissionDecisionReason":"STOP: Use jCodemunch MCP tools for code exploration. Use mcp_jcodemunch_get_file_content or mcp_jcodemunch_get_file_outline instead of read_file for code files. Use mcp_jcodemunch_search_text instead of grep_search. Exceptions: non-code config files (.json, .yaml, .md, .env) and pre-edit reads."}'
          exit 0
          ;;
        *)
          # Non-code files (.json, .yaml, .md, .env, etc.) are allowed
          exit 0
          ;;
      esac
    fi

    # grep_search/semantic_search/file_search without a specific code file path - allow
    # (these may search across workspace which is fine)
    ;;
esac

# Allow everything else
exit 0
