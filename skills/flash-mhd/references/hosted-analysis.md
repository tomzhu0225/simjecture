# FLASH analysis in the hosted scientific executor

General hosted Python is available through `run_command`; it is not restricted
to ITER examples. Each command starts with a fresh scratch directory populated
from its declared project inputs. Only declared outputs are copied back. Unpack
and analyze in one command, or declare extracted files as outputs before the next
command. Inspection-only calls may use `outputs=[]`; their console is retained.
Use `kind="simulation"` when executing FLASH or another numerical model, and
`kind="command"` for analysis, plotting, compilation and inspection. Output
files do not determine the category. Give each call a descriptive name and
create subdirectories before saving into them, such as `mkdir -p generated`.

`simulate_native` returns `project_outputs`, including the raw-output archive.
Use that project-relative ZIP path as an input. Native archives contain actual
plotfiles even when the FLASH application has a different output basename.
Read times from the `real scalars` table and sort by those times; forced plotfile
names can sort before the initial snapshot.

For the commissioned **single-block 2D uniform grid**:

```python
import glob
import zipfile
import h5py
import numpy as np
from matplotlib import pyplot as plt

with zipfile.ZipFile(archive_path) as archive:
    archive.extractall("fields")
frames = []
for path in glob.glob("fields/*hdf5_plt_cnt_*"):
    with h5py.File(path, "r") as data:
        scalars = {row[0].decode().strip(): float(row[1])
                   for row in data["real scalars"]}
    frames.append((scalars["time"], path))
frames.sort()
with h5py.File(frames[-1][1], "r") as data:
    bx, by = np.asarray(data["magx"])[0, 0], np.asarray(data["magy"])[0, 0]
    bounds = np.asarray(data["bounding box"])[0]
ny, nx = bx.shape
x = bounds[0, 0] + (np.arange(nx) + .5) * np.diff(bounds[0])[0] / nx
y = bounds[1, 0] + (np.arange(ny) + .5) * np.diff(bounds[1])[0] / ny
fig, axis = plt.subplots(layout="constrained")
image = axis.pcolormesh(x, y, np.hypot(bx, by), shading="nearest")
axis.streamplot(x, y, bx, by, color="white", density=.8)
axis.set(xlabel="x (code length)", ylabel="y (code length)", aspect="equal",
         title=f"Magnetic geometry · t={frames[-1][0]:.4g}")
fig.colorbar(image, ax=axis, label="|B| (code units)")
fig.savefig("magnetic_geometry.png", dpi=160)
```

Pass the archive and analysis script as `inputs`, and declare the plot/metrics
as `outputs`. This example assumes one block and one z plane. For AMR, multiple
blocks, RZ or 3D, inspect bounding boxes and coordinate metadata and assemble the
domain correctly. A field plot is a visualization; a reconnection-rate claim
requires a defined flux/field-line diagnostic, a time interval and validity checks.
