#!/usr/bin/env bash
# End-to-end smoke test of the loop, generate -> gate -> train -> eval ->
# judge, on a handful of rows with the offline mock teacher and mock judge.
# No API calls. Needs the training environment (a GPU and .venv-train) for
# the train and eval steps; everything before them runs on any Python.
#
#     ./smoke.sh                      # writes results/smoke/
#     OUT=/tmp/smoke PY=python3 ./smoke.sh
#
# The log of the last run is results/smoke/smoke.log. The point is that the
# whole loop runs from nothing in one command, not the numbers it prints:
# the mock teacher writes the same few hints for every position.
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv-train/bin/python}
OUT=${OUT:-results/smoke}
BASE=${BASE:-unsloth/Qwen3-1.7B}
rm -rf "$OUT"
mkdir -p "$OUT/data"
exec > >(tee "$OUT/smoke.log") 2>&1
echo "== smoke run $(date -u +%Y-%m-%dT%H:%M:%SZ) with $PY into $OUT"

echo "== 1. positions (python-chess verified, disjoint from the eval set)"
$PY run_datagen.py positions --n 12 --seed 7 --out "$OUT/positions.jsonl"

echo "== 2. generate 8 conversations with the mock teacher"
$PY run_datagen.py generate "$OUT/positions.jsonl" --n 8 --teacher mock:teacher --out "$OUT/generated.jsonl" --seed 7 --workers 2 < /dev/null

echo "== 3. gate with the code checks and the mock judge"
$PY run_datagen.py gate "$OUT/generated.jsonl" --out "$OUT/data" --judge mock:judge --seed 7 --holdout 0.25 < /dev/null

echo "== 4. train one epoch of QLoRA on the gated rows"
$PY train.py --data "$OUT/data/train.jsonl" --out "$OUT/model" --epochs 1 --seed 3407 < /dev/null

echo "== 5. eval base vs tuned on two challenge scenarios, judged by the mock judge"
$PY eval.py --model "$OUT/model/adapter" --baseline "$BASE" --eval-set challenge --limit 2 --judge mock:judge --out "$OUT/eval" < /dev/null

echo "== done: $OUT/eval/results.md"
sed -n '1,12p' "$OUT/eval/results.md"
