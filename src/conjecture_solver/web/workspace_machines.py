"""Visible machine provisioning and execution pool controls."""

import sys

from ..execution_pool import MachineRegistry


class MachineWorkspace:
    @property
    def machine_registry(self):
        return MachineRegistry(self.root / "machines")

    def machines(self):
        return {
            "machines": self.machine_registry.catalogue(),
            "local_defaults": {
                "id": "local",
                "kind": "local",
                "label": "This machine",
                "root": str(self.root / "execution-workers/local"),
                "python": sys.executable,
                "config": {
                    "execution_backend": self.execution["backend"],
                    "cpus": 2,
                    "memory_mb": 4096,
                    "max_jobs": 2,
                    "gpu_ids": [],
                    "capabilities": [],
                },
            },
        }

    def save_machine(self, payload):
        return self.machine_registry.save(payload)

    def prepare_machine(self, identifier):
        return self.machine_registry.start_prepare(identifier)

    def check_machine(self, identifier):
        return self.machine_registry.check(identifier)

    def machine_jobs(self, identifier):
        return self.machine_registry.worker_status(identifier)

    def cancel_machine_job(self, identifier, job):
        return self.machine_registry.transport(identifier).call("cancel", identifier=job)
