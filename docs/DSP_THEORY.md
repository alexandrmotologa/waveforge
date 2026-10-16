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

## 3. Karplus-Strong Physical String Modeling

The Karplus-Strong algorithm simulates plucked acoustic strings through a filtered recursive delay loop:

$$y[n] = x[n] + \rho \cdot H_{\text{loss}}(y[n - N])$$

where:
- $N = \text{round}(f_s / f_0)$ represents the fundamental wavelength in samples.
- $\rho \in [0.95, 0.999]$ represents the loop reflection decay coefficient.
- $H_{\text{loss}}(z)$ is a one-pole lowpass filter representing high-frequency loss due to string stiffness and air damping:
  $$y_{\text{loss}}[n] = (1 - d) \cdot y_{\text{loss}}[n-1] + d \cdot x_{\text{loss}}[n]$$
- $x[n]$ is a finite burst of white noise injected at $t = 0$ over duration $N$ samples.

---

## 4. Vocal Formant Resonator

Human vowels are produced by resonances in the vocal tract termed formants ($F_1, F_2, F_3$). WaveForge models vowels as three parallel second-order bandpass resonators:

$$y_{\text{vowel}}[n] = \sum_{k=1}^3 g_k \cdot \text{BPF}_k(x[n], F_k, Q_k)$$

Standard acoustic formant frequencies used for vowel interpolation:
- Vowel A: $F_1 = 800\text{ Hz}, F_2 = 1200\text{ Hz}, F_3 = 2800\text{ Hz}$
- Vowel E: $F_1 = 500\text{ Hz}, F_2 = 1800\text{ Hz}, F_3 = 2500\text{ Hz}$
- Vowel I: $F_1 = 270\text{ Hz}, F_2 = 2300\text{ Hz}, F_3 = 3000\text{ Hz}$
- Vowel O: $F_1 = 450\text{ Hz}, F_2 = 800\text{ Hz}, F_3 = 2500\text{ Hz}$
- Vowel U: $F_1 = 300\text{ Hz}, F_2 = 870\text{ Hz}, F_3 = 2250\text{ Hz}$

A continuous parameter $p \in [0.0, 4.0]$ interpolates formant center frequencies across phonemes.

---

## 5. Stereo BBD Chorus and Quadrature Modulation

Analog bucket-brigade device (BBD) chorus relies on variable delay lines modulated by low-frequency oscillators in quadrature phase split ($\Delta \phi = 90^\circ = \pi/2$):

$$\tau_L(t) = \tau_0 + \Delta \tau \cdot \sin(2\pi f_{\text{rate}} t)$$
$$\tau_R(t) = \tau_0 + \Delta \tau \cdot \cos(2\pi f_{\text{rate}} t)$$

Fractional sample delay readings use 4-point, 3rd-order Hermite polynomial interpolation to eliminate clicks and phase distortion:

$$h_0(s) = -\frac{1}{2}s^3 + s^2 - \frac{1}{2}s$$
$$h_1(s) = \frac{3}{2}s^3 - \frac{5}{2}s^2 + 1$$
$$h_2(s) = -\frac{3}{2}s^3 + 2s^2 + \frac{1}{2}s$$
$$h_3(s) = \frac{1}{2}s^3 - \frac{1}{2}s^2$$

---

## 6. Roland TR-808 Percussion Synthesis

### Kick Drum
The 808 kick combines an exponential frequency sweep with a fast attack click and soft saturation:

$$f_{\text{kick}}(t) = f_{\text{end}} + (f_{\text{start}} - f_{\text{end}}) \cdot e^{-t / \tau_{\text{pitch}}}$$
$$y_{\text{body}}(t) = \sin\left(2\pi \int_0^t f_{\text{kick}}(u) \, du\right)$$
$$y_{\text{kick}}(t) = \tanh\left(D \cdot (y_{\text{body}}(t) + c(t)) \cdot e^{-t / \tau_{\text{amp}}}\right)$$

### Snare Drum
The snare combines dual harmonic sinusoidal body tones and bandpass-filtered white noise:

$$y_{\text{snare}}(t) = \tanh\left(1.5 \cdot \left[(1 - m) \cdot y_{\text{body}}(t) e^{-t / \tau_t} + m \cdot y_{\text{noise}}(t) e^{-t / \tau_s}\right]\right)$$

### 6-Oscillator Metallic Hi-Hat
Simulates the TR-808 metallic cymbal circuit by summing six inharmonic square wave oscillators through a highpass filter:

$$F_{\text{cluster}} = \{243, 340, 540, 800, 1080, 1200\}\text{ Hz}$$
$$y_{\text{metallic}}(t) = \text{HPF}\left(\frac{1}{6} \sum_{k=1}^6 \text{sgn}(\sin(2\pi F_k t)), f_c = 7200\text{ Hz}\right)$$

---

## 7. 303 Portamento Slide Dynamics

Portamento glide follows single-pole exponential smoothing toward the target note frequency:

$$f[n] = f_{\text{target}} + (f[n-1] - f_{\text{target}}) \cdot e^{-1 / (\tau_{\text{slide}} f_s)}$$

When slide is inactive, $f[n] = f_{\text{target}}$ transitions instantaneously on step triggers.
