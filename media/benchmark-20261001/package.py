# ruff: noqa: E501  # Embedded visual text, ASS and HTML assets.
"""Create a shareable, self-contained package of public video deliverables."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/benchmark-video-20261001"
PUB = OUT / "deliverables"


def main():
    validation = json.loads((OUT / "validation.json").read_text())
    PUB.mkdir(exist_ok=True)
    for lang in ["zh", "en"]:
        film = OUT / f"simjecture-ai-fusion-benchmark-{lang}.mp4"
        assert hashlib.sha256(film.read_bytes()).hexdigest() == validation["films"][lang]["sha256"]
        for name in [
            film.name,
            f"simjecture-ai-fusion-benchmark-{lang}.srt",
            f"chapters-{lang}.txt",
        ]:
            shutil.copy2(OUT / name, PUB / name)
        poster = PUB / lang / "frames"
        poster.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / lang / "frames/01-motivation-0.png", poster / "01-motivation-0.png")
    for name in ["facts.json", "validation.json", "index.html"]:
        shutil.copy2(OUT / name, PUB / name)
    source = PUB / "source"
    source.mkdir(exist_ok=True)
    for path in SRC.iterdir():
        if path.is_file():
            shutil.copy2(path, source / path.name)
    page = (
        (PUB / "index.html")
        .read_text()
        .replace(
            '<p><a href="https://github.com',
            '<p><a href="source/script-zh.md">中文口播稿</a> · <a href="source/script-en.md">English script</a> · <a href="source/sources.md">Sources and limits</a> · <a href="validation.json">Media validation</a></p><p><a href="https://github.com',
        )
    )
    (PUB / "index.html").write_text(page)

    def clock(seconds):
        value = round(seconds)
        return f"{value // 60}:{value % 60:02}"

    timing = f"Chinese: {clock(validation['films']['zh']['duration_seconds'])}. English: {clock(validation['films']['en']['duration_seconds'])}."
    (PUB / "README.txt").write_text(
        (
            "Simjecture — AI for fusion and plasma simulation benchmark\n\nChinese: 9:23. English: 9:51. 1920×1080, H.264/AAC.\nStock synthetic narration; visible and selectable captions; 12 chapters.\n\nPlay either MP4 directly or open index.html. SRT captions and editable\nbilingual scripts/storyboard/sources are included. This is a benchmark of\nrecorded-data analysis, not proof of general autonomous fusion research.\n\nMeasured sweep: 2026-10-01; task pack 0.3.0; development branch\nfeature/benchmark-leaderboard. See source/sources.md for evidence.\n"
        ).replace("Chinese: 9:23. English: 9:51.", timing)
    )
    archive = OUT / "simjecture-ai-fusion-benchmark-bilingual.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=5) as bundle:
        for path in sorted(PUB.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(PUB))
    print(f"Packaged {archive.name}: {archive.stat().st_size / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
