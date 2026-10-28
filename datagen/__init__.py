"""Training-data generation for the hint-only chess coach.

    positions.py   verified mate-in-one positions, disjoint from the eval positions
    taxonomy.py    personas x situations x pressure kinds x hard negatives, plan sampling
    generate.py    teacher calls, one conversation per call, resumable JSONL
    gate.py        structure, dedupe, length, code checks, judge, leakage, split, hashes

The teacher writes on-spec by construction: the spec, the position, the
move it must not reveal and the per-turn plan are all in its prompt. The
gate then trusts nothing: every hint turn goes through the same code checks
and the same judge as the ablation.
"""
