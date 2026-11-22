#!/usr/bin/env python3
"""Synthetic two-drive gantry MIMO servo study.

Requires Python 3.10+, NumPy and SciPy. All parameters are illustrative;
no values are measured CNC equipment data.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

I2 = np.eye(2)
Z2 = np.zeros((2, 2))
L = np.array([[1.0, -1.0], [-1.0, 1.0]])
SAMPLE_HZ = [1, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300]
COUPLING_N_M = [0.0, 200_000.0, 500_000.0, 800_000.0, 1_200_000.0]


def controller_gains():
    masses = np.array([20.0, 25.0])
    viscous = np.array([600.0, 680.0])
    wn = 2.0 * np.pi * 20.0
    zeta = 0.90
    kp = masses * wn**2
    kd = np.maximum(2.0 * zeta * masses * wn - viscous, 0.0)
    wf = 2.0 * np.pi * 250.0
    return kp, kd, wf


def plant(load_case, kc):
    if load_case == "nominal":
        mass = np.array([20.0, 25.0])
        visc = np.array([600.0, 680.0])
    elif load_case == "asymmetric_load":
        mass = np.array([30.0, 22.0])
        visc = np.array([720.0, 650.0])
    else:
        raise ValueError(f"unknown load case: {load_case}")
    mr = mass[0] * mass[1] / np.sum(mass)
    cc = 2.0 * 0.08 * np.sqrt(max(kc, 0.0) * mr)
    M = np.diag(mass)
    K = kc * L
    D = np.diag(visc) + cc * L
    return mass, M, D, K, cc


def state_matrix(M, D, K, kp, kd, wf, sync_kp=0.0, sync_kd=0.0):
    Minv = np.linalg.inv(M)
    Kc = np.diag(kp) + sync_kp * L
    Dc = np.diag(kd) + sync_kd * L
    # State [xL,xR,vL,vR,zL,zR], with zdot=wf*(x-z).
    # Filtered derivative feedback is wf*(x-z); reference derivative is omitted.
    return np.block([
        [Z2, I2, Z2],
        [-Minv @ (K + Kc + wf * Dc), -Minv @ D, Minv @ (wf * Dc)],
        [wf * I2, Z2, -wf * I2],
    ])


def step(A, M, kp, refs, duration=0.4, samples=401):
    B = np.vstack([Z2, np.linalg.inv(M) @ np.diag(kp), Z2])
    forcing = B @ np.asarray(refs, dtype=float)
    t = np.linspace(0.0, duration, samples)
    sol = solve_ivp(
        lambda _t, x: A @ x + forcing, (0.0, duration), np.zeros(6),
        t_eval=t, rtol=1e-8, atol=1e-11,
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    return t, sol.y[:2]


def Cjw(f, kp, kd, wf, sync_kp=0.0, sync_kd=0.0):
    s = 1j * 2.0 * np.pi * f
    deriv = wf * s / (s + wf)
    return np.diag(kp + kd * deriv) + (sync_kp + sync_kd * deriv) * L


def frequency_metrics(M, D, K, kp, kd, wf, sync_kp=0.0, sync_kd=0.0):
    min_sig, min_freq = np.inf, np.nan
    peak_s, peak_cross, peak_cross_f = 0.0, 0.0, np.nan
    for f in np.logspace(np.log10(0.2), np.log10(500.0), 1400):
        s = 1j * 2.0 * np.pi * f
        P = np.linalg.inv(M * s**2 + D * s + K)
        loop = P @ Cjw(f, kp, kd, wf, sync_kp, sync_kd)
        R = I2 + loop
        sv = np.linalg.svd(R, compute_uv=False)
        if sv[-1] < min_sig:
            min_sig, min_freq = float(sv[-1]), float(f)
        S = np.linalg.inv(R)
        peak_s = max(peak_s, float(np.linalg.svd(S, compute_uv=False)[0]))
        T = S @ loop
        cross = max(
            abs(T[1, 0]) / max(abs(T[0, 0]), 1e-15),
            abs(T[0, 1]) / max(abs(T[1, 1]), 1e-15),
        )
        if cross > peak_cross:
            peak_cross, peak_cross_f = float(cross), float(f)

    samples = []
    for f in SAMPLE_HZ:
        s = 1j * 2.0 * np.pi * f
        P = np.linalg.inv(M * s**2 + D * s + K)
        loop = P @ Cjw(f, kp, kd, wf, sync_kp, sync_kd)
        R = I2 + loop
        S = np.linalg.inv(R)
        T = S @ loop
        sv = np.linalg.svd(R, compute_uv=False)
        samples.append({
            "frequency_hz": f,
            "sigma_min_I_plus_L": float(sv[-1]),
            "sigma_max_S": float(np.linalg.svd(S, compute_uv=False)[0]),
            "T_left_from_right_abs": float(abs(T[0, 1])),
            "T_right_from_left_abs": float(abs(T[1, 0])),
        })
    return {
        "min_sigma_I_plus_L": min_sig,
        "frequency_min_sigma_hz": min_freq,
        "peak_sigma_S": peak_s,
        "peak_cross_axis_ratio": peak_cross,
        "frequency_peak_cross_ratio_hz": peak_cross_f,
        "frequency_samples": samples,
    }


def poles(A):
    p = np.linalg.eigvals(A)
    remax = float(np.max(p.real))
    cp = [x for x in p if x.imag > 1e-6]
    zeta = [-x.real / abs(x) for x in cp]
    return {
        "max_real_pole_rad_s": remax,
        "stable_by_poles": bool(remax < 0.0),
        "min_complex_pole_damping_ratio": float(np.min(zeta)) if zeta else None,
    }


def summarize(load_case, kc):
    mass, M, D, K, cc = plant(load_case, kc)
    kp, kd, wf = controller_gains()
    A = state_matrix(M, D, K, kp, kd, wf)
    pole = poles(A)
    freq = frequency_metrics(M, D, K, kp, kd, wf)
    _, common = step(A, M, kp, [1e-3, 1e-3])
    _, one = step(A, M, kp, [1e-3, 0.0])
    fmode = np.sqrt(max(kc * (1.0 / mass[0] + 1.0 / mass[1]), 0.0)) / (2.0 * np.pi)
    return {
        "load_case": load_case,
        "mass_left_kg": mass[0],
        "mass_right_kg": mass[1],
        "coupling_stiffness_n_m": kc,
        "coupling_damping_n_s_m": cc,
        "flexible_differential_mode_hz": fmode,
        "peak_common_move_sync_error_um": float(np.max(np.abs(common[0] - common[1])) * 1e6),
        "peak_other_drive_motion_percent_of_single_drive_step": float(np.max(np.abs(one[1])) / 1e-3 * 100.0),
        "controller_kp_left_n_m": kp[0],
        "controller_kp_right_n_m": kp[1],
        "controller_kd_left_n_s_m": kd[0],
        "controller_kd_right_n_s_m": kd[1],
        **pole,
        **{k: v for k, v in freq.items() if k != "frequency_samples"},
        "frequency_samples": freq["frequency_samples"],
    }


def compare_sync():
    load_case, kc = "asymmetric_load", 500_000.0
    _, M, D, K, _ = plant(load_case, kc)
    kp, kd, wf = controller_gains()
    candidates = [
        ("decentralized_PD", 0.0, 0.0),
        ("sync_P_500k", 500_000.0, 0.0),
        ("sync_PD_500k_1500", 500_000.0, 1500.0),
        ("sync_PD_500k_3000", 500_000.0, 3000.0),
    ]
    rows = []
    for name, skp, skd in candidates:
        A = state_matrix(M, D, K, kp, kd, wf, skp, skd)
        pp = poles(A)
        ff = frequency_metrics(M, D, K, kp, kd, wf, skp, skd)
        _, pos = step(A, M, kp, [1e-3, 1e-3])
        rows.append({
            "controller": name,
            "load_case": load_case,
            "coupling_stiffness_n_m": kc,
            "sync_kp_n_m": skp,
            "sync_kd_n_s_m": skd,
            "peak_common_move_sync_error_um": float(np.max(np.abs(pos[0] - pos[1])) * 1e6),
            **pp,
            **{k: v for k, v in ff.items() if k != "frequency_samples"},
        })
    return rows


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="./generated")
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary, frf = [], []
    for load in ["nominal", "asymmetric_load"]:
        for kc in COUPLING_N_M:
            result = summarize(load, kc)
            summary.append({k: v for k, v in result.items() if k != "frequency_samples"})
            for row in result["frequency_samples"]:
                frf.append({"load_case": load, **row})
    comp = compare_sync()
    write_csv(out / "gantry-mimo-coupling-envelope.csv", summary)
    write_csv(out / "gantry-mimo-frequency-response-samples.csv", frf)
    write_csv(out / "gantry-mimo-sync-controller-comparison.csv", comp)
    print(f"Wrote {len(summary)} coupling cases and {len(frf)} frequency samples")
    for row in summary:
        print(row["load_case"], f"kc={row['coupling_stiffness_n_m']:.0f}",
              f"f_diff={row['flexible_differential_mode_hz']:.2f}Hz",
              f"sync_peak={row['peak_common_move_sync_error_um']:.2f}um",
              f"cross={row['peak_cross_axis_ratio']:.3f}",
              f"min_sigma={row['min_sigma_I_plus_L']:.3f}",
              f"stable={row['stable_by_poles']}")
    print("Cross-coupled controller comparison:")
    for row in comp:
        print(row["controller"], f"sync_peak={row['peak_common_move_sync_error_um']:.2f}um",
              f"min_sigma={row['min_sigma_I_plus_L']:.3f}",
              f"peak_S={row['peak_sigma_S']:.3f}",
              f"zeta_min={row['min_complex_pole_damping_ratio']:.3f}")


if __name__ == "__main__":
    main()
