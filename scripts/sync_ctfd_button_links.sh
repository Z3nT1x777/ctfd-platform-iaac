#!/bin/bash
###
# Sync CTFd challenge connection_info with launch button links.
# Uses the ORCHESTRATOR_SIGNING_SECRET for authentication.
# No API token needed!
#
# Usage:
#   ./sync_ctfd_button_links.sh http://192.168.56.10
#
###

set -e

CTFD_URL="${1:-http://192.168.56.10}"
SECRET="${ORCHESTRATOR_SIGNING_SECRET:-ChangeMe-Orchestrator-Signing-Secret}"

echo "🔄 Syncing CTFd challenges with launch button links..."
echo "   URL: $CTFD_URL"
echo "   Secret: ${SECRET:0:10}..."

response=$(curl -s -X POST "$CTFD_URL/plugins/orchestrator/sync" \
  -H "X-Orchestrator-Secret: $SECRET" \
  -H "Content-Type: application/json")

echo "📋 Response:"
echo "$response" | jq '.' 2>/dev/null || echo "$response"

# Check if successful
if echo "$response" | grep -q '"ok": true'; then
    echo "✅ Sync completed successfully!"
    exit 0
else
    echo "❌ Sync failed!"
    exit 1
fi
