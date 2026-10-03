import pytest

from conjecture_solver.mpi_launch import mpi_command


def test_explicit_slots_follow_reservation(monkeypatch):
    monkeypatch.setenv("SIMJECTURE_CPU_SLOTS", "16")
    argv = mpi_command(16, "./flash4", ["-par_file", "input.par"])
    assert argv[argv.index("--host") + 1] == "localhost:16"
    assert "--nooversubscribe" in argv and "--oversubscribe" not in argv
    assert argv[-3:] == ["./flash4", "-par_file", "input.par"]


def test_mpi_cannot_exceed_allocated_cpus(monkeypatch):
    monkeypatch.setenv("SIMJECTURE_CPU_SLOTS", "4")
    with pytest.raises(ValueError, match="Reserve resources"):
        mpi_command(16, "./flash4")
    with pytest.raises(ValueError, match="allocated 4"):
        mpi_command(4, "./flash4", slots=16)


def test_reserved_slots_are_not_replaced_by_host_topology(monkeypatch):
    monkeypatch.setenv("SIMJECTURE_CPU_SLOTS", "1")
    monkeypatch.setattr("os.sched_getaffinity", lambda _: set(range(128)))
    with pytest.raises(ValueError, match="1 CPU slots"):
        mpi_command(2, "./flash4")


@pytest.mark.parametrize("ranks", [0, -1, True, "4"])
def test_invalid_ranks_are_rejected(monkeypatch, ranks):
    monkeypatch.setenv("SIMJECTURE_CPU_SLOTS", "4")
    with pytest.raises(ValueError, match="positive integer"):
        mpi_command(ranks, "./flash4")


@pytest.mark.parametrize(
    "key", ["SIMJECTURE_CPU_SLOTS", "SIMJECTURE_MPI_HELPER", "SIMJECTURE_EXECUTION_BACKEND"]
)
def test_capability_cannot_override_allocated_execution_environment(key):
    from conjecture_solver.mvp_skills import MVPCapabilityConfig

    with pytest.raises(ValueError, match="cannot override sandbox variables"):
        MVPCapabilityConfig.model_validate(
            {
                "manifest": {
                    "name": "example",
                    "version": "1",
                    "skill": "flash-mhd",
                    "description": "Example",
                    "executable_kind": "python",
                },
                "runtime_root": "/tmp/example",
                "executable": "bin/python",
                "environment": {key: "override"},
            }
        )
