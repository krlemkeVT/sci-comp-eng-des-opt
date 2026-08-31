# Instructive Example — Reference Airplane

An *"instructive example"* using a reference airplane from **Dr. Brian German** at the **June 2018 AIAA Short Course**.

> *The rest of the calculations on the slides that follow are mine. Don't blame Dr. German.*

*Copyright © 2018 by Brian J. German.*

## Airplane and Mission Data

| Quantity | Symbol | Value (SI) | Value (US) |
|----------|--------|------------|------------|
| Max gross mass | $m$ | 1000 kg | 2200 lbs |
| Structural mass | $m_S$ | 450 kg | 990 lbs |
| Max payload mass | $m_P$ | 200 kg | 440 lbs |
| Battery pack mass | $m_B = m - m_S - m_P$ | 350 kg | 770 lbs |
| Pack cell mass fraction | $\mu_B$ | 0.75 | – |
| Cell specific energy | $e_{\text{cell}}$ | 221 Wh/kg (from X-57 battery analysis) | – |
| Initial battery margin | $\Delta E_{B,\text{initial}} = 0.1\, e_{\text{cell}} \mu_B m_B$ | 5.8 kWh | – |
| Final battery margin | $\Delta E_{B,\text{final}} = 0.15\, e_{\text{cell}} \mu_B m_B$ | 8.7 kWh | – |
| Energy transfer efficiency | $\eta = \eta_P \eta_M \eta_E = (0.87)(0.96)(0.98)$ | 0.82 | – |

## Cruise / Aerodynamic Data

| Quantity | Value | Notes |
|----------|-------|-------|
| Cruise altitude | 4500 ft | (listed as "Cruise airspeed: 4500 ft" on the slide) |
| Cruise airspeed | ~110 KTAS | "maybe 110 KTAS but not really directly used here" |
| Lift-to-drag ratio $(L/D)$ | 14 | matched to cruise speed |

> **Atmosphere at the quoted cruise altitude.** For reference, the ICAO standard
> atmosphere at **4,500 ft (1,371.6 m)**, computed with the [`ambiance`](https://pypi.org/project/ambiance/) package:
> $\rho = 1.0717$ kg/m³, $a = 334.99$ m/s, $T = 279.24$ K, $p = 85.900$ kPa.
>
> None of these enter the arithmetic below. The electrified range equation
> $R = E^{*}\,\eta\,(1/g)\,(L/D)\,(1 - m_\text{empty}/m - m_\text{payload}/m)$ has **no
> density term** — altitude reaches it only indirectly, through whatever $L/D$ and
> airspeed the designer picks for that condition. That is the opposite of the
> [ASW example](../../ex_01_asw/docs/ex_01_asw_sizing.md), where the Breguet *range*
> equation divides by true airspeed and so the standard-atmosphere speed of sound
> does drive the sizing loop.

## Mission Segments (Power & Time)

| Segment | Time $\Delta t$ | Battery power $P_B$ |
|---------|-----------------|---------------------|
| Takeoff | $\Delta t_{TO} = 1$ min $= 0.017$ hrs | $P_{B,TO} = 100$ kW |
| Climb | $\Delta t_{CLI} = 6$ mins $= 0.1$ hrs | $P_{B,CLI} = 85$ kW |
| Reserve | $\Delta t_{RES} = 30$ mins $= 0.5$ hrs (**daytime VFR requirement**) | $P_{B,RES} = 50$ kW |

## Showcase 1 — No Cell-to-Battery Installation Weight Penalty (Install Factor 1.0)

*Copyright © 2022 by Marty K. Bradley. (Slide 200.)*

This first showcase computes the achievable range when the **cell-to-battery install factor is 1.0** — i.e. the battery pack has *no* installation weight penalty, so the pack specific energy equals the full cell specific energy, $E^{*} = 221$ Wh/kg.

### Inputs (from the airplane/mission data above)

| Quantity | Symbol | Value | Units |
|----------|--------|-------|-------|
| Lift-to-drag ratio | $L/D$ | 14 | – |
| Energy transfer efficiency | $\eta$ | 0.82 | – |
| Specific energy (install factor 1.0) | $E^{*}$ | 221 | Wh/kg |
| Battery mass fraction | $m_{\text{bat}}/m_{\text{TOW}}$ | 0.35 | – |
| Gravitational acceleration | $g$ | 9.8 | m/s² |

### Step 1 — Breguet (battery) range

Using the battery-mass-fraction form of the range equation:

$$R = E^{*} \cdot \eta \cdot \frac{1}{g} \cdot \frac{L}{D} \cdot \frac{m_{\text{bat}}}{m_{\text{TOW}}}$$

Substitute the numbers (keeping $E^{*}$ in Wh/kg):

$$R = \frac{221}{9.8} \times 0.82 \times 14 \times 0.35 = 90.6\ \frac{\text{m}\cdot\text{h}}{\text{s}}$$

Convert the mixed units to kilometres with the factor $60^2 / 1000 = 3.6$ (hours→seconds, metres→kilometres):

$$R = 90.6 \times 3.6 = \underline{326\ \text{km}} \quad\checkmark$$

This matches the **Breguet Range = 326 km** cell.

### Step 2 — Cruise duration

The cruise speed is $V = 211$ km/hr. Flying the full Breguet range in cruise:

$$\Delta t_{\text{cruise}} = \frac{R}{V} = \frac{326\ \text{km}}{211\ \text{km/hr}} = 1.55\ \text{hrs} \quad\checkmark$$

### Step 3 — Cruise energy

At cruise power $P_{\text{cruise}} = 50$ kW:

$$E_{\text{cruise}} = P_{\text{cruise}} \cdot \Delta t_{\text{cruise}} = 50\ \text{kW} \times 1.545\ \text{hrs} = 77.3\ \text{kWh} \quad\checkmark$$

(The stored duration is 1.545 hrs — the table rounds it to 1.55 for display, so $50 \times 1.545 = 77.3$ rather than $77.5$ kWh.)

## Showcase 2 — Baseline Case, with 0.25 Cell-to-Battery Installation Weight (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 201.)*

This baseline case adds a **0.25 cell-to-battery installation weight penalty**: only 75% of the battery-pack mass is usable cell mass, so the **install factor is 0.75**. The effective pack specific energy drops accordingly:

$$E^{*} = 221\ \text{Wh/kg} \times 0.75 = 166\ \text{Wh/kg}$$

All other inputs ($L/D = 14$, $\eta = 0.82$, $m_{\text{bat}}/m_{\text{TOW}} = 0.35$, $V = 211$ km/hr) are unchanged from Showcase 1.

### Step 1 — Breguet (battery) range

$$R = \frac{166}{9.8} \times 0.82 \times 14 \times 0.35 = 68.1\ \frac{\text{m}\cdot\text{h}}{\text{s}}$$

$$R = 68.1 \times 3.6 = \underline{245\ \text{km}} \quad\checkmark$$

The range falls from 326 km to **245 km** — a factor of 0.75, exactly the install factor (range is linear in $E^{*}$).

### Step 2 — Cruise duration

$$\Delta t_{\text{cruise}} = \frac{R}{V} = \frac{245\ \text{km}}{211\ \text{km/hr}} = 1.16\ \text{hrs} \quad\checkmark$$

### Step 3 — Cruise energy

$$E_{\text{cruise}} = 50\ \text{kW} \times 1.161\ \text{hrs} = 58.0\ \text{kWh} \quad\checkmark$$

All non-cruise segment durations are zero, so **Total Mission Energy = 58.0 kWh**.

### Comparison

| Output | Install factor 1.0 | Baseline (install factor 0.75) |
|--------|-------------------|-------------------------------|
| Effective $E^{*}$ (Wh/kg) | 221 | 166 |
| Breguet / Cruise Range (km) | 326 | 245 |
| Cruise duration (hrs) | 1.55 | 1.16 |
| Cruise Energy / Total Mission Energy (kWh) | 77.3 | 58.0 |

The installation weight penalty scales range and cruise energy down by the install factor (0.75): $326 \times 0.75 = 245$ km, $77.3 \times 0.75 = 58.0$ kWh.

## Showcase 3 — Add Takeoff & Climb Energy (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 202.)*

Starting from the baseline case (install factor 0.75, $E^{*} = 166$ Wh/kg), this showcase now **charges the takeoff and climb segments their real durations** instead of zeroing them. The **total mission energy is fixed at 58.0 kWh** (the same battery), so any energy spent on takeoff and climb is *no longer available for cruise* — the cruise range shrinks.

> **Takeoff and Climb Energy Reduce Cruise Energy.**

### Step 1 — Takeoff and climb energy

Using $E = P \cdot \Delta t$ with the real segment durations from the mission data:

| Segment | Power (kW) | Duration (hrs) | Energy (kWh) |
|---------|-----------|----------------|--------------|
| Takeoff | 100 | 0.017 | $100 \times 0.017 = 1.7$ |
| Climb | 85 | 0.1 | $85 \times 0.1 = 8.5$ |

### Step 2 — Remaining cruise energy

The total mission energy budget is unchanged at 58.0 kWh. Subtract the takeoff and climb energy:

$$E_{\text{cruise}} = E_{\text{total}} - E_{TO} - E_{CLI} = 58.0 - 1.7 - 8.5 = 47.8\ \text{kWh} \quad\checkmark$$

### Step 3 — Cruise duration

$$\Delta t_{\text{cruise}} = \frac{E_{\text{cruise}}}{P_{\text{cruise}}} = \frac{47.8\ \text{kWh}}{50\ \text{kW}} = 0.96\ \text{hrs} \quad\checkmark$$

### Step 4 — Cruise range

$$R_{\text{cruise}} = V \cdot \Delta t_{\text{cruise}} = 211\ \text{km/hr} \times 0.956\ \text{hrs} = \underline{202\ \text{km}} \quad\checkmark$$

### Comparison across all three showcases

| Output | Install factor 1.0 | Baseline (0.75) | Add TO & Climb (0.75) |
|--------|-------------------|-----------------|-----------------------|
| Effective $E^{*}$ (Wh/kg) | 221 | 166 | 166 |
| Breguet Range (km) | 326 | 245 |  |
| Takeoff Energy (kWh) | 0.0 | 0.0 | 1.7 |
| Climb Energy (kWh) | 0.0 | 0.0 | 8.5 |
| Cruise Energy (kWh) | 77.3 | 58.0 | 47.8 |
| Total Mission Energy (kWh) | 77.3 | 58.0 | 58.0 |
| **Cruise Range (km)** | **326** | **245** | **202** |

The takeaway: **takeoff + climb energy (1.7 + 8.5 = 10.2 kWh) directly displaces cruise energy**, dropping the achievable range from 245 km to 202 km at the same total mission energy.

## Showcase 4 — Add 30-Minute Reserve (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 203.)*

Building on Showcase 3, this case now also reserves energy for the **30-minute reserve segment** (the daytime VFR requirement). The **total mission energy is still fixed at 58.0 kWh**, so the reserve — like takeoff and climb — comes out of the same budget, leaving even less for cruise.

> **30 Minute Reserve Reduces Useable Range.**

### Step 1 — Reserve energy

$$E_{\text{RES}} = P_{\text{RES}} \cdot \Delta t_{\text{RES}} = 50\ \text{kW} \times 0.50\ \text{hrs} = 25.0\ \text{kWh}$$

(Takeoff and climb energy are unchanged from Showcase 3: 1.7 kWh and 8.5 kWh.)

### Step 2 — Remaining cruise energy

Subtract takeoff, climb, and reserve from the fixed 58.0 kWh budget:

$$E_{\text{cruise}} = 58.0 - 1.7 - 8.5 - 25.0 = 22.8\ \text{kWh} \quad\checkmark$$

### Step 3 — Cruise duration

$$\Delta t_{\text{cruise}} = \frac{22.8\ \text{kWh}}{50\ \text{kW}} = 0.46\ \text{hrs} \quad\checkmark$$

### Step 4 — Cruise range

$$R_{\text{cruise}} = V \cdot \Delta t_{\text{cruise}} = 211\ \text{km/hr} \times 0.456\ \text{hrs} = \underline{96\ \text{km}} \quad\checkmark$$

The 30-minute reserve alone consumes 25.0 kWh — nearly half the total budget — cutting the useable cruise range from 202 km down to just **96 km**.

### Mass breakdown (shown on this slide, common to all cases)

| Quantity | Value | Units |
|----------|-------|-------|
| Empty Weight | 450 | kg |
| Payload | 200 | kg |
| Battery | 350 | kg |
| MTOW | 1000 | kg |
| $m_{\text{bat}}/\text{MTOW}$ | 0.350 | – |

### Comparison across all four showcases

| Output | Install factor 1.0 | Baseline (0.75) | Add TO & Climb | 30 min reserve |
|--------|-------------------|-----------------|----------------|----------------|
| Effective $E^{*}$ (Wh/kg) | 221 | 166 | 166 | 166 |
| Breguet Range (km) | 326 | 245 | 245 (n/a) | 245 (n/a) |
| Takeoff Energy (kWh) | 0.0 | 0.0 | 1.7 | 1.7 |
| Climb Energy (kWh) | 0.0 | 0.0 | 8.5 | 8.5 |
| Reserve Energy (kWh) | 0.0 | 0.0 | 0.0 | 25.0 |
| Cruise Energy (kWh) | 77.3 | 58.0 | 47.8 | 22.8 |
| Total Mission Energy (kWh) | 77.3 | 58.0 | 58.0 | 58.0 |
| **Cruise Range (km)** | **326** | **245** | **202** | **96** |

The full story: the ideal 326 km Breguet range is progressively eroded by the installation penalty (→245), takeoff/climb overhead (→202), and finally the mandatory 30-minute reserve (→96) — leaving less than a third of the ideal useable range.

## Showcase 5 — Usable SOC Window: Top 10% & Bottom 10% Not Used (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 204.)*

For good battery **cycle life**, the **top 10% and bottom 10% of the state of charge (SOC) are not used** — so only the middle 80% of the battery energy is available. This reserved 20% is charged as **SOC Energy**, coming out of the same fixed 58.0 kWh budget.

> **Battery Top 10% & Bottom 10% Not Used for Good Cycle Life.**

### Step 1 — SOC (unusable) energy

Reserve 20% of the total battery energy for the unused top/bottom SOC window:

$$E_{\text{SOC}} = 0.20 \times E_{\text{total}} = 0.20 \times 58.0 = 11.6\ \text{kWh}$$

(Takeoff 1.7 kWh, climb 8.5 kWh, and reserve 25.0 kWh are unchanged from Showcase 4. EOL Energy remains 0.0 kWh — end-of-life degradation is not yet applied on this slide.)

### Step 2 — Remaining cruise energy

Subtract takeoff, climb, reserve, and the SOC window from the fixed 58.0 kWh:

$$E_{\text{cruise}} = 58.0 - 1.7 - 8.5 - 25.0 - 11.6 = 11.2\ \text{kWh} \quad\checkmark$$

### Step 3 — Cruise duration

$$\Delta t_{\text{cruise}} = \frac{11.2\ \text{kWh}}{50\ \text{kW}} = 0.22\ \text{hrs} \quad\checkmark$$

### Step 4 — Cruise range

$$R_{\text{cruise}} = V \cdot \Delta t_{\text{cruise}} = 211\ \text{km/hr} \times 0.224\ \text{hrs} = \underline{47\ \text{km}} \quad\checkmark$$

Restricting to the usable 80% SOC window removes another 11.6 kWh, cutting the useable cruise range from 96 km down to just **47 km**.

### Comparison across all five showcases

| Output | Install factor 1.0 | Baseline (0.75) | Add TO & Climb | 30 min reserve | 20% SOC |
|--------|-------------------|-----------------|----------------|----------------|---------|
| Effective $E^{*}$ (Wh/kg) | 221 | 166 | 166 | 166 | 166 |
| Breguet Range (km) | 326 | 245 | 245 (n/a) | 245 (n/a) | 245 (n/a) |
| Takeoff Energy (kWh) | 0.0 | 0.0 | 1.7 | 1.7 | 1.7 |
| Climb Energy (kWh) | 0.0 | 0.0 | 8.5 | 8.5 | 8.5 |
| Reserve Energy (kWh) | 0.0 | 0.0 | 0.0 | 25.0 | 25.0 |
| SOC Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 11.6 |
| EOL Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Cruise Energy (kWh) | 77.3 | 58.0 | 47.8 | 22.8 | 11.2 |
| Total Mission Energy (kWh) | 77.3 | 58.0 | 58.0 | 58.0 | 58.0 |
| **Cruise Range (km)** | **326** | **245** | **202** | **96** | **47** |

The cumulative erosion: ideal 326 km → installation penalty (245) → takeoff/climb (202) → 30-min reserve (96) → usable SOC window (**47 km**). The realistic useable range is only about **14%** of the ideal Breguet range.

## Showcase 6 — Reserve 10% Capacity for End-of-Life Degradation (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 205.)*

A battery loses capacity as it ages. To ensure the airplane still meets its mission at **end of life (EOL)**, **10% of the battery capacity is held in reserve for life degradation**. This EOL Energy is charged against the same fixed 58.0 kWh budget.

> **Save 10% Battery Capacity for Life Degradation.**

### Step 1 — EOL (life-degradation) energy

$$E_{\text{EOL}} = 0.10 \times E_{\text{total}} = 0.10 \times 58.0 = 5.8\ \text{kWh}$$

(Takeoff 1.7, climb 8.5, reserve 25.0, and SOC 11.6 kWh are all unchanged from Showcase 5.)

### Step 2 — Remaining cruise energy

Subtract takeoff, climb, reserve, SOC, and EOL from the fixed 58.0 kWh:

$$E_{\text{cruise}} = 58.0 - 1.7 - 8.5 - 25.0 - 11.6 - 5.8 = 5.4\ \text{kWh} \quad\checkmark$$

### Step 3 — Cruise duration

$$\Delta t_{\text{cruise}} = \frac{5.4\ \text{kWh}}{50\ \text{kW}} = 0.11\ \text{hrs} \quad\checkmark$$

### Step 4 — Cruise range

$$R_{\text{cruise}} = V \cdot \Delta t_{\text{cruise}} = 211\ \text{km/hr} \times 0.108\ \text{hrs} = \underline{23\ \text{km}} \quad\checkmark$$

Holding back 10% for life degradation removes another 5.8 kWh, cutting the useable cruise range from 47 km down to just **23 km**.

### Comparison across all six showcases

| Output | Install factor 1.0 | Baseline (0.75) | Add TO & Climb | 30 min reserve | 20% SOC | 10% life degradation |
|--------|-------------------|-----------------|----------------|----------------|---------|----------------------|
| Effective $E^{*}$ (Wh/kg) | 221 | 166 | 166 | 166 | 166 | 166 |
| Breguet Range (km) | 326 | 245 | 245 (n/a) | 245 (n/a) | 245 (n/a) | 245 (n/a) |
| Takeoff Energy (kWh) | 0.0 | 0.0 | 1.7 | 1.7 | 1.7 | 1.7 |
| Climb Energy (kWh) | 0.0 | 0.0 | 8.5 | 8.5 | 8.5 | 8.5 |
| Reserve Energy (kWh) | 0.0 | 0.0 | 0.0 | 25.0 | 25.0 | 25.0 |
| SOC Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 11.6 | 11.6 |
| EOL Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.8 |
| Cruise Energy (kWh) | 77.3 | 58.0 | 47.8 | 22.8 | 11.2 | 5.4 |
| Total Mission Energy (kWh) | 77.3 | 58.0 | 58.0 | 58.0 | 58.0 | 58.0 |
| **Cruise Range (km)** | **326** | **245** | **202** | **96** | **47** | **23** |

The complete erosion story: ideal 326 km → installation penalty (245) → takeoff/climb (202) → 30-min reserve (96) → usable SOC window (47) → EOL degradation reserve (**23 km**). Once all real-world considerations are stacked up, the useable range is only about **7%** of the ideal Breguet range — a dramatic illustration of why naive Breguet-range estimates massively overstate electric-aircraft capability.

## Showcase 7 — Add a VTOL Takeoff & Landing? (Install Factor 0.75)

*Copyright © 2022 by Marty K. Bradley. (Slide 206.)*

The final case asks: what if we make it a **VTOL** (vertical takeoff and landing) aircraft? This requires adding vertical-lift hardware and a high-power hover, which changes several inputs at once.

> **Add 100 kg of vertical lift motors and 1 minute 500 kW hover.**
>
> Also: **L/D reduced by 2**, and the reserve now covers **1 TO + 1 Land + 10 min**.

### Step 1 — Vehicle changes from adding VTOL

**(a) Mass shift — 100 kg of vertical-lift motors.** Empty weight rises from 450 → **550 kg**. With MTOW fixed at 1000 kg and payload 200 kg, the battery shrinks:

$$m_{\text{bat}} = 1000 - 550 - 200 = 250\ \text{kg} \quad\Rightarrow\quad \frac{m_{\text{bat}}}{\text{MTOW}} = 0.250$$

**(b) Aerodynamics — L/D reduced by 2.** The lift rotors/hardware hurt cruise efficiency: $L/D = 14 - 2 = 12$. Because power required scales with $1/(L/D)$, the cruise, climb, and reserve powers all rise by the factor $14/12$:

| Segment | Baseline power | VTOL power ($\times 14/12$) |
|---------|---------------|-----------------------------|
| Cruise | 50 kW | $50 \times \tfrac{14}{12} = 58.3$ kW |
| Climb | 85 kW | $85 \times \tfrac{14}{12} = 99.2$ kW |
| Reserve | 50 kW | $50 \times \tfrac{14}{12} = 58.3$ kW |

**(c) Hover — 500 kW for 1 minute.** The vertical takeoff uses a 500 kW hover for 1 min (0.017 hrs).

### Step 2 — New total mission energy (smaller battery)

With only 250 kg of battery at the unrounded $E^{*} = 165.75$ Wh/kg:

$$E_{\text{total}} = 250\ \text{kg} \times 165.75\ \text{Wh/kg} = 41.4\ \text{kWh}$$

(The energy budget itself drops from 58.0 to 41.4 kWh because 100 kg of battery was traded for lift motors.)

### Step 3 — Segment energies ($E = P \cdot \Delta t$)

| Segment | Power (kW) | Duration (hrs) | Energy (kWh) |
|---------|-----------|----------------|--------------|
| Takeoff (500 kW hover, 1 min) | 500 | 0.017 | $500 \times 0.0167 = 8.3$ |
| Climb | 99.2 | 0.1 | $99.2 \times 0.1 = 9.9$ |
| Reserve (1 land hover + 10 min loiter) | 58.3 | 0.31 | $\approx 18.1$ |
| SOC (20% window) | – | – | 11.6 |
| EOL (10% degradation) | – | – | 5.8 |

### Step 4 — Remaining cruise energy (goes negative!)

$$E_{\text{cruise}} = 41.4 - 8.3 - 9.9 - 18.1 - 11.6 - 5.8 = \underline{-12.3\ \text{kWh}} \quad\checkmark$$

The overheads **exceed the entire available battery energy** — there is no energy left for cruise, and the balance is negative.

### Step 5 — Cruise range (negative = infeasible)

$$\Delta t_{\text{cruise}} = \frac{-12.3\ \text{kWh}}{58.3\ \text{kW}} = -0.21\ \text{hrs}$$

$$R_{\text{cruise}} = 211\ \text{km/hr} \times (-0.21\ \text{hrs}) = \underline{-45\ \text{km}} \quad\checkmark$$

A **negative range is physically impossible** — it means this VTOL configuration cannot even complete its takeoff, hover, climb, and mandatory reserves on the available battery, let alone cruise anywhere. The mission does not close.

### Comparison across all seven showcases

| Output | Install 1.0 | Baseline 0.75 | Add TO & Climb | 30 min reserve | 20% SOC | 10% life deg. | Add VTOL |
|--------|------------|---------------|----------------|----------------|---------|---------------|----------|
| $L/D$ | 14 | 14 | 14 | 14 | 14 | 14 | 12 |
| Effective $E^{*}$ (Wh/kg) | 221 | 166 | 166 | 166 | 166 | 166 | 166 |
| $m_{\text{bat}}$ (kg) | 350 | 350 | 350 | 350 | 350 | 350 | 250 |
| $m_{\text{bat}}/$MTOW | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.25 |
| Breguet Range (km) | 326 | 245 | 245 (n/a) | 245 (n/a) | 245 (n/a) | 245 (n/a) | 150 (n/a) |
| Takeoff Energy (kWh) | 0.0 | 0.0 | 1.7 | 1.7 | 1.7 | 1.7 | 8.3 |
| Climb Energy (kWh) | 0.0 | 0.0 | 8.5 | 8.5 | 8.5 | 8.5 | 9.9 |
| Reserve Energy (kWh) | 0.0 | 0.0 | 0.0 | 25.0 | 25.0 | 25.0 | 18.1 |
| SOC Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 11.6 | 11.6 | 11.6 |
| EOL Energy (kWh) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.8 | 5.8 |
| Cruise Energy (kWh) | 77.3 | 58.0 | 47.8 | 22.8 | 11.2 | 5.4 | -12.3 |
| Total Mission Energy (kWh) | 77.3 | 58.0 | 58.0 | 58.0 | 58.0 | 58.0 | 41.4 |
| **Cruise Range (km)** | **326** | **245** | **202** | **96** | **47** | **23** | **-45** |

The conclusion of the whole series: adding VTOL capability — heavier lift motors (less battery), worse cruise L/D, and a power-hungry hover — pushes the mission energy balance **negative**. With this battery technology, the VTOL version simply **cannot fly the mission**. It is a stark illustration of how demanding VTOL is on electric energy budgets.


