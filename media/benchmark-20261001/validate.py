"""Check final media, narration/caption fidelity, timing and public facts."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/benchmark-video-20261001"
DATA = json.loads((SRC / "content.json").read_text())
FACTS = json.loads((OUT / "facts.json").read_text())


def norm(text):
    return re.sub(r"\s+", "", text)


def seconds(value):
    h, m, s = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    assert FACTS["pack_version"] == "0.3.0"
    assert (
        FACTS["configurations"] == 42
        and FACTS["attempts"] == 252
        and FACTS["unavailable_attempts"] == 24
    )
    tasks = {t["id"]: t for t in FACTS["tasks"]}
    assert sum(r["trials"] for r in tasks["csv-energy"]["rows"]) == 188
    assert sum(r["passes"] for r in tasks["csv-energy"]["rows"]) == 100
    assert sum(r["numeric_passes"] for r in tasks["csv-energy"]["rows"]) == 161
    assert sum(r["trials"] for r in tasks["rz-diagnostics"]["rows"]) == 40
    assert sum(r["passes"] for r in tasks["rz-diagnostics"]["rows"]) == 34
    assert len(DATA["scenes"]) == 12
    assert len(re.findall(r"^## ", (SRC / "outline.md").read_text(), re.M)) == 12
    checks = {
        "facts": "42 configurations, 252 scheduled, 24 no-inference, CSV 100/188 and RZ 34/40",
        "films": {},
    }
    for lang in ["zh", "en"]:
        expected = "\n\n---\n\n".join(
            "## " + s["id"] + " — " + s["title_" + lang] + "\n\n" + s[lang] for s in DATA["scenes"]
        )
        assert (SRC / f"script-{lang}.md").read_text() == "# " + DATA[
            "title_" + lang
        ] + "\n\n" + expected + "\n"
        video = OUT / f"simjecture-ai-fusion-benchmark-{lang}.mp4"
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_format",
                    "-show_streams",
                    "-show_chapters",
                    "-of",
                    "json",
                    str(video),
                ]
            )
        )
        v = next(s for s in probe["streams"] if s["codec_type"] == "video")
        a = next(s for s in probe["streams"] if s["codec_type"] == "audio")
        sub = next(s for s in probe["streams"] if s["codec_type"] == "subtitle")
        duration = float(probe["format"]["duration"])
        assert 300 <= duration <= 600
        assert (v["width"], v["height"], v["codec_name"], a["codec_name"], sub["codec_name"]) == (
            1920,
            1080,
            "h264",
            "aac",
            "mov_text",
        )
        assert v["r_frame_rate"] == "24/1" and len(probe["chapters"]) == 12
        assert abs(float(v["duration"]) - float(a["duration"])) < 0.25
        timeline = json.loads((OUT / lang / "timeline.json").read_text())
        assert abs(timeline["duration"] - duration) < 0.35
        for chapter, scene in zip(probe["chapters"], timeline["scenes"], strict=True):
            assert abs(float(chapter["start_time"]) - scene["start"]) < 0.02
        last = 0
        count = 0
        text = []
        for block in (
            (OUT / f"simjecture-ai-fusion-benchmark-{lang}.srt").read_text().strip().split("\n\n")
        ):
            lines = block.splitlines()
            start, end = map(seconds, lines[1].split(" --> "))
            assert last <= start < end <= duration
            last = end
            count += 1
            text.append("".join(lines[2:]))
        assert norm("".join(text)) == norm("".join(s[lang] for s in DATA["scenes"]))
        # Decode every frame and all audio; catch damaged packets beyond metadata.
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-f",
                "null",
                "-",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        checksum = hashlib.sha256(video.read_bytes()).hexdigest()
        checks["films"][lang] = {
            "duration_seconds": duration,
            "resolution": "1920×1080",
            "fps": 24,
            "video": "H.264",
            "audio": "AAC 48 kHz",
            "caption_cues": count,
            "chapters": 12,
            "bytes": video.stat().st_size,
            "sha256": checksum,
            "full_decode": "passed",
            "narration_caption_fidelity": "passed",
        }
        print(
            f"{lang}: {duration:.2f}s, 1080p, {count} aligned captions, full decode passed",
            flush=True,
        )
    # Scan only authored public prose. Do not read or reproduce historical credentials.
    prose = (
        "\n".join(p.read_text() for p in SRC.glob("*.md"))
        + "\n"
        + (SRC / "content.json").read_text()
    )
    assert not re.search(
        r"(?:sk-|tp-)[A-Za-z0-9]{16,}|ssh\s+-p\s+23|(?:\d{1,3}\.){3}\d{1,3}", prose
    )
    checks["public_prose_secret_scan"] = "passed"
    (OUT / "validation.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
