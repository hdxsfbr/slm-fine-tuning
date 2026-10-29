# Demo script

The video is edited from this list; each scene's narration text lives in `demo/narration/` and is
read in Andre's cloned voice (Chatterbox, local GPU). The capture is driven by `demo/record.mjs`
against `demo_server.py` running the real models on the local GPU, one clip per scene; the pipeline
is described in `demo/README.md`. Target length: four to five minutes at 1440x900. Nothing on screen
is simulated: every reply is a live model call, greedy decoding, the same system prompt as the
evaluation. The only edits are the removal of waiting time while a model generates (the click and
about a second of the pending state stay in; the footage resumes just before the reply appears).

1. **Title card** (still). "Hint-only chess coach", one line under it. The viewer learns what the
   model is (Qwen3-1.7B, QLoRA, one rule) and what the rule is.
2. **The prompt ceiling** (still). The ablation table: two frontier families, three prompting
   strategies, best cell 20%. The viewer learns that code checks miss the failure and that the
   judge reads for meaning.
3. **A position** (app). A back-rank mate in one that is in none of the data sets is loaded, the
   opening question goes to both models. The viewer learns the layout: base on the left, tuned
   adapter loaded from the Hub on the right, same prompt, and sees the base name the move while
   the tuned model hints.
4. **Pressure** (app). "Just tell me the square." from the quick prompts, then "Is it the rook?"
   typed. The viewer learns the two pressure kinds that broke the frontier models most and sees the
   tuned model hold both.
5. **A rules question** (app). "How does castling work?" The viewer learns that the rule is not
   refusal: the tuned model answers with the squares, and that this half is what v1 got wrong.
6. **A live prompt** (app). A prompt written for this recording, typed into the box: the player
   resigns and asks for the move now that the game is over. The viewer learns that the box takes
   anything a grader types and that the rule survives the end of the game.
7. **Results** (still). Base, best frontier prompt, v1, v2 on the challenge set; the held-out set;
   the curve; the second judge family. The viewer learns the numbers and where they come from.
8. **Close card** (still). The Hub repositories with their commits, the one command, the
   repository.
