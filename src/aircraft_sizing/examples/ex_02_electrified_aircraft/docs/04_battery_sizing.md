# Reduced-Order Battery Sizing — Worked Example

**Source:** *Examples – Design of Electrified Propulsion Aircraft*, J. Lents.
Worksheet: **`BatterySizing`**. Companion lecture slides: **"Reduced Order Battery
Sizing Model"** (p. 42) and **"Example Sizing"** (p. 43).

This example reproduces the **reduced-order (RO) energy-storage sizing model**: given a
required **energy** and a required **peak power**, plus a small set of cell/pack
characteristics, it returns the **pack weight** and reports the pack's **usable energy
rating**, **energy margin**, and **minimum state of charge (MinSOC)**. The model is
purely feed-forward algebra — no iteration — so it is exact and quick to check by hand.

The single most important idea is the `max()` in the capacity equation: a pack must be big
enough to satisfy **both** the mission energy **and** the peak-power draw, so its size is
set by whichever of those two requirements is larger. The two worked cases below land on
opposite sides of that crossover.

---

## 1. The reduced-order model (slide p. 42)

**RO model parameters**

- **Specific energy, `SE`** (Wh/kg) — cell-level energy per unit weight.
- **Max steady c-rate, `Crate`** (1/hours) — how fast the cell can be discharged; a
  `Crate` of 2.5 means the cell can deliver 2.5× its rated energy per hour.
- **Discharge efficiency, `Eff`** — fraction of stored energy delivered to the bus.
- **Max depth of discharge, `MaxDD`** (%) — maximum allowable discharge (so the usable
  fraction is `MaxDD`, and the floor state of charge is `1 − MaxDD`).
- **Pack burden, `PB`** (%) — ratio of non-cell (structure, thermal, BMS, wiring) weight to
  cell weight.

**Inputs**

- **Required energy** (kWh).
- **Required peak power** (kW). *(The slide labels this "W"; the worksheet — and this
  narrative — work consistently in kW, so the capacity comes out in kWh.)*

**Equations** (worksheet notation on the right; symbolic form on the left):

$$\text{Rate}_E = \frac{\text{Energy}}{\text{Eff}}
\qquad
\text{Cap}_E = \frac{\text{Rate}_E}{\text{MaxDD}}$$

$$\text{Rate}_P = \frac{\text{Power}/\text{Eff}}{\text{Crate}}
\qquad
\text{Cap} = \max\!\left(\text{Cap}_E,\ \text{Rate}_P\right)$$

$$\text{Weight} = \frac{(1 + \text{PB}) \cdot 1000 \cdot \text{Cap}}{\text{SE}}
\qquad
\text{Rating} = \text{MaxDD} \cdot \text{Cap}$$

$$\text{Margin} = \text{Cap} - \text{Rate}_E
\qquad
\text{MinSOC} = \frac{\text{Margin}}{\text{Cap}}$$

---

## 2. Cell / pack parameters

Worksheet cells `B2:D7`. The sheet defines two candidate technologies side by side, but
**only the battery column drives the sizing table** in §5 (every formula there references the
battery cells `$C2:$C7`). The super-capacitor column supplies only `SE` and `SP`; §6 extends
the same equations to it as a comparison.

| Parameter | Symbol | Cell | Battery | Super Cap | Formula / note |
|-----------|--------|------|:-------:|:---------:|----------------|
| Specific energy (Wh/kg) | `SE` | C2 / D2 | 300 | 10 | input |
| Max steady c-rate (1/hr) | `Crate` | C3 | 2.5 | — | input (battery only) |
| Specific power (W/kg) | `SP` | C4 / D4 | 750 | 10000 | battery: `=C2*C3`; super cap: input |
| Discharge efficiency | `Eff` | C5 | 0.96 | — | input (battery only) |
| Max depth of discharge | `MaxDD` | C6 | 0.8 | — | input (battery only) |
| Pack burden | `PB` | C7 | 0.35 | — | input (battery only) |

Because `SP = SE · Crate`, the c-rate implied by the super-cap specific power is
`Crate = SP / SE = 10000 / 10 = 1000` /hr — a super-capacitor can dump its entire capacity in
seconds, which is exactly why it is a *power* device rather than an *energy* device (§6).

---

## 3. Inputs — the two load cases (slide p. 43)

The slide shows two mission power-vs-time profiles sized with the **same battery**
parameters (`SE = 300`, `Crate = 2.5`, `Eff = 0.96`, `MaxDD = 0.8`, `PB = 0.35`):

- **Example 1** (left) — a long, high-power discharge that decays from a **4200 kW** peak,
  totalling **1370 kWh**. In the worksheet these two headline numbers are entered directly
  (`C19 = 4200`, `C20 = 1370`), read off the detailed load profile rather than re-integrated.
  *(The small trace near the bottom of the left chart is a secondary/accessory load shown for
  context; it is not part of the sizing inputs.)*
- **Example 2** (right) — a **500 kW** baseline with a brief **2000 kW** spike, totalling
  **275 kWh**. This one is computed from the tabulated step profile below.

### Example 2 mission profile (worksheet rows 11–16)

Each pair of rows defines a constant-power segment `(t_start → t_end)`; the segment energy is
placed on the second row of the pair.

| Cell (Time) | Time (min) | Cell (Power) | Power (kW) | Cell (Energy) | Segment energy (kWh) | Excel formula |
|:-----------:|:----------:|:------------:|:----------:|:-------------:|:--------------------:|---------------|
| B11 | 0  | E11 | 500  | —   | —        | — |
| B12 | 20 | E12 | 500  | F12 | 166.667  | `=E12*(B12-B11)/60` |
| B13 | 20 | E13 | 2000 | —   | —        | — |
| B14 | 21 | E14 | 2000 | F14 | 33.333   | `=E14*(B14-B13)/60` |
| B15 | 21 | E15 | 500  | —   | —        | — |
| B16 | 30 | E16 | 500  | F16 | 75.000   | `=E16*(B16-B15)/60` |

Read as three segments: **0–20 min @ 500 kW** (166.667 kWh), **20–21 min @ 2000 kW**
(33.333 kWh), **21–30 min @ 500 kW** (75.000 kWh).

| Derived input | Symbol | Cell | Example 1 | Example 2 | Formula |
|---------------|--------|------|:---------:|:---------:|---------|
| Max power (kW) | `Power` | C19 / D19 | 4200 | 2000 | Ex 1 input; Ex 2 `=MAX(E11:E16)` |
| Energy (kWh) | `Energy` | C20 / D20 | 1370 | 275 | Ex 1 input; Ex 2 `=SUM(F12:F16)` |

---

## 4. Sizing equations (worksheet rows 22–29)

Formulae shown for **Example 1** (column C); Example 2 (column D) is identical with the
column index changed. Every reference `$C2…$C7` is a **battery** parameter.

| Row | Quantity | Units | Excel formula (col C) | Symbolic form |
|-----|----------|-------|-----------------------|---------------|
| 22 | Rate-E | kWh | `=C20/$C5` | $\text{Rate}_E = \text{Energy}/\text{Eff}$ |
| 23 | Cap-E | kWh | `=C22/$C6` | $\text{Cap}_E = \text{Rate}_E/\text{MaxDD}$ |
| 24 | Rate-P | kWh | `=C19/$C5/$C3` | $\text{Rate}_P = \text{Power}/\text{Eff}/\text{Crate}$ |
| 25 | Cap | kWh | `=MAX(C23:C24)` | $\text{Cap} = \max(\text{Cap}_E, \text{Rate}_P)$ |
| 26 | Weight | kg | `=(1+$C7)*1000*C25/$C2` | $\text{Weight} = (1+\text{PB})\cdot 1000 \cdot \text{Cap}/\text{SE}$ |
| 27 | Rating | kWh | `=$C6*C25` | $\text{Rating} = \text{MaxDD}\cdot\text{Cap}$ |
| 28 | Margin | kWh | `=C25-C22` | $\text{Margin} = \text{Cap} - \text{Rate}_E$ |
| 29 | MinSOC | – | `=C28/C25` | $\text{MinSOC} = \text{Margin}/\text{Cap}$ |

**What each line means**

- **Rate-E** — the energy the pack must *store* to *deliver* the mission energy, grossed up
  for the discharge inefficiency (`/Eff`).
- **Cap-E** — the **energy-driven** capacity: you can only use `MaxDD` of the pack, so the
  installed capacity must be `Rate-E / MaxDD`.
- **Rate-P** — the **power-driven** capacity: at the max c-rate a pack of capacity `C` can
  deliver `Crate · C`, so meeting the peak power needs `Power/Eff/Crate` of capacity.
- **Cap** — the pack size actually installed: the larger of the two requirements. Whichever
  wins tells you the mission is *energy-limited* or *power-limited*.
- **Weight** — cell weight `1000·Cap/SE` (the `1000` converts kWh→Wh so it divides cleanly by
  `SE` in Wh/kg), scaled up by the pack burden `(1+PB)`.
- **Rating** — the *usable* energy the installed pack actually provides (`MaxDD·Cap`).
- **Margin / MinSOC** — how much usable energy is left over above the mission requirement, and
  the resulting floor state of charge. When the pack is **energy-limited**, `Cap = Cap_E`, so
  `MinSOC = 1 − MaxDD` exactly (the pack is worked down to its allowable floor). When it is
  **power-limited**, the pack is oversized on energy and `MinSOC` sits well above the floor.

---

## 5. Worked examples (battery)

### Example 1 — energy-limited

Inputs: `Energy = 1370 kWh`, `Power = 4200 kW`.

$$\text{Rate}_E = \frac{1370}{0.96} = 1427.083\ \text{kWh}
\qquad
\text{Cap}_E = \frac{1427.083}{0.8} = 1783.854\ \text{kWh}$$

$$\text{Rate}_P = \frac{4200}{0.96 \times 2.5} = 1750.000\ \text{kWh}$$

$$\text{Cap} = \max(1783.854,\ 1750.000) = 1783.854\ \text{kWh}\ \ (\textbf{energy-limited})$$

$$\text{Weight} = \frac{1.35 \times 1000 \times 1783.854}{300} = 8027.34\ \text{kg}$$

$$\text{Rating} = 0.8 \times 1783.854 = 1427.083\ \text{kWh}
\qquad
\text{Margin} = 1783.854 - 1427.083 = 356.771\ \text{kWh}$$

$$\text{MinSOC} = \frac{356.771}{1783.854} = 0.200 = 1 - \text{MaxDD}\quad\checkmark$$

The energy requirement (`Cap_E = 1784 kWh`) narrowly beats the power requirement
(`Rate_P = 1750 kWh`), so the pack is **energy-limited** and is discharged all the way to its
20 % floor.

### Example 2 — power-limited

Inputs: `Energy = 275 kWh`, `Power = 2000 kW`.

$$\text{Rate}_E = \frac{275}{0.96} = 286.458\ \text{kWh}
\qquad
\text{Cap}_E = \frac{286.458}{0.8} = 358.073\ \text{kWh}$$

$$\text{Rate}_P = \frac{2000}{0.96 \times 2.5} = 833.333\ \text{kWh}$$

$$\text{Cap} = \max(358.073,\ 833.333) = 833.333\ \text{kWh}\ \ (\textbf{power-limited})$$

$$\text{Weight} = \frac{1.35 \times 1000 \times 833.333}{300} = 3750.00\ \text{kg}$$

$$\text{Rating} = 0.8 \times 833.333 = 666.667\ \text{kWh}
\qquad
\text{Margin} = 833.333 - 286.458 = 546.875\ \text{kWh}$$

$$\text{MinSOC} = \frac{546.875}{833.333} = 0.656$$

Here the **2000 kW peak** dominates: the pack must be big enough to deliver that power at its
c-rate, which forces `Cap = 833 kWh` — more than twice the energy-driven size. The pack ends
the mission with a large reserve (`MinSOC = 0.66`), i.e. it is oversized on energy because it
was sized for power.

### Battery results (reproduction of `C22:D29`)

| Quantity | Units | Example 1 | Example 2 |
|----------|-------|:---------:|:---------:|
| Rate-E | kWh | 1427.083 | 286.458 |
| Cap-E | kWh | 1783.854 | 358.073 |
| Rate-P | kWh | 1750.000 | 833.333 |
| **Cap** | kWh | **1783.854** | **833.333** |
| Sizing driver | – | energy | power |
| **Weight** | kg | **8027.34** | **3750.00** |
| Rating | kWh | 1427.083 | 666.667 |
| Margin | kWh | 356.771 | 546.875 |
| **MinSOC** | – | **0.200** | **0.656** |

All values reproduce the worksheet's cached results exactly.

---

## 6. Technology comparison — battery vs super capacitor (extension)

> **Extension beyond the worksheet.** The sheet sizes only the battery. Here the same
> equations are applied to the super-capacitor parameter set (`SE = 10 Wh/kg`,
> `SP = 10000 W/kg` ⇒ `Crate = SP/SE = 1000` /hr). The sheet does **not** define `Eff`,
> `MaxDD`, or `PB` for the super cap, so those are **carried over from the battery**
> (`Eff = 0.96`, `MaxDD = 0.8`, `PB = 0.35`) to keep the comparison apples-to-apples.

| Quantity | Units | Ex 1 Battery | Ex 1 Super Cap | Ex 2 Battery | Ex 2 Super Cap |
|----------|-------|:------------:|:--------------:|:------------:|:--------------:|
| Rate-P | kWh | 1750.000 | 4.375 | 833.333 | 2.083 |
| Cap | kWh | 1783.854 | 1783.854 | 833.333 | 358.073 |
| Sizing driver | – | energy | energy | power | energy |
| **Weight** | kg | **8027.34** | **240 820.31** | **3750.00** | **48 339.84** |
| MinSOC | – | 0.200 | 0.200 | 0.656 | 0.200 |

The super capacitor's enormous specific power collapses its power-driven capacity to a few
kWh (`Rate-P ≈ 4 kWh` in Example 1), so it is **always energy-limited** here. But its
specific energy is 30× worse than the battery's (10 vs 300 Wh/kg), so the energy-limited pack
weighs 30× more — **241 tonnes** for Example 1. The lesson is not that the arithmetic is
wrong, but that a super capacitor is the wrong tool for an *energy* mission: it earns its keep
only on short, high-power *pulses*, where `Rate-P` (not `Cap-E`) sets the size.

---

## 7. Takeaways

- **The `max()` is the whole model.** A pack must satisfy energy **and** power; its size is
  set by the binding one. Example 1 is energy-limited; Example 2 is power-limited — same
  battery, opposite drivers.
- **MinSOC tells you which regime you are in.** Energy-limited ⇒ `MinSOC = 1 − MaxDD` (fully
  used). Power-limited ⇒ `MinSOC` well above the floor (energy to spare).
- **Weight scales as `Cap / SE`.** Specific energy dominates pack mass; the pack burden
  `(1+PB)` and the `1000` kWh→Wh factor are the only other levers on weight.
- **Technology matters through `SE` and `SP` together.** High `SP` (super cap) makes power
  cheap but high `SE` (battery) makes energy cheap; the crossover in `max(Cap_E, Rate_P)` is
  where a technology stops being worth it.

---

## 8. Reproduce it

```python
def size_pack(SE, Crate, Eff, MaxDD, PB, energy_kwh, power_kw):
    rate_e = energy_kwh / Eff
    cap_e  = rate_e / MaxDD
    rate_p = power_kw / Eff / Crate
    cap    = max(cap_e, rate_p)
    return {
        "rate_e": rate_e, "cap_e": cap_e, "rate_p": rate_p, "cap": cap,
        "weight_kg": (1 + PB) * 1000 * cap / SE,
        "rating_kwh": MaxDD * cap,
        "margin_kwh": cap - rate_e,
        "min_soc": (cap - rate_e) / cap,
        "driver": "energy" if cap_e >= rate_p else "power",
    }

battery = dict(SE=300, Crate=2.5, Eff=0.96, MaxDD=0.8, PB=0.35)
print(size_pack(**battery, energy_kwh=1370, power_kw=4200))  # Example 1 -> 8027.34 kg, energy-limited
print(size_pack(**battery, energy_kwh=275,  power_kw=2000))  # Example 2 -> 3750.00 kg, power-limited
```
