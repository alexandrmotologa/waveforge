# Digital Signal Processing Theory in WaveForge

WaveForge uses exact analytical mathematical formulations for signal synthesis and filtering. This document details the mathematical algorithms implemented across the engine.

## 1. Anti-Aliased PolyBLEP Oscillators

Naive digital waveforms (sawtooth, square waves) contain instantaneous step jumps. In discrete sampling, discontinuities generate infinite harmonic series that reflect across the Nyquist limit ($f_s / 2$), causing aliasing noise.

The Polynomial Band-Limited Step (PolyBLEP) algorithm replaces sharp transitions with a local 2nd-order polynomial residual.

Let normalized phase be $t \in [0.0, 1.0)$, and normalized phase increment be $dt = f_0 / f_s$.

### PolyBLEP Residual Function
For a step discontinuity at phase 0:

$$\text{polyblep}(t, dt) = \begin{cases} 2 \left(\frac{t}{dt}\right) - \left(\frac{t}{dt}\right)^2 - 1.0 & \text{if } 0 \le t < dt \\ \left(\frac{t-1}{dt}\right)^2 + 2\left(\frac{t-1}{dt}\right) + 1.0 & \text{if } 1-dt < t < 1 \\ 0.0 & \text{otherwise} \end{cases}$$

### Waveform Formulations

#### Sawtooth Wave
Naive sawtooth ramp:
$$y_{\text{naive}}(t) = 2t - 1.0$$
Corrected PolyBLEP output:
$$y_{\text{saw}}(t) = y_{\text{naive}}(t) - \text{polyblep}(t, dt)$$

#### Square and Pulse Waves (Duty Cycle $w \in (0, 1)$)
$$y_{\text{naive}}(t) = \begin{cases} +1.0 & \text{if } t < w \\ -1.0 & \text{if } t \ge w \end{cases}$$
Corrected PolyBLEP output:
$$y_{\text{pulse}}(t) = y_{\text{naive}}(t) + \text{polyblep}(t, dt) - \text{polyblep}((t - w + 1) \pmod 1, dt)$$

#### Triangle Wave
Synthesized via analytical integration of the anti-aliased square wave with a 1-pole highpass DC-blocking filter ($R = 0.999$) to remove drift:
$$y_{\text{tri}}[n] = y_{\text{tri}}[n-1] + 4.0 \cdot dt \cdot y_{\text{pulse}}[n]$$

---

## 2. Biquad Filter Difference Equations (RBJ Cookbook)

WaveForge implements all 8 biquad topologies defined in Robert Bristow-Johnson's Audio EQ Cookbook using the Direct Form II Transposed (DF2T) structure.

### Direct Form II Transposed Difference Equations
Normalized by $a_0 = 1$:

$$y[n] = b_0 x[n] + z_1[n-1]$$
$$z_1[n] = b_1 x[n] - a_1 y[n] + z_2[n-1]$$
$$z_2[n] = b_2 x[n] - a_2 y[n]$$

DF2T requires only two internal delay registers ($z_1, z_2$) and provides numerical resistance against coefficient quantization artifacts.

### Coefficient Calculations
Given cutoff frequency $f_0$, sample rate $f_s$, resonance $Q$, and gain $A = 10^{\text{dB} / 40}$:

$$\omega_0 = 2\pi \frac{f_0}{f_s}$$
$$\alpha = \frac{\sin(\omega_0)}{2Q}$$

#### Lowpass Filter (LPF)
$$b_0 = \frac{1 - \cos(\omega_0)}{2}, \quad b_1 = 1 - \cos(\omega_0), \quad b_2 = \frac{1 - \cos(\omega_0)}{2}$$
$$a_0 = 1 + \alpha, \quad a_1 = -2 \cos(\omega_0), \quad a_2 = 1 - \alpha$$

#### Highpass Filter (HPF)
$$b_0 = \frac{1 + \cos(\omega_0)}{2}, \quad b_1 = -(1 + \cos(\omega_0)), \quad b_2 = \frac{1 + \cos(\omega_0)}{2}$$
$$a_0 = 1 + \alpha, \quad a_1 = -2 \cos(\omega_0), \quad a_2 = 1 - \alpha$$

#### Bandpass Filter (BPF, 0 dB peak gain)
$$b_0 = \alpha, \quad b_1 = 0, \quad b_2 = -\alpha$$
$$a_0 = 1 + \alpha, \quad a_1 = -2 \cos(\omega_0), \quad a_2 = 1 - \alpha$$

#### Notch Filter
$$b_0 = 1, \quad b_1 = -2 \cos(\omega_0), \quad b_2 = 1$$
$$a_0 = 1 + \alpha, \quad a_1 = -2 \cos(\omega_0), \quad a_2 = 1 - \alpha$$

---

## 3. Analog Exponential Envelopes

Analog envelope generators use capacitor charging circuits with characteristic exponential curves:

$$V(t) = V_{\text{target}} + (V(t-1) - V_{\text{target}}) \cdot e^{-1 / (\tau f_s)}$$

- **Attack Stage**: Targets an overshooting voltage ($1.5$) so that crossing $1.0$ remains punchy and near-linear before switching.
- **Decay Stage**: Decays toward the exact sustain level.
- **Release Stage**: Decays toward a negative offset ($-0.05$) to ensure zero level is cleanly achieved without an infinite numeric tail.
