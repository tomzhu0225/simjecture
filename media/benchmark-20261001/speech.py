"""Synthesize stock narration with cached scene audio and word timing receipts."""

import asyncio
import hashlib
import json
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/benchmark-video-20261001"
DATA = json.loads(Path(__file__).with_name("content.json").read_text())
VOICES = {"en": "en-US-GuyNeural", "zh": "zh-CN-YunxiNeural"}
RATE = {"en": "-8%", "zh": "-8%"}


async def main():
    semaphore = asyncio.Semaphore(3)

    async def scene(lang, s):
        folder = OUT / lang / "speech"
        folder.mkdir(parents=True, exist_ok=True)
        stem = folder / s["id"]
        signature = hashlib.sha256((s[lang] + VOICES[lang] + RATE[lang]).encode()).hexdigest()
        receipt = stem.with_suffix(".json")
        if (
            receipt.exists()
            and stem.with_suffix(".mp3").exists()
            and json.loads(receipt.read_text()).get("sha256") == signature
        ):
            return
        async with semaphore:
            for attempt in range(4):
                try:
                    events = []
                    with stem.with_suffix(".mp3").open("wb") as stream:
                        async for chunk in edge_tts.Communicate(
                            s[lang], VOICES[lang], rate=RATE[lang], boundary="WordBoundary"
                        ).stream():
                            if chunk["type"] == "audio":
                                stream.write(chunk["data"])
                            elif chunk["type"] == "WordBoundary":
                                events.append(chunk)
                    if not events:
                        raise RuntimeError("No word timing events")
                    receipt.write_text(
                        json.dumps(
                            {
                                "sha256": signature,
                                "voice": VOICES[lang],
                                "rate": RATE[lang],
                                "synthetic": True,
                                "events": events,
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                    print(f"{lang} {s['id']}: {len(events)} aligned words", flush=True)
                    return
                except Exception as error:
                    if attempt == 3:
                        raise
                    print(f"Retrying speech {lang}/{s['id']}: {type(error).__name__}", flush=True)
                    await asyncio.sleep(2 * (attempt + 1))

    await asyncio.gather(*(scene(lang, s) for lang in VOICES for s in DATA["scenes"]))


if __name__ == "__main__":
    asyncio.run(main())
