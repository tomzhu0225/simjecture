"""Transfer verified model bytes to the existing remote training host, with resumable parts."""

import json
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from remote import REMOTE_ROOT, connection, python

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "models" / "Qwen3.5-9B"


def main():
    manifest = json.loads((MODEL / "verified-manifest.json").read_bytes())

    def transfer(item):
        name = item["path"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Unexpected model manifest path")
        remote = f"{REMOTE_ROOT}/models/Qwen3.5-9B/{name}"
        check = python(f"""from pathlib import Path
import json
p=Path({remote!r}); part=p.with_name(p.name+'.part')
print(json.dumps({{'complete':p.exists() and p.stat().st_size=={item["bytes"]},'offset':part.stat().st_size if part.exists() else 0}}))
""")
        if check.returncode:
            raise RuntimeError("Cannot inspect the remote model destination")
        status = json.loads(check.stdout)
        if status["complete"]:
            print("remote_present", name, flush=True)
            return
        offset = status["offset"]
        print("transferring", name, "from", offset, flush=True)
        script = f"""from pathlib import Path
import sys,shutil,hashlib,os
p=Path({remote!r}); p.parent.mkdir(parents=True,exist_ok=True)
part=p.with_name(p.name+'.part')
if (part.stat().st_size if part.exists() else 0)!={offset}:raise ValueError('Resume offset changed')
with part.open('ab') as stream:shutil.copyfileobj(sys.stdin.buffer,stream,4*1024*1024)
if part.stat().st_size!={item["bytes"]}:raise ValueError('Transfer is incomplete')
with part.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
if actual!={item["sha256"]!r}:raise ValueError('Transfer checksum mismatch')
os.replace(part,p)
print('verified',p.name,actual)
"""
        with (MODEL / name).open("rb") as stream:
            stream.seek(offset)
            result = subprocess.run(
                connection() + ["python3", "-c", shlex.quote(script)],
                stdin=stream,
                capture_output=True,
                check=False,
            )
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace")[-1000:])
        print(result.stdout.decode().strip(), flush=True)

    # Small files first so configuration is available while weights are staged.
    items = sorted(manifest["files"], key=lambda item: item["bytes"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(transfer, items))
    encoded = json.dumps(manifest)
    result = python(f"""from pathlib import Path
import json
p=Path({REMOTE_ROOT!r})/'models/Qwen3.5-9B/verified-manifest.json'
p.write_text({encoded!r})
print(json.dumps({{'status':'verified','model_loaded':False,'training_updates':0}}))
""")
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1000:])
    (ROOT / "reports" / "remote_model_transfer.json").write_bytes(result.stdout)
    print(result.stdout.decode(), flush=True)


if __name__ == "__main__":
    main()
