#!/usr/bin/env python3
"""Synthetic prescribed moving-payload gantry model and optional MIMO disk-margin estimates.

Python 3.10+, NumPy and SciPy are required.  Optional MIMO multiloop estimates
require python-control==0.10.2 and Slycot (AB13MD).  All plant values are
illustrative assumptions, not CNC machine specifications.
"""
from __future__ import annotations
import argparse, csv, importlib.util, math
from pathlib import Path
import numpy as np
from scipy.linalg import eigvalsh
from scipy.signal import cont2discrete

TS=1e-3; L=1.60; T_MOVE=2.0; T_END=2.5
MASS_SET=(5.0,15.0,30.0)
CONTROLLERS=(("independent_PD",0.0,0.0),("synchronization_medium_PD",20000.0,200.0))
I2=np.eye(2); LD=np.array([[1.0,-1.0],[-1.0,1.0]])
EZ=np.array([0.0,0.0,1.0]); G=9.80665
M0=np.diag([75.0,12.0,9.0,2.0])
K0=np.diag([0.0,12*(2*np.pi*25)**2,9*(2*np.pi*50)**2,2*(2*np.pi*72)**2])
VC=np.array([0.0,1.0,0.0,-1.0])
K0=K0+0.15*np.sqrt(K0[1,1]*K0[3,3])*np.outer(VC,VC)
D0=np.diag([1600.0,2*.035*12*2*np.pi*25,2*.020*9*2*np.pi*50,2*.025*2*2*np.pi*72])
D0=D0+0.03*np.sqrt(D0[1,1]*D0[3,3])*np.outer(VC,VC)
BF=np.array([[1.0,1.0],[-L/2,L/2],[0.0,0.0],[0.0,0.0]])
CQ=np.array([[1.0,-L/2,0.0,0.0],[1.0,L/2,0.0,0.0]])
ALPHA=float(np.exp(-2*np.pi*60*TS)); GAMMA=(1-ALPHA)/TS
KP=50000.0; KD=2500.0

def phi(s):
    k=np.pi/L
    return np.sin(k*s), k*np.cos(k*s), -(k*k)*np.sin(k*s)

def kin(q,s):
    p,dp,ddp=phi(s); ht=.12; et=.18; a=s-L/2
    P=np.array([[1,a,p,ht*p],[0,0,0,0],[0,0,0,et*p]],float)
    Ps=np.array([[0,1,dp,ht*dp],[0,0,0,0],[0,0,0,et*dp]],float)
    Pss=np.array([[0,0,ddp,ht*ddp],[0,0,0,0],[0,0,0,et*ddp]],float)
    r=np.array([q[0]+a*q[1]+p*q[2]+ht*p*q[3],s,et*p*q[3]])
    rs=np.array([q[1]+dp*q[2]+ht*dp*q[3],1.0,et*dp*q[3]])
    rss=Pss@q
    return r,P,Ps,rs,rss

def traj(t):
    tau=min(max(t/T_MOVE,0.0),1.0)
    d=.8*L
    b=10*tau**3-15*tau**4+6*tau**5
    bd=30*tau**2-60*tau**3+30*tau**4
    bdd=60*tau-180*tau**2+120*tau**3
    if t>=T_MOVE: bd=bdd=0.0
    return .1*L+d*b,d*bd/T_MOVE,d*bdd/T_MOVE**2

def terms(q,s,sd,sdd,m):
    _,P,Ps,rs,rss=kin(q,s)
    M=M0+m*P.T@P
    Md=m*(Ps.T@P+P.T@Ps)*sd
    cv=2*m*(P.T@Ps)*sd
    ca=m*P.T@(rss*sd**2+rs*sdd)
    fg=-m*G*(P.T@EZ)
    Mf=np.block([[M,m*(P.T@rs).reshape(4,1)],[m*(rs.reshape(1,3)@P),np.array([[m*float(rs@rs)]])]])
    return M,Md,cv,ca,fg,Mf

def gains(skp,skd):
    return KP*I2+skp*LD,KD*I2+skd*LD

def rhs(q,v,u,t,m,mode):
    s,sd,sdd=(.1*L,0.0,0.0) if mode=="frozen_initial" else traj(t)
    M,Md,cv,ca,fg,_=terms(q,s,sd,sdd,m)
    f=BF@u-D0@v-K0@q+fg
    if mode=="moving_full": f=f-cv@v-ca
    elif mode not in ("moving_mass_only","frozen_initial"): raise ValueError(mode)
    return v,np.linalg.solve(M,f)

def q_equilibrium(m):
    q=np.zeros(4); fg=terms(q,.1*L,0.0,0.0,m)[4]
    q=np.linalg.lstsq(K0,fg,rcond=None)[0]; q[0]=1e-3
    return q

def rk4(q,v,u,t,m,mode):
    f=lambda x,y,z:rhs(x,y,u,z,m,mode)
    k1x,k1v=f(q,v,t); k2x,k2v=f(q+.5*TS*k1x,v+.5*TS*k1v,t+.5*TS)
    k3x,k3v=f(q+.5*TS*k2x,v+.5*TS*k2v,t+.5*TS)
    k4x,k4v=f(q+TS*k3x,v+TS*k3v,t+TS)
    return q+TS*(k1x+2*k2x+2*k3x+k4x)/6,v+TS*(k1v+2*k2v+2*k3v+k4v)/6

def simulate(m,name,skp,skd,mode,keep_trace):
    gp,gd=gains(skp,skd); q=q_equilibrium(m); v=np.zeros(4)
    prev=np.zeros(2); df=np.zeros(2); ref=np.array([1e-3,1e-3]); rows=[]
    for k in range(round(T_END/TS)):
        t=k*TS; y=CQ@q; e=ref-y
        df=ALPHA*df+GAMMA*(e-prev); u=gp@e+gd@df
        q,v=rk4(q,v,u,t,m,mode); prev=e
        s,sd,sdd=traj(t+TS)
        if mode=="frozen_initial": s=.1*L; sd=sdd=0.0
        M,Md,cv,ca,_,Mf=terms(q,s,sd,sdd,m)
        p,_,_,_,_=kin(q,s)
        err=p[0]-ref[0]; skew=(CQ@q)[1]-(CQ@q)[0]
        rows.append((t+TS,s,sd,err,skew,q[2],q[3],np.linalg.norm(Md,2),
                     np.linalg.norm(cv@v),np.linalg.norm(ca),np.min(eigvalsh(M)),
                     np.min(eigvalsh(Mf)),np.max(np.abs(u))))
    a=np.asarray(rows); moving=(a[:,0]>=.1)&(a[:,0]<=1.9); dwell=a[:,0]>=2.1
    summary={
      "controller":name,"model_mode":mode,"payload_mass_kg":m,"move_duration_s":T_MOVE,
      "move_distance_m":.8*L,"max_payload_speed_m_s":float(a[:,2].max()),
      "peak_payload_point_error_um_all":float(np.max(np.abs(a[:,3]))*1e6),
      "peak_payload_point_error_um_after_100ms":float(np.max(np.abs(a[a[:,0]>=.1,3]))*1e6),
      "rms_payload_point_error_um_during_move":float(np.sqrt(np.mean(a[moving,3]**2))*1e6),
      "peak_payload_point_error_um_final_dwell":float(np.max(np.abs(a[dwell,3]))*1e6),
      "peak_sync_skew_um_during_move":float(np.max(np.abs(a[moving,4]))*1e6),
      "rms_sync_skew_um_during_move":float(np.sqrt(np.mean(a[moving,4]**2))*1e6),
      "peak_bending_coordinate_um_during_move":float(np.max(np.abs(a[moving,5]))*1e6),
      "peak_torsion_mrad_during_move":float(np.max(np.abs(a[moving,6]))*1e3),
      "peak_Mdot_matrix_2norm_numeric_under_m_rad_coordinate_units":float(np.max(a[:,7])),
      "peak_velocity_transport_generalized_term_2norm_numeric_under_m_rad_coordinate_units":float(np.max(a[:,8])),
      "peak_acceleration_transport_generalized_term_2norm_numeric_under_m_rad_coordinate_units":float(np.max(a[:,9])),
      "min_generalized_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units":float(np.min(a[:,10])),
      "min_augmented_q_s_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units":float(np.min(a[:,11])),
      "peak_command_force_N":float(np.max(a[:,12])),"trajectory_samples":len(a)}
    trace=a if keep_trace else None
    return summary,trace

def verify_equations():
    out=[]
    for m in MASS_SET:
      for s in np.linspace(.1*L,.9*L,41):
        q=np.array([1e-4,1e-4,2e-5,1e-3]); sd=.75; eps=1e-6
        Mp=terms(q,s+eps*sd,sd,0,m)[0]; Mm=terms(q,s-eps*sd,sd,0,m)[0]
        Md=terms(q,s,sd,0,m)[1]; errM=np.linalg.norm((Mp-Mm)/(2*eps)-Md)/max(1,np.linalg.norm(Md))
        v=np.array([.012,-.004,.003,.0005]); acc=np.array([.08,.025,-.04,.006]); sdd=-.12; h=2e-5
        r,P,Ps,rs,rss=kin(q,s); aa=P@acc+2*Ps@v*sd+rss*sd**2+rs*sdd
        qp=q+v*h+.5*acc*h*h; qm=q-v*h+.5*acc*h*h
        sp=s+sd*h+.5*sdd*h*h; sm=s-sd*h+.5*sdd*h*h
        rfd=(kin(qp,sp)[0]-2*r+kin(qm,sm)[0])/h**2
        erra=np.linalg.norm(rfd-aa)/max(1,np.linalg.norm(aa))
        def mom(qx,vx,sx,sv):
            _,px,psx,rsx,_=kin(qx,sx); vl=px@vx+rsx*sv
            return m*px.T@vl,m*sv*(psx.T@vl)
        pplus,gplus=mom(q+v*h+.5*acc*h*h,v+acc*h,s+sd*h+.5*sdd*h*h,sd+sdd*h)
        pminus,gminus=mom(q-v*h+.5*acc*h*h,v-acc*h,s-sd*h+.5*sdd*h*h,sd-sdd*h)
        pd=(pplus-pminus)/(2*h)-mom(q,v,s,sd)[1]
        el=m*P.T@aa; erre=np.linalg.norm(pd-el)/max(1,np.linalg.norm(el))
        mineig=np.min(eigvalsh(terms(q,s,sd,0,m)[5]))
        out.append({"payload_mass_kg":m,"load_position_m":s,"test_speed_m_s":sd,
          "scaled_Mdot_finite_difference_discrepancy_denominator_max1":errM,
          "scaled_payload_acceleration_chain_rule_discrepancy_denominator_max1":erra,
          "scaled_q_euler_lagrange_residual_denominator_max1":erre,
          "min_augmented_q_s_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units":mineig})
    return out

def controller_ss(skp,skd):
    gp,gd=gains(skp,skd)
    A=np.block([[ALPHA*I2,-GAMMA*I2],[np.zeros((2,2)),np.zeros((2,2))]])
    B=np.vstack([GAMMA*I2,I2]); C=np.hstack([ALPHA*gd,-GAMMA*gd]); D=gp+GAMMA*gd
    return A,B,C,D

def disk_margins(out):
    if importlib.util.find_spec("control") is None or importlib.util.find_spec("slycot") is None:
        raise RuntimeError("MIMO disk-margin estimate requires python-control==0.10.2 and Slycot AB13MD; no numeric margin was computed")
    import control
    fhz=np.geomspace(.2,.499/TS,1024); omega=2*np.pi*fhz; rows=[]
    for m in MASS_SET:
      for frac in (.1,.5,.9):
        q=np.zeros(4); _,P,_,_,_=kin(q,frac*L); M=M0+m*P.T@P
        Ac=np.block([[np.zeros((4,4)),np.eye(4)],[-np.linalg.solve(M,K0),-np.linalg.solve(M,D0)]])
        Bc=np.vstack([np.zeros((4,2)),np.linalg.solve(M,BF)])
        Cc=np.hstack([CQ,np.zeros((2,4))])
        Ad,Bd,Cd,Dd,_=cont2discrete((Ac,Bc,Cc,np.zeros((2,2))),TS,method="zoh")
        plant=control.ss(Ad,Bd,Cd,Dd,dt=TS)
        for name,skp,skd in CONTROLLERS:
          A,B,C,D=controller_ss(skp,skd); ctrl=control.ss(A,B,C,D,dt=TS)
          for side,loop in (("plant_output_feedback_channels",plant*ctrl),("plant_input_actuator_channels",ctrl*plant)):
            poles=np.asarray(control.poles(control.feedback(loop,np.eye(2))))
            stable=bool(np.max(np.abs(poles))<1)
            r={"payload_mass_kg":m,"load_position_fraction":frac,"controller":name,"margin_port":side,
               "skew_sigma":0.0,"nominal_closed_loop_stable":stable,
               "max_closed_loop_pole_radius":float(np.max(np.abs(poles))),
               "frequency_grid_points":len(fhz),"frequency_min_hz":float(fhz[0]),"frequency_max_hz":float(fhz[-1]),
               "algorithm":"python-control disk_margins + Slycot AB13MD structured-mu upper bound",
               "minimum_sampled_frequency_disk_margin_estimate":None,"critical_frequency_hz":None,
               "status":"nominal_unstable_not_evaluated" if not stable else "not_evaluated"}
            if stable:
              dm,gm,pm=control.disk_margins(loop,omega,skew=0.0,returnall=True)
              ix=int(np.argmin(dm))
              r.update({"minimum_sampled_frequency_disk_margin_estimate":float(np.min(dm)),
                        "critical_frequency_hz":float(fhz[ix]),
                        "status":"sampled_slycot_mu_upper_bound_reciprocal_not_global_certificate"})
            rows.append(r)
    write_csv(out/"gantry-mimo-multiloop-disk-margin.csv",rows)

def write_csv(path,rows):
    if rows:
      with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir",default=str(Path(__file__).resolve().parent/"generated-moving-load"))
    ap.add_argument("--include-timeseries",action="store_true",help="write 7,500-row selected-case trace")
    ap.add_argument("--disk-margin",action="store_true",help="optional sampled MIMO multiloop disk-margin estimates")
    args=ap.parse_args(); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    summaries=[]; traces=[]
    for name,skp,skd in CONTROLLERS:
      for m in MASS_SET:
        for mode in ("moving_full","moving_mass_only","frozen_initial"):
          row,tr=simulate(m,name,skp,skd,mode,args.include_timeseries); summaries.append(row)
          if tr is not None and m==15.0 and name=="synchronization_medium_PD":
            traces.extend([[mode,*x.tolist()] for x in tr])
    write_csv(out/"gantry-moving-load-model-comparison.csv",summaries)
    checks=verify_equations(); write_csv(out/"gantry-moving-load-equation-checks.csv",checks)
    print("cases",len(summaries),"equation_checks",len(checks))
    print("max_Mdot_FD_error",max(r["scaled_Mdot_finite_difference_discrepancy_denominator_max1"] for r in checks))
    print("max_acceleration_chain_rule_error",max(r["scaled_payload_acceleration_chain_rule_discrepancy_denominator_max1"] for r in checks))
    print("max_q_Euler_Lagrange_residual",max(r["scaled_q_euler_lagrange_residual_denominator_max1"] for r in checks))
    print("min_augmented_q_s_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units",min(r["min_augmented_q_s_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units"] for r in checks))
    for r in summaries:
      print(r["payload_mass_kg"],r["controller"],r["model_mode"],
        "payload_RMS_um",round(r["rms_payload_point_error_um_during_move"],3),
        "sync_peak_um",round(r["peak_sync_skew_um_during_move"],3),
        "bend_peak_um",round(r["peak_bending_coordinate_um_during_move"],4),
        "torsion_peak_mrad",round(r["peak_torsion_mrad_during_move"],5))
    if args.include_timeseries:
      cols=["model_mode","time_s","load_position_m","load_speed_m_s","payload_point_error_m","sync_skew_m",
        "beam_bending_coordinate_m","beam_torsion_rad","Mdot_matrix_2norm_numeric_under_m_rad_coordinate_units","velocity_transport_generalized_term_2norm_numeric_under_m_rad_coordinate_units",
        "acceleration_transport_generalized_term_2norm_numeric_under_m_rad_coordinate_units","min_generalized_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units","min_augmented_q_s_mass_matrix_eigenvalue_numeric_under_m_rad_coordinate_units","peak_command_force_N"]
      with (out/"gantry-moving-load-selected-timeseries.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(cols); w.writerows(traces)
    if args.disk_margin: disk_margins(out)

if __name__=="__main__": main()
