#!/usr/bin/env python3
"""Aggregate prospective island-scaling summaries and plot archived FLASH fields."""
import argparse, io, json, math, sys, tarfile
from itertools import product
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from scipy.stats import t as student_t


def crossing(ts, ys, target):
    ids = np.flatnonzero(ys >= target)
    if not len(ids):
        return None
    i = int(ids[0])
    if i == 0:
        return float(ts[0])
    if ys[i] <= ys[i-1]:
        return None
    f = (target-ys[i-1])/(ys[i]-ys[i-1])
    return float(ts[i-1]+f*(ts[i]-ts[i-1]))


def az_midline_paths(bx, by):
    """Reconstruct A_z(x,0) from both field components in a common boundary gauge."""
    ny,nx=bx.shape; dx=dy=1.0/nx; mid=ny//2
    bymid=.5*(by[mid-1]+by[mid])
    # Integrate Bx vertically, retaining the x-dependent lower-boundary gauge
    # induced by any small but finite normal By on the reflecting boundary.
    abottom=-np.r_[0.0,np.cumsum(.5*(by[0,:-1]+by[0,1:])*dx)]
    abx=abottom+np.sum(bx[:mid],axis=0)*dy
    # Both paths share A_z at the lower-left corner.
    aby=abx[0]-np.r_[0.0,np.cumsum(.5*(bymid[:-1]+bymid[1:])*dx)]
    mismatch=abx-aby
    scale=max(float(np.ptp(abx)),float(np.ptp(aby)),1e-300)
    return abx, aby, float(np.max(np.abs(mismatch))/scale)


def secondary_extrema(az, x, prominence=0.005):
    """Find peaks on the full, gauge-shifted signal; crop only after prominence calculation."""
    smooth=gaussian_filter1d(np.asarray(az,float),sigma=1.0,mode="nearest")
    maxima,_=find_peaks(smooth,prominence=prominence)
    minima,_=find_peaks(-smooth,prominence=prominence)
    indices=[int(i) for i in np.r_[maxima,minima] if .04<=abs(x[i])<=.22]
    return indices


def flux_from_by(by):
    ny,nx=by.shape; dx=1.0/nx; dy=1.0/ny
    x=-.5+(np.arange(nx)+.5)*dx; y=-.5+(np.arange(ny)+.5)*dy
    ix=np.argsort(np.abs(x))[:2]
    from_left=np.cumsum(by,axis=1)*dx-.5*by*dx
    line=from_left[:,ix].mean(axis=1); fy=np.argsort(np.abs(y))[:8]
    design=np.column_stack((np.ones(8),y[fy]**2,y[fy]**4))
    return float(np.linalg.lstsq(design,line[fy],rcond=None)[0][0])


def archive_screen(path, low, high):
    """Recompute sheet width, topology, A-path closure and native budgets from archives."""
    states=[]; native=None; log_text=""
    with tarfile.open(path,"r:gz") as tf:
        for member in tf.getmembers():
            stream=tf.extractfile(member)
            if stream is None: continue
            if "hdf5_plt_cnt_" in member.name:
                with h5py.File(io.BytesIO(stream.read()),"r") as h:
                    scalars=h["real scalars"][()]
                    tm=float(next(r["value"] for r in scalars if r["name"].decode().strip().casefold()=="time"))
                    states.append((tm,np.asarray(h["magx"][0,0],float),np.asarray(h["magy"][0,0],float),
                                   np.asarray(h["dens"][0,0],float),np.asarray(h["pres"][0,0],float)))
            elif member.name.endswith("flash_run.dat"):
                native=np.loadtxt(io.BytesIO(stream.read()),comments="#")
            elif member.name.endswith("flash_run.log"):
                log_text=stream.read().decode("utf-8",errors="replace")
    states.sort(key=lambda row:row[0])
    if not states: return {"defined":False,"reason":"no HDF5 plot states in archive"}
    psi0=flux_from_by(states[0][2]); minimum_fwhm=float("inf"); max_secondary=0; max_path_mismatch=0.0
    minrho=float("inf"); minpres=float("inf"); n_window=0
    for tm,bx,by,rho,pres in states:
        minrho=min(minrho,float(rho.min())); minpres=min(minpres,float(pres.min()))
        if not low<=flux_from_by(by)-psi0<=high: continue
        n_window+=1; ny,nx=bx.shape; dx=dy=1.0/nx; y=-.5+(np.arange(ny)+.5)*dy
        jz=np.gradient(by,dx,axis=1)-np.gradient(bx,dy,axis=0)
        central=np.flatnonzero(np.abs(y)<=.15); current=np.abs(jz[:,nx//2]); peak=int(central[np.argmax(current[central])])
        half=.5*current[peak]; lo=hi=peak
        while lo>0 and current[lo-1]>=half: lo-=1
        while hi<ny-1 and current[hi+1]>=half: hi+=1
        minimum_fwhm=min(minimum_fwhm,float(hi-lo+1))
        x=-.5+(np.arange(nx)+.5)*dx
        abx,aby,patherr=az_midline_paths(bx,by)
        max_path_mismatch=max(max_path_mismatch,patherr)
        max_secondary=max(max_secondary,len(secondary_extrema(aby,x)))
    if native is None or native.ndim!=2 or native.shape[1]<6:
        mass_drift=energy_drift=None; budget_reason="native flash_run.dat absent or malformed"
    else:
        mass_drift=float(np.max(np.abs(native[:,1]/native[0,1]-1)))
        energy_drift=float(np.max(np.abs(native[:,5]/native[0,5]-1)))
        budget_reason=None
    return {"defined":True,"window_states":n_window,"minimum_current_fwhm_cells":None if not np.isfinite(minimum_fwhm) else minimum_fwhm,
            "secondary_extrema_max_count":max_secondary,"max_relative_A_z_path_mismatch":max_path_mismatch,
            "minimum_saved_density":minrho,"minimum_saved_pressure":minpres,
            "max_relative_mass_drift":mass_drift,"max_relative_total_energy_drift":energy_drift,
            "mass_budget_ok":mass_drift is not None and mass_drift<=1e-8,
            "energy_budget_ok":energy_drift is not None and energy_drift<=1e-4,
            "saved_floors_ok":minrho>1e-10 and minpres>1e-10,
            "A_z_paths_ok":max_path_mismatch<=.15,
            "preplasmoid":max_secondary==0 if n_window else False,
            "floor_energyfix_correction_counters_available":False,
            "correction_counter_limit":"no per-step floor/E_modification counters are exposed in the archived dat/log; plot-state minima do not rule out intermediate corrections",
            "budget_undefined_reason":budget_reason,"log_bytes":len(log_text)}


def rate_from_path(ts, values, low, high, normalization):
    lo,hi=crossing(ts,values,low),crossing(ts,values,high)
    if lo is None or hi is None or hi<=lo or not np.isfinite(normalization) or normalization<=0:
        return None
    value=(high-low)/(hi-lo)/normalization
    return float(value) if np.isfinite(value) and value>0 else None


def complete_rate_set(rates):
    """Both field paths at both cadences are mandatory for quantitative eligibility."""
    return len(rates)==4 and all(v is not None and np.isfinite(v) and v>0 for v in rates.values())


def summarize_rate_set(rates):
    """Incomplete path/cadence measurements become explicit nulls, never half-estimates."""
    if not complete_rate_set(rates):
        return {"complete":False,"rate":None,"rate_path_min":None,"rate_path_max":None,
                "censor_reason":"one or more field-path/cadence rates are missing, nonfinite, or nonpositive"}
    fine=[rates["by_dt005"],rates["bx_dt005"]]
    return {"complete":True,"rate":float(np.mean(fine)),
            "rate_path_min":float(min(rates.values())),"rate_path_max":float(max(rates.values())),
            "censor_reason":None}


def fit(cases, key="rate"):
    good = [c for c in cases if c.get("eligible") and c.get("eta_inverse") is not None
            and c.get(key) is not None and np.isfinite(c[key]) and c[key]>0
            and c.get("rate_path_min") is not None and c["rate_path_min"]>0
            and c.get("rate_path_max") is not None and c["rate_path_max"]>0]
    if len(good) < 3:
        return {"n": len(good), "defined": False, "reason": "fewer than three eligible cases"}
    x = np.log([c["eta_inverse"] for c in good])
    y = np.log([c[key] for c in good])
    design = np.column_stack((np.ones(len(x)), x))
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y-design@beta
    df = len(x)-2
    se = math.sqrt(float(residual@residual/df) / float(np.sum((x-x.mean())**2)))
    crit = float(student_t.ppf(0.975, df))
    grid = np.linspace(float(x.min()), float(x.max()), 80)
    sigma2 = float(residual@residual/df)
    mean_se = np.sqrt(sigma2*(1.0/len(x)+(grid-float(x.mean()))**2/float(np.sum((x-x.mean())**2))))
    means = beta[0]+beta[1]*grid
    mixed_intervals=[]; mixed_slopes=[]
    for choices in product(("rate_path_min","rate_path_max"),repeat=len(good)):
        yy=np.log([c[field] for c,field in zip(good,choices)])
        bb=np.linalg.lstsq(design,yy,rcond=None)[0]
        rr=yy-design@bb
        ss=math.sqrt(float(rr@rr/df)/float(np.sum((x-x.mean())**2)))
        mixed_slopes.append(float(bb[1]))
        mixed_intervals.append((float(bb[1]-crit*ss),float(bb[1]+crit*ss)))
    mixed_envelope={"combinations":len(mixed_intervals),"slope_range":[min(mixed_slopes),max(mixed_slopes)],
                    "confidence_interval_envelope":[min(v[0] for v in mixed_intervals),max(v[1] for v in mixed_intervals)]}
    conservative_interval=[min(beta[1]-crit*se,mixed_envelope["confidence_interval_envelope"][0]),
                           max(beta[1]+crit*se,mixed_envelope["confidence_interval_envelope"][1])]
    point_rows=[]
    for i,c in enumerate(good):
        prediction=float(design[i]@beta)
        lo=float(math.log(c["rate_path_min"])-prediction)
        hi=float(math.log(c["rate_path_max"])-prediction)
        distance=0.0 if lo<=0.0<=hi else min(abs(lo),abs(hi))
        point_rows.append({"id":c["id"],"S_eta":c["eta_inverse"],"log_residual":float(residual[i]),
                           "residual_interval_log":[lo,hi],"distance_to_zero_after_envelope":distance,
                           "departure_excess_log":float(distance)})
    max_departure=max(r["departure_excess_log"] for r in point_rows)
    departure_threshold=math.log(1.25)
    branch_status="departure_over_25pct_detected" if max_departure>departure_threshold else "no_sampled_departure_over_25pct"
    return {"n": len(good), "p": float(beta[1]), "ci95": [float(beta[1]-crit*se), float(beta[1]+crit*se)],
            "mixed_envelope_slope_fits":mixed_envelope,"conservative_interval_including_path_cadence_envelope":conservative_interval,
            "conservative_interval_including_path_spread":conservative_interval,
            "intercept": float(beta[0]), "mean_fit_logS": grid.tolist(), "mean_fit_logR": means.tolist(),
            "mean_fit_ci95_logR": [ (means-crit*mean_se).tolist(), (means+crit*mean_se).tolist() ],
            "r_squared": float(1-(residual@residual)/np.sum((y-y.mean())**2)),
            "max_abs_log_residual": float(np.max(np.abs(residual))), "df": df,
            "point_residuals":point_rows,"branch_departure_threshold_fraction":0.25,
            "branch_departure_threshold_log":departure_threshold,"branch_status":branch_status,
            "branch_uncertainty_rule":"distance from fitted residual to the full asymmetric case log-rate envelope; no symmetry about the fine-cadence mean assumed"}


def compare_refinement(base_matched, refined, margin=0.10):
    b=fit(base_matched); r=fit(refined)
    if "p" not in b or "p" not in r:
        return {"status":"inconclusive_too_few_matched_cases","base_fit":b,"refined_fit":r,"margin":margin}
    blo,bhi=b["conservative_interval_including_path_spread"]
    rlo,rhi=r["conservative_interval_including_path_spread"]
    delta=float(r["p"]-b["p"])
    interval=[float(rlo-bhi),float(rhi-blo)]
    bm={c["eta_inverse"]:c for c in base_matched}; rm={c["eta_inverse"]:c for c in refined}
    resolution_pairs=[]
    for seta in sorted(set(bm)&set(rm)):
        bc,rc=bm[seta],rm[seta]
        ratio=float(rc["nx"])/float(bc["nx"]) if bc.get("nx") and rc.get("nx") else None
        cells_delta=float(rc["resolution_cells_SP"]-bc["resolution_cells_SP"]) if rc.get("resolution_cells_SP") is not None and bc.get("resolution_cells_SP") is not None else None
        fwhm_delta=(float(rc["measured_current_fwhm_cells"]-bc["measured_current_fwhm_cells"])
                    if rc.get("measured_current_fwhm_cells") is not None and bc.get("measured_current_fwhm_cells") is not None else None)
        resolution_pairs.append({"S_eta":seta,"grid_ratio":ratio,"nominal_cells_delta":cells_delta,"measured_fwhm_cells_delta":fwhm_delta})
    spatial_refinement_meaningful=(len(resolution_pairs)>=3 and all(p["grid_ratio"] is not None and p["grid_ratio"]>=1.20
                                  and p["nominal_cells_delta"] is not None and p["nominal_cells_delta"]>=1.0 for p in resolution_pairs))
    if not spatial_refinement_meaningful:
        status="inconclusive_refinement_not_meaningful"
    elif interval[0]>=-margin and interval[1]<=margin:
        status="persistence_within_margin"
    elif interval[1]<-margin or interval[0]>margin:
        status="persistence_incompatible"
    else:
        status="persistence_inconclusive"
    return {"status":status,"p_base_matched":b["p"],"p_refined":r["p"],"delta_p":delta,
            "conservative_delta_interval":interval,"equivalence_margin":margin,
            "spatial_refinement_meaningful":spatial_refinement_meaningful,"matched_resolution_pairs":resolution_pairs,
            "base_matched_fit":b,"refined_fit":r}


def band_decision(f):
    if "conservative_interval_including_path_spread" not in f: return "inconclusive"
    lo,hi=f["conservative_interval_including_path_spread"]
    if lo>=-.60 and hi<=-.40: return "inside_allowed_band"
    return "disjoint_below" if hi<-.60 else ("disjoint_above" if lo>-.40 else "overlaps_allowed_band")


def assess_powerlaw(base_all, base_matched, refined, persistence):
    bb,bm,br=band_decision(base_all),band_decision(base_matched),band_decision(refined)
    same_side=(bm==br and bm in ("disjoint_below","disjoint_above"))
    refined_points={r["S_eta"]:r for r in refined.get("point_residuals",[])}
    base_points={r["S_eta"]:r for r in base_matched.get("point_residuals",[])}
    common_departures=[]
    for seta in sorted(set(refined_points)&set(base_points)):
        if (refined_points[seta]["departure_excess_log"]>math.log(1.25)
                and base_points[seta]["departure_excess_log"]>math.log(1.25)):
            common_departures.append(seta)
    if same_side:
        verdict="falsified_finite_sample_band_violation"
    elif persistence.get("status")=="persistence_incompatible":
        verdict="inconclusive_numerical_refinement_sensitivity"
    elif common_departures:
        verdict="falsified_finite_sample_common_branch_departure"
    elif (bb==bm==br=="inside_allowed_band" and persistence.get("status")=="persistence_within_margin"
          and base_all.get("branch_status")=="no_sampled_departure_over_25pct"
          and refined.get("branch_status")=="no_sampled_departure_over_25pct"):
        verdict="compatible_finite_sample_not_universal"
    else:
        verdict="inconclusive"
    return {"finite_sample_assessment":verdict,"base_all_band_status":bb,
            "base_matched_band_status":bm,"refined_band_status":br,
            "same_side_matched_band_violation":same_side,
            "common_branch_departure_resistivities":common_departures,
            "limitations":"OLS t intervals use residual variation in deterministic points; path and 0.10-cadence envelope is included, but spatial uncertainty is represented only by matched base/refined comparisons. Sampling is finite and does not prove a continuous-domain claim."}


def qualification_fixtures():
    x=np.linspace(-.5,.5,512,endpoint=False)+.5/512
    quiet=-.2*x*x
    island=quiet+.03*np.exp(-.5*((x-.14)/.025)**2)
    outside=quiet+.03*np.exp(-.5*((x-.32)/.025)**2)
    quiet_n=len(secondary_extrema(quiet,x)); island_n=len(secondary_extrema(island,x))
    shifted_n=len(secondary_extrema(island+123.456,x)); outside_n=len(secondary_extrema(outside,x))
    n=128; xx=-.5+(np.arange(n)+.5)/n; yy=xx.copy()
    # Analytic A_z has nonzero Bx and an x-dependent lower-boundary contribution.
    bxline=.04*np.cos(np.pi*xx)
    bx=np.tile(bxline,(n,1))
    by=-.04*np.pi*np.cos(2*np.pi*xx)[None,:]+.04*np.pi*np.sin(np.pi*xx)[None,:]*(yy[:,None]+.5)
    _,_,azerr=az_midline_paths(bx,by)
    seta=np.array([250.,500.,1000.,2000.,4000.])
    rates=.2*seta**-.5
    base_n={250.:96,500.:128,1000.:128,2000.:192,4000.:256}
    base=[{"id":f"s{int(s)}","eta_inverse":float(s),"rate":float(r),
           "rate_path_min":float(r*.998),"rate_path_max":float(r*1.002),"eligible":True,
           "nx":base_n[float(s)],"resolution_cells_SP":base_n[float(s)]/math.sqrt(float(s)),
           "measured_current_fwhm_cells":4.0}
          for s,r in zip(seta,rates)]
    matched=[c for c in base if c["eta_inverse"] in (250.,1000.,4000.)]
    ref_n={250.:120,1000.:160,4000.:320}
    refined=[dict(c,id="refined_"+c["id"],nx=ref_n[c["eta_inverse"]],
                  resolution_cells_SP=ref_n[c["eta_inverse"]]/math.sqrt(c["eta_inverse"]),
                  measured_current_fwhm_cells=5.0) for c in matched]
    ref=compare_refinement(matched,refined)
    altered=[dict(c) for c in base]
    altered[2]["rate"]*=1.8; altered[2]["rate_path_min"]*=1.8; altered[2]["rate_path_max"]*=1.8
    branch=fit(altered)
    matched_altered=[dict(c,id="refined_"+c["id"]) for c in matched]
    for c in matched_altered:
        if c["eta_inverse"]==1000.0:
            c["rate"]*=1.8;c["rate_path_min"]*=1.8;c["rate_path_max"]*=1.8
    altered_matched=[c for c in altered if c["eta_inverse"] in (250.,1000.,4000.)]
    robust_branch=assess_powerlaw(fit(altered),fit(altered_matched),
                                  fit(matched_altered),compare_refinement(altered_matched,matched_altered))
    missing={"by_dt005":.1,"bx_dt005":None,"by_dt010":.1,"bx_dt010":None}
    incomplete=summarize_rate_set(missing)
    # S_eta-dependent asymmetric bounds require mixed, not only all-low/all-high, fits.
    lower_mult=[.95,.80,.99,.90,.97]; upper_mult=[1.01,1.04,1.35,1.02,1.10]
    mixed=[dict(c,rate_path_min=c["rate"]*l,rate_path_max=c["rate"]*u)
           for c,l,u in zip(base,lower_mult,upper_mult)]
    mixed_fit=fit(mixed)
    xxlog=np.log([c["eta_inverse"] for c in mixed]); X=np.column_stack((np.ones(len(xxlog)),xxlog)); brute=[]
    for choices in product(("rate_path_min","rate_path_max"),repeat=len(mixed)):
        yylog=np.log([c[field] for c,field in zip(mixed,choices)])
        brute.append(float(np.linalg.lstsq(X,yylog,rcond=None)[0][1]))
    mixed_range=mixed_fit["mixed_envelope_slope_fits"]["slope_range"]
    incomplete_summary=summarize_rate_set(missing)
    incomplete_case={"rate":incomplete_summary["rate"],"rate_path_min":incomplete_summary["rate_path_min"],
                     "rate_path_max":incomplete_summary["rate_path_max"],"eligible":False,
                     "censor_reason":incomplete_summary["censor_reason"]}
    # Deliberate grid disagreement is numerical sensitivity, not a physical falsifier.
    incompatible_refined=[]
    for c in refined:
        q=dict(c); q["rate"]=(.2*q["eta_inverse"]**-.9); q["rate_path_min"]=q["rate"]*.998; q["rate_path_max"]=q["rate"]*1.002
        incompatible_refined.append(q)
    incompatible=compare_refinement(matched,incompatible_refined)
    sensitivity_assessment=assess_powerlaw(fit(base),fit(matched),fit(incompatible_refined),incompatible)
    checks={
      "topology_non_detection":quiet_n==0,
      "secondary_extremum_detection":island_n>0,
      "topology_gauge_shift_invariance":shifted_n==island_n,
      "topology_spatial_window_exclusion":outside_n==0,
      "two_path_missing_rate_censored":not complete_rate_set(missing),
      "incomplete_case_serializes_without_plot_rate":incomplete_case["rate"] is None and not incomplete_case["eligible"] and bool(incomplete_case["censor_reason"]),
      "known_powerlaw_slope":abs(fit(base)["p"]+.5)<1e-10,
      "mixed_asymmetric_envelope_enumerates_2_power_n":mixed_fit["mixed_envelope_slope_fits"]["combinations"]==32 and mixed_range[0]<=min(brute)+1e-12 and mixed_range[1]>=max(brute)-1e-12,
      "mixed_bounds_include_a_false_branch_guard":mixed_fit["branch_status"]=="no_sampled_departure_over_25pct",
      "matched_refinement_decision_executed":ref["status"]=="persistence_within_margin",
      "matched_spatial_resolution_increment_qualified":ref.get("spatial_refinement_meaningful",False),
      "known_branch_departure_flagged":branch["branch_status"]=="departure_over_25pct_detected",
      "matched_branch_departure_uses_resistivity_not_case_id":1000.0 in robust_branch["common_branch_departure_resistivities"],
      "mixed_rate_envelopes_cover_all_endpoint_choices":mixed_range[0]<=min(brute)+1e-12 and mixed_range[1]>=max(brute)-1e-12 and mixed_fit["mixed_envelope_slope_fits"]["combinations"]==32,
      "asymmetric_uncertainty_does_not_create_false_branch":mixed_fit["branch_status"]=="no_sampled_departure_over_25pct",
      "incomplete_case_has_null_rate_and_serializes":bool(incomplete["rate"] is None and incomplete["rate_path_min"] is None and incomplete["censor_reason"] is not None and json.dumps(incomplete,allow_nan=False)),
      "grid_disagreement_is_not_physical_falsification":sensitivity_assessment["finite_sample_assessment"]=="inconclusive_numerical_refinement_sensitivity",
      "common_gauge_Az_path_fixture":bool(azerr<.15 and np.max(np.abs(bx))>0 and np.ptp(by[0])>0),
    }
    return {"kind":"analysis_qualification_fixtures","checks":checks,
            "all_passed":all(checks.values()),"metrics":{"quiet_extrema":quiet_n,"island_extrema":island_n,
            "gauge_shifted_extrema":shifted_n,"outside_roi_extrema":outside_n,
            "analytic_Az_path_relative_mismatch":azerr,"known_slope":fit(base).get("p"),
            "matched_refinement":ref["status"],"branch_fixture_status":branch["branch_status"],
            "matched_resolution_pairs":ref.get("matched_resolution_pairs"),
            "common_branch_departures":robust_branch["common_branch_departure_resistivities"],
            "missing_path_complete_set":complete_rate_set(missing),"incomplete_serialized_rate":incomplete["rate"],
            "incomplete_case_rate_and_bounds": [incomplete_case["rate"],incomplete_case["rate_path_min"],incomplete_case["rate_path_max"]],
            "mixed_rate_slope_range":mixed_range,"brute_mixed_slope_range":[min(brute),max(brute)],
            "grid_disagreement_assessment":sensitivity_assessment["finite_sample_assessment"],
            "nonzero_Bx_fixture_path_mismatch":azerr},
            "fixtures":"synthetic diagnostic qualification only; not scientific evidence"}


def load_case(summary_path, archive_path):
    s = json.loads(Path(summary_path).read_text())
    m = s["metrics"]
    ts = np.array([r["time"] for r in s["timeseries"]], dtype=float)
    fluxes = {"by": np.array([r["reconnected_flux_from_by"] for r in s["timeseries"]], dtype=float),
              "bx": np.array([r["reconnected_flux_from_bx"] for r in s["timeseries"]], dtype=float)}
    norm=m["B_up"]**2/math.sqrt(m["rho_up"])
    path_rates={}
    for path,values in fluxes.items():
        path_rates[f"{path}_dt005"]=rate_from_path(ts,values,m["flux_low"],m["flux_high"],norm)
        ix=np.arange(0,len(ts),2)
        if ix[-1]!=len(ts)-1: ix=np.r_[ix,len(ts)-1]
        path_rates[f"{path}_dt010"]=rate_from_path(ts[ix],values[ix],m["flux_low"],m["flux_high"],norm)
    rates=list(path_rates.values())
    rate_summary=summarize_rate_set(path_rates)
    paths_complete=rate_summary["complete"]
    rmid,rlo,rhi=rate_summary["rate"],rate_summary["rate_path_min"],rate_summary["rate_path_max"]
    checks = s["checks"]
    reached = all(path_rates[k] is not None for k in ("by_dt005","bx_dt005"))
    screen=archive_screen(archive_path,m["flux_low"],m["flux_high"])
    fwhm=screen.get("minimum_current_fwhm_cells")
    secondary=screen.get("secondary_extrema_max_count")
    preplasmoid=screen.get("preplasmoid",False)
    nominal_cells=s["realized"]["ny"]/math.sqrt(m["nominal_eta_inverse"])
    initial_sheet_cells=s["realized"]["ny"]/s["realized"]["alpha"]
    resolved=nominal_cells>=4 and initial_sheet_cells>=4 and fwhm is not None and fwhm>=4.0
    numerical_base=all(checks.get(k,False) for k in ("completed","representation","physics_controls","boundaries","diagnostics","numerical_regime"))
    numerically_valid=numerical_base and screen.get("mass_budget_ok",False) and screen.get("energy_budget_ok",False) and screen.get("saved_floors_ok",False)
    az_paths_ok=screen.get("A_z_paths_ok",False)
    reasons=[]
    if not reached: reasons.append("both flux paths did not cross the full flux window: censored")
    if not paths_complete: reasons.append(rate_summary["censor_reason"])
    if not resolved: reasons.append("nominal or measured current-sheet resolution floor failed")
    if not preplasmoid: reasons.append("secondary A_z extrema detected or no saved flux-window states")
    if not az_paths_ok: reasons.append("common-gauge A_z reconstructions from Bx and By disagree by more than 15% of range")
    if not numerically_valid: reasons.append("conservation, saved-floor, or solver checks failed")
    eligible=reached and paths_complete and resolved and preplasmoid and az_paths_ok and numerically_valid
    cadence_delta=(max(abs(path_rates[f"{path}_dt010"]-path_rates[f"{path}_dt005"])/path_rates[f"{path}_dt005"]
                       for path in ("by","bx")) if paths_complete else None)
    path_delta=(abs(path_rates["by_dt005"]-path_rates["bx_dt005"])/rmid if paths_complete else None)
    return {"id": s.get("experiment_id", Path(summary_path).parent.name), "eta": s["realized"]["eta"],
            "family": s["realized"].get("resolution_family", "base"),
            "eta_inverse": m["nominal_eta_inverse"], "nx": s["realized"]["nx"], "ny": s["realized"]["ny"],
            "rate": rmid, "rate_path_min": rlo, "rate_path_max": rhi,
            "eligible": eligible, "reached_window": reached, "resolved": resolved,
            "preplasmoid": preplasmoid, "numerically_valid":numerically_valid,"A_z_paths_ok":az_paths_ok,
            "path_rates":path_rates,"output_cadence_sensitivity_fraction":cadence_delta,"fine_flux_path_sensitivity_fraction":path_delta,
            "censor_reasons":reasons,
            "resolution_cells_SP": nominal_cells,"initial_sheet_cells":initial_sheet_cells,
            "measured_current_fwhm_cells": fwhm,"secondary_extrema_count_recomputed":secondary,
            "max_relative_A_z_path_mismatch":screen.get("max_relative_A_z_path_mismatch"),
            "max_relative_mass_drift":screen.get("max_relative_mass_drift"),
            "max_relative_total_energy_drift":screen.get("max_relative_total_energy_drift"),
            "minimum_saved_density":screen.get("minimum_saved_density"),"minimum_saved_pressure":screen.get("minimum_saved_pressure"),
            "correction_counters_available":screen.get("floor_energyfix_correction_counters_available"),
            "correction_counter_limit":screen.get("correction_counter_limit"),
            "archive": str(archive_path), "summary": str(summary_path), "raw": s}


def draw_field(case, outdir):
    target = 0.03
    s = case["raw"]
    flux = np.array([r["reconnected_flux_from_by"] for r in s["timeseries"]])
    times = np.array([r["time"] for r in s["timeseries"]])
    tmid = crossing(times, flux, target)
    if tmid is None:
        tmid = float(times[-1])
    selected = None
    with tarfile.open(case["archive"], "r:gz") as tf:
        for member in tf.getmembers():
            if "hdf5_plt_cnt_" not in member.name:
                continue
            stream = tf.extractfile(member)
            if stream is None:
                continue
            content = stream.read()
            with h5py.File(io.BytesIO(content), "r") as h:
                row = h["real scalars"][()]
                tm = float(next(r["value"] for r in row if r["name"].decode().strip().casefold() == "time"))
                if selected is None or abs(tm-tmid) < selected[0]:
                    fields = {k: np.asarray(h[k][0, 0], dtype=float) for k in ("magx", "magy")}
                    selected = (abs(tm-tmid), tm, fields)
    if selected is None:
        return None
    _, tm, f = selected
    bx, by = f["magx"], f["magy"]
    ny, nx = bx.shape
    x = np.linspace(-0.5, 0.5, nx, endpoint=False)+0.5/nx
    y = np.linspace(-0.5, 0.5, ny, endpoint=False)+0.5/ny
    jz = np.gradient(by, 1/nx, axis=1)-np.gradient(bx, 1/ny, axis=0)
    dx=1/nx; dy=1/ny
    abottom=-np.r_[0.0,np.cumsum(.5*(by[0,:-1]+by[0,1:])*dx)]
    az = np.zeros_like(bx)
    az[0] = abottom + .5*dy*bx[0]
    az[1:] = az[0] + np.cumsum(0.5*(bx[:-1]+bx[1:])*dy, axis=0)
    _,_,azerr=az_midline_paths(bx,by)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    im = axes[0].pcolormesh(x, y, np.hypot(bx, by), shading="auto", cmap="viridis")
    axes[0].contour(x, y, az, levels=18, colors="white", linewidths=.45, alpha=.85)
    axes[0].set_title(r"$|B|$ and $A_z$ contours")
    fig.colorbar(im, ax=axes[0], label="normalized magnetic field")
    im2 = axes[1].pcolormesh(x, y, jz, shading="auto", cmap="RdBu_r", vmin=-np.max(np.abs(jz)), vmax=np.max(np.abs(jz)))
    axes[1].set_title(r"$J_z=\partial_x B_y-\partial_y B_x$")
    fig.colorbar(im2, ax=axes[1], label="normalized current density")
    for ax in axes:
        ax.set(xlabel="x", ylabel="y", xlim=(-.5,.5), ylim=(-.5,.5), aspect="equal")
    fig.suptitle(f"{case['id']} at t={tm:.4g}; A_z path mismatch={azerr:.3g}")
    path = Path(outdir)/f"field_current_{case['id']}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return str(path)


def main():
    if len(sys.argv)>1 and sys.argv[1]=="--qualify":
        if len(sys.argv)!=3: raise SystemExit("usage: analysis.py --qualify OUTPUT.json")
        payload=qualification_fixtures()
        Path(sys.argv[2]).write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
        print(json.dumps(payload,indent=2))
        return
    p = argparse.ArgumentParser()
    p.add_argument("--case", action="append", nargs=2, metavar=("SUMMARY", "RAW_TAR"), required=True)
    p.add_argument("--outdir", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    outdir = Path(a.outdir); outdir.mkdir(parents=True, exist_ok=True)
    cases = [load_case(*pair) for pair in a.case]
    base = [c for c in cases if c["family"] == "base"]
    refined = [c for c in cases if c["family"] == "refined"]
    fb, fr = fit(base, "rate"), fit(refined, "rate")
    refined_s={c["eta_inverse"] for c in refined if c["eligible"]}
    base_matched=[c for c in base if c["eta_inverse"] in refined_s]
    fbm=fit(base_matched,"rate")
    persistence=compare_refinement(base_matched,refined,margin=.10)
    assessment=assess_powerlaw(fb,fbm,fr,persistence)
    eligible = [c for c in cases if c["eligible"]]
    plt.figure(figsize=(7.2, 5.2))
    colors = {False:"#2457a6", True:"#d05a35"}
    for c in cases:
        if c["rate"] is not None:
            plt.errorbar(c["eta_inverse"], c["rate"], yerr=[[c["rate"]-c["rate_path_min"]],[c["rate_path_max"]-c["rate"]]], fmt="o", color=colors[c["family"] == "refined"], capsize=3)
    for family, f, color, label in (("base",fb,colors[False],"base-resolution fit"),("refined",fr,colors[True],"refined fit")):
        if "mean_fit_logS" in f:
            xx=np.exp(np.asarray(f["mean_fit_logS"])); yy=np.exp(np.asarray(f["mean_fit_logR"]))
            band=np.exp(np.asarray(f["mean_fit_ci95_logR"]))
            plt.plot(xx, yy, color=color, lw=1.7, label=f"{label}: p={f['p']:.3f} [{f['ci95'][0]:.3f}, {f['ci95'][1]:.3f}]")
            plt.fill_between(xx, band[0], band[1], color=color, alpha=.14)
    plt.xscale("log"); plt.yscale("log")
    plt.xlabel(r"nominal $S_\eta=1/\eta$ (not dimensional Lundquist number)")
    plt.ylabel(r"$R=(d\Psi/dt)/(B_{up}^2/\sqrt{\rho_{up}})$")
    plt.title("Fresh recorded island-coalescence rates; bars show flux-path spread")
    plt.legend(fontsize=8)
    plt.grid(True, which="both", alpha=.25); plt.tight_layout()
    scaling_path = outdir/"scaling_uncertainty.png"; plt.savefig(scaling_path, dpi=180); plt.close()
    fig,ax=plt.subplots(figsize=(7.2,4.8),constrained_layout=True)
    for label,f,color,marker in (("base matched",fbm,colors[False],"o"),("refined",fr,colors[True],"s")):
        for row in f.get("point_residuals",[]):
            lo,hi=row["residual_interval_log"]
            ax.errorbar(row["S_eta"],row["log_residual"],
                        yerr=[[max(0.0,row["log_residual"]-lo)],[max(0.0,hi-row["log_residual"])]],
                        fmt=marker,color=color,capsize=3,
                        label=label if row==f.get("point_residuals",[])[0] else None)
    threshold=math.log(1.25)
    ax.axhline(0,color="black",lw=.8);ax.axhline(threshold,color="gray",ls="--");ax.axhline(-threshold,color="gray",ls="--")
    ax.set_xscale("log");ax.set_xlabel(r"nominal $S_\eta=1/\eta$");ax.set_ylabel("log-rate residual after fitted power law")
    ax.set_title("Branch residuals; dashed lines mark the 25% departure rule")
    ax.grid(True,which="both",alpha=.25);ax.legend(fontsize=8)
    branch_path=outdir/"branch_residuals.png";fig.savefig(branch_path,dpi=180);plt.close(fig)
    field_figures=[]
    for c in cases:
        fig = draw_field(c, outdir)
        if fig: field_figures.append(fig)
    result = {"protocol": {"flux_window": [0.01,0.05], "observable": "fixed-window mean normalized flux-transfer rate",
              "fit": "OLS(log R, log S_eta), two-sided 95% Student-t intervals; enumerate every per-case low/high rate-envelope combination (2^n fits) and take the full slope/CI envelope",
              "allowed_p": [-0.60,-0.40], "resolution_rule": "at least 4 cells per nominal delta_SP/L=S_eta^-1/2 and measured central-sheet |Jz| FWHM at least 4 cells; each matched refinement is 1.25x N and adds at least one nominal-width cell",
              "eligibility": "both flux paths must produce finite positive full-window rates at full and decimated cadence; all numeric/conservation/floor checks pass; common-gauge A_z path mismatch<=0.15; resolved; and no detected secondary A_z extrema of full-domain prominence>=0.005 in |x|=[0.04,0.22]",
              "branch_rule": "form the fitted residual interval from each case's asymmetric rate bounds; departure requires its entire interval to lie beyond +/-ln(1.25). Robust claim falsification requires the same matched S_eta departure in both grids",
              "persistence_rule": "compare refined slope with the base fit on the identical refined S_eta subset; conservative difference interval must lie wholly within +/-0.10 to establish finite-sample persistence, wholly outside to indicate incompatibility, otherwise inconclusive",
              "decision": "a band violation is decisive only when matched base and refined conservative 95% intervals are disjoint from the allowed band on the same side; overlapping intervals are not rejection. Refinement incompatibility is numerical sensitivity, not a physical falsifier. No finite set proves a continuous-domain or universal claim."},
              "n_cases": len(cases), "n_eligible": len(eligible), "cases": [{k:v for k,v in c.items() if k!="raw"} for c in cases],
              "base_fit": fb, "base_matched_fit":fbm,"refined_fit": fr,"refinement_persistence":persistence,
              "assessment":assessment,
              "conservation_and_floor_rules":{"max_relative_mass_drift":1e-8,"max_relative_total_energy_drift":1e-4,
              "minimum_saved_density_and_pressure":1e-10,"per_step_correction_counters_available":False,
              "limit":"Native budget tracks mass/total energy; archived runtime exposes no per-step floor/E_modification counters. Saved minima and dat drift do not exclude intermediate corrections."},
              "figures": {"scaling": str(scaling_path),"branch_residuals":str(branch_path), "fields_current": field_figures}}
    Path(a.output).write_text(json.dumps(result, indent=2, allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("n_cases","n_eligible","base_fit","base_matched_fit","refined_fit","refinement_persistence","assessment")}, indent=2))

if __name__ == "__main__": main()
