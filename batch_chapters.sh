#!/usr/bin/env bash
# Batch translate all Renegade Immortal chapters using proven CLI
set -e

SRC="/c/Users/Marc/Downloads/wuxiaworld"
OUT="${SRC}/target"
VENV="/c/Users/Marc/Documents/1G1R/_Programmation/noveltrad/.venv/Scripts/python"
COUNT=0
SUCCESS=0
FAIL=0
SKIP=0

export PYTHONPATH=

cd "/c/Users/Marc/Documents/1G1R/_Programmation/noveltrad"

for f in "$SRC"/*.txt; do
    fname=$(basename "$f")
    stem="${fname%.txt}"
    out="${OUT}/${stem}_${stem}.txt"
    COUNT=$((COUNT + 1))

    if [ -f "$out" ] && [ "$(wc -c < "$out")" -gt 100 ]; then
        echo "[$COUNT] SKIP $fname"
        SKIP=$((SKIP + 1))
        continue
    fi

    echo "[$COUNT] $fname ..."
    if "$VENV" -m src.backend.cli translate "$f" \
        --profile premium --source-lang en --target-lang fr \
        --output "$OUT" --timeout 600 --quiet 2>&1 | tail -3; then
        SUCCESS=$((SUCCESS + 1))
        echo "  OK (success=$SUCCESS fail=$FAIL skip=$SKIP)"
    else
        FAIL=$((FAIL + 1))
        echo "  FAIL (success=$SUCCESS fail=$FAIL skip=$SKIP)"
    fi
done

echo "DONE: $SUCCESS success, $FAIL fail, $SKIP skip, $COUNT total"
