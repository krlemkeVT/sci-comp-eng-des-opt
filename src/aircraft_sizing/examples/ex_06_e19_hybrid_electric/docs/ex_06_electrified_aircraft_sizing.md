# Conceptual Sizing of an Electrified Aircraft — Full Worked Example (E-19 Hybrid-Electric Commuter)

A detailed, end-to-end conceptual-sizing walkthrough for a **hybrid-electric** aircraft, following the method of **de Vries et al. (AIAA 2026-4690)** and its open-source companion code. Every method step is documented with (a) the **paper equation/table number**, (b) the equation itself, and (c) a link to the **exact line of companion code** that implements it. The design example (the **E-19** 19-pax commuter) is carried all the way through **both** a Class I and a Class II mass estimate.

This is the electrified counterpart to the fuel-based [ASW example](../../asw/docs/ex_05_asw_sizing.md). The contrast is the point: fuel burns off (weight drops through the mission), but **battery mass is constant**, which reshapes the range equation, the sizing loop, and the whole mass build-up.

---

## Source, License, and How to Run

**Paper.** R. de Vries, A. K. Jeyaraj, F. Salucci, A. Brown, M. A. Clarke, P. J. Ansell, M. F. M. Hoogreef, B. Zaghari, S. Liscouët-Hanke, R. Love, M. Ilak, G. Cinar, *"Conceptual Design of Electrified Aircraft: A Practical Guide for Engineering Students and Practitioners,"* **AIAA AVIATION 2026 Forum**, San Diego, CA, AIAA 2026-4690. DOI: [10.2514/6.2026-4690](https://doi.org/10.2514/6.2026-4690). © 2026 the authors; published by AIAA. A non-profit initiative of the AIAA Electrified Aircraft Technologies (EAT) and Aircraft Design (AD) Technical Committees.

**Companion code** (referenced throughout as `references/ElectricAircraftDesignExample_AIAA2026/<file>`): <https://github.com/EAT-AD-TC/ElectricAircraftDesignExample_AIAA2026>, vendored here as a **git submodule** pinned to tag `v1.0`.

```bash
# fetch the referenced companion code (first time only)
git submodule update --init references/ElectricAircraftDesignExample_AIAA2026
# run the authors' notebook
cd references/ElectricAircraftDesignExample_AIAA2026
python -m pip install -r requirements.txt
jupyter lab E_19_Worked_Example.ipynb
```

> **License caveat.** The upstream repository ships **no `LICENSE` file**, so reuse terms are not formally granted. It is included here **by reference** (a submodule pointer, not a redistributed copy) for education. Equations and numerical data reproduced below are facts/methods restated in our own words with citation; the paper's prose and figures are **not** reproduced. Confirm reuse terms with the authors/EAT-TC before redistributing the code or publishing derivatives. See `references/NOTICE.md`.

**Numbers convention.** Two sources can differ slightly:
- **"Paper"** = the published tables (e.g. *Table 30*).
- **"Notebook v1.0"** = what the pinned companion code computes today (independently reproduced for this document).

Where they differ (a fraction of a percent, from small input rounding such as cruise $L/D = 19.42$ in code vs. $19.3$ in the paper text), both are shown.

---

## 0. Master Cross-Reference Index

**Equations** (paper № → what it does → companion code):

| Paper Eq | Quantity | Companion code (`references/…AIAA2026/`) |
|---|---|---|
| 29 | Breguet range (fuel), reserve fuel | `special_functions.py:419` `conventional_breguet_weight_fraction`; loiter `:582` |
| 30–32 | Hybrid Breguet (energy form) | `class_1_sizing.py:50` `compute_E0_tot_hybrid_single_phase` |
| 33 | **Pure-electric** Breguet (energy) | `class_1_sizing.py:36` `compute_E0_tot_electric_single_phase` |
| 34–36 | Lost range / fuel-fraction w/ reserves | (method; not separately coded) |
| 49, 51 | MTOM mass identity / fraction form | Class I loop, `E_19_Worked_Example.ipynb` cell 19 |
| 52 | Raymer OEM fraction $A\,m^{C}$ | Table 13 (not used for E-19) |
| 53 | **Torenbeek OEM** (Class I) | `class_1_sizing.py:13` `oe_mass`, table `:3` |
| 54 | Wing mass | `class_2_airframe_structure.py:10` `wing_mass_eq22` |
| 55–58 | Tail mass (light / transport) | `class_2_airframe_structure.py:69,80,89,97` |
| 59 | Fuselage **length** $l=a\,W^{c}$ | `class_2_airframe_structure.py:453` `tail_areas_from_volume_coefficients` |
| 60 | Fuselage mass | `class_2_airframe_structure.py:115` `fuselage_mass_eq27` |
| 61 | Landing-gear mass | `class_2_airframe_structure.py:160` `landing_gear_mass_eq28` |
| 62 / 63 | Nacelle mass, prop / jet | `class_2_airframe_structure.py:205 / 228` |
| 64 / 65 | Engine mass (uninstalled / installed) | `class_2_prop_parallel_hybrid.py:62 / 67` |
| 66 / 67 | Propeller mass, piston / turboprop | `class_2_prop_parallel_hybrid.py:70` |
| 68–71 | Gearbox mass | (method; not coded in E-19 path) |
| 72 | Fuel-system mass | `class_2_prop_parallel_hybrid.py:74` |
| 73 / 76 | Battery mass — energy (pack / cell) | `class_1_sizing.py:228` / `class_2_battery_sizing.py:4` |
| 74, 75, 78, 79 | Pack knockdowns, power density | Table 17, 19 |
| 77 | Battery mass — power sizing | (method) |
| 80–82 | Supercapacitor mass | `class_2_battery_sizing.py:44,64` |
| 83 | Electric-motor mass (torque density) | `class_2_battery_sizing.py:76` `motor_generator_mass` |
| 84 | Inverter mass | `class_2_battery_sizing.py:101` `inverter_mass` |
| 85 | Cable mass | `class_2_battery_sizing.py:112` |
| 86, 88 | Battery heat load, BTMS mass | cell 25 (`m_btms = 0.6·P_bat·(1−η_bat)`) |
| 89 / 92 | Motor / inverter cooling mass | `class_2_battery_sizing.py:185 / 220` |
| 94 | $(L/D)_{\max}$ estimate | `class_1_aero.py:6` `ld_max_lofi` |
| 95 | Stall-speed constraint | `SMP_W_P.py:184` |
| 96–99 | Take-off constraint (TOP) | `SMP_W_P.py` (TOP method) |
| 100 | Max-cruise-speed constraint | `SMP_W_P.py:294` |
| 101–103 | Rate-of-climb / ceiling constraint | `SMP_W_P.py:15,73` (Roskam FAR-23) |
| Table 7 | Powertrain component power split | `powertrain_component_sizing.py:35` (parallel) |

**Data tables** (all reproduced in the relevant section below): 1 (categories), 5 (drag polar), 6 ($C_{L\max}$), 7 (power split), 8 (efficiencies), 9 (constraint sources), 13/14 (OEM constants), 15 (mass refs), 16 (engine constants), 17/19 (battery knockdowns), 21/22 (E-19 TLARs), 23 (wing), 25 (aero), 26/27 (constraint I/O), 28 (powertrain), 29 (energy allowances), 30/31 (Class I), 32 (Class II inputs), 33/34 (systems), 35 (Class II results), 36 ($K_{LD}$), 37 (fuel props).

*Appendix E (Generalized Powertrain Sizing) is intentionally out of scope for this example.*

---

## 1. The Conceptual-Sizing Process

Conceptual sizing turns **top-level aircraft requirements (TLARs)** into first estimates of maximum take-off mass (MTOM), wing area, and installed power. The paper's Fig. 1 workflow, as executed for the E-19:

1. **Requirements analysis** — turn TLARs into hard constraints (§4).
2. **Configuration selection** — category, reference aircraft, layout, powertrain architecture (§5).
3. **Aerodynamics** — a low-fidelity drag polar and cruise $L/D$ (§6).
4. **Powertrain & wing sizing** — the constraint / **Sizing-Matrix-Plot (SMP)** diagram → $W/S$, $W/P$, then the powertrain component power split (§7).
5. **Energy estimation** — Breguet for the energy-intensive phases + allowances (§8, §9).
6. **Class I mass estimation** — statistical OEM + battery/fuel, iterate MTOM (§9).
7. **Energy estimation (Class II)** — refine with systems power draws (§10).
8. **Class II mass estimation** — component-by-component airframe + powertrain + systems, iterate MTOM (§10).
9. **Present & sanity-check results** (§11).

Steps 6 and 8 are **fixed-point iterations**: many masses depend on MTOM, so we guess MTOM, evaluate, and repeat until it stops moving.

---

## 2. What Electrification Changes (vs. a Fuel Aircraft)

| Aspect | Fuel (ASW example) | Electrified (this example) |
|---|---|---|
| Energy-source mass in flight | **decreases** (fuel burns off) → log term in Breguet | **constant** for batteries → range **linearizes** in the battery fraction (Eq 33) |
| Mass identity | $m = \dfrac{m_\text{fixed}}{1-\frac{m_e}{m}-\frac{m_f}{m}}$ | adds a **battery** term $-\frac{m_\text{bat}}{m}$ (Eq 51) |
| Storage sizing | fuel mass = energy/$e_f$ | battery mass = max( energy/$e_\text{bat}$ , power/$p_\text{bat}$ ) (Eq 73/77) |
| Powertrain | one gas turbine | **network** of components tied by power split $\Phi$ and efficiencies (Table 7) |
| New masses | — | inverter, motor, **battery thermal management (BTMS)**, cooling |

The E-19 answer is a **parallel hybrid**: fly the nominal mission **fully electric** ($\Phi=1$), and keep a small **kerosene turboshaft range-extender** just for the IFR reserves.

---

## 3–5. Requirements, Category, Configuration

### Step 1 — TLARs (Table 21) and derived requirements (Table 22)

| Requirement | Value | Remark |
|---|---|---|
| Certification | Part 23 (commuter) | ≤19 seats |
| Payload $m_{PL}$ | **1,805 kg** (3,980 lb) | 19 pax × 95 kg |
| Electric range @ max PL | **190 km** (103 nmi) | flown **on batteries** |
| Take-off field length | 1,440 m (4,725 ft) | matches BAe Jetstream 31 |
| Approach speed | 56 m/s (109 kt) | → stall speed $V_s=V_\text{app}/1.3=43.1$ m/s |
| IFR reserves | 185 km + 45 min | on the **turboshaft range-extender** |
| Cruise altitude | 3,048 m (10,000 ft) | $\rho=0.9046$ kg/m³ |
| Service ceiling | 7,620 m (25,000 ft) | $\rho=0.5489$ kg/m³ |
| **MTOM limit** | **8,618 kg** (19,000 lb) | CS-23 ceiling (a hard cap) |
| Climb (23.65, AEO, SL) | 1.52 m/s & 4% gradient | flaps TO, gear up |
| Climb gradient (23.67 OEI) | 1.2% @ 5,000 ft; 0.6% @ SL | one engine inoperative |

### Step 2 — Category & configuration

The paper's **aircraft categories** (Table 1) place the E-19 as a **Commuter** (Part 23, 12,500–19,000 lb, twin turboprop):

| Category | Cert. | MTOM [lb] | Propulsion | Engines | Aisles |
|---|---|---|---|---|---|
| Commercial jet | Part 25 | >19,000 | Turbofan | ≥2 | ≥1 |
| Regional turboprop | Part 25 | >19,000 | Turboprop | ≥2 | 1 |
| Business jet | Part 23/25 | </>19,000 | Turbofan | ≥1 | 1 |
| **Commuter** ← E-19 | **Part 23** | **12,500–19,000** | **Turboprop** | **2** | **1** |
| General aviation | Part 23 | <12,500 | Piston | 1–2 | 1/none |
| Military transport | Military | >12,500 | Turboprop/fan | ≥2 | N/A |

**E-19 configuration:** low wing, conventional tail, two wing-mounted tractor propellers, retractable gear, **parallel-hybrid** powertrain with the electrified components (incl. batteries) in the nacelles. Wing parameters (Table 23):

| $A$ | $\lambda$ | $\Lambda_{c/2}$ | $(t/c)_\text{root}$ | wing |
|---|---|---|---|---|
| **12** | 0.39 | 0° | 0.12 | low |

*(Companion inputs: `E_19_Worked_Example.ipynb` cells 1, 5.)*

---

## 6. Step 3 — Aerodynamics

### Drag polar

The low-fidelity parabolic polar (code `class_1_aero.py:31` `drag_polar_lofi`):

$$C_D = C_{D_0} + \frac{C_L^2}{\pi A e}$$

$C_{D_0}$ and Oswald $e$ come from **Table 5** (clean configuration; the bold row is the E-19 pick):

| Aircraft type | $C_{D_0,\text{clean}}$ | $e_\text{clean}$ |
|---|---|---|
| High-subsonic jet | 0.014–0.020 | 0.75–0.85 |
| **Large turboprop** ← E-19 | **0.018–0.024** | **0.80–0.85** |
| Twin-engine piston | 0.022–0.028 | 0.75–0.80 |
| Single piston, retractable | 0.020–0.030 | 0.75–0.80 |
| Single piston, fixed gear | 0.025–0.040 | 0.65–0.75 |

**E-19:** $C_{D_0}=0.020$, $e=0.80$ (Table 25). Configuration deltas for TO/landing (flaps + gear) come from Roskam Table 3.6.

$C_{L\max}$ from **Table 6** (bold = E-19 "small twin engine props", high end):

| Aircraft type | clean | TO | Landing |
|---|---|---|---|
| Small single-engine props | 1.3–1.9 | 1.3–1.9 | 1.6–2.3 |
| **Small twin-engine props** ← E-19 | 1.2–**1.8** | 1.4–**2.0** | 1.6–**2.5** |
| Regional turboprops | 1.5–1.9 | 1.7–2.1 | 1.9–3.3 |
| Transport jets | 1.2–1.8 | 1.6–2.2 | 1.8–2.8 |

**E-19:** $C_{L\max}=1.8/2.0/2.5$ (clean/TO/L).

### Cruise $L/D$

Two routes. **(a) Statistical** $(L/D)_{\max}$ (Appendix B, **Eq 94**; code `class_1_aero.py:6`):

$$\left(\frac{L}{D}\right)_{\max}=K_{LD}\sqrt{\frac{A}{S_\text{wet}/S_\text{ref}}}$$

with $K_{LD}$ from **Table 36** (Civil jets 15.5; Military jets 14; **prop, retractable gear 11**; prop, fixed 9; high-AR 13; sailplane 15), and $S_\text{wet}/S_\text{ref}\approx4$–8.

**(b)** The E-19 instead sets cruise at the polar's max-$L/D$ point directly (cell 7):

$$C_{L,\text{cr}}=\sqrt{\pi e A\,C_{D_0}}=0.78,\quad C_{D,\text{cr}}=2C_{D_0}=0.04,\quad \boxed{(L/D)_\text{cr}=\tfrac12\sqrt{\tfrac{\pi A e}{C_{D_0}}}=19.42}$$

*(Paper text rounds this to 19.3; the companion notebook uses 19.42. This 0.6% difference is the main reason the notebook's MTOM lands ~0.3% below the paper's.)*

---

## 7. Step 4 — Powertrain & Wing Sizing: the Constraint Diagram (SMP)

This is the heart of point-performance sizing. We plot every performance requirement as a curve in **wing-loading $W/S$ vs. power-loading $W/P$** space; the feasible region is where **all** requirements are met, and we pick a **design point** inside it. Code: `SMP_W_P.py:132` `constraints_raymer` (curves) and `:328` `plot_constraint_diagram`; the E-19 overlay uses `SMP_W_P_design_point.py`.

Two kinds of constraints (paper Appendix C, Fig. 16; sources catalogued in Table 9):

### 7a. Vertical constraints (set a maximum $W/S$)

**Stall / approach speed (Eq 95, `SMP_W_P.py:184`).** From lift equilibrium at $C_{L\max,L}$:

$$\frac{W}{S}=\tfrac12\rho V_s^2\,C_{L\max,L}$$

Regulations tie approach to stall by $V_\text{app}=1.3\,V_s$. **E-19:** $V_s=43.1$ m/s, $C_{L\max,L}=2.5$, $\rho=1.225$ → $W/S_\text{stall}=\mathbf{2{,}844\ N/m^2}$ (verified from code).

**Landing distance (`SMP_W_P.py:185`).** A Roskam-form relation $W/S = (s_\text{land}-S_a)\,\rho_r\,C_{L\max,L}/5\cdot g$ with $S_a=305$ m (twin turboprop). **E-19:** $\approx4{,}390\ N/m^2$ (less restrictive than stall).

**Service ceiling / loiter** also give vertical limits ($1{,}444$ and $2{,}319\ N/m^2$) but for the E-19 SMP they are **excluded** from the feasible-region $W/S$ cap (cell 11 passes `include_ceiling_constraint=False`), so **stall governs**: $W/S_\text{limit}=2{,}844\ N/m^2$.

### 7b. Power constraints (set a minimum $W/P$, i.e. a maximum power)

**Take-off (Eq 96–99).** Via the take-off parameter (propeller form):

$$TOP_\text{prop}=\frac{(W_\text{TO}/S)(W_\text{TO}/P_s)}{C_{L,\text{TO}}},\qquad C_{L,\text{TO}}=\frac{C_{L\max,\text{TO}}}{1.21}$$

empirically tied to ground roll/field length by $s_\text{TOG}=4.9\,TOP_{23}+0.009\,TOP_{23}^2$ (Eq 98) and $s_\text{TO}=8.134\,TOP_{23}+0.0149\,TOP_{23}^2$ (Eq 99). *Note:* $W/P_s$ here is **shaft** power — convert to propulsive $W/P_p$ for the SMP.

**Maximum cruise speed (Eq 100, `SMP_W_P.py:294`).** From steady level flight, with $K=1/(\pi e A)$:

$$\frac{W}{P_p}=\left[\frac{\tfrac12\rho V_\max^3 C_{D_0}}{W/S}+\frac{2K}{\rho V_\max}\frac{W}{S}\right]^{-1}$$

evaluated at **cruise** density/weight (not TO). **E-19:** at $W/S=2546$, $W/P_\text{max-speed}\approx0.184\ N/W$ (not binding).

**Rate of climb & ceiling (Eq 101–103, `SMP_W_P.py:15,73`).** Max ROC for a propeller aircraft:

$$ROC_{\max}=\eta_p\frac{P_p}{W}-\frac{1}{\sqrt{2\rho}}\left(\frac{W}{S}\right)^{1/2}\frac{1}{C_L^{3/2}/C_D},\quad\text{best at }C_{L,\text{ROC}}=\sqrt{3C_{D_0}\pi Ae},\ C_D=4C_{D_0}$$

Isolating $W/P_p$ gives the climb power constraint; setting $ROC=0$ gives the absolute ceiling, and $ROC=$ (100 ft/min prop) gives the service ceiling. The companion uses **Roskam's FAR-23** climb-rate (Eq 3.24) and climb-gradient (Eq 3.29/3.30) relations directly (`FAR_23_climb_rate_roskam`, `FAR_23_climb_gradient_roskam`).

**OEI over-sizing.** A one-engine-inoperative requirement's $W/P$ is divided by $N/(N-1)$ to over-size for engine loss (here $N=2$ → factor 2; `SMP_W_P.py:277`).

**Constraint source catalogue (Table 9)** — where to find each constraint's equations across the handbooks:

| Constraint | Roskam[1] | Raymer[2] | Torenbeek[4] | Torenbeek[3] | Gudmundsson[6] |
|---|---|---|---|---|---|
| Stall | 3.1.1 | 5.3.2 | 9.3.1 | 5.4.4 | 3.2.2 |
| Take-off | 3.2.1/3.2.3 | 5.3.3/5.3.4 | 9.4 | 5.4.5 | 3.2.1 |
| Max speed | 3.6 | 5.2.4/5.3.7 | 9.2 | 5.4.1 | 3.2.1 |
| Max ROC | 3.4.4.1/3.4.9 | 5.3.11 | – | 5.4.3 | 3.2.1 |
| Climb gradient | 3.4.4.2/3.4.7 | – | 9.3.2/9.3.3 | 5.4.3 | – |
| Ceiling | 3.4.10.2 | 5.3.12 | – | – | 3.2.1 |
| OEI climb gradient | 3.4.4.2/3.4.7 | – | 9.3.4 | – | – |

### 7c. E-19 constraint inputs & design point

Constraint inputs (Table 26; `E_19_Worked_Example.ipynb` cell 10):

| $V_s$ | $s_\text{land}$ | $s_\text{TO}$ | $V_\text{cr}$ | climb grad | ROC | $\rho_\text{SL}$ | $\rho_\text{ceil}$ | $\rho_\text{cr}$ | $\rho_\text{climb}$ | $\eta_p$ |
|---|---|---|---|---|---|---|---|---|---|---|
| 43.1 | 1200 m | 1440 m | 82.3 | 0.06 | 1.52 | 1.225 | 0.549 | 0.905 | 1.100 | 0.8 |

Computed constraint values (reproduced from code):

| Constraint | Value | Type |
|---|---|---|
| Stall $W/S$ | **2,844 N/m²** | vertical (governing) |
| Landing $W/S$ | 4,390 N/m² | vertical |
| Climb-envelope $W/P$ @ $W/S{=}2546$ | 0.103 N/W | power (governing) |
| Max-speed $W/P$ @ $W/S{=}2546$ | 0.184 N/W | power |

The auto-selected point (0.95×stall) is $(W/S,\,W/P)=(2702,\ 0.099)$. The example instead **fixes the design point to match the reference E-19** (Table 27):

$$\boxed{W_\text{TO}/S=2{,}546\ \text{N/m}^2,\qquad W_\text{TO}/P=0.0676\ \text{N/W}}$$

The chosen $W/P=0.0676$ is *below* the climb envelope (0.103) — i.e. **more installed power** than climb alone needs — because the reference design conservatively sized power for a full one-engine-inoperative take-off. From the design point and the MTOM limit:

$$S=\frac{m_\text{MTO}\,g}{W/S}=\frac{8618\cdot9.81}{2546}=\mathbf{33.2\ m^2},\qquad P=\frac{m_\text{MTO}\,g}{W/P}=\frac{8618\cdot9.81}{0.0676}=\mathbf{1{,}251\ kW}$$

*(both update as MTOM converges; `E_19_Worked_Example.ipynb` cell 13.)*

### 7d. From propulsive power to component power — the power split (Table 7)

The propulsive $W/P_p$ is split into **each component's** rating using the architecture, the **supplied-power ratio $\Phi$** (fraction of propulsive power from the battery branch), and component efficiencies. **Parallel** relations (code `powertrain_component_sizing.py:35–68`):

$$\frac{W}{P_\text{te}}=\frac{W/P_p}{\eta_p\eta_\text{gb}\!\left(\frac{\Phi}{1-\Phi}\frac{\eta_\text{em}}{\eta_\text{te}}+1\right)},\quad
\frac{W}{P_\text{em}}=\frac{W/P_p}{\eta_p\eta_\text{gb}\!\left(1+\frac{1-\Phi}{\Phi}\frac{\eta_\text{te}}{\eta_\text{em}}\right)},\quad
\frac{W}{P_\text{bat}}=\frac{W/P_p}{\eta_p\eta_\text{gb}\!\left(\eta_\text{em}+\frac{1-\Phi}{\Phi}\eta_\text{te}\right)}$$

(Series forms at `:11–32`.) Representative efficiencies (Table 8):

| Component | Symbol | Typical | E-19 (Table 28) |
|---|---|---|---|
| Generator | $\eta_\text{gen}$ | 0.92–0.97 | — |
| Power electronics | $\eta_\text{pm}$ | 0.97–0.99 | (in $\eta_\text{em}$) |
| Distribution | $\eta_\text{pd}$ | 0.97–0.99 | (neglected) |
| Electric motor (+inverter) | $\eta_\text{em}$ | 0.92–0.97 | **0.95** |
| Gearbox | $\eta_\text{gb}$ | 0.97–0.99 | **0.99** |
| Propeller | $\eta_p$ | 0.70–0.85 | **0.80** |
| Gas turbine | $\eta_\text{te}$ | 0.30–0.50 | **0.24** |

At $\Phi=1$ (E-19 nominal, fully electric) these collapse to $P_\text{em}=P_p/(\eta_p\eta_\text{gb})$, $P_\text{bat}=P_p/(\eta_p\eta_\text{gb}\eta_\text{em})$, and $P_\text{te}\to0$ (the turboshaft carries none of the nominal mission; it is sized separately as the **cruise range-extender**). Computed component power loadings (cell 15):

$$W/P_\text{em}=0.0854,\quad W/P_\text{bat}=0.0898,\quad W/P_\text{te}=0.208\ (\text{cruise-sized}).$$

Other powertrain inputs (Table 28): motor specific power $PD_\text{motor}=4.94$ kW/kg, inverter $PD_\text{inv}=12$ kW/kg, and $\eta_\text{te}\eta_\text{gb}\eta_p=0.19$ overall for the range-extender fuel calc.

---

## 8. Governing Sizing Equations

### 8a. Mass identity (Eq 49, 51)

$$m_\text{MTO}=m_{OE}+m_{PL}+m_f+m_\text{bat}\qquad\Longleftrightarrow\qquad
m_\text{MTO}=\frac{m_{PL}}{1-\frac{m_{OE}}{m_\text{MTO}}-\frac{m_f}{m_\text{MTO}}-\frac{m_\text{bat}}{m_\text{MTO}}}$$

### 8b. Operating empty mass, Class I (Eq 52, 53)

Raymer fraction (Eq 52, $m$ in **lb**, constants in Table 13): $m_{OE}/m_\text{MTO}=A\,m_\text{MTO}^{C}$. For **high battery fraction** this over-predicts empty mass, so the E-19 uses **Torenbeek (Eq 53)** with coefficients from Table 14 (code `class_1_sizing.py:13`, table `:3`):

$$m_{OE}=C_\text{mpl}\,m_{PL}+C_\text{MTO}\,m_\text{MTO}+m_\text{fix}$$

| Configuration (decks, aisles) | $C_\text{mpl}$ | $C_\text{MTO}$ | $m_\text{fix}$ |
|---|---|---|---|
| **1, 1 (narrowbody)** ← E-19 | **1.25** | **0.20** | **500 kg** |
| 1, 2 | 1.50 | 0.21 | 600 |
| 2, 4 | 1.75 | 0.22 | 700 |

*(The narrowbody column is noted in the paper as reasonable for large regional turboprops with high hybridization when batteries are in the wing/nacelles.)* **E-19:** $m_{OE}=1.25\,m_{PL}+0.20\,m_\text{MTO}+500 = 2756.25+0.20\,m_\text{MTO}$.

### 8c. Electric & hybrid Breguet (Eq 30–33)

The hybrid Breguet (constant $\Phi$; branch efficiencies $\eta_1,\eta_2,\eta_3$ from Table 11: parallel $\eta_1{=}\eta_\text{te}$, $\eta_2{=}\eta_\text{em}$, $\eta_3{=}\eta_p$) at $\Phi\to1$ gives the **pure-electric** range (Eq 33). Inverted for the battery energy needed to fly range $R$ at flight weight $W=W_{OE}+W_{PL}$ (code `class_1_sizing.py:36`):

$$K=\eta_2\eta_3\,\frac{L}{D}\,\frac{e_\text{bat}}{g}\ \ (\text{max all-battery range}),\qquad E_{0,\text{bat}}=\frac{e_\text{bat}}{g}\cdot\frac{R\,W}{K-R}$$

No logarithm (weight is constant); range is capped by $K$ no matter how big the battery.

### 8d. Battery mass (Eq 73–79)

**Energy sizing** (Eq 73, code `class_1_sizing.py:228`): $m_\text{bat}=k_\text{bat}\,E_\text{bat}/e_\text{bat}$, where $k_\text{bat}$ is pack overhead and $e_\text{bat}$ is usable pack specific energy. **Power sizing** (Eq 77): $m_\text{bat}=P_\text{bat}/p_\text{bat}$ — size for both, take the heavier. Usable density folds in **knockdowns** (Eq 74/75, Table 17): $e_\text{bat}=e_\text{cell}\,k_\text{pack}k_\text{DOD}k_\text{SOH}k_R$.

| Knockdown | Typical |
|---|---|
| $k_\text{pack}$ (overhead) | 0.7–0.85 |
| $k_\text{DOD}$ (depth of discharge) | 0.8–0.9 |
| $k_\text{SOH}$ (degradation) | 0.8–0.9 |
| $k_R$ (internal resistance) | 0.9–0.95 |

Cell C-rates (Table 19): ultra-high-energy <0.5 h⁻¹; high-energy 1–2; high-power 2–5. **E-19:** uses an **effective** $e_\text{bat}=160$ Wh/kg and $k_\text{bat}=1.18$ (≈18% overhead), assuming the pack discharges fast enough that **energy**, not power, is the sizing condition.

### 8e. Reserve fuel (Eq 29)

The range-extender fuel is the conventional propeller Breguet, energy form (code `special_functions.py:419`): weight fraction $=\exp\!\big[-R\,g/(\eta_\text{total}\,e_f\,L/D)\big]$, plus a loiter endurance form using PSFC (`:582`). Fuel properties (Table 37): **Jet-A $e_f=42.8$ MJ/kg** (E-19), Avgas 43.5 MJ/kg.

---

## 9. Class I Mass Estimation — Full Worked Convergence

**Inputs** (cell 19): $m_\text{MTO}^{(0)}=8600$ kg, $m_{PL}=1805$, $e_\text{bat}=160{\cdot}3600=576{,}000$ J/kg, $e_f=42.8{\times}10^6$, $k_\text{bat}=1.18$, $\eta_{1,2,3}=0.24,0.95,0.80$, $L/D=19.42$, allowances $E_\text{allow}=233.28{\times}10^6$ J (taxi/TO/descent/landing, from the DLR eCommuter study), reserve fuel with 5% trapped.

**Loop** (each iteration):
1. $m_{OE}=1.25(1805)+0.20\,m_\text{MTO}+500$  (Eq 53)
2. cruise battery energy $E_0$ via Eq 33 at flight weight $(m_{OE}+m_{PL})g$
3. $m_\text{bat}=1.18\,(E_0+E_\text{allow})/576000$  (Eq 73)
4. reserve fuel $m_f=1.05\,[1-(1-f_R)(1-f_\text{loiter})]\,m_\text{MTO}$  (Eq 29 ×2)
5. $m_\text{MTO}^\text{new}=m_{OE}+m_\text{bat}+m_{PL}+m_f$; repeat until $|\Delta|<1$ kg.

**Convergence (reproduced from companion code — matches the notebook exactly):**

| Iter | $m_\text{MTO}$ guess [kg] | $m_{OE}$ [kg] | $E_0$ [J] | Battery [kg] | Fuel [kg] | new $m_\text{MTO}$ | err |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8,600.0 | 4,476.3 | 1.016×10⁹ | 2,559.8 | 197.3 | 9,038.4 | 438.4 |
| 2 | 9,038.4 | 4,563.9 | 1.030×10⁹ | 2,588.9 | 207.4 | 9,165.2 | 126.8 |
| 3 | 9,165.2 | 4,589.3 | 1.035×10⁹ | 2,597.3 | 210.3 | 9,201.8 | 36.7 |
| 4 | 9,201.8 | 4,596.6 | 1.036×10⁹ | 2,599.7 | 211.1 | 9,212.4 | 10.6 |
| 5 | 9,212.4 | 4,598.7 | 1.036×10⁹ | 2,600.4 | 211.4 | 9,215.5 | 3.1 |
| 6 | 9,215.5 | 4,599.4 | 1.036×10⁹ | 2,600.6 | 211.4 | 9,216.4 | 0.9 ✓ |

**Verify Eq 53 by hand:** iter 1, $m_{OE}=2756.25+0.20(8600)=4476.3$ ✓; iter 6, $2756.25+0.20(9216.4)=4599.5$ ✓.
**Verify the battery** (iter 6): $1.18\,(1.036{\times}10^9+233.28{\times}10^6)/576000 = 2600.6$ kg ✓.

**Converged Class I** (notebook v1.0): **MTOM 9,216 kg**, $m_{OE}$ 4,599, battery 2,601, $E_0$ 1,036 MJ, fuel 211, 6 iters.
**Paper (Table 30/31):** MTOM 9,240 kg, $m_{OE}$ 4,604, battery 2,619, $E_0$ 1,045 MJ, fuel 213 — identical method, ~0.3% higher from the $L/D$ 19.3-vs-19.42 rounding.

**Reading the result.** The Class I MTOM (9,216 kg) is **well above** the 8,618 kg CS-23 limit: the Torenbeek regression **over-predicts** empty mass for such a battery-heavy aircraft, and the fixed battery mass amplifies it (the "snowball"). That is exactly why we go to Class II.

---

## 10. Class II Mass Estimation — Component Build-Up

Class II replaces the single OEM regression with a **component-by-component** build-up, re-iterating MTOM. The Class I result seeds it. Class II loop: `E_19_Worked_Example.ipynb` cell 25 (`converge_mtom_with_class2_struct_oe`), cell 26.

$$m_\text{MTO}=\underbrace{(m_\text{wing}+m_\text{tail}+m_\text{fus}+m_\text{LG}+m_\text{nac})}_{\text{airframe}}+\underbrace{(m_\text{TE}+m_\text{prop}+m_\text{fs}+m_\text{motor}+m_\text{ctrl})}_{\text{powertrain}}+\underbrace{(m_\text{sys}+m_\text{furn}+m_\text{ops})}_{\text{systems}}+m_\text{bat}+m_f+m_{PL}+\underbrace{(m_\text{inv}+m_\text{cool}+m_\text{BTMS})}_{\text{thermal/elec}}$$

### 10a. Airframe structure (Eq 54–63)

**Wing (Eq 54, code `class_2_airframe_structure.py:10`):**
$$\frac{W_w}{W_G}=k_w\,b^{0.75}\left(1+\sqrt{\tfrac{b_\text{ref}}{b_s}}\right)n_\text{ult}^{0.55}\left(\frac{b_s/t_r}{W_G/S}\right)^{0.30},\quad b_s=\frac{b}{\cos\Lambda_{c/2}}$$
$k_w=4.90{\times}10^{-3}$ (light, $W_G<12{,}500$ lb) or $6.67{\times}10^{-3}$ (transport); $b_\text{ref}=1.905$ m. Adjustments: **−5%** for 2 wing engines (**−10%** for 4), **−5%** if main gear not wing-mounted. **E-19:** $n_\text{ult}=5.7$, light, 2 wing engines.

**Tail — light aircraft (Eq 55, `:69`):** $W_\text{tail}=k_\text{wt}(n_\text{ult}S_\text{tail}^2)^{0.75}$, $k_\text{wt}=0.64$. *(Transport polynomial method Eq 56–58 at `:80,89,97`.)* Tail **areas** from volume coefficients (`:453`): $S_h=c_h\bar c_w S/L_h$, $S_v=c_v b S/L_v$, with $c_h{=}0.90$, $c_v{=}0.08$; and fuselage **length** (**Eq 59**) $l_f=a_\text{fus}\,m_\text{MTO}^{c_\text{fus}}$ ($a_\text{fus}{=}0.169$, $c_\text{fus}{=}0.51$ in SI), tail arms $L_h=L_v=0.52\,l_f$.

**Fuselage mass (Eq 60, `:115`):** $W_f=k_\text{wf}\sqrt{V_D\,l_t/(b_f+h_f)}\,S_G^{1.2}$, $k_\text{wf}=0.23$. Adjustments: **+8%** pressurized, +4% fuselage engines, **+7%** main gear on fuselage, +10% freighter, −4% no gear bay. **E-19:** pressurized, $V_D{=}144$ m/s, $b_f{=}2.2$, $h_f{=}2.4$, $S_G{=}95$ m².

**Landing gear (Eq 61, `:160`):** $W_\text{uc}=k_\text{uc}(A+B\,W_\text{TO}^{3/4}+C\,W_\text{TO}+D\,W_\text{TO}^{2/3})$; $k_\text{uc}=1$ (low wing). Retractable nose $(A,B,C,D)=(9.1,0.082,0,2.97{\times}10^{-6})$; main $(18.1,0.131,0.019,2.23{\times}10^{-5})$.

**Nacelle — prop (Eq 62, `:205`):** $W_n=0.0635\,\text{ESHP}_\text{TO}$ (+0.018 kg/hp if gear in nacelle, +0.05 kg/hp over-wing exhaust). **E-19:** ESHP = 1600 hp. *(Jet form Eq 63: $W_n=k_n T_\text{TO}$, $k_n=0.055$/0.065.)*

**Airframe mass references by category (Table 15):** Commercial jet/regional TP/business/commuter → Torenbeek[3], Raymer[2]; GA → Gudmundsson[6], Nicolai[5], Roskam[1]; military → Nicolai[5], Roskam[1], Raymer[2].

### 10b. Fuel-burning powertrain (Eq 64–72)

**Engine mass (Eq 64/65, code `class_2_prop_parallel_hybrid.py:62`):** uninstalled $m_\text{eng}=K_\text{eng}P_\text{rated}+m_0$; installed $=1.205\,m_\text{eng}N$ (turboprop). Constants (Table 16):

| Engine | $K_\text{eng}$ | $m_0$ |
|---|---|---|
| Piston | 0.814 kg/kW | 23.2 kg |
| **Turboprop** ← E-19 | **0.225 kg/kW** | **−4.4 kg** |
| Turboshaft | 0.077 kg/kW | 101.1 kg |
| Turbofan | 17.55 kg/kN | 256.6 kg |

**Propeller (Eq 67, `:70`):** $m_\text{prop}=1.003\,P_\text{rated}^{0.678}N$ (turboprop). **Fuel system (Eq 72, `:74`):** $m_\text{fs}=0.454\,m_f^{0.48}\,10^{0.297N_\text{eng}+0.028N_\text{tank}}$. *(Gearbox Eq 68–71 not on the E-19 path.)*

### 10c. Electric powertrain & thermal (Eq 73–92)

**Motor (Eq 83, `class_2_battery_sizing.py:76`):** $m_\text{motor}=P_\text{em}/(T_\text{density}\,\omega)$, $\omega=2\pi\,\text{RPM}/60$ — **or**, as the E-19 path actually does, by **specific power** $m_\text{motor}=P_\text{em}/PD_\text{motor}$ (`class_2_prop_parallel_hybrid.py:79`, $PD_\text{motor}=4.94$ kW/kg). **Motor controller:** $P_\text{em}/PD_\text{ctrl}$ (`:82`). **Inverter (Eq 84, `:101`):** $m_\text{inv}=P_\text{inv}/PD_\text{inv}$ ($PD_\text{inv}=12$ kW/kg). **Cable (Eq 85, `:112`):** $m_\text{cable}=L(\rho_cA_c+\rho_iA_i)$.

**Thermal management:** battery heat load (Eq 86) $\dot Q=P_\text{bat}(1-\eta_\text{bat})$; **BTMS mass (Eq 88)** $m_\text{BTMS}=0.6\,\dot Q$ (E-19 uses $\eta_\text{bat}=0.90$, cell 25); **motor cooling (Eq 89, `:185`)** $m=P_\text{loss}(1-\eta_\text{motor})/PD_\text{motorCool}$ ($PD{=}0.8$ kW/kg); **inverter cooling (Eq 92, `:220`)** $m=P_\text{bat}(1-\eta_\text{inv})/PD_\text{invCool}$ ($PD{=}1.25$ kW/kg).

The range-extender turboshaft is also **altitude-lapsed**: $P_z=P_\text{ref}(\rho_z/\rho_\text{ref})^{\xi}$, $\xi=0.7$ (`special_functions.py:32`).

### 10d. Systems (Table 24) & furnishings

On-board systems use **FLOPS/GASP** correlations (code `class_2_systems.py`, `systems_simplified.py`), with the paper's suggested adaptations (Table 24): hydraulics ÷2 (1.5-redundancy), electrical ÷2 and avionics ÷2 (too high for a small aircraft). **E-19 systems (Tables 33/34, notebook values):**

| System | Mass [kg] | System | Mass [kg] |
|---|---|---|---|
| Hydraulic (÷2) | 44 | Instruments | 57 |
| Flight controls | 54–91 | **Total systems** | **≈594** |
| ECS | 75 | Galley/furnishings | 572 |
| Electrical (÷2) | 252 | Operator items | 180 |
| Ice protection | 41 | | |

Systems also draw **electrical power** in cruise (lights $0.31\,l_f$, avionics $0.02\,l_f^{1.55}$, fuel system $2.88e^{0.0399 l_f/N}$ kW; `systems_simplified.py:9`), converted to extra battery energy (~26 MJ) that is added to the Class II battery sizing.

### 10e. Class II convergence & results

The Class II loop (seeded at the Class I MTOM 9,216 kg) converges **downward** — the component build-up is lighter than the Class I regression, which cascades into less battery and a smaller aircraft:

| Iter | $m_\text{MTO}$ [kg] | airframe [kg] | battery [kg] | fuel [kg] | motor [kg] | turboprop [kg] | err |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 9,216.4 | 2,583 | 1,986 | 211.5 | 342 | 84.8 | 277 |
| 2 | 8,939.3 | 2,524 | 1,966 | 205.1 | 332 | 81.9 | 116 |
| 4 | 8,775.5 | 2,489 | 1,954 | 201.3 | 325 | 80.2 | 20 |
| 6 | 8,743.7 | 2,482 | 1,951 | 200.7 | 324 | 79.9 | 1.4 |
| 8 | **8,742** | 2,481 | 1,951 | 200.6 | 324 | 79.9 | 0.6 ✓ |

**Converged Class II** (notebook v1.0): **MTOM 8,742 kg**, airframe 2,481, battery 1,951, fuel 201, wing area **33.69 m²**, span **20.1 m**, $S_h$ 5.65 m², $S_v$ 6.02 m², installed EM power **1,005 kW**, range-extender turboshaft **334 kW** (167 kW/engine), cruise $E_0$ **694 MJ (193 kWh)**.

**Paper (Table 35):** MTOM 8,763 kg, airframe 2,486, battery 1,964, fuel 202, motor 325, turboshaft 80, propeller 65, BTMS 101, inverter 139, motor cooling 105, inverter cooling 13, wing 33.77 m², span 20.12 m.

> The Class II cruise energy (694 MJ) is much lower than Class I (1,036 MJ). In the companion code the electric-cruise energy is evaluated with the **airframe + payload** weight only (the `OE` passed to Eq 33 is the airframe sum, not the full flying weight incl. battery/powertrain/systems). This is a **modelling simplification** in the notebook — it understates flight weight and therefore battery energy. Flagged so students don't treat the 694 MJ as physically complete; a higher-fidelity loop would use full flight weight.

---

## 11. Results & Comparison to the E-19 Reference

| Quantity | This model (Class II) | E-19 paper reference | Δ |
|---|---:|---:|---:|
| MTOM [kg] | 8,742 | 8,618 | +1.4% |
| Operating empty mass [kg] | ≈6,570 | 6,621 | −0.8% |
| Battery [kg] | 1,951 | 2,018 | −3.3% |
| Fuel (IFR reserves) [kg] | 201 | 192 | +4.7% |
| Airframe structure [kg] | 2,481 | 2,446 | +1.4% |
| Installed EM power [kW] | 1,005 | 1,251 | −20% |
| Wing area [m²] | 33.69 | 33.20 | +1.5% |
| Wing span [m] | 20.1 | 20.0 | +0.5% |
| Cruise $L/D$ | 19.42 | 19.40 | — |

The Class II **MTOM lands within ~1.4%** of both the CS-23 limit and the reference E-19 — a credible conceptual estimate, and far better than Class I's +7%. (The installed-EM-power gap reflects the reference's conservative full-OEI-takeoff power sizing, discussed in §7c.) **Bottom line:** for a battery-heavy aircraft, the statistical OEM (Class I) over-predicts empty mass and inflates MTOM; the component-level Class II build-up — including the electrified-specific inverter/motor/BTMS masses — is what brings it back to reality.

---

## 12. Notes, Caveats & Known Simplifications

- **Effective battery specific energy.** The E-19 uses $e_\text{bat}=160$ Wh/kg with pack overhead $k_\text{bat}=1.18$; the paper text calls 160 an "effective" value, while the code applies the 1.18 explicitly — net usable ≈136 Wh/kg. Use the knockdowns of §8d (Table 17) for a first-principles pack.
- **Energy allowance = 233.28 MJ** (taxi/TO/descent/landing) is hard-coded from the DLR eCommuter study — larger than the 32.4 kWh of Table 29; the code value is what reproduces the reported battery mass.
- **Class II cruise energy** uses airframe+payload weight only (see §10e box) — a simplification to be aware of.
- **Motor mass** in the E-19 path uses *specific power* (4.94 kW/kg), not the torque-density Eq 83; both are provided in the code.
- **Paper vs. notebook v1.0** differ ≲0.3% (Class I) / ≲0.3% (Class II) from $L/D$ rounding — both are shown above.
- **Out of scope (by request):** Appendix E (Generalized Powertrain Sizing).

---

## 13. Key Takeaways

1. **Constant battery mass** removes the logarithm from the range equation (Eq 33) and caps range by the battery *fraction* — the defining difference from fuel sizing.
2. **The SMP/constraint diagram** turns point-performance requirements into $W/S$ and $W/P$; stall governs $W/S$, climb/OEI governs $W/P$, and the design point sets wing area and installed power.
3. **The powertrain is a network**: $\Phi$ and component efficiencies (Table 7) turn one propulsive $W/P$ into per-component ratings and masses.
4. **Class I → Class II matters most for electrified aircraft**: the statistical OEM over-predicts empty mass at high battery fraction; the component build-up (with inverter/motor/BTMS) restores a credible MTOM.
5. **Reserves on fuel, mission on battery** keeps the heavy battery sized only for the nominal electric range while a light turboshaft covers regulatory reserves.

*Reproduce every number by running `references/ElectricAircraftDesignExample_AIAA2026/E_19_Worked_Example.ipynb` (submodule).*
