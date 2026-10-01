# AI for fusion and plasma simulation: benchmark documentary

Two factual, narrated videos based on Simjecture's **owned 2026-10-01 benchmark**, each within the requested **5–10 minutes**. The broader research motivation is fusion/plasma simulation; the measured tasks specifically analyze recorded diagnostic data. The scripts distinguish numerical correctness, timed delivery, availability, cost estimates, and statistical limits.

- [English narration](script-en.md)
- [中文口播稿](script-zh.md)
- [Matching twelve-beat storyboard](outline.md)
- [Evidence, limitations and source links](sources.md)
- `content.json`: editable bilingual scene source.
- `speech.py`: stock synthesized narration with aligned word receipts.
- `graphics.py`: original 1920×1080 data graphics.
- `render.py`: in-scene dissolves, captions, chapter metadata and H.264/AAC encoding.
- `validate.py`: full decode, 1080p streams, chapter/caption timing, narration fidelity and public fact checks.
- `package.py`: portable bilingual ZIP and a public-only preview folder.

Generated deliverables are in `artifacts/benchmark-video-20261001/` at the repository root:

```text
index.html                              Offline video player
simjecture-ai-fusion-benchmark-bilingual.zip  Shareable package
deliverables/                           Public-only browser preview
simjecture-ai-fusion-benchmark-zh.mp4     Chinese film
simjecture-ai-fusion-benchmark-en.mp4     English film
simjecture-ai-fusion-benchmark-zh.srt     Chinese captions
simjecture-ai-fusion-benchmark-en.srt     English captions
chapters-zh.txt / chapters-en.txt        Chapter starts
validation.json                         Media checks
facts.json                              Frozen public dashboard snapshot
zh/ and en/                             Scene images, audio, timing and render logs
```

The MP4s contain visible captions and an additional selectable caption track. Narration uses stock synthetic voices, disclosed in the film and player. No named person's voice is cloned. There is no third-party footage or background music. The files can be played directly; `index.html` also works through an ordinary local HTTP server. Large artifacts and the isolated production environment remain excluded from Git.

## Rebuild

Use Python 3.12+, FFmpeg/ffprobe with `libx264`, AAC and libass, plus Noto Sans CJK fonts. Commands below run from the Simjecture repository root. The speech stage uses the Edge online speech service; it does not use a model API key, benchmark inference, or the user's coding-plan credentials. Text must be appropriate for sending to that speech service.

```bash
uv venv artifacts/benchmark-video-20261001/.venv
uv pip install --python artifacts/benchmark-video-20261001/.venv/bin/python \
  -r media/benchmark-20261001/requirements.txt

.venv/bin/python - <<'PY'
import json
from pathlib import Path
from conjecture_solver.llm_bench.official import dashboard
Path('artifacts/benchmark-video-20261001/facts.json').write_text(
    json.dumps(dashboard(), ensure_ascii=False, indent=2)
)
PY

artifacts/benchmark-video-20261001/.venv/bin/python media/benchmark-20261001/speech.py
artifacts/benchmark-video-20261001/.venv/bin/python media/benchmark-20261001/graphics.py
artifacts/benchmark-video-20261001/.venv/bin/python media/benchmark-20261001/render.py
artifacts/benchmark-video-20261001/.venv/bin/python media/benchmark-20261001/validate.py
artifacts/benchmark-video-20261001/.venv/bin/python media/benchmark-20261001/package.py
```

`script-en.md` and `script-zh.md` mirror the paragraphs in `content.json`; keep them synchronized when editing. If narration changes, regenerate speech and chapter timings. Exact duration is measured from audio and encoding, rather than inferred from word count. The renderer rejects a version outside 300–600 seconds.

The graphics show selected comparisons and explicitly label the top-ten completed RZ ranking subset, with two additional unfinished examples. The Pareto view includes all eligible completed configurations, excluding partial cost bounds. Source grades are never modified by the production scripts.
