# Range Equation — Worked Example

## Baseline Parameters

| Parameter | Symbol | Value | Units |
|-----------|--------|-------|-------|
| Specific energy | $E^{*}$ | 300 | Wh/kg |
| Lift-to-drag ratio | $L/D$ | 15 | – |
| Total efficiency | $\eta_{\text{total}}$ | 70% = 0.7 | – |
| Battery mass fraction | $m_{\text{battery}}/m$ | 20% = 0.2 | – |
| Empty mass fraction | $m_{\text{empty}}/m$ | 55% = 0.55 | – |
| Payload mass | $m_{\text{payload}}$ | 1000 | kg |

## Goal

**Use the equation to reproduce the same range.**

The form of the range equation used here is written in terms of the **battery mass fraction**:

$$R = E^{*} \cdot \eta_{\text{total}} \cdot \frac{1}{g} \cdot \frac{L}{D} \cdot \frac{m_{\text{battery}}}{m}$$

## Step-by-Step Walkthrough

### Step 1 — Substitute the values

$$R = \frac{300\ \text{Wh/kg}}{9.8\ \text{m/s}^2} \times 0.7 \times 15 \times 0.2$$

- $E^{*} = 300$ Wh/kg
- $g = 9.8$ m/s²
- $\eta_{\text{total}} = 0.7$
- $L/D = 15$
- $m_{\text{battery}}/m = 0.2$

### Step 2 — Evaluate the numeric product

$$\frac{300}{9.8} \times 0.7 \times 15 \times 0.2 = 64.3$$

So $R = 64.3$ — but in the mixed units of $\dfrac{\text{Wh/kg}}{\text{m/s}^2}$, which still needs to be resolved.

### Step 3 — Resolve the units

Use the following identities:

- $W = \text{N}\cdot\text{m/s}$  (a watt is a newton-metre per second)
- $g = 9.8\ \text{m/s}^2 = 9.8\ \text{N/kg}$

Substituting, the units simplify:

$$\frac{\text{Wh/kg}}{\text{m/s}^2}
= \frac{(\text{N}\cdot\text{m/s})\cdot\text{h} / \text{kg}}{\text{N/kg}}
= \frac{\text{m}}{\text{s}} \cdot \text{h}$$

So the intermediate result is:

$$R = 64.3\ \frac{\text{m}\cdot\text{h}}{\text{s}}$$

### Step 4 — Convert to kilometres

Convert hours to seconds ($1\ \text{h} = 60^2\ \text{s} = 3600\ \text{s}$) and metres to kilometres ($1\ \text{km} = 1000\ \text{m}$):

$$R = 64.3 \times \frac{60^2\ (\text{s/hr})}{1000\ (\text{m/km})}$$

$$R = \frac{64.3 \times 3600}{1000} = \underline{231\ \text{km}}$$

## Result

$$\boxed{R \approx 231\ \text{km}}$$

> **Note on units:** Keeping $E^{*}$ in Wh/kg (rather than converting to J/kg up front) leaves the answer in the mixed units $\frac{\text{m}\cdot\text{h}}{\text{s}}$. The final factor of $60^2/1000$ handles both the hour→second and metre→kilometre conversions in one step.
