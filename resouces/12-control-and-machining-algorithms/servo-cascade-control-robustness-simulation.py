#!/usr/bin/env python3
"""Synthetic cascaded-servo design and robustness study.
Python 3.10+, NumPy only. All parameters and results are synthetic teaching
examples, not measurements, drive settings, acceptance limits, or safety proof.
"""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass(frozen=True)
class Plant:
    name: str
    description: str
    inertia: tuple[float, ...]
    viscous: tuple[float, ...]
    stiffness: tuple[float, ...]
    shaft_damping: tuple[float, ...]
    coulomb: tuple[float, ...]

PLANTS = (
    Plant("nominal_cold", "Nominal two-inertia, cold-state reference", (0.010, 0.020), (0.006, 0.014), (1400.0,), (0.35,), (0.012, 0.018)),
    Plant("heavy_load_cold", "Higher load inertia, cold state", (0.010, 0.032), (0.006, 0.018), (1400.0,), (0.42,), (0.012, 0.020)),
    Plant("heavy_load_hot", "Higher load inertia, illustrative hot-state stiffness/damping drift", (0.010, 0.032), (0.008, 0.025), (1260.0,), (0.39,), (0.014, 0.022)),
    Plant("three_mode_reference", "Three-inertia reference with two flexible couplings", (0.010, 0.008, 0.020), (0.005, 0.007, 0.013), (1200.0, 850.0), (0.35, 0.28), (0.010, 0.012, 0.018)),
)

TS = 0.0005
TAU_CURRENT = 0.001
TORQUE_LIMIT = 1.0
VELOCITY_LIMIT = 1.5
SIMULATION_SECONDS = 1.5
STEP_TIME = 0.05
LOAD_DISTURBANCE = 0.25
DISTURBANCE_START = 0.40
DISTURBANCE_END = 0.70
ANTI_WINDUP_TAW = 0.030
FREQUENCY_RAD_S = np.logspace(-1, 4.2, 12000)

@dataclass(frozen=True)
class Controller:
    name: str
    speed_bandwidth_hz: float
    speed_integral_zero_hz: float
    position_bandwidth_hz: float
    kp_speed: float
    ki_speed: float
    kp_position: float

def controller_design(name: str, speed_bw: float, speed_zero: float, position_bw: float) -> Controller:
    jm, jl = PLANTS[0].inertia
    jeq = jm * jl / (jm + jl)
    kp_v = jeq * 2.0 * np.pi * speed_bw
    ki_v = kp_v * 2.0 * np.pi * speed_zero
    kp_p = 2.0 * np.pi * position_bw
    return Controller(name, speed_bw, speed_zero, position_bw, kp_v, ki_v, kp_p)

CONTROLLERS = (
    controller_design("aggressive_reference", 16.0, 6.0, 2.5),
    controller_design("conservative_candidate", 12.0, 4.0, 1.5),
)

def state_space(plant: Plant):
    n = len(plant.inertia)
    a = np.zeros((2*n, 2*n), dtype=float)
    b = np.zeros(2*n, dtype=float)
    for i in range(n):
        a[2*i, 2*i+1] = 1.0
        a[2*i+1, 2*i+1] -= plant.viscous[i] / plant.inertia[i]
        if i == 0:
            b[2*i+1] = 1.0 / plant.inertia[i]
        if i < n-1:
            k, c, j = plant.stiffness[i], plant.shaft_damping[i], i+1
            a[2*i+1, 2*i] -= k / plant.inertia[i]
            a[2*i+1, 2*i+1] -= c / plant.inertia[i]
            a[2*i+1, 2*j] += k / plant.inertia[i]
            a[2*i+1, 2*j+1] += c / plant.inertia[i]
            a[2*j+1, 2*i] += k / plant.inertia[j]
            a[2*j+1, 2*i+1] += c / plant.inertia[j]
            a[2*j+1, 2*j] -= k / plant.inertia[j]
            a[2*j+1, 2*j+1] -= c / plant.inertia[j]
    c_speed = np.zeros(2*n)
    c_speed[1] = 1.0
    c_position = np.zeros(2*n)
    c_position[-2] = 1.0
    return a, b, c_speed, c_position

def loop_frequency_response(plant: Plant, controller: Controller, delay_samples: int):
    a, b, c_speed, c_position = state_space(plant)
    identity = np.eye(a.shape[0])
    w = FREQUENCY_RAD_S
    gm = np.empty(len(w), dtype=complex)
    gl = np.empty(len(w), dtype=complex)
    for index, omega in enumerate(w):
        state = np.linalg.solve(1j*omega*identity-a, b)
        gm[index] = c_speed @ state
        gl[index] = c_position @ state
    # Integer feedback delay + half-sample ZOH phase approximation; not exact DT.
    equivalent_delay = (delay_samples + 0.5) * TS
    actuator = np.exp(-1j*w*equivalent_delay) / (1.0 + 1j*w*TAU_CURRENT)
    cv = controller.kp_speed + controller.ki_speed/(1j*w)
    open_speed = cv * actuator * gm
    closed_speed_to_load_position = cv * actuator * gl / (1.0 + open_speed)
    open_position = controller.kp_position * closed_speed_to_load_position
    return w, open_speed, open_position

def crossings(w, values, target):
    indices = np.where((values[:-1]-target)*(values[1:]-target) <= 0.0)[0]
    result = []
    for i in indices:
        x1,x2 = np.log(w[i]),np.log(w[i+1])
        y1,y2 = values[i],values[i+1]
        result.append(float(w[i]) if y2 == y1 else float(np.exp(x1+(target-y1)*(x2-x1)/(y2-y1))))
    return result

def margin_summary(w, loop):
    magnitude_db = 20.0*np.log10(np.maximum(np.abs(loop),1e-300))
    phase_deg = np.unwrap(np.angle(loop))*180.0/np.pi
    gain_cross = crossings(w,magnitude_db,0.0)
    k_min = int(np.floor((-float(np.max(phase_deg))-180.0)/360.0))-1
    k_max = int(np.ceil((-float(np.min(phase_deg))-180.0)/360.0))+1
    phase_cross = []
    for k in range(k_min,k_max+1):
        phase_cross.extend(crossings(w,phase_deg,-180.0-360.0*k))
    pm_values = []
    for wc in gain_cross:
        phase = float(np.interp(np.log(wc),np.log(w),phase_deg))
        pm_values.append((180.0+phase,wc))
    gm_values = []
    for wc in phase_cross:
        mag = float(np.interp(np.log(wc),np.log(w),magnitude_db))
        gm_values.append((-mag,wc))
    pm = min(pm_values,key=lambda x:abs(x[0])) if pm_values else (float("nan"),float("nan"))
    gm = min(gm_values,key=lambda x:abs(x[0])) if gm_values else (float("nan"),float("nan"))
    return {
        "pm_deg":pm[0],"pm_crossover_hz":pm[1]/(2*np.pi),
        "gm_db":gm[0],"gm_phase_crossover_hz":gm[1]/(2*np.pi),
        "gain_crossovers_hz":";".join(f"{v/(2*np.pi):.6g}" for v in gain_cross),
        "phase_crossovers_hz":";".join(f"{v/(2*np.pi):.6g}" for v in phase_cross),
        "gain_crossover_count":len(gain_cross),"phase_crossover_count":len(phase_cross)
    }

def closed_loop_poles(plant: Plant, controller: Controller):
    a,b,c_speed,c_position = state_space(plant)
    n = a.shape[0]
    aug = np.zeros((n+2,n+2))
    aug[:n,:n] = a
    aug[:n,n] = b
    aug[n,:n] = -(controller.kp_speed/TAU_CURRENT)*c_speed - (controller.kp_speed*controller.kp_position/TAU_CURRENT)*c_position
    aug[n,n] = -1.0/TAU_CURRENT
    aug[n,n+1] = controller.ki_speed/TAU_CURRENT
    aug[n+1,:n] = -c_speed-controller.kp_position*c_position
    poles = np.linalg.eigvals(aug)
    order = np.argsort(poles.real)[::-1]
    return float(np.max(poles.real)), ";".join(f"{poles[i].real:.6g}{poles[i].imag:+.6g}j" for i in order[:min(4,len(order))])

def nonlinear_derivative(z, t, command, plant):
    n = len(plant.inertia)
    q = z[:2*n]
    torque_state = z[-1]
    theta, omega = q[0::2],q[1::2]
    net = -np.asarray(plant.viscous)*omega - np.asarray(plant.coulomb)*np.tanh(omega/0.01)
    net[0] += float(np.clip(torque_state,-TORQUE_LIMIT,TORQUE_LIMIT))
    for j in range(n-1):
        shaft_torque = plant.stiffness[j]*(theta[j+1]-theta[j]) + plant.shaft_damping[j]*(omega[j+1]-omega[j])
        net[j] += shaft_torque
        net[j+1] -= shaft_torque
    if DISTURBANCE_START <= t < DISTURBANCE_END:
        net[-1] -= LOAD_DISTURBANCE
    dz = np.zeros(2*n+1)
    dz[0:2*n:2] = omega
    dz[1:2*n:2] = net/np.asarray(plant.inertia)
    dz[-1] = (command-torque_state)/TAU_CURRENT
    return dz

def simulate_step(plant, controller, delay_samples, step_rad):
    n = len(plant.inertia)
    samples = int(SIMULATION_SECONDS/TS)
    substeps = 4
    h = TS/substeps
    state = np.zeros(2*n+1)
    integrator = 0.0
    feedback = [(0.0,0.0)]*(delay_samples+1)
    commands = np.zeros(samples)
    actual = np.zeros(samples)
    position = np.zeros(samples)
    saturation = np.zeros(samples,dtype=bool)
    max_twist = np.zeros(samples)
    for k in range(samples):
        t = k*TS
        feedback.append((state[-3],state[1]))
        theta_delayed, speed_delayed = feedback.pop(0)
        reference = step_rad if t >= STEP_TIME else 0.0
        velocity_ref = float(np.clip(controller.kp_position*(reference-theta_delayed),-VELOCITY_LIMIT,VELOCITY_LIMIT))
        error = velocity_ref-speed_delayed
        raw = controller.kp_speed*error+integrator
        command = float(np.clip(raw,-TORQUE_LIMIT,TORQUE_LIMIT))
        integrator += (controller.ki_speed*error+(command-raw)/ANTI_WINDUP_TAW)*TS
        commands[k] = command
        saturation[k] = abs(raw)>TORQUE_LIMIT
        for sub in range(substeps):
            ts = t+sub*h
            k1 = nonlinear_derivative(state,ts,command,plant)
            k2 = nonlinear_derivative(state+0.5*h*k1,ts+0.5*h,command,plant)
            k3 = nonlinear_derivative(state+0.5*h*k2,ts+0.5*h,command,plant)
            k4 = nonlinear_derivative(state+h*k3,ts+h,command,plant)
            state += h*(k1+2*k2+2*k3+k4)/6.0
        position[k] = state[-3]
        actual[k] = state[-1]
        angles = state[:2*n:2]
        max_twist[k] = float(np.max(np.abs(np.diff(angles)))) if n>1 else 0.0
    times = np.arange(samples)*TS
    active = np.where(times>=STEP_TIME)[0]
    error = step_rad-position[active]
    overshoot = max(0.0,(float(np.max(position[active]))-step_rad)/abs(step_rad)*100.0)
    tolerance = max(abs(step_rad)*0.02,1e-5)
    settling = float("nan")
    for idx in active:
        if np.all(np.abs(position[idx:]-step_rad)<=tolerance):
            settling = float(times[idx]-STEP_TIME)
            break
    return {
        "plant":plant.name,"controller":controller.name,"step_rad":step_rad,
        "feedback_delay_ms":delay_samples*TS*1000.0,"overshoot_pct":overshoot,
        "settling_time_s":settling,"rmse_rad":float(np.sqrt(np.mean(error**2))),
        "saturation_fraction_pct":float(np.mean(saturation[active])*100.0),
        "peak_command_nm":float(np.max(np.abs(commands))),
        "peak_actual_torque_nm":float(np.max(np.abs(actual))),
        "max_coupling_twist_rad":float(np.max(max_twist)),
        "final_position_error_rad":float(step_rad-position[-1])
    }

def write_csv(path: Path, rows):
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    margin_rows = []
    for plant in PLANTS:
        pole_by_controller = {}
        for controller in CONTROLLERS:
            max_real,pole_text = closed_loop_poles(plant,controller)
            pole_by_controller[controller.name] = (max_real,pole_text)
            for delay_samples in (0,1,2):
                w,open_speed,open_position = loop_frequency_response(plant,controller,delay_samples)
                sm,pm = margin_summary(w,open_speed),margin_summary(w,open_position)
                margin_rows.append({
                    "plant":plant.name,"controller":controller.name,
                    "speed_bandwidth_setting_hz":controller.speed_bandwidth_hz,
                    "speed_integral_zero_hz":controller.speed_integral_zero_hz,
                    "position_bandwidth_setting_hz":controller.position_bandwidth_hz,
                    "kp_speed_nm_s_rad":controller.kp_speed,"ki_speed_nm_rad":controller.ki_speed,
                    "kp_position_per_s":controller.kp_position,"sample_time_ms":TS*1000.0,
                    "feedback_delay_ms":delay_samples*TS*1000.0,"current_actuator_tau_ms":TAU_CURRENT*1000.0,
                    "speed_pm_deg":sm["pm_deg"],"speed_pm_crossover_hz":sm["pm_crossover_hz"],
                    "speed_gm_db":sm["gm_db"],"speed_gm_phase_crossover_hz":sm["gm_phase_crossover_hz"],
                    "speed_gain_crossover_count":sm["gain_crossover_count"],
                    "speed_phase_crossover_count":sm["phase_crossover_count"],
                    "speed_gain_crossovers_hz":sm["gain_crossovers_hz"],
                    "speed_phase_crossovers_hz":sm["phase_crossovers_hz"],
                    "position_pm_deg":pm["pm_deg"],"position_pm_crossover_hz":pm["pm_crossover_hz"],
                    "position_gm_db":pm["gm_db"],"position_gm_phase_crossover_hz":pm["gm_phase_crossover_hz"],
                    "position_gain_crossover_count":pm["gain_crossover_count"],
                    "position_phase_crossover_count":pm["phase_crossover_count"],
                    "position_gain_crossovers_hz":pm["gain_crossovers_hz"],
                    "position_phase_crossovers_hz":pm["phase_crossovers_hz"],
                    "max_closed_loop_pole_real_1_s_delay_omitted":pole_by_controller[controller.name][0],
                    "dominant_poles_delay_omitted":pole_by_controller[controller.name][1],
                    "classification":"synthetic SISO nested-loop linearization; equivalent delay approximation; not MIMO/disk-margin or machine data"
                })
    write_csv(args.output_dir/"servo-cascade-loop-margins-synthetic.csv",margin_rows)
    time_rows = []
    candidate = CONTROLLERS[1]
    for plant in PLANTS:
        for step_rad in (0.12,0.25):
            for delay_samples in (0,1,2):
                time_rows.append(simulate_step(plant,candidate,delay_samples,step_rad))
    write_csv(args.output_dir/"servo-cascade-step-response-synthetic.csv",time_rows)
    config = {
        "classification":"synthetic_simulation_not_machine_measurement","python":"3.10+","dependencies":{"numpy":"runtime"},
        "simulation":{"sample_time_s":TS,"current_actuator_time_constant_s":TAU_CURRENT,
            "feedback_delay_samples":[0,1,2],"total_simulation_s":SIMULATION_SECONDS,"rk4_substeps_per_sample":4,
            "torque_limit_nm":TORQUE_LIMIT,"velocity_reference_limit_rad_s":VELOCITY_LIMIT,
            "load_disturbance_nm":LOAD_DISTURBANCE,"disturbance_interval_s":[DISTURBANCE_START,DISTURBANCE_END],
            "step_time_s":STEP_TIME,"step_amplitudes_rad":[0.12,0.25],
            "anti_windup":"discrete back-calculation; tracking time constant 30 ms"},
        "current_actuator":"first-order torque/current closed-loop approximation; no inverter/PMSM electrical switching model",
        "feedback":"load-side position feedback and motor-side speed feedback; delayed by integer controller samples",
        "controller_designs":[{"name":c.name,"speed_bandwidth_setting_hz":c.speed_bandwidth_hz,
            "speed_integral_zero_hz":c.speed_integral_zero_hz,"position_bandwidth_setting_hz":c.position_bandwidth_hz,
            "kp_speed_nm_s_rad":c.kp_speed,"ki_speed_nm_rad":c.ki_speed,"kp_position_per_s":c.kp_position} for c in CONTROLLERS],
        "plant_conditions":[{"name":p.name,"description":p.description,"inertia_kg_m2":p.inertia,
            "viscous_nm_s_rad":p.viscous,"shaft_stiffness_nm_rad":p.stiffness,
            "shaft_damping_nm_s_rad":p.shaft_damping,"coulomb_nm":p.coulomb} for p in PLANTS],
        "linear_margin_method":"SISO motor-speed inner loop and nested load-position outer loop; exact flexible plant FRF; first-order actuator lag; pure-delay equivalent (feedback delay + half sample); all detected gain/phase crossovers retained; Coulomb friction and saturation excluded from linear margins",
        "closed_loop_poles":"continuous augmented linearization around zero speed, no sample/compute delay, no Coulomb friction and no saturation; only a local linear check",
        "nonlinear_simulation":"sampled controller with integer feedback delay, torque saturation, back-calculation anti-windup, Coulomb friction, flexible coupling, and a load torque disturbance",
        "limitations":[
            "All inertias, damping, stiffness, friction, torque/velocity limits and disturbances are synthetic assumptions, not OEM or machine data",
            "Two-mass and three-mass systems are lumped SISO examples; no multiaxis/MIMO coupling, encoder quantization, current ripple, bus jitter or thermal dynamics model",
            "The hot-state change is a prescribed parameter variant, not a measured thermal law",
            "Equivalent delay frequency response is approximate; use exact discrete-time/internal-delay models for design sign-off",
            "GM/PM values are classical SISO loop margins, not disk margins or robust-stability proof",
            "Time-domain saturation response does not prove stability for all inputs or machine safety"]
    }
    (args.output_dir/"servo-cascade-control-simulation-config.json").write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {len(margin_rows)} loop-margin rows and {len(time_rows)} time-response rows to {args.output_dir}")

if __name__ == "__main__":
    main()
