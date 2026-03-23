#!/usr/bin/env bash
# scripts/verify-gateway.sh
# Verifies the OmegA Gateway is alive and conforming to the API contract.
#
# Usage:
#   BEARER_TOKEN=<token> bash scripts/verify-gateway.sh
#   GATEWAY_URL=http://127.0.0.1:8788 BEARER_TOKEN=<token> bash scripts/verify-gateway.sh
#
# Environment variables:
#   GATEWAY_URL    Base URL of the gateway (default: http://127.0.0.1:8787)
#   BEARER_TOKEN   Bearer token to use for authenticated requests

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8787}"
BEARER_TOKEN="${BEARER_TOKEN:-}"
PASS=0
FAIL=0

green() { printf "\033[0;32m[PASS]\033[0m %s\n" "$1"; }
red()   { printf "\033[0;31m[FAIL]\033[0m %s\n" "$1"; }

check() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if echo "$actual" | grep -qF "$expected"; then
        green "$name"
        PASS=$((PASS + 1))
    else
        red "$name — expected to find '$expected' in: $actual"
        FAIL=$((FAIL + 1))
    fi
}

check_status() {
    local name="$1"
    local expected_code="$2"
    local actual_code="$3"
    if [ "$actual_code" = "$expected_code" ]; then
        green "$name (HTTP $actual_code)"
        PASS=$((PASS + 1))
    else
        red "$name — expected HTTP $expected_code, got $actual_code"
        FAIL=$((FAIL + 1))
    fi
}

echo "Verifying gateway at $GATEWAY_URL"
echo "========================================="

# --- Unauthenticated endpoints ---

HEALTH=$(curl -sf "$GATEWAY_URL/health" 2>/dev/null || echo '{}')
check "GET /health — ok field"      '"ok":true'      "$HEALTH"
check "GET /health — service field" '"service":"Gateway"' "$HEALTH"
check "GET /health — version field" '"version":"0.1"'     "$HEALTH"

HEALTHZ=$(curl -sf "$GATEWAY_URL/healthz" 2>/dev/null || echo '{}')
check "GET /healthz" '"ok":true' "$HEALTHZ"

ROOT=$(curl -sf "$GATEWAY_URL/" 2>/dev/null || echo '{}')
check "GET / — service"  '"service":"OMEGA Gateway"' "$ROOT"
check "GET / — status"   '"status":"operational"'    "$ROOT"
check "GET / — version"  '"version":"0.1"'           "$ROOT"

READY=$(curl -sf "$GATEWAY_URL/ready" 2>/dev/null || echo '{}')
check "GET /ready" '"status":"ready"' "$READY"

# --- Auth tests ---

AUTH_401=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "$GATEWAY_URL/api/v1/chat" \
    -H "Content-Type: application/json" \
    -d '{"user":"test"}')
if [ -z "$BEARER_TOKEN" ]; then
    check_status "POST /api/v1/chat — no auth, no token configured (permissive)" "200" "$AUTH_401"
else
    check_status "POST /api/v1/chat — missing Authorization header = 401" "401" "$AUTH_401"
fi

if [ -n "$BEARER_TOKEN" ]; then
    AUTH_403=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$GATEWAY_URL/api/v1/chat" \
        -H "Authorization: Bearer wrong-token-xyz" \
        -H "Content-Type: application/json" \
        -d '{"user":"test"}')
    check_status "POST /api/v1/chat — wrong token = 403" "403" "$AUTH_403"
fi

# --- Chat endpoint (authenticated) ---

if [ -n "$BEARER_TOKEN" ]; then
    AUTH_HEADER="Authorization: Bearer $BEARER_TOKEN"

    CHAT=$(curl -sf -X POST "$GATEWAY_URL/api/v1/chat" \
        -H "$AUTH_HEADER" \
        -H "Content-Type: application/json" \
        -d '{"user":"say the word OK and nothing else","mode":"local","temperature":0.0}' \
        2>/dev/null || echo '{}')
    check "POST /api/v1/chat — reply field present"       '"reply"'        "$CHAT"
    check "POST /api/v1/chat — mode field present"        '"mode"'         "$CHAT"
    check "POST /api/v1/chat — memory_hits field present" '"memory_hits"'  "$CHAT"

    # --- Providers endpoint ---

    PROVIDERS=$(curl -sf "$GATEWAY_URL/api/v1/providers" \
        -H "$AUTH_HEADER" 2>/dev/null || echo '{}')
    check "GET /api/v1/providers — contains perplexity" 'perplexity' "$PROVIDERS"
    check "GET /api/v1/providers — contains anthropic"  'anthropic'  "$PROVIDERS"
fi

echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    echo "GATEWAY IS NOT READY FOR CUTOVER"
    exit 1
else
    echo "Gateway is ready."
    exit 0
fi
