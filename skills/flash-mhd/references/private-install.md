# Private FLASH install overlay

FLASH cannot be redistributed by Simjecture. The public installer never contains
a FLASH URL. Operators who already hold a FLASH Center license can point
Simjecture at **their own** Git remote:

```bash
export FLASH_SETUP_ARGS="<Application> -auto ..."
export FLASH_OBJDIR="<object-directory-name>"
export FLASH_PREFLIGHT_PARFILE="/absolute/path/to/operator-owned.par"
uv run simjecture install flash \
  --repository git@github.com:<you>/<your-private-flash>.git \
  --git-ref <tag-or-commit>
```

`--repository` is supplied by the operator. Simjecture clones it with the
operator's Git credentials and builds it. Hosting FLASH on GitHub, including a
private repository, can still violate the FLASH license; only licensed holders
should have access.

A **private overlay** is optional. Use it to keep setup arguments and a default
remote out of the shell history. Never commit FLASH source, binaries, object
directories, modified units, or a Git remote that hosts FLASH.

## Overlay locations

`simjecture install flash` looks for an optional overlay executable named
`flash/bootstrap.sh` in this order:

1. `$SIMJECTURE_PRIVATE_ROOT/flash/bootstrap.sh`
2. `<checkout>/.private/flash/bootstrap.sh`

`.private/` is Git-ignored. Put `$SIMJECTURE_PRIVATE_ROOT` in the process
environment, not in a tracked file. If no overlay is present, the public
`skills/flash-mhd/scripts/bootstrap_flash.sh` builder is used when
`--repository` or `--source` is supplied. Otherwise install stays
verification-only.

## Bootstrap contract

The script is invoked as:

```text
bootstrap.sh --prefix RUNTIME --project-root CHECKOUT --jobs N \
  [--source FLASH_TREE] [--git-url URL] [--git-ref REF] [--repair]
```

On success the script must leave an installer-managed runtime whose
`share/build-record.json` exists, plus the files named by the FLASH capability
descriptor (`bin/flash-python`, `bin/flash4`, and a preflight parameter file).

## Optional private Git remote

A private Git hosting of FLASH is **not** a Simjecture feature and is not a
substitute for a FLASH Center license. The FLASH terms restrict redistribution
of original or modified source. A private GitHub repository still copies FLASH
onto GitHub's servers and to every account with access.

If you still keep a licensed working copy on a private remote that only
licensed holders can read, configure it in the overlay, for example:

```bash
FLASH_GIT_URL="git@github.com:<owner>/<private-repo>.git"
FLASH_GIT_REF="<tag-or-commit>"
```

Then:

```bash
uv run simjecture install flash
```

clones through your Git credentials and builds. `--source` remains available
and skips the clone. Do not put `FLASH_GIT_URL` in `skills/`, `capabilities/`,
or any other tracked path.

## Suggested overlay layout

```text
.private/flash/
  bootstrap.sh     # executable, operator-owned
  config.env       # optional; sourced by your bootstrap, never committed
```

A typical `config.env` names only things you already obtained:

```bash
FLASH_SETUP_ARGS="<Application> -auto ..."
FLASH_OBJDIR="<object-directory-name>"
# FLASH_GIT_URL="git@github.com:<owner>/<private-repo>.git"
# FLASH_GIT_REF="<tag-or-commit>"
```

After a successful overlay install:

```bash
uv run simjecture doctor --profile flash
```

The probe remains permanently non-evidentiary. Rebuild after compiler, MPI,
HDF5, FLASH source, or setup-unit changes.
