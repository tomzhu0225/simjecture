"""Recognize the frozen wrapper's explicit refusal before remote submission."""
import json

MESSAGE = 'ValueError: Configured SSH control socket is unavailable; no run submitted'


def presubmission_failure(directory):
    path = directory / 'research/progress.json'
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    if not isinstance(value, dict) or value.get('phase') != 'solver':
        return False
    if type(value.get('exit_code')) is not int or value['exit_code'] == 0:
        return False
    error = value.get('stderr')
    return (isinstance(error, str) and 'remote_plasma.py' in error
            and MESSAGE in error.splitlines())
