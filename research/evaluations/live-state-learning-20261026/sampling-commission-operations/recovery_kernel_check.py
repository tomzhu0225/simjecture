
import json,torch
from torch.nn import functional as F
from simjecture_monitor.kernels import enable_fla_prefill
from transformers.models.qwen3_5 import modeling_qwen3_5
assert 'A100' in torch.cuda.get_device_name(0), 'Training requires the remote A100'
torch.manual_seed(123)
enable_fla_prefill()
x=(torch.randn(1,64,128,device='cuda',dtype=torch.bfloat16)*.1).requires_grad_()
w=(torch.randn(64,4,device='cuda',dtype=torch.bfloat16)*.1).requires_grad_()
x2=x.detach().clone().requires_grad_();w2=w.detach().clone().requires_grad_()
probe=torch.randn_like(x).float()
a=modeling_qwen3_5.causal_conv1d_fn(x,w,activation='silu')
b=F.silu(F.conv1d(x2,w2[:,None,:],padding=3,groups=64)[...,:128])
(a.float()*probe).mean().backward();(b.float()*probe).mean().backward()
relative=lambda left,right:float((left.float()-right.float()).norm()/right.float().norm().clamp_min(1e-12))
result={'gpu':torch.cuda.get_device_name(0),'forward_relative_error':relative(a,b),'input_gradient_relative_error':relative(x.grad,x2.grad),'weight_gradient_relative_error':relative(w.grad,w2.grad)}
print(json.dumps(result))
assert max(result[k] for k in result if k.endswith('error'))<.02, result
