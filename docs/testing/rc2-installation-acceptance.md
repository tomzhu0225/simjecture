# rc2 installation acceptance — 2026-09-27

This records testing of the rc2 development code, not a change to the published rc1 assets.
The target was Ubuntu 22.04.5, x86-64, with NVIDIA Tesla P40 GPUs (driver 580.159.04).
Linux namespaces were denied by the host. Actual capability tests used the checked
non-root PRoot backend, with its cooperative-execution warning retained.

## Scope and method

A new account and workspace were created, retaining only the existing DeepSeek API
connection and the user's supplied FLASH source archive as inputs. No existing solver
runtimes or conversations were imported. This was a clean workspace test, not an OS
reimage. Package download caches were reused on repeat tests; runtime directories were
removed before the second one-click installation pass.

The five one-click installations were started through real Chromium GUI buttons,
then repeated from empty runtime directories. Their compilers and scientific libraries
were provisioned by the installer into managed environments, without per-tool apt or
sudo fixes. FLASH and CUDA were exercised through real DeepSeek-assisted conversations.

| Tool | Installation route | Execution/readback result |
| --- | --- | --- |
| WarpX CPU 26.07 | Install button | 6 declared preflight checks passed |
| Singularity-EOS 1.12.1 | Install button | 5 declared checks passed for the analytic query runtime |
| M-ANEOS 1.0 | Install button | 8 declared checks passed, including a real query |
| atoMEC 1.4.0 | Install button | 4 declared checks passed, including a helium calculation |
| Optab 1.3.1 | Install button | 11 declared checks passed, including MPI/HDF5 output and all 4,278 expected NIST ion groups |
| FLASH 4.8 | Agent + supplied licensed source | 2D ideal-MHD Orszag–Tang build; 10 actual backend checks passed |
| WarpX CUDA 26.07 | Agent + automatic managed prerequisites/source build | 2D CUDA/openPMD build for sm_61; 6 actual backend checks passed |
| Built-in Python | GUI conversation | Euler calculation, CSV and PNG saved; browser rendered the image and four equation nodes |

The CUDA agent also ran a 64×64 electron/proton PIC case for 25 steps. Twelve
operational checks passed, including field/particle output readback and a saved figure.
Its separate scientific-evidence eligibility flag remained false, as intended.
A controlled build interruption followed by an incremental 12-job resume verified
that downloads, completed objects and logs could be reused.

The supplied 33,340,720-byte FLASH archive was also uploaded through the GUI and
downloaded back byte-for-byte. The attachment limit is now 64 MiB, so this source
archive no longer requires an external file-transfer command.

## Failures caught and fixed

- Bootstrap scripts assumed scientific compilers and libraries were already present.
  The common managed-environment preparer now installs compatible prerequisites.
- Progress logs hid the useful error behind “bootstrap failed”. Diagnostic tails and
  persistent preflight output directories now preserve the actual failure.
- An upstream Optab downloader ignored a failed conversion and left partial HDF5 data.
  Downloads now retry; conversion failure and missing ion groups prevent readiness.
- A CUDA venv pointed to Python outside its capability mount. Managed Python now
  stays within the runtime; registration rejects inaccessible interpreter symlinks.
- A WSL-specific CUDA descriptor and system-header path were unsuitable for native
  Linux. The bootstrap now generates the host's descriptor and uses managed headers.
- Agent builds launched with detached shell commands were cleaned up when the
  short terminal action ended. A monitored long-running command tool now handles them.
- A FLASH agent mistook a host-only test for backend readiness. The deployment guide,
  registration validation and custom-tool Check readiness action now require the
  actual capability check. Passed custom variants also update their catalogue group.

## Fresh root installer and retry tests

The one-command installer was also exercised from a root SSH session with a new
installation directory. It automatically created the non-root service account and
started the GUI without a CLI agent or API key. M-ANEOS was then installed through
that GUI and passed all eight checks.

Re-running the installer preserved a private-settings fixture and research files.
An intentionally failed upgrade preserved the previous working launcher, version and
service. An intentionally failed first installation succeeded on an ordinary retry,
without manual cleanup. The top-level launcher remained root-owned and dropped
privileges on subsequent starts. Host namespace restrictions and /root permissions
were not relaxed.

These tests establish installation and interface readiness for the named configurations.
They do not qualify every upstream feature, application, geometry or physical model.
The published rc1 release is unchanged; these corrections belong to rc2 development.

## Automated regression checks

The targeted deployment, runtime bootstrap, workspace, provider-session, browser,
installer, simulation and skill suites finished with **80 passed, 2 skipped**.
The two skips require local PRoot/non-root execution; that backend was exercised
by the real remote capability tests above. Lint, shell syntax and diff checks passed.

## Research handoff follow-up

The workspace lifecycle update passed 41 workspace, browser and session tests,
including a real supervised study against the deterministic provider, background
report delivery, waiting for an active conversation, restart deduplication, and
preparing another study without losing its predecessor. Two focused handoff/browser
checks passed again after the final navigation change.

On the remote test host, the existing completed Euler study was returned to the real
DeepSeek agent through the GUI's **Explain in conversation** button. The agent read
the saved report and evidence and explained the independently accepted falsification
in the original conversation. All seven linked study artifacts returned HTTP 200;
45 equation nodes rendered, and the study card navigated directly to the explanation.
No additional autonomous study was launched for this check. Both local and remote
workspace servers were updated; published preview release assets remain unchanged.
