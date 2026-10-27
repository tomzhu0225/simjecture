from pathlib import Path
import json,shutil,tarfile
exp={1000:{192:'exp_c90e9b96ba8406a99246fb8e',256:'exp_f2da6ae1b2ce992ddf16cf82',384:'exp_56eca6327dc2e3f0fd4942d4'},2000:{192:'exp_82b78fe2f19144b3b6ca29af',256:'exp_d72d5627834d2ca1456a280c',384:'exp_9ed2782a9af6b2446c71285a'}}
manifest=[];inputs=['spatial_inputs.json','null_diagnostic.py','reduce_archive.py']
for S,grids in exp.items():
 for n,eid in grids.items():
  w=Path('../experiments')/eid/'workspace';r=json.loads((w/'result.json').read_text());name=f'spatial_S{S}_n{n}.json';shutil.copyfile(w/'result.json',name);inputs.append(name);c={'experiment':eid,'summary':name,'raw_samples':[]}; flux=[v['reconnected_flux_from_by'] for v in r['timeseries']];idx={0}
  for z in [.01,.03,.05]:
   i=next(i for i,v in enumerate(flux) if v>=z);idx.update([i-1,i])
  wanted={r['fields'][i]['path']:i for i in idx}
  with tarfile.open(w/'fields.tar.gz','r|gz') as tar:
   for m in tar:
    if m.name not in wanted:continue
    i=wanted[m.name];out=f'raw_S{S}_n{n}_i{i}.h5';Path(out).write_bytes(tar.extractfile(m).read());inputs.append(out);c['raw_samples'].append({'index':i,'input':out})
  if n==384:c['series']=f'S{S}_n{n}_magnetic.h5';inputs.append(c['series'])
  manifest.append(c)
 for tag,eid in [('cfl','exp_0b86a9ee47886cb02451c2c2' if S==1000 else 'exp_9a9dff759f89368261125a4b'),('base256',grids[256])]:
  out=f'{tag}_{S}.json';shutil.copyfile(Path('../experiments')/eid/'workspace/result.json',out);inputs.append(out)
Path('spatial_inputs.json').write_text(json.dumps(manifest,indent=2));Path('spatial_input_list.json').write_text(json.dumps(inputs))
print('input bytes',sum(Path(v).stat().st_size for v in inputs))
