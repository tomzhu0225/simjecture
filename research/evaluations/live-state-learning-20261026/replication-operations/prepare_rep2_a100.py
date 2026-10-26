from pathlib import Path
import hashlib,importlib.metadata,json,os,subprocess,sys,tarfile,time,traceback
root=Path('/content/science-attention');status=dict(stage='verifying_assets',started_at=time.time())
source=root/'replication-source-04f905c';env=dict(os.environ,PYTHONPATH=str(source/'packages/simjecture-monitor/src'),OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',HF_HUB_DISABLE_XET='1')
def save():
 p=root/'rep2-prepare-status.tmp';p.write_text(json.dumps(status,indent=2));p.replace(root/'rep2-prepare-status.json')
def execute(name,args,timeout):
 status['stage']=name;save()
 with (root/('rep2-'+name+'.log')).open('w') as log:subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout)
save()
try:
 with (root/'validation-model-assets.tar.gz').open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='4b7a12dfa53e2bfc18ad0073c5fa5b820b6da08fa04c36ac8de722fcaee47bd0'
 with tarfile.open(root/'validation-model-assets.tar.gz') as tar:tar.extractall(root,filter='data')
 manifest=json.loads((root/'validation-assets/manifest.json').read_text())
 for policy,record in manifest['models'].items():
  for name,expected in record['adapter_hashes'].items():
   with (root/'validation-assets'/policy/'adapter'/name).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
 execute('dependencies',[sys.executable,'-m','pip','install','-q','torch==2.11.0','transformers==5.20.1','peft==0.21.2','huggingface-hub==1.33.0','pydantic==2.13.4','flash-linear-attention==0.6.0','fla-core==0.6.0'],600)
 from packaging.version import Version
 try:version=importlib.metadata.version('torchao')
 except importlib.metadata.PackageNotFoundError:version=None
 if version and Version(version)<Version('0.16'):execute('remove-incompatible-torchao',[sys.executable,'-m','pip','uninstall','-y','torchao'],60)
 os.environ['HF_HUB_DISABLE_XET']='1'
 from huggingface_hub import snapshot_download
 status['stage']='base-download';save()
 base=snapshot_download('internlm/Intern-Decision-4B',revision='38c9dafbbef52dd04bae943c0c6ac918419adfd5',token=False,allow_patterns=['*.json','*.safetensors','*.txt','*.model','*.jinja','*.py','README.md','LICENSE*'],max_workers=8)
 status['base']=base;save()
 execute('kernel-parity',[sys.executable,str(root/'recovery_kernel_check.py')],300)
 status.update(stage='ready',ended_at=time.time(),models=manifest['models'],packages={k:importlib.metadata.version(k) for k in ['torch','transformers','peft','huggingface-hub','fla-core','pydantic']});save()
except Exception:status.update(stage='failed',error=traceback.format_exc(),ended_at=time.time());save()
print(json.dumps(status),flush=True)
