"""Identify provider rejection before any scientific or coprocessor action."""
import json

def initial_429(directory, starts):
 if len(starts)!=1 or starts[0].get('returncode')!=1:
  return False
 if (directory/'research/SUBMISSION.json').exists():
  return False
 if any((directory/'research/runs').glob('*/receipt.json')):
  return False
 if any((directory/'monitor').glob('attention-[0-9]*.json')):
  return False
 path=directory/'supervisor/turn-00001/response.json'
 if not path.is_file():return False
 try:events=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
 except (ValueError,OSError):return False
 if not events or any(not isinstance(e,dict) or e.get('type') not in {'thread.started','turn.started','error','turn.failed'} for e in events):
  return False
 for event in events:
  if event.get('type') not in {'error','turn.failed'}:continue
  error=event.get('error',{});message=error.get('message','') if isinstance(error,dict) else ''
  if '429 Too Many Requests' in str(event.get('message','')) or '429 Too Many Requests' in message:return True
 return False
