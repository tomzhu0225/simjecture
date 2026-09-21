#!/usr/bin/env python3
"""Evaluation-only CLI wrapper: retain fresh reviewer sessions for token accounting.

Removing --ephemeral changes local retention only. It does not resume reviewer
threads, alter prompts, select a model, or change tool permissions.
"""

import os
import sys

os.execvp("codex-glm", ["codex-glm", *(a for a in sys.argv[1:] if a != "--ephemeral")])
