# Add a capability

A capability exposes a named executable runtime without giving the model host
shell authority.

1. Add a versioned capability manifest under `capabilities/`.
2. Define the immutable runtime path, probe command, resource environment, and
   compatible skill identity.
3. Add or update the corresponding skill under `skills/`.
4. Make the health probe deterministic and inexpensive.
5. Test workbench execution, evidence-stage source sealing, commissioning, and
   scientific-command binding.
6. Regenerate public schemas if an action model changed.

When the configured executable is a launcher or interpreter that invokes
sibling scientific binaries, declare those binaries and build records through
`identity_files`. Simjecture hashes the declared regular files at discovery and
checks them again before every execution. Paths must remain inside the runtime;
missing files, directories, symlinks, traversal, and duplicates are rejected.

Capability availability, commissioning, and scientific validity are different
states. A healthy runtime may execute workbench code. It may produce scientific
evidence only after a suitable instrument claim is supported and the scientific
command was prospectively authorized.

Do not place a problem-specific experiment plan in a general capability skill.
Skills may capture stable interface facts and numerical hazards; the agent owns
the active scientific design.
