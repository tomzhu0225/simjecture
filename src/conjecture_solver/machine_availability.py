"""Thirty-second lightweight worker heartbeats, independent of browser activity."""

import time
from concurrent.futures import ThreadPoolExecutor

from .execution_pool import MachineRegistry, WorkerUnavailable
from .machine_setup import DISCOVER
from .worker_protocol import ACTIVE, load, lock, private_put

POLL_SECONDS = 30


def check_availability(registry, identifier):
    profile = registry.public(identifier)
    machine = registry.machine(identifier)
    started = time.monotonic()
    availability = {"checked_at": time.time(), "online": False, "status": "offline"}
    if profile.get("preparation", {}).get("status") == "working":
        return {"status": "preparing", "online": None, "checked_at": time.time()}
    try:
        transport = registry.transport(identifier)
        if not profile.get("probe"):
            transport.run(
                ["python3" if machine.kind == "ssh" else machine.python, "-c", DISCOVER],
                {},
                timeout=8,
                login_user=True,
            )
            availability.update(online=True, status="setup_needed")
        else:
            try:
                response = transport.call("heartbeat", timeout=8)
            except ValueError as error:
                if "Unknown execution worker method" not in str(error):
                    raise
                response = transport.call("status", timeout=8)
            ready = (
                response["capacity"] == machine.config.model_dump(mode="json")
                and profile["probe"]["execution"]["available"]
                and response.get("worker_id", profile["probe"]["worker_id"])
                == profile["probe"]["worker_id"]
            )
            jobs = [job for job in response.get("jobs", []) if job["status"] in ACTIVE]
            availability.update(
                online=True,
                status="ready" if ready else "setup_needed",
                active_jobs=len(jobs),
                resources_in_use={
                    key: sum(
                        j.get("resources", {}).get(key, 0)
                        for j in jobs
                        if j["status"] in {"running", "cancelling"}
                    )
                    for key in ("cpus", "memory_mb", "gpus")
                },
            )
    except (ValueError, OSError, WorkerUnavailable) as error:
        availability["error"] = str(error)
    availability["latency_ms"] = round((time.monotonic() - started) * 1000)
    availability["checked_at"] = time.time()
    with lock(registry.root):
        path = registry.path(identifier)
        current = load(path)
        if current and MachineRegistry(registry.root).machine(identifier) == machine:
            current["availability"] = availability
            private_put(path, current)
    return availability


def poll_machines(registry):
    identifiers = [item["machine"]["id"] for item in registry.catalogue()]
    if identifiers:
        with ThreadPoolExecutor(max_workers=min(len(identifiers), 4)) as pool:
            list(pool.map(lambda identifier: check_availability(registry, identifier), identifiers))
