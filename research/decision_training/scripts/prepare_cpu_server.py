"""Deploy the pinned native worker to the newly connected independent CPU host."""

import base64
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    route = json.loads((ROOT / "config/ssh-cpu-route.local.json").read_bytes())
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for prefix in ["vendor/simjecture/src", "research_decision", "schemas"]:
            for path in (ROOT / prefix).rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    tar.add(path, arcname=path.relative_to(ROOT).as_posix())
    payload = base64.b64encode(buffer.getvalue()).decode()
    remote = "/srv/simjecture-decision"
    prepare = r"""from pathlib import Path
import json,os,subprocess,sys,shutil
root=Path('/srv/simjecture-decision')
runtime=root/'resources/cpu-runtime'
runtime.parent.mkdir(parents=True,exist_ok=True)
if not (runtime/'bin/python').exists():subprocess.run([sys.executable,'-m','venv','--without-pip',str(runtime)],check=True)
python=runtime/'bin/python'
subprocess.run([sys.executable,'-m','pip','--python',str(python),'install','--index-url','https://repo.huaweicloud.com/repository/pypi/simple','simjecture[process]==0.7.1','numpy==1.26.4','scipy==1.17.1','jsonschema==4.26.0'],check=True)
wrapper=root/'resources/cpu-python'
wrapper.write_text('#!/bin/sh\nexport PYTHONPATH="'+str(root)+'/vendor/simjecture/src:'+str(root)+'${PYTHONPATH:+:$PYTHONPATH}"\nexport ASCEND_RT_VISIBLE_DEVICES= CUDA_VISIBLE_DEVICES= TORCH_DEVICE_BACKEND_AUTOLOAD=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\nexec '+str(python)+' "$@"\n'.replace('\\n','\n'))
wrapper.chmod(0o755)
sys.path.insert(0,str(root/'vendor/simjecture/src'))
tail=Path(__file__).read_text().split('from conjecture_solver.execution_worker import Worker\n',1)[1]
code='from pathlib import Path\nimport json\nroot=Path('+repr(str(root))+')\nfrom conjecture_solver.execution_worker import Worker\n'+tail
os.execv(str(wrapper),[str(wrapper),'-c',code])
from conjecture_solver.execution_worker import Worker
worker=Worker(root/'cpu-worker')
worker.configure(dict(execution_backend='process-cooperative',capabilities=[],cpus=16,memory_mb=24576,gpu_ids=[],max_jobs=16))
probe=worker.probe()
(root/'cpu-preparation.json').write_text(json.dumps(dict(ready=probe['execution']['available'],probe=probe),indent=2))
print(json.dumps(dict(ready=probe['execution']['available'],cpus=16,memory_mb=24576)))
"""
    source = base64.b64encode(prepare.encode()).decode()
    script = f"""import base64,io,json,tarfile,subprocess,os
from pathlib import Path
root=Path({remote!r});root.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode({payload!r})),mode='r:gz') as tar:
 for member in tar:
  path=(root/member.name).resolve()
  if not path.is_relative_to(root) or not member.isfile():raise ValueError('Unsafe preparation payload')
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
p=root/'prepare-cpu.py';p.write_bytes(base64.b64decode({source!r}))
with (root/'prepare-cpu.log').open('ab') as log:
 child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
print(json.dumps(dict(preparation_pid=child.pid,scientific_studies_started=0)))
"""
    result = subprocess.run(
        route + ["python3", "-"], input=script.encode(), capture_output=True, timeout=60, check=True
    )
    print(result.stdout.decode())


if __name__ == "__main__":
    main()
