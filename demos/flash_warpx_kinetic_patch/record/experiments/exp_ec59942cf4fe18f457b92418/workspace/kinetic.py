"""Advance an explicitly mapped FLASH patch with fully kinetic WarpX.

Commissioning starter only: collisionless initial-value dynamics with absorbing
boundaries. Boundary/relaxation controls and pressure estimators need review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
from pywarpx import callbacks, fields, particle_containers, picmi


def load_particles(data, meta, ppc, seed):
    if ppc < 8:
        raise ValueError("Use at least eight particles per cell for quiet covariance matching")
    rng = np.random.default_rng(seed)
    nz, nx = data["n"].shape
    dx, dz = meta["cell_size_m"]
    xx, zz = np.meshgrid(data["x"], data["z"])
    # Paired positions and weights make the initial charge exactly neutral.
    xp = xx.ravel()[:, None] + (rng.random((nx * nz, ppc)) - 0.5) * dx
    zp = zz.ravel()[:, None] + (rng.random((nx * nz, ppc)) - 0.5) * dz
    weight = np.repeat(data["n"].ravel() * dx * dz / ppc, ppc)
    maxima = {}
    for name, key in [("ions", "i"), ("electrons", "e")]:
        mass = meta["scales"]["ion_mass_kg" if key == "i" else "electron_mass_kg"]
        random = rng.normal(size=(nx * nz, ppc, 3))
        random -= random.mean(axis=1, keepdims=True)
        cov = np.einsum("npi,npj->nij", random, random) / ppc
        val, vec = np.linalg.eigh(cov)
        whitening = (vec * (1 / np.sqrt(val))[:, None, :]) @ vec.transpose(0, 2, 1)
        random = np.einsum("npi,nij->npj", random, whitening)
        velocity = data["u" + key].reshape(-1, 1, 3) + random * np.sqrt(
            data["t" + key].reshape(-1, 1, 1) / mass
        )
        speed2 = (velocity**2).sum(axis=-1)
        maxima[name] = float(np.sqrt(speed2.max()) / picmi.constants.c)
        gamma=1/np.sqrt(1-speed2/picmi.constants.c**2)
        maxima[name+"_initial_energy_J_per_m"] = float(np.sum(weight.reshape(nx*nz,ppc)*mass*picmi.constants.c**2*(gamma-1)))
        maxima[name+"_initial_number_per_m"] = float(weight.sum())
        if maxima[name] >= 0.6:
            raise ValueError("Reduce vA/c: kinetic initial particles are too relativistic")
        proper = velocity / np.sqrt(1 - speed2[..., None] / picmi.constants.c**2)
        pc = particle_containers.ParticleContainerWrapper(name)
        pc.add_real_comp("origin_r")
        pc.add_particles(
            x=xp.ravel(),
            y=np.zeros(xp.size),
            z=zp.ravel(),
            ux=proper[:, :, 0].ravel(),
            uy=proper[:, :, 1].ravel(),
            uz=proper[:, :, 2].ravel(),
            w=weight,
            unique_particles=True,
            origin_r=np.maximum(np.abs(xp),np.abs(zp)).ravel(),
        )
    return maxima


def moments(sim, meta, bins, roi_half):
    """Return spatially binned nonrelativistic velocity-covariance tensors.

    Bulk velocity is removed within each bin, not once for the whole patch.
    This starter does not select a scientific reconnection/exhaust ROI.
    """
    result = {}
    bounds = np.array(meta["bounds_xz_m"])
    center = bounds.mean(axis=1)
    half = np.asarray(roi_half) * meta["scales"]["length_m"]
    lower, upper = center - half, center + half
    area = np.prod((upper - lower) / bins)
    for name in ("ions", "electrons"):
        pc = particle_containers.ParticleContainerWrapper(name)

        def get(component, pc=pc):
            return np.concatenate(getattr(pc, "get_particle_" + component)(copy_to_host=True))

        x, z, w = get("x"), get("z"), get("weight")
        origin=np.concatenate(pc.get_particle_real_arrays("origin_r",level=0,copy_to_host=True))
        proper = np.column_stack([get("ux"), get("uy"), get("uz")])
        velocity = proper / np.sqrt(
            1 + (proper**2).sum(axis=1, keepdims=True) / picmi.constants.c**2
        )
        good = (x >= lower[0]) & (x < upper[0]) & (z >= lower[1]) & (z < upper[1])
        ix = ((x[good] - lower[0]) / (upper[0] - lower[0]) * bins).astype(int)
        iz = ((z[good] - lower[1]) / (upper[1] - lower[1]) * bins).astype(int)
        index = iz * bins + ix
        w = w[good]
        v = velocity[good]
        count = np.bincount(index, minlength=bins * bins)
        weights = np.bincount(index, weights=w, minlength=bins * bins)
        mean = np.zeros((bins * bins, 3))
        for i in range(3):
            mean[:, i] = np.bincount(
                index, weights=w * v[:, i], minlength=bins * bins
            ) / np.maximum(weights, 1e-300)
        dv = v - mean[index]
        mass = meta["scales"]["ion_mass_kg" if name == "ions" else "electron_mass_kg"]
        pressure = np.zeros((bins * bins, 3, 3))
        for i in range(3):
            for j in range(3):
                pressure[:, i, j] = (
                    mass
                    * np.bincount(index, weights=w * dv[:, i] * dv[:, j], minlength=bins * bins)
                    / area
                )
        scalar = np.trace(pressure, axis1=1, axis2=2) / 3
        if not np.isfinite(pressure).all():
            raise ValueError("Non-finite realized particle pressure")
        departure = np.linalg.norm(pressure - scalar[:, None, None] * np.eye(3), axis=(1, 2)) / (
            np.sqrt(3) * np.maximum(scalar, 1e-300)
        )
        result[name] = {
            "count": count,
            "normalized_velocity_fourth_moment": (np.bincount(index,weights=w*np.sum(dv*dv,axis=1)**2,minlength=bins*bins)/np.maximum(weights,1e-300)) / np.maximum((np.trace(pressure,axis1=1,axis2=2)*area/(mass*np.maximum(weights,1e-300)))**2,1e-300),
            "effective_count": weights**2 / np.maximum(np.bincount(index, weights=w*w, minlength=bins*bins),1e-300),
            "relativistic_pressure_correction": np.bincount(index, weights=w*np.sum(dv*dv,axis=1)*(np.sqrt(1+np.sum(proper[good]**2,axis=1)/picmi.constants.c**2)-1), minlength=bins*bins) / np.maximum(np.bincount(index,weights=w*np.sum(dv*dv,axis=1),minlength=bins*bins),1e-300),
            "number_density": weights / area,
            "origin_outside_small_patch_fraction": np.bincount(index,weights=w*(origin[good]>.3*meta['scales']['length_m']),minlength=bins*bins)/np.maximum(weights,1e-300),
            "origin_boundary_collar_fraction": np.bincount(index,weights=w*(origin[good]>(np.max(abs(bounds))-.02*meta['scales']['length_m'])),minlength=bins*bins)/np.maximum(weights,1e-300),
            "velocity": mean,
            "pressure": pressure,
            "isotropy_departure": departure,
        }
    return result


def main(a):
    if not 0 < a.cfl < 1:
        raise ValueError("CFL and interior ROI fraction must be between zero and one")
    if a.moment_bins < 1 or a.diagnostics < 1 or a.minimum_bin_particles < 1:
        raise ValueError("Require positive diagnostic counts")
    meta = json.loads(a.patch.with_suffix(".json").read_text())
    if hashlib.sha256(a.patch.read_bytes()).hexdigest() != meta["patch_sha256"]:
        raise ValueError("Prepared patch hash does not match its manifest")
    with np.load(a.patch, allow_pickle=False) as f:
        data = {k: f[k].copy() for k in f.files}
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    nz, nx = meta["shape_zx"]
    dx, dz = meta["cell_size_m"]
    bounds = np.array(meta["bounds_xz_m"])
    dt = a.cfl / (picmi.constants.c * np.sqrt(dx**-2 + dz**-2))
    omega = meta["scales"]["omega_ci_reference_s1"]
    steps = a.steps if a.steps is not None else math.ceil(a.duration_omegaci / (omega * dt))
    grid = picmi.Cartesian2DGrid(
        number_of_cells=[nx, nz],
        lower_bound=bounds[:, 0].tolist(),
        upper_bound=bounds[:, 1].tolist(),
        lower_boundary_conditions=["absorbing_silver_mueller"] * 2,
        upper_boundary_conditions=["absorbing_silver_mueller"] * 2,
        lower_boundary_conditions_particles=["absorbing"] * 2,
        upper_boundary_conditions_particles=["absorbing"] * 2,
        warpx_max_grid_size=a.max_grid_size,
        warpx_blocking_factor=8,
    )
    solver = picmi.ElectromagneticSolver(grid=grid, method="Yee")
    sim = picmi.Simulation(
        solver=solver,
        time_step_size=dt,
        max_steps=steps,
        particle_shape="quadratic",
        verbose=0,
        warpx_evolve_scheme=picmi.ExplicitEvolveScheme(),
        warpx_current_deposition_algo="esirkepov",
        warpx_random_seed=a.seed,
        warpx_serialize_initial_conditions=True,
        warpx_amrex_the_arena_init_size=256 * 1024**2,
        warpx_used_inputs_file=str(output / "warpx_used_inputs"),
    )
    for name, mass, charge in [
        ("ions", meta["scales"]["ion_mass_kg"], picmi.constants.q_e),
        ("electrons", meta["scales"]["electron_mass_kg"], -picmi.constants.q_e),
    ]:
        sim.add_species(picmi.Species(name=name, mass=mass, charge=charge), layout=None)
    initial = {}

    def inject():
        initial.update(load_particles(data, meta, a.ppc, a.seed))

    callbacks.installparticleloader(inject)

    def load_fields():
        fields.BxFPExternalWrapper()[:, :] = data["bx"].T
        fields.BzFPExternalWrapper()[:, :] = data["bz"].T
        fields.ByFPExternalWrapper()[:, :] = 0.0
        fields.EyFPExternalWrapper()[:, :] = data["ey"].T
        fields.ExFPExternalWrapper()[:, :] = 0.0
        fields.EzFPExternalWrapper()[:, :] = 0.0

    sim.add_applied_field(
        picmi.LoadInitialFieldFromPython(
            load_from_python=load_fields,
            load_B=True,
            load_E=True,
            warpx_do_initial_div_cleaning=False,
        )
    )
    period = max(1, steps // max(a.diagnostics, 1))
    sim.add_diagnostic(
        picmi.FieldDiagnostic(
            name="fields",
            grid=grid,
            period=max(1,steps//a.field_diagnostics),
            data_list=["E", "B", "J", "rho"],
            write_dir=str(output),
            warpx_format="openpmd",
            warpx_openpmd_backend="h5",
        )
    )
    for name, kind in [("field_energy", "FieldEnergy"), ("particle_energy", "ParticleEnergy")]:
        sim.add_diagnostic(
            picmi.ReducedDiagnostic(
                name=name, diag_type=kind, period=period, path=str(output / "reduced") + "/"
            )
        )
    start = time.monotonic()
    sim.initialize_inputs()
    if a.boundary_accounting:
        for species in sim.species:
            for boundary in ('xlo','xhi','zlo','zhi'):
                setattr(species.species,'save_particles_at_'+boundary,1)
    sim.initialize_warpx()
    def save_fields(label):
        arrays={k:getattr(fields,k.upper()[0]+k[1:]+"Wrapper")()[:,:].copy().T for k in ("bx","by","bz","ex","ey","ez")}
        np.savez_compressed(output / (label+"_fields.npz"),**arrays)
    save_fields("initial")
    initial_fields = {
        "bx": fields.BxWrapper()[:, :].copy(),
        "bz": fields.BzWrapper()[:, :].copy(),
        "ey": fields.EyWrapper()[:, :].copy(),
    }
    transfer_error = {
        k: float(np.max(np.abs(v - data[k].T)) / max(np.max(np.abs(data[k])), 1e-300))
        for k, v in initial_fields.items()
    }
    initialization_elapsed = time.monotonic() - start
    phase_times = []
    lost_energy=0.0
    poynting_energy=0.0
    previous_flux=None
    previous_time=0.0
    history = []
    raw = {}
    done = 0
    while True:
        moment_start = time.monotonic()
        measurement = moments(sim, meta, a.moment_bins, [a.roi_x,a.roi_z])
        if a.secondary_bins:
            secondary=moments(sim,meta,a.secondary_bins,[a.roi_x,a.roi_z])
            for sp,vals in secondary.items():
                for key,array in vals.items():raw[f"substep{done}_{sp}_{key}"]=array
        field_activity={}
        field_raw={}
        for comp in ('Bx','By','Bz','Ex','Ey','Ez'):
            q=getattr(fields,comp+'Wrapper')()[:,:].copy().T
            for axis,target in [(0,nz),(1,nx)]:
                if q.shape[axis]==target+1:
                    q=(np.take(q,np.arange(target),axis=axis)+np.take(q,np.arange(1,target+1),axis=axis))/2
            mask=(abs(data['z'][:,None])<a.roi_z*meta['scales']['length_m'])&(abs(data['x'][None,:])<a.roi_x*meta['scales']['length_m'])
            field_activity[comp+'_roi_rms']=float(np.sqrt(np.mean(q[mask]**2)))
            field_raw[comp]=q
        budget={}
        if a.boundary_accounting:
            buffer=particle_containers.ParticleBoundaryBufferWrapper()
            for sp in ('ions','electrons'):
                mass=meta['scales']['ion_mass_kg' if sp=='ions' else 'electron_mass_kg']
                for boundary in ('xlo','xhi','zlo','zhi'):
                    if buffer.get_particle_boundary_buffer_size(sp,boundary[0]+"_"+boundary[1:])==0:continue
                    def bget(comp):
                        arrays=buffer.get_particle_boundary_buffer(sp,boundary[0]+"_"+boundary[1:],comp,level=0)
                        return np.concatenate([v.get() if hasattr(v,'get') else np.asarray(v) for v in arrays])
                    wp=bget('w');up=np.column_stack([bget('ux'),bget('uy'),bget('uz')])
                    lost_energy+=float(np.sum(wp*mass*picmi.constants.c**2*(np.sqrt(1+np.sum(up*up,axis=1)/picmi.constants.c**2)-1)))
            buffer.clear_buffer()
            mu0=1.25663706127e-6
            sx=(field_raw['Ey']*field_raw['Bz']-field_raw['Ez']*field_raw['By'])/mu0
            sz=(field_raw['Ex']*field_raw['By']-field_raw['Ey']*field_raw['Bx'])/mu0
            flux=float(dz*(sx[:,-1].sum()-sx[:,0].sum())+dx*(sz[-1,:].sum()-sz[0,:].sum()))
            if previous_flux is not None:poynting_energy+=(previous_flux+flux)*.5*(done*dt-previous_time)
            previous_flux=flux;previous_time=done*dt
            budget=dict(absorbed_particle_energy_J_per_m=lost_energy,estimated_poynting_outflow_J_per_m=poynting_energy,instant_boundary_poynting_W_per_m=flux,live_particle_energy_J_per_m=sum(particle_containers.ParticleContainerWrapper(sp).get_species_energy_sum() for sp in ('ions','electrons')))
        row = {"energy_boundary_accounting":budget,"field_activity":field_activity,"step": done, "time_s": done * dt, "time_omegaci": done * dt * omega}
        for species, values in measurement.items():
            eligible = values["count"] >= a.minimum_bin_particles
            departure = values["isotropy_departure"][eligible]
            row[species] = {
                "eligible_bins": int(eligible.sum()),
                "median_departure": float(np.median(departure)) if len(departure) else None,
                "p90_departure": float(np.percentile(departure, 90)) if len(departure) else None,
            }
            for key, array in values.items():
                raw[f"step{done}_{species}_{key}"] = array
        phase_times.append(dict(step=done, moment_seconds=time.monotonic()-moment_start))
        history.append(row)
        (output / 'progress.json').write_text(json.dumps(dict(duration_omegaci=done*dt*omega,steps=done,elapsed_s=time.monotonic()-start))+'\n')
        np.savez_compressed(output / "moments.npz", **raw)
        (output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
        if done >= steps:
            break
        take = min(period, steps - done)
        evolve_start = time.monotonic()
        sim.step(take)
        phase_times[-1]["evolve_steps"] = take
        phase_times[-1]["evolve_seconds"] = time.monotonic()-evolve_start
        done += take
    np.savez_compressed(output / "moments.npz", **raw)
    (output / "history.json").write_text(json.dumps(history, indent=2) + "\n")
    save_fields("final")
    from amrex import space2d as amrex

    result = {
        "completed": True,
        "backend": amrex.Config.gpu_backend,
        "gpu": amrex.Config.have_gpu,
        "steps": done,
        "dt_s": dt,
        "dt_omega_pe": dt * meta["scales"]["omega_pe_reference_s1"],
        "duration_omegaci": done * dt * omega,
        "elapsed_s": time.monotonic() - start,
        "initialization_seconds": initialization_elapsed,
        "phase_times": phase_times,
        "storage_bytes": sum(p.stat().st_size for p in output.rglob("*") if p.is_file()),
        "initial_field_relative_errors": transfer_error,
        "initial_maximum_particle_speed_over_c": initial,
        "patch_sha256": meta["patch_sha256"],
        "ppc_per_species": a.ppc,
        "seed": a.seed,
        "moment_convention": (
            "Nonrelativistic m*n*<v_prime v_prime>, velocity v=u/sqrt(1+u^2/c^2); "
            "local bin mean subtracted."
        ),
        "isotropy_metric": "Frobenius(P-tr(P)I/3)/(sqrt(3)*tr(P)/3)",
        "moment_bins_per_axis": a.moment_bins,
        "window_candidate": [0.3,0.8],
        "boundary_accounting_enabled": a.boundary_accounting,
        "poynting_estimator": "E cross B at nearest interior cell centers, normal flux quadrature on each face and trapezoidal sampling; spatial/time quadrature residual retained, not exact boundary flux.",
        "secondary_bins": a.secondary_bins,
        "minimum_bin_particles": a.minimum_bin_particles,
        "window_area_time_mean": {},
        "roi_half_code": [a.roi_x,a.roi_z],
        "scope": (
            "Collisionless one-way local continuation. Absorbing boundaries, transfer relaxation "
            "and numerical/particle controls remain scientific qualification requirements."
        ),
    }
    from estimator import estimate
    for species in ('ions','electrons'):
        result['window_area_time_mean'][species]=estimate(raw,history,species)
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


def cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--patch", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--ppc", type=int, default=16)
    p.add_argument("--seed", type=int, default=20261008)
    p.add_argument("--steps", type=int)
    p.add_argument("--duration-omegaci", type=float, default=0.02)
    p.add_argument("--boundary-accounting", action="store_true")
    p.add_argument("--secondary-bins", type=int,default=0)
    p.add_argument("--field-diagnostics", type=int, default=4)
    p.add_argument("--diagnostics", type=int, default=8)
    p.add_argument("--cfl", type=float, default=0.7)
    p.add_argument("--max-grid-size", type=int, default=64)
    p.add_argument("--moment-bins", type=int, default=8)
    p.add_argument("--roi-x", type=float, default=0.04)
    p.add_argument("--roi-z", type=float, default=0.015)
    p.add_argument("--minimum-bin-particles", type=int, default=64)
    main(p.parse_args())

if __name__ == "__main__":
    cli()
