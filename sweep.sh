#!/usr/bin/env bash
# Train one cell per argument and evaluate it on the challenge set with the
# judge, tuned model only. Each argument is a cell name followed by train.py
# flags:
#
#     ./sweep.sh "s2024 --seed 2024" "ep3 --epochs 3" "r32 --r 32 --alpha 32"
#
# DATA (default data/v3c/train.jsonl), OUT (default results/sweep_<date>),
# PY (default .venv-train/bin/python) and JUDGE (default: eval.py's default)
# come from the environment. A cell whose eval has a results.md is skipped,
# so a stopped sweep resumes. Models land in models/sweep_<name>, logs in
# OUT/train_<name>.log and OUT/eval_<name>.log.
set -uo pipefail
cd "$(dirname "$0")"
PY=${PY:-.venv-train/bin/python}
DATA=${DATA:-data/v3c/train.jsonl}
OUT=${OUT:-results/sweep_$(date +%F)}
mkdir -p "$OUT"
judge_flag=()
if [ -n "${JUDGE:-}" ]; then judge_flag=(--judge "$JUDGE"); fi
for cell in "$@"; do
    name=${cell%% *}
    flags=${cell#"$name"}
    model=models/sweep_$name
    evaldir=$OUT/eval_$name
    if [ -f "$evaldir/results.md" ]; then echo "== $name: done, skipping"; continue; fi
    echo "== $name: train$flags  $(date -u +%H:%M:%SZ)"
    if [ ! -f "$model/adapter/adapter_config.json" ]; then
        # shellcheck disable=SC2086
        $PY train.py --data "$DATA" --out "$model" $flags > "$OUT/train_$name.log" 2>&1 < /dev/null \
            || { echo "== $name: train failed, see $OUT/train_$name.log"; continue; }
    fi
    echo "== $name: eval  $(date -u +%H:%M:%SZ)"
    $PY eval.py --model "$model/adapter" --no-baseline --out "$evaldir" "${judge_flag[@]}" > "$OUT/eval_$name.log" 2>&1 < /dev/null \
        || echo "== $name: eval failed, see $OUT/eval_$name.log"
    grep -h 'Tuned minus base\|^| local:models' "$evaldir/results.md" 2>/dev/null | head -3
done
echo "== sweep done $(date -u +%H:%M:%SZ)"
