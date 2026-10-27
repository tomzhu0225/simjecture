import subprocess
from types import SimpleNamespace
import pytest
from readonly_physics_readiness import wait_for_ready

COMMAND=['ssh','example-host','test -x /opt/solver']

class Clock:
    def __init__(self): self.now=100
    def time(self): return self.now
    def sleep(self, seconds): self.now+=seconds

def check(responses, *, stop_by=500):
    clock=Clock(); records=[]; calls=[]
    def run(command, **kwargs):
        calls.append((command,kwargs)); clock.now+=.1
        response=responses.pop(0)
        if isinstance(response, Exception): raise response
        return SimpleNamespace(returncode=response[0],stderr=response[1],stdout='')
    result=wait_for_ready(COMMAND,stop_by=stop_by,on_attempt=records.append,
                          run=run,clock=clock.time,sleep=clock.sleep)
    return result,records,calls,clock

def test_short_connection_failures_are_retained_before_a_successful_readiness_check():
    result,records,calls,clock=check([(255,'Connection closed by remote host'),(0,'')])
    assert result['ready'] and len(records)==len(calls)==2
    assert records[0]['stderr_tail']=='Connection closed by remote host'
    assert clock.now<106 and all(c[0]==COMMAND for c in calls)

@pytest.mark.parametrize('failure',[(255,'Host key verification failed.'),(255,'Permission denied (publickey).'),(1,'')])
def test_identity_permission_and_missing_binary_errors_do_not_retry(failure):
    result,records,calls,_=check([failure])
    assert not result['ready'] and len(calls)==1
    assert result['reason']=='nonretryable_readiness_failure'

def test_timeout_evidence_and_absolute_bound_are_preserved():
    result,records,calls,clock=check([subprocess.TimeoutExpired(COMMAND,1,stderr=b'timed out')],stop_by=101)
    assert not result['ready'] and records[0]['timeout']
    assert records[0]['stderr_tail']=='timed out' and calls[0][1]['timeout']==1
    assert clock.now==101

def test_retry_count_is_bounded_for_fast_unknown_transport_errors():
    result,records,calls,_=check([(255,'')]*6)
    assert not result['ready'] and len(records)==len(calls)==6

def test_remote_solver_commands_cannot_be_replayed_by_this_helper():
    with pytest.raises(ValueError,match='read-only'):
        wait_for_ready(['ssh','example-host','python run_solver.py'],stop_by=1,on_attempt=lambda r:None)
    with pytest.raises(ValueError,match='read-only'):
        wait_for_ready(['ssh','example-host','test -x /opt/solver; python run_solver.py'],stop_by=1,on_attempt=lambda r:None)
