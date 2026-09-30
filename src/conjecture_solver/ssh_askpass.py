#!/usr/bin/env python3
"""OpenSSH password input from a private child environment, never command arguments."""

import os
import sys

if "password" not in " ".join(sys.argv[1:]).lower():
    raise SystemExit(1)
sys.stdout.write(os.environ.get("SIMJECTURE_SSH_PASSWORD", ""))
