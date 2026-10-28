"""Prepare a new bounded native-sampling commission; never allocate here."""
from pathlib import Path
import ast, json, hashlib, time
r=Path(__file__).parent
source='workflow-return-source-171ac44'
names=['attach_r11.py','deploy_r11_a100.py','prepare_r11_a100.py','r11_service.py','remote_r11_guard.py','remote_r11_proxy.py','r11_colab_control.py','local_r11_failsafe.py','install_r11_controls.py','r11_control_once.py','run_r11_auth.py']
written=[]
for old in names:
 name=old.replace('r11','c12')
 text=(r/old).read_text().replace('r11','c12').replace('R11','C12').replace('Simjecture-C12-20261027','Simjecture-C12-20261028').replace('replication-source-04f905c',source).replace('replication-env','control-commission-env')
 if old=='r11_service.py': text=text.replace("'independent/v1'","'scientific-route-question/v1'")
 if old=='run_r11_auth.py': text=text.replace('One continuation preflight, after 279 retained starts; deducted from remaining 361','One preflight deducted from the new 73-start native-sampling commission')
 ast.parse(text,filename=name)
 p=r/name;assert not p.exists(),name;p.write_text(text)
 written.append(dict(path=name,sha256=hashlib.sha256(text.encode()).hexdigest(),derived_from=old))
text=(r/'qualify_control_commission_v2_physics.py').read_text().replace('control-commission-physics-02','c12-physics').replace('control-commission-v2-backend.json','c12-backend.json').replace('control-commission-v2-source-8626a77',source)
ast.parse(text);(r/'qualify_c12_physics.py').write_text(text)
(r/'c12-operations-prepared.json').write_text(json.dumps(dict(at=time.time(),source=source,operations=written),indent=2)+'\n')
print('Prepared',len(written)+1,'scripts; no compute allocated')
