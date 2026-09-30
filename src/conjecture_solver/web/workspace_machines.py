"""Visible machine onboarding, live availability and agent-guided preparation."""

import sys
import time
import uuid

from ..execution_pool import MachineRegistry
from ..machine_availability import POLL_SECONDS, check_availability, poll_machines
from ..machine_setup import MAINTENANCE, basic_profile
from ..worker_protocol import Machine, contained, load, private_put


class MachineWorkspace:
    @property
    def machine_registry(self):
        return MachineRegistry(self.root / "machines")

    def machines(self):
        return {
            "machines": self.machine_registry.catalogue(),
            "poll_seconds": POLL_SECONDS,
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
        if "address" not in payload:
            return self.machine_registry.save(payload)
        machine = basic_profile(payload["address"], payload.get("overrides"))
        if not payload.get("id"):
            for record in self.machine_registry.catalogue():
                candidate = record["machine"]
                if all(candidate[key] == machine[key] for key in ("host", "port", "user")):
                    machine["id"] = candidate["id"]
                    break
        if payload.get("id"):
            machine["id"] = payload["id"]
        path = self.machine_registry.path(machine["id"])
        old = load(path).get("machine")
        if old:
            machine = old | {key: machine[key] for key in ("host", "port", "user")}
            for key in ("root", "run_as", "config", "python"):
                if key in payload:
                    machine[key] = payload[key]
            if payload.get("overrides") is not None:
                machine["automatic_setup"] = basic_profile(
                    payload["address"], payload["overrides"]
                )["automatic_setup"]
        for key in ("label", "identity_file", "known_hosts"):
            if payload.get(key):
                machine[key] = payload[key]
        if payload.get("password"):
            machine["password"] = payload["password"]
        saved = self.machine_registry.save(machine)
        if not old or any(
            old.get(key) != saved["machine"].get(key)
            for key in ("root", "host", "port", "user", "run_as", "config", "automatic_setup")
        ):
            self.machine_registry.start_prepare(saved["machine"]["id"])
        return self.machine_registry.public(saved["machine"]["id"])

    def prepare_machine(self, identifier):
        return self.machine_registry.start_prepare(identifier)

    def check_machine(self, identifier):
        result = self.machine_registry.check(identifier)
        check_availability(self.machine_registry, identifier)
        return result

    def refresh_machine_availability(self, identifier):
        return check_availability(self.machine_registry, identifier)

    def poll_machine_availability(self):
        poll_machines(self.machine_registry)

    def machine_jobs(self, identifier):
        return self.machine_registry.worker_status(identifier)

    def cancel_machine_job(self, identifier, job):
        return self.machine_registry.transport(identifier).call("cancel", identifier=job)

    def prepare_machine_chat(self, payload):
        machine = self.machine_registry.machine(payload.get("id"))
        goal = str(payload.get("goal") or "Prepare this machine for plasma experiments.").strip()
        if len(goal) > 8000:
            raise ValueError("Keep setup instructions under 8000 characters")
        project = self.create({"name": f"Prepare {machine.label or machine.id}"})
        prompt = (
            f"Help me prepare the registered execution machine {machine.id}. {goal}\n\n"
            "Use execution_machines to inspect its connection, hardware, setup status and jobs. "
            "Use prepare/check for the managed worker. Use execution_machine_command for "
            "operator-authorized setup and solver commands through its saved SSH connection; "
            "credentials stay on the coordinator. Inspect installed tools and source first. "
            "Keep builds, logs and tables in persistent directories. Prefer existing tested "
            "runtimes; run real demonstrations before registering descriptor directories with "
            "execution_machines(action='configure', configuration=...). Preserve active jobs "
            "and frozen instruments; use a new runtime directory for changes. Explain "
            "consequential solver/physics choices and ask when they are missing. This is "
            "machine preparation, not a scientific research result. Do not ask me to fill "
            "environment variables or setup forms."
        )
        return {"project": project["id"], "prompt": prompt, "view": "interactive"}

    def configure_machine(self, identifier, configuration):
        profile = self.machine_registry.machine(identifier).model_dump(mode="json")
        allowed = {"root", "run_as", "config", "python", "label"}
        if not isinstance(configuration, dict) or set(configuration) - allowed:
            raise ValueError("Configure only root, run_as, config, python or label")
        if "config" in configuration:
            configuration = configuration | {"config": profile["config"] | configuration["config"]}
        profile.update(configuration)
        # Explicit operator/agent configuration takes precedence over automatic suggestions.
        profile["automatic_setup"] = None
        return self.machine_registry.save(Machine.model_validate(profile).model_dump(mode="json"))

    def machine_command(self, identifier, command, timeout_seconds=60):
        if not isinstance(command, str) or not command.strip() or len(command) > 32000:
            raise ValueError("Supply a bounded setup command")
        if not 1 <= timeout_seconds <= 7200:
            raise ValueError("Setup command timeout must be between 1 and 7200 seconds")
        self.machine_registry.machine(identifier)
        operation = "setup_" + uuid.uuid4().hex
        path = contained(self.machine_registry.root, f"maintenance/{operation}.json")
        record = {
            "id": operation,
            "machine": identifier,
            "command": command,
            "status": "running",
            "created_at": time.time(),
            "scientific_status": "not_evidence",
        }
        private_put(path, record)
        try:
            result = self.machine_registry.transport(identifier).run(
                ["python3", "-c", MAINTENANCE],
                {"command": command, "timeout": timeout_seconds},
                timeout=timeout_seconds + 10,
                login_user=True,
            )
            record.update(
                result,
                status="timed_out"
                if result["timed_out"]
                else "succeeded"
                if result["returncode"] == 0
                else "failed",
            )
        except Exception as error:
            # A missing reply is not permission to repeat a possibly executed command.
            record.update(status="unconfirmed", error=str(error))
        record["finished_at"] = time.time()
        private_put(path, record)
        return record
