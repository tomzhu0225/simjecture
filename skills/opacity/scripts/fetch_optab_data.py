"""Fetch upstream NIST inputs with retries and reject incomplete conversions."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
import threading
from pathlib import Path

import h5py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def main():
    source = Path(sys.argv[1]).resolve()
    nist = source / "database/NIST"
    local = threading.local()

    def get(url, **kwargs):
        if not hasattr(local, "session"):
            local.session = requests.Session()
            adapter = HTTPAdapter(
                max_retries=Retry(
                    total=4,
                    backoff_factor=1,
                    status_forcelist=(429, 500, 502, 503, 504),
                    allowed_methods=("GET",),
                )
            )
            local.session.mount("https://", adapter)
        response = local.session.get(url, timeout=(20, 120), **kwargs)
        response.raise_for_status()
        return response

    requests.get = get
    os.chdir(nist)
    runpy.run_path(str(nist / "get_nist_parallel.py"), run_name="__main__")
    # Upstream ignores the converter exit code, which can leave a partial HDF5
    # file after one failed HTTP request. Run it with checked status ourselves.
    subprocess.run([str(source / "database/src/convert_nist_h5")], check=True)
    with h5py.File(source / "database/h5/NIST.h5", "r") as data:
        expected = {f"{z:03d}.{ion:02d}" for z in range(1, 93) for ion in range(z)}
        if set(data["prop"]) != expected:
            raise ValueError("NIST conversion is incomplete; retry installation")
        for name in expected:
            if not {"mass", "nstates", "eneion", "ene", "gtot", "term", "conf"} <= set(
                data["prop"][name]
            ):
                raise ValueError(f"NIST conversion is incomplete for {name}")
    print("Verified all 4278 NIST ion groups", flush=True)


if __name__ == "__main__":
    main()
