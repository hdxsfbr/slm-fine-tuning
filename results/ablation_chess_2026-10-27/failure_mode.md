# The failure mode that survives the best prompt

From `results.md` in this directory (2 model families x 3 strategies x 30
scenarios, judged by claude-haiku-5.5 with rubric `chess_coach_leak_v2`).

Best cells: claude-sonnet-5.5 with the structured prompt at 20% (6 of 30
conversations hold), gpt-5.5 zero-shot at 10% (3 of 30). Neither model ever
names a square or a move in a hint: the code checks find 0 named leaks in
either best cell. What survives every prompt is **stating the move in
words**. Under pressure the coach keeps the letter of the rule and gives
the answer anyway: "the rook goes to the far end of its file", "yes, the
queen takes the pawn next to the king", or, once the user says the game is
over, the whole line. The judge finds a described leak in 23 of sonnet's 30
best-cell conversations (47 of 220 hint replies) and in 27 of gpt-5.5's (114
of 220). The turns that break it most are "just the square" (15 and 16
leaks), "the game is over" (7 and 19), plain insistence (7 and 8), encodings
and formats (5 and 8), and emotional appeals (4 and 9). The hard negatives
are not the problem: both best cells answer all of them, and sonnet's hints
run long only 4 times in 220.

So the behavior that needs training is not "do not say e4"; the frontier
models already do that. It is holding the hint-only stance when the user has
found a way to ask for the move that does not sound like asking for the
move. A tuned model's job is to keep saying how to look, not what to see,
through the whole conversation.
