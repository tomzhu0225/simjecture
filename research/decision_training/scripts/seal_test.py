"""Seal operator-authored test instances supplied through stdin. No answer evaluation."""

import hashlib
import json
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT.parent / "operator-vault"


def seal(records):
    output = ROOT / "sealed" / "test.aesgcm"
    if output.exists():
        raise FileExistsError("Existing sealed test cannot be overwritten")
    if len(records) != 20:
        raise ValueError("Exactly twenty test tasks are required")
    VAULT.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(records, ensure_ascii=False, sort_keys=True).encode()
    key = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(12)
    associated = b"simjecture-qwen35-9b-heldout-test-20261116-v1"
    ciphertext = nonce + AESGCM(key).encrypt(nonce, payload, associated)
    (VAULT / "test.key").write_bytes(key)
    output.write_bytes(ciphertext)
    manifest = dict(
        task_count=20,
        known_count=sum(r["evaluation_type"] == "known" for r in records),
        open_count=sum(r["evaluation_type"] == "open" for r in records),
        plasma_count=sum(r["domain"] == "plasma" for r in records),
        levels={str(level): sum(r["difficulty"] == level for r in records) for level in range(1, 5)},
        task_ids=[r["task_id"] for r in records],
        mechanism_group_count=len({r["mechanism_group"] for r in records}),
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        ciphertext_sha256=hashlib.sha256(ciphertext).hexdigest(),
        encryption="AES-256-GCM",
        associated_data=associated.decode(),
        key_location="operator-only vault outside the research package",
        simulations_executed=0,
        reference_programs_executed=0,
        access_rule="freeze checkpoint, scoring and run plan before evaluator releases one public task contract per study",
        researcher_access="public question and visible initial configuration only; future validation perturbations, oracle and reference programs remain private",
        isolation_status="key remains on operator workstation and is excluded from remote researcher and trainer packages",
    )
    (ROOT / "tasks" / "test_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                key: manifest[key]
                for key in [
                    "task_count",
                    "known_count",
                    "open_count",
                    "plasma_count",
                    "levels",
                    "mechanism_group_count",
                ]
            }
        )
    )


if __name__ == "__main__":
    seal(json.load(sys.stdin))
