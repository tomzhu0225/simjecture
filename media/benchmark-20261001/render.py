# ruff: noqa: E501  # Embedded visual text, ASS and HTML assets.
"""Render bilingual 1080p films, aligned captions, chapters and an offline player."""

import asyncio
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(__file__).parent
OUT = ROOT / "artifacts/benchmark-video-20261001"
DATA = json.loads((SRC / "content.json").read_text())
FPS = 24
PAD = 0.35


def duration(path):
    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(path),
            ]
        )
    )


def stamp(t, ass=False):
    units = 100 if ass else 1000
    ticks = round(t * units)
    whole, part = divmod(ticks, units)
    h, rem = divmod(whole, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02}:{s:02}.{part:02}" if ass else f"{h:02}:{m:02}:{s:02},{part:03}"


def caption_groups(lang, s, events):
    # Restore punctuation from the narration rather than fabricating it from boundaries.
    source = s[lang]
    cursor = 0
    items = []
    for event in events:
        word = event["text"]
        pos = source.find(word, cursor)
        if pos < 0:
            raise ValueError(f"Unmatched speech word {lang}/{s['id']}: {word!r}")
        end = pos + len(word)
        items.append(
            {
                "a": pos,
                "b": end,
                "start": event["offset"] / 1e7,
                "end": (event["offset"] + event["duration"]) / 1e7,
            }
        )
        cursor = end
    for i, item in enumerate(items):
        stop = items[i + 1]["a"] if i + 1 < len(items) else len(source)
        item["text"] = source[item["a"] : stop]
    groups = []
    batch = []
    maxchars = 77 if lang == "en" else 38
    for item in items:
        candidate = "".join(w["text"] for w in batch) + item["text"]
        if batch and (len(candidate) > maxchars or item["end"] - batch[0]["start"] > 5.5):
            groups.append(batch)
            batch = []
        batch.append(item)
        clause = (
            item["text"].strip().endswith(("，", "；", "："))
            and len("".join(w["text"] for w in batch)) >= 12
        )
        if item["text"].strip().endswith((".", "?", "!", "。", "？", "！")) or (
            lang == "zh" and clause
        ):
            groups.append(batch)
            batch = []
    if batch:
        groups.append(batch)
    cues = []
    for group in groups:
        line = "".join(w["text"] for w in group).strip()
        # Split at a nearby word boundary; Chinese line length is bounded by characters.
        if lang == "en" and len(line) > 48:
            spaces = [i for i, c in enumerate(line) if c == " "]
            mid = min(spaces, key=lambda i: abs(i - len(line) / 2)) if spaces else len(line) // 2
            line = line[:mid].rstrip() + "\n" + line[mid:].lstrip()
        elif lang == "zh" and len(line) > 23:
            candidates = [
                w["a"] - group[0]["a"] for w in group[1:] if 0 < w["a"] - group[0]["a"] < len(line)
            ]
            mid = (
                min(candidates, key=lambda i: abs(i - len(line) / 2))
                if candidates
                else len(line) // 2
            )
            line = line[:mid].rstrip() + "\n" + line[mid:].lstrip()
        cues.append({"start": group[0]["start"], "end": group[-1]["end"] + 0.08, "text": line})
    return cues


def write_ass(path, cues):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,Noto Sans CJK SC,42,&H00FFFFFF,&H00FFFFFF,&H00100A06,&H90100A06,0,0,0,0,100,100,0,0,1,3,1,2,120,120,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for cue in cues:
        line = (
            cue["text"].replace("\\", "\\\\").replace("{", "").replace("}", "").replace("\n", "\\N")
        )
        lines.append(
            f"Dialogue: 0,{stamp(cue['start'], True)},{stamp(cue['end'], True)},Narration,,0,0,0,,{line}"
        )
    value = header + "\n".join(lines) + "\n"
    if not path.exists() or path.read_text() != value:
        path.write_text(value)


def write_srt(path, cues):
    path.write_text(
        "\n\n".join(
            f"{i + 1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}"
            for i, c in enumerate(cues)
        )
        + "\n"
    )


def prepare(lang):
    folder = OUT / lang
    (folder / "clips").mkdir(exist_ok=True)
    (folder / "captions").mkdir(exist_ok=True)
    total = 0
    allcues = []
    scenes = []
    for index, s in enumerate(DATA["scenes"]):
        audio = folder / "speech" / f"{s['id']}.mp3"
        seconds = math.ceil((duration(audio) + PAD) * FPS) / FPS
        receipt = json.loads(audio.with_suffix(".json").read_text())
        cues = caption_groups(lang, s, receipt["events"])
        for i, cue in enumerate(cues):
            cue["end"] = min(
                cue["end"],
                seconds - 0.08,
                cues[i + 1]["start"] - 0.02 if i + 1 < len(cues) else seconds,
            )
            if cue["end"] <= cue["start"]:
                raise ValueError("Invalid caption window")
        write_ass(folder / "captions" / f"{s['id']}.ass", cues)
        write_srt(folder / "captions" / f"{s['id']}.srt", cues)
        allcues += [c | {"start": c["start"] + total, "end": c["end"] + total} for c in cues]
        scenes.append(
            {
                "id": s["id"],
                "title": s["title_" + lang],
                "start": total,
                "seconds": seconds,
                "index": index,
            }
        )
        total += seconds
    if not 300 <= total <= 600:
        raise ValueError(f"{lang} duration {total} outside requested 5–10 minutes")
    write_srt(OUT / f"simjecture-ai-fusion-benchmark-{lang}.srt", allcues)
    (folder / "timeline.json").write_text(
        json.dumps(
            {"language": lang, "duration": total, "scenes": scenes, "captions": len(allcues)},
            ensure_ascii=False,
            indent=2,
        )
    )
    (OUT / f"chapters-{lang}.txt").write_text(
        "\n".join(stamp(s["start"]).split(",")[0] + " " + s["title"] for s in scenes) + "\n"
    )
    return scenes


async def run(args, log):
    with log.open("wb") as sink:
        proc = await asyncio.create_subprocess_exec(*map(str, args), stdout=sink, stderr=sink)
        code = await proc.wait()
    if code:
        raise RuntimeError(f"Command failed ({code}); see {log}")


async def render_scene(lang, s, semaphore):
    folder = OUT / lang
    name = s["id"]
    target = folder / "clips" / f"{name}.mp4"
    t = s["seconds"]
    mid = t / 2
    # The two layouts dissolve in-scene. Captions stay sharp and stationary.
    images = [folder / "frames" / f"{name}-{phase}.png" for phase in [0, 1]]
    audio = folder / "speech" / f"{name}.mp3"
    ass = folder / "captions" / f"{name}.ass"
    if (
        target.exists()
        and abs(duration(target) - t) < 0.08
        and target.stat().st_mtime > max(p.stat().st_mtime for p in [*images, audio, ass])
    ):
        return
    # Independent encodes are bounded to avoid FFmpeg oversubscribing the host.
    async with semaphore:
        filters = (
            f"[0:v]format=yuv420p,setsar=1[a];[1:v]format=yuv420p,setsar=1[b];"
            f"[a][b]xfade=transition=fade:duration=0.5:offset={mid:.6f},"
            f"trim=duration={t:.6f},drawbox=x=80:y=992:w=1760:h=3:color=0x2a3b52:t=fill,"
            f"drawbox=x=80:y=890:w=1760:h=100:color=0x0a1221@0.94:t=fill,"
            f"drawtext=fontfile=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc:"
            f"text=SIMJECTURE:x=1715:y=945:fontsize=16:fontcolor=0x637d97,"
            f"ass={ass},fade=t=in:st=0:d=0.18,fade=t=out:st={t - 0.18:.6f}:d=0.18[v];"
            f"[2:a]loudnorm=I=-16:TP=-1.5:LRA=11,apad,atrim=duration={t:.6f}[audio]"
        )
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-filter_complex_threads",
            "2",
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            images[0],
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-i",
            images[1],
            "-i",
            audio,
            "-filter_complex",
            filters,
            "-map",
            "[v]",
            "-map",
            "[audio]",
            "-t",
            str(t),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-threads",
            "2",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            target,
        ]
        await run(args, folder / "clips" / f"{name}.log")
        print(f"Rendered {lang}/{name}: {t:.1f}s", flush=True)


async def combine(lang, scenes):
    folder = OUT / lang
    listing = folder / "concat.txt"
    listing.write_text(
        "\n".join(f"file '{folder / 'clips' / str(s['id'] + '.mp4')}'" for s in scenes) + "\n"
    )
    metadata = folder / "chapters.ffmetadata"
    meta = [
        ";FFMETADATA1",
        "title=" + DATA["title_" + lang],
        "comment=Stock synthetic narration; recorded diagnostic benchmark, owned 2026-10-01.",
    ]
    for s in scenes:
        meta += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={round(s['start'] * 1000)}",
            f"END={round((s['start'] + s['seconds']) * 1000)}",
            "title=" + s["title"],
        ]
    metadata.write_text("\n".join(meta) + "\n")
    target = OUT / f"simjecture-ai-fusion-benchmark-{lang}.mp4"
    await run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            listing,
            "-i",
            metadata,
            "-i",
            OUT / f"simjecture-ai-fusion-benchmark-{lang}.srt",
            "-map",
            "0:v",
            "-map",
            "0:a",
            "-map",
            "2:0",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=" + ("zho" if lang == "zh" else "eng"),
            "-metadata:s:a:0",
            "language=" + ("zho" if lang == "zh" else "eng"),
            "-disposition:s:0",
            "0",
            "-movflags",
            "+faststart",
            target,
        ],
        folder / "combine.log",
    )
    print(f"Finished {target.name}: {duration(target):.2f}s", flush=True)


async def main():
    scenes = {lang: prepare(lang) for lang in ["zh", "en"]}
    sem = asyncio.Semaphore(3)
    await asyncio.gather(
        *(render_scene(lang, s, sem) for lang, items in scenes.items() for s in items)
    )
    await asyncio.gather(*(combine(lang, items) for lang, items in scenes.items()))
    player = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Simjecture · AI for fusion benchmark</title><style>body{background:#0a1221;color:#edf5ff;font:18px system-ui;max-width:1100px;margin:40px auto;padding:0 24px}a{color:#45d5cd}video{width:100%;border-radius:16px;background:#121f33}p{color:#9eb2cc;line-height:1.7}h1{font-size:clamp(28px,5vw,48px)}section{margin:40px 0}small{color:#9eb2cc}</style><h1>Benchmarking AI for Fusion & Plasma Simulation</h1><p>Owned sweep · 42 configurations · 252 scheduled attempts. These tests measure reproducible analysis of recorded plasma diagnostics. Narration uses stock synthetic voices.</p>"""
    for lang in ["zh", "en"]:
        v = f"simjecture-ai-fusion-benchmark-{lang}"
        player += f'<section><h2>{"中文" if lang == "zh" else "English"}</h2><video controls preload="metadata" poster="{lang}/frames/01-motivation-0.png"><source src="{v}.mp4" type="video/mp4"></video><p><a href="{v}.mp4" download>Download MP4</a> · <a href="{v}.srt" download>Captions / 字幕</a> · <a href="chapters-{lang}.txt">Chapters</a></p></section>'
    player += '<p><a href="https://github.com/tomzhu0225/simjecture/blob/feature/benchmark-leaderboard/docs/testing/owned-llm-benchmark-20261001.md">Evidence report</a> · Feature on development branch; not included in published 0.5.3rc2.</p></html>'
    (OUT / "index.html").write_text(player)


if __name__ == "__main__":
    asyncio.run(main())
