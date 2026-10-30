# Demo video pipeline

Produces `out/chess-coach-demo.mp4` (1440x900, 30 fps, H.264 + AAC 48 kHz): a screen capture of the
demo page (`demo_server.py`, the base model and the tuned adapter on the local GPU) narrated in
Andre's cloned voice (Chatterbox standard model, local GPU, the reference recording is Andre's own).
The scene list is [`../demo-script.md`](../demo-script.md); each scene's narration is
`narration/sNN_<name>.txt`. Everything is scripted, so the video can be regenerated after a change.

Nothing on screen is simulated. Every reply is a live call to the two models with greedy decoding and
the evaluation's system prompt. The only edits are the removal of waiting time while a model
generates, listed under "What is cut" below.

## Regenerate

Run from the repository root. `playwright-core` is not a project dependency; point `NODE_PATH` at
any `node_modules` that has it (the scripts load it with `createRequire`).

1. **Narration** (needs the `chatterbox` conda env and the voice reference in `~/code/chatterbox-play`):
   ```bash
   conda run -n chatterbox --no-capture-output python -u docs/demo/tts_std.py docs/demo/narration docs/demo/audio < /dev/null
   conda run -n chatterbox --no-capture-output python -u docs/demo/tts_std.py docs/demo/narration docs/demo/audio s03,s04 < /dev/null   # only these scenes
   bash docs/demo/verify.sh audio        # duration against word count, loudness, silent gaps
   ```
   One WAV per scene (`audio/sNN_*_norm.wav`, 48 kHz mono, loudness-normalised) and `audio/durations.json`.
2. **Slides**:
   ```bash
   NODE_PATH=<dir with node_modules/playwright-core> node docs/demo/slides.mjs
   ```
   renders the four stills in `slides/` to `slides/png/sNN_<name>.png` (1440x900) and the
   thumbnail (`slides/thumbnail.html`) to `thumbnail.png` (1280x720).
3. **Capture.** The server must be running with the models the video claims (the adapter by Hub id
   at its pinned commit), on a port nothing else uses:
   ```bash
   .venv-train/bin/python demo_server.py --model hdxsfbr/qwen3-1.7b-chess-coach-hints@5f3bb8046ae96bd197ab93cc60964ba6c02243fb \
       --baseline unsloth/Qwen3-1.7B --port 7865 < /dev/null > /tmp/demo-server.log 2>&1 &
   curl -s localhost:7865/api/health      # the loaded revisions
   NODE_PATH=<...> node docs/demo/record.mjs                              # all scenes -> docs/demo/clips/
   NODE_PATH=<...> CLIPS_DIR=/tmp/dry node docs/demo/record.mjs           # a dry run into a throwaway directory
   NODE_PATH=<...> SCENES=s04,s05 node docs/demo/record.mjs               # selected scenes
   bash docs/demo/verify.sh sheets       # a contact sheet per clip, to look at before moving on
   ```
   The scenes continue one conversation that the server holds (session `demo-recorder`, which the
   recorder sets in the page's localStorage before each scene) and the page restores on load, so
   they run in order: s03 loads the position (which starts the conversation over) and s04 to s06 add
   turns to it. A single scene can be re-recorded with `SCENES=` only while the server still holds
   the state the scene before it left, and only once on that state; otherwise run again from s03.
   `BASE` (default `http://localhost:7865`), `CLIPS_DIR` and `CHROME` are read from the environment.
4. **Assembly**:
   ```bash
   bash docs/demo/mux.sh
   bash docs/demo/verify.sh final        # ffprobe, contact sheet, per-scene audio and video lengths
   ```
   Kill the server when the take is done.

## How the capture works

- One browser context per scene at 1440x900, so each scene is its own clip, `clips/sNN_<name>.webm`.
  A cursor is injected into every page; it follows the real mouse events and glides to each target
  before it clicks.
- The frames come from a CDP screencast that `record.mjs` timestamps itself and assembles into a
  30 fps WebM, so a clip's time is the wall clock and a cut is exact (Playwright's `recordVideo`
  drifts from the wall clock during fast page updates).
- `slow(label, fn)` wraps the wait for each reply. It records `[start + 1.0, end - 0.4]` (seconds
  from the clip's first frame) into `clips/cuts.json`: the click and a second of the pending state
  stay in, and the footage resumes 0.4 s before the reply appears. The two models answer one after
  the other (one GPU), so a turn has two cuts and the base reply is on screen while the tuned one
  is pending. Page loads at the start of a scene are recorded as a cut `[0, ready]`.
- `mux.sh` strips the intervals in `cuts.json`, paces each scene to its narration (a short clip
  holds its last frame, a long one is sped up by at most 1.6x), re-encodes every scene and still to
  one intermediate (H.264 crf 20, AAC, 48 kHz stereo), concatenates, and fades the last second out.
  Stills are held for their narration plus 0.6 s. Narration starts 0.2 s into its scene.

## What is cut

- **Model waits.** In scenes s03 to s06, the time each model takes to generate its reply, less the
  second that stays in. Each cut is in `clips/cuts.json`; the log of the take prints it as `cut a-b`.
- **Page loads.** The first fraction of a second of each scene, before the page has drawn.

## Deliverables

| File | What |
| --- | --- |
| `out/chess-coach-demo.mp4` | the narrated video |
| `thumbnail.png` | the YouTube thumbnail, 1280x720, rendered from `slides/thumbnail.html` |
| `youtube.md` | title, description, chapters and upload notes |
| `slides/*.html` | the four stills (title, ceiling, results, close) and the thumbnail, source of the PNGs |
| `narration/*.txt`, `tts_std.py` | the narration text and the script that voices it |
| `record.mjs`, `mux.sh`, `slides.mjs`, `verify.sh` | capture, assembly, slides, checks |

Generated media (`audio/`, `clips/`, `slides/png/`, `out/`) is gitignored; the scripts, narration
and slide HTML are the source of truth. `thumbnail.png` is committed.
