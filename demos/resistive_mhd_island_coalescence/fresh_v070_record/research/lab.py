# Generated local scientific client.
import json, subprocess
class Client:
    def _call(self, operation, **arguments):
        p = subprocess.run(['/home/tomzhu0225/src/simjecture-prx-island-v0.7.0/.venv/bin/python', '-m', 'conjecture_solver.research_service',
            '--root', '/home/tomzhu0225/src/simulations/other_demos/resistive_mhd_island_scaling/outputs/fresh_band_v070__20261025T1153', '--call', operation], input=json.dumps(arguments),
            capture_output=True, text=True, env=__import__('os').environ | {
                'PYTHONPATH': '/home/tomzhu0225/src/simjecture-prx-island-v0.7.0/src'})
        receipt = json.loads(p.stdout)
        if not receipt['ok']: raise RuntimeError(receipt['error'])
        return receipt['result']
    def run(self, source, args=(), **kw): return self._call('run', source=source, args=args, **kw)
    def analyze(self, source, args=(), **kw):
        # Frozen exploratory analysis; cannot approve or support a claim.
        return self._call('analyze', source=source, args=args, **kw)
    def progress(self, **kw): return self._call('progress', **kw)
    def cancel(self, experiment, **kw): return self._call('cancel', experiment=experiment, **kw)
    def director_status(self): return self._call('director_status')
    def director_ack(self, decision, **kw):
        return self._call('director_ack', decision=decision, **kw)
    def request_time(self, **kw): return self._call('request_time', **kw)
    def request_help(self, question, **kw):
        return self._call('request_help', question=question, **kw)
    def help_status(self, identifier=None): return self._call('help_status', identifier=identifier)
    def import_helper_artifact(self, task, artifact, destination):
        return self._call('import_helper_artifact', task=task,
                          artifact=artifact, destination=destination)
    def machines(self): return self._call('machines')
    def fetch_remote(self, **kw): return self._call('fetch_remote', **kw)
    def read_instrument(self, capability, **kw):
        return self._call('read_instrument', capability=capability, **kw)
    def commit(self, statement, **kw): return self._call('commit', statement=statement, **kw)
    def review(self, experiments, conclusion, **kw):
        return self._call('review', experiments=experiments, conclusion=conclusion, **kw)
    def status(self, compact=True): return self._call('status', compact=compact)
    def review_status(self, identifier): return self._call('review_status', identifier=identifier)
    def assess_report(self, report='RESULTS.md', **kw):
        return self._call('assess_report', report=report, **kw)
    def report_assessment_status(self, identifier):
        return self._call('report_assessment_status', identifier=identifier)
    def wait(self, reason, **kw): return self._call('wait', reason=reason, **kw)
    def waiting_status(self): return self._call('waiting_status')
    def reproduce_anchor(self, **kw): return self._call('reproduce_anchor', **kw)
    def method(self, **kw): return self._call('method', **kw)
    def register_capability(self, name, **kw):
        return self._call('register_capability', name=name, **kw)
    def note(self, statement, **kw): return self._call('note', statement=statement, **kw)
    def notes(self, **kw): return self._call('notes', **kw)
    def brief(self, **kw): return self._call('brief', **kw)
    def compare(self, experiments, metrics):
        return self._call('compare', experiments=experiments, metrics=metrics)
lab = Client()
