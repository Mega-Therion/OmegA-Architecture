#!/usr/bin/env bash
# scripts/benchmark.sh
# Benchmarks the OmegA Gateway.
# Run against the Python gateway first (baseline), then against the Rust binary.
#
# Usage:
#   GATEWAY_URL=http://127.0.0.1:8787 BEARER_TOKEN=<token> bash scripts/benchmark.sh
#   GATEWAY_URL=http://127.0.0.1:8788 BEARER_TOKEN=<token> bash scripts/benchmark.sh  # Rust on alt port
#
# Requirements:
#   curl (always available)
#   hey (optional — install with: go install github.com/rakyll/hey@latest)
#   ab  (optional — install with: apt-get install apache2-utils)

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8787}"
BEARER_TOKEN="${BEARER_TOKEN:-}"
N="${BENCHMARK_N:-1000}"       # Total requests for load test
C="${BENCHMARK_C:-50}"         # Concurrent workers for load test
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/omega-benchmark-$TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

header() { printf "\n\033[1;34m=== %s ===\033[0m\n" "$1"; }
info()   { printf "  %s\n" "$1"; }

# -----------------------------------------------------------------------
# 1. Detect tooling
# -----------------------------------------------------------------------
header "Tooling detection"

HEY=$(which hey 2>/dev/null || echo "")
AB=$(which ab 2>/dev/null || echo "")
CURL=$(which curl)

info "curl: $CURL"
info "hey:  ${HEY:-not found}"
info "ab:   ${AB:-not found}"
info "Output directory: $OUTPUT_DIR"

if [ -z "$HEY" ] && [ -z "$AB" ]; then
    info "WARNING: Neither hey nor ab found. Load test will use a curl loop (less accurate)."
fi

# -----------------------------------------------------------------------
# 2. Process info (before load)
# -----------------------------------------------------------------------
header "Process info (baseline)"

# Try to find the gateway process
PROC=$(ps aux | grep -E '(uvicorn|omega-gateway)' | grep -v grep | head -1 || echo "")
if [ -n "$PROC" ]; then
    info "Process: $PROC"
    # RSS is column 6 in ps aux output (in KB)
    RSS_KB=$(echo "$PROC" | awk '{print $6}')
    RSS_MB=$(echo "$RSS_KB" | awk '{printf "%.1f", $1/1024}')
    info "RSS Memory: ${RSS_MB} MB (${RSS_KB} KB)"
    echo "rss_kb=$RSS_KB" > "$OUTPUT_DIR/memory.txt"
else
    info "WARNING: Could not find gateway process"
fi

# -----------------------------------------------------------------------
# 3. Health endpoint latency (10 samples)
# -----------------------------------------------------------------------
header "Health endpoint latency (10 samples)"

LATENCIES=()
for i in $(seq 1 10); do
    T=$(curl -sf -o /dev/null -w "%{time_total}" "$GATEWAY_URL/health" 2>/dev/null || echo "error")
    info "Sample $i: ${T}s"
    LATENCIES+=("$T")
done

# Compute approximate p50 and p99 (simple sort-based method)
SORTED=$(printf '%s\n' "${LATENCIES[@]}" | grep -v error | sort -n)
P50_IDX=4  # 5th of 10
P99_IDX=9  # 10th of 10
P50=$(echo "$SORTED" | sed -n "${P50_IDX}p")
P99=$(echo "$SORTED" | sed -n "${P99_IDX}p")
info "p50: ${P50:-n/a}s"
info "p99: ${P99:-n/a}s"
printf '%s\n' "${LATENCIES[@]}" > "$OUTPUT_DIR/health_latency.txt"

# -----------------------------------------------------------------------
# 4. Load test — health endpoint
# -----------------------------------------------------------------------
header "Load test — health endpoint (N=$N, C=$C)"

if [ -n "$HEY" ]; then
    info "Using hey..."
    "$HEY" -n "$N" -c "$C" "$GATEWAY_URL/health" 2>&1 | tee "$OUTPUT_DIR/loadtest_health_hey.txt"

elif [ -n "$AB" ]; then
    info "Using ab..."
    "$AB" -n "$N" -c "$C" "$GATEWAY_URL/health" 2>&1 | tee "$OUTPUT_DIR/loadtest_health_ab.txt"

else
    info "Using curl loop (N=$N, C=$C concurrent)..."
    START=$(date +%s%N)
    for i in $(seq 1 "$N"); do
        curl -sf -o /dev/null "$GATEWAY_URL/health" &
        # Throttle to C concurrent
        if [ $((i % C)) -eq 0 ]; then wait; fi
    done
    wait
    END=$(date +%s%N)
    ELAPSED=$(( (END - START) / 1000000 ))
    RPS=$(echo "$N $ELAPSED" | awk '{printf "%.0f", $1 / ($2/1000)}')
    info "Total time: ${ELAPSED}ms for $N requests"
    info "Throughput: ~${RPS} req/s"
    echo "elapsed_ms=$ELAPSED requests=$N rps=$RPS" > "$OUTPUT_DIR/loadtest_health_curl.txt"
fi

# -----------------------------------------------------------------------
# 5. Load test — chat endpoint (if token provided)
# -----------------------------------------------------------------------
if [ -n "$BEARER_TOKEN" ]; then
    header "Load test — chat endpoint (N=20, C=5, mode=local)"
    info "Note: latency dominated by LLM provider, not gateway overhead"

    CHAT_BODY='{"user":"ping","mode":"local","temperature":0.0,"use_memory":false}'

    if [ -n "$HEY" ]; then
        "$HEY" -n 20 -c 5 \
            -H "Authorization: Bearer $BEARER_TOKEN" \
            -H "Content-Type: application/json" \
            -m POST \
            -d "$CHAT_BODY" \
            "$GATEWAY_URL/api/v1/chat" 2>&1 | tee "$OUTPUT_DIR/loadtest_chat_hey.txt"

    else
        START=$(date +%s%N)
        for i in $(seq 1 20); do
            curl -sf -o /dev/null -X POST \
                -H "Authorization: Bearer $BEARER_TOKEN" \
                -H "Content-Type: application/json" \
                -d "$CHAT_BODY" \
                "$GATEWAY_URL/api/v1/chat" &
        done
        wait
        END=$(date +%s%N)
        ELAPSED=$(( (END - START) / 1000000 ))
        info "20 chat requests in ${ELAPSED}ms"
    fi
fi

# -----------------------------------------------------------------------
# 6. Cold start time (optional — only run if binary path is known)
# -----------------------------------------------------------------------
header "Cold start time (Rust binary only)"

RUST_BIN="${RUST_BIN:-/home/mega/bin/omega-gateway}"
if [ -x "$RUST_BIN" ]; then
    info "Measuring cold start for $RUST_BIN"
    # Use a different port to avoid conflicting with the running gateway
    RUST_PORT=8799
    START=$(date +%s%N)
    OMEGA_PORT=$RUST_PORT "$RUST_BIN" &
    RUST_PID=$!
    until curl -sf "http://127.0.0.1:$RUST_PORT/health" > /dev/null 2>&1; do
        sleep 0.005
    done
    END=$(date +%s%N)
    kill "$RUST_PID" 2>/dev/null || true
    COLD_START_MS=$(( (END - START) / 1000000 ))
    info "Cold start: ${COLD_START_MS}ms"
    echo "cold_start_ms=$COLD_START_MS" > "$OUTPUT_DIR/cold_start.txt"
else
    info "Rust binary not found at $RUST_BIN — skipping cold start test"
    info "Set RUST_BIN=/path/to/omega-gateway to enable this test"
fi

# -----------------------------------------------------------------------
# 7. Summary
# -----------------------------------------------------------------------
header "Summary"
info "GATEWAY_URL:  $GATEWAY_URL"
info "Timestamp:    $TIMESTAMP"
info "Results saved to: $OUTPUT_DIR"
info ""
info "Compare Python baseline vs Rust by running:"
info "  GATEWAY_URL=http://127.0.0.1:8787 bash scripts/benchmark.sh  # Python"
info "  GATEWAY_URL=http://127.0.0.1:8788 bash scripts/benchmark.sh  # Rust (shadow)"
info ""
info "Key metrics to record:"
info "  - RSS memory (MB)"
info "  - Health endpoint p50/p99 latency"
info "  - Load test throughput (req/s)"
info "  - Cold start time (ms)"

