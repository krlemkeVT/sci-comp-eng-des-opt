# Equations for Electrified Aircraft

## Range Equation

$$R = E^{*} \cdot \eta_{\text{total}} \cdot \frac{1}{g} \cdot \frac{L}{D} \cdot \left(1 - \frac{m_{\text{empty}}}{m} - \frac{m_{\text{payload}}}{m}\right)$$

## Symbols

| Symbol | Description |
|--------|-------------|
| $R$ | Range |
| $E^{*}$ | Specific energy |
| $\eta_{\text{total}}$ | Total efficiency |
| $g$ | Gravitational acceleration |
| $L/D$ | Lift-to-drag ratio |
| $m$ | Total mass |
| $m_{\text{empty}}$ | Empty mass |
| $m_{\text{payload}}$ | Payload mass |
| $\text{PAX}$ | Number of passengers |
| $m_{\text{pax}}$ | Mass per passenger |

## Total Mass Equation

$$m = \frac{\text{PAX} \cdot m_{\text{pax}}}{1 - \dfrac{m_{\text{empty}}}{m} - \dfrac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R}$$

### Derivation (from the Range Equation)

**Step 1 — Start from the range equation.**

$$R = E^{*} \cdot \eta_{\text{total}} \cdot \frac{1}{g} \cdot \frac{L}{D} \cdot \left(1 - \frac{m_{\text{empty}}}{m} - \frac{m_{\text{payload}}}{m}\right)$$

**Step 2 — Group the constant prefactor.** Let

$$K = E^{*} \cdot \eta_{\text{total}} \cdot \frac{1}{g} \cdot \frac{L}{D}$$

so the range equation becomes

$$R = K \left(1 - \frac{m_{\text{empty}}}{m} - \frac{m_{\text{payload}}}{m}\right)$$

**Step 3 — Divide both sides by $K$.**

$$\frac{R}{K} = 1 - \frac{m_{\text{empty}}}{m} - \frac{m_{\text{payload}}}{m}$$

Substituting $K$ back in, the left-hand side is

$$\frac{R}{K} = \frac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R$$

which is the energy/range term that appears in the final denominator.

**Step 4 — Isolate the payload mass fraction.**

$$\frac{m_{\text{payload}}}{m} = 1 - \frac{m_{\text{empty}}}{m} - \frac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R$$

**Step 5 — Multiply through by $m$ and solve for $m$.**

$$m_{\text{payload}} = m \left(1 - \frac{m_{\text{empty}}}{m} - \frac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R\right)$$

$$m = \frac{m_{\text{payload}}}{1 - \dfrac{m_{\text{empty}}}{m} - \dfrac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R}$$

**Step 6 — Express the payload as passengers.** The payload mass is the number of passengers times the mass per passenger, $m_{\text{payload}} = \text{PAX} \cdot m_{\text{pax}}$:

$$m = \frac{\text{PAX} \cdot m_{\text{pax}}}{1 - \dfrac{m_{\text{empty}}}{m} - \dfrac{g}{E^{*} \cdot \eta_{\text{total}} \cdot L/D} \cdot R}$$

> **Note:** The empty mass fraction $\dfrac{m_{\text{empty}}}{m}$ remains on the right-hand side. It is treated as a fixed *fraction* (e.g. 55%), so the equation is used with that fraction specified rather than $m_{\text{empty}}$ as an absolute value.
