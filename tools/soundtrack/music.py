"""
Original synthwave score for the Vault Runner 3D videos (pure numpy, no samples).

Every sound is synthesized: band-limited saws (polyBLEP) for pads, bass, arps
and lead; sine sweeps and filtered noise for drums; a convolution reverb; and
kick sidechain ducking. The tempo is tuned per video so a bar line lands exactly
on the end of the intro card AND on the first frame of the boss fight, where
the drop hits.

    python tools/soundtrack/music.py      # writes music_full.wav, music_linkedin.wav
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
import wave, sys

SR = 44100
rng = np.random.default_rng(423)

# ------------------------------------------------------------ building blocks
def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def saw(freq, n, detune_cents=0.0, phase0=None):
    """Band-limited (polyBLEP) sawtooth. freq may be a scalar or an array."""
    f = np.broadcast_to(np.asarray(freq, float) * 2 ** (detune_cents / 1200), (n,))
    dt = f / SR
    p0 = rng.random() if phase0 is None else phase0
    t = (p0 + np.cumsum(dt)) % 1.0
    y = 2 * t - 1
    m = t < dt
    x = t[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = t > 1 - dt
    x = (t[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y

def filt(x, fc, kind="low", order=2):
    if kind == "band":
        sos = butter(order, [fc[0], min(fc[1], 0.45 * SR)], "band", fs=SR, output="sos")
    else:
        sos = butter(order, min(fc, 0.45 * SR), kind, fs=SR, output="sos")
    return sosfilt(sos, x)

def adsr(n, a, d, s, r, gate):
    """gate = seconds the note is held; release follows."""
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = t > gate
    e[rel] = e[rel] * np.exp(-(t[rel] - gate) / max(r, 1e-4))
    return e

def noise(n):
    return rng.standard_normal(n)

def pan2(x, p):
    a = (p + 1) * np.pi / 4
    return np.vstack([x * np.cos(a), x * np.sin(a)])


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR) + SR
        self.dry = np.zeros((2, self.n))
        self.duck = np.zeros((2, self.n))          # sidechained by the kick
        self.rev = np.zeros((2, self.n))           # reverb send
        self.sc = np.ones(self.n)

    def add(self, t, sig, bus="dry", pan=0.0, send=0.0):
        if sig.ndim == 1:
            sig = pan2(sig, pan)
        i = int(round(t * SR))
        if i < 0:
            sig = sig[:, -i:]
            i = 0
        j = min(self.n, i + sig.shape[1])
        if j <= i:
            return
        seg = sig[:, : j - i]
        getattr(self, bus)[:, i:j] += seg
        if send:
            self.rev[:, i:j] += seg * send

    def kick_duck(self, t, depth=0.55, rel=0.11):
        i = int(t * SR)
        if i < 0 or i >= self.n:
            return
        L = min(int(0.45 * SR), self.n - i)
        tt = np.arange(L) / SR
        self.sc[i:i + L] = np.minimum(self.sc[i:i + L], 1 - depth * np.exp(-tt / rel))

    def render(self, total):
        ir_n = int(2.6 * SR)
        tt = np.arange(ir_n) / SR
        irs = []
        for _ in range(2):
            ir = noise(ir_n) * np.exp(-tt / 0.55)
            ir = filt(ir, 6500)
            ir[: int(0.02 * SR)] = 0
            irs.append(ir / np.sqrt(np.sum(ir ** 2)))
        wet = np.vstack([fftconvolve(self.rev[c], irs[c])[: self.n] for c in range(2)])
        out = self.dry + self.duck * self.sc + 0.9 * wet
        n = int(total * SR)
        out = out[:, :n]
        out /= np.max(np.abs(out)) + 1e-9
        out = np.tanh(1.6 * out) / np.tanh(1.6)
        fade = int(1.4 * SR)
        out[:, -fade:] *= np.linspace(1, 0, fade) ** 2
        out[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
        return out


# ------------------------------------------------------------ instruments
def kick(vel=1.0):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 46 + 115 * np.exp(-t / 0.035)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.26)
    click = filt(noise(n), 3000, "high") * np.exp(-t / 0.003) * 0.35
    return np.tanh(1.8 * (body + click)) * vel

def snare(vel=1.0):
    n = int(0.35 * SR); t = np.arange(n) / SR
    nz = filt(noise(n), (1400, 8000), "band") * np.exp(-t / 0.14)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)
    return (0.9 * nz + 0.55 * tone) * vel

def hat(open_=False, vel=1.0):
    n = int((0.3 if open_ else 0.08) * SR); t = np.arange(n) / SR
    return filt(noise(n), 7500, "high") * np.exp(-t / (0.16 if open_ else 0.022)) * vel

def crash(vel=1.0):
    n = int(2.6 * SR); t = np.arange(n) / SR
    return filt(noise(n), 4500, "high") * np.exp(-t / 1.0) * vel

def boom(vel=1.0):
    n = int(1.6 * SR); t = np.arange(n) / SR
    f = 30 + 45 * np.exp(-t / 0.25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7) * vel

def riser(seconds, vel=1.0):
    n = int(seconds * SR)
    out = np.zeros(n)
    chunks = 40
    for k in range(chunks):
        a, b = k * n // chunks, (k + 1) * n // chunks
        lo = 300 * (25 ** (k / chunks))
        seg = filt(noise(b - a + 800), (lo, lo * 2.2), "band")[800:]
        out[a:b] = seg
    return out * np.linspace(0, 1, n) ** 2.2 * vel

def whoosh(vel=1.0):
    n = int(0.8 * SR)
    out = np.zeros(n)
    for k in range(16):
        a, b = k * n // 16, (k + 1) * n // 16
        fc = 250 * (20 ** (k / 16))
        out[a:b] = filt(noise(b - a + 600), fc)[600:]
    env = np.linspace(0, 1, n) ** 3
    env[-int(0.06 * SR):] *= np.linspace(1, 0, int(0.06 * SR))
    return out * env * vel

def pad(notes, gate, cutoff, attack=0.12, vel=1.0):
    n = int((gate + 1.2) * SR)
    e = adsr(n, attack, 0.6, 0.8, 0.45, gate)
    L = np.zeros(n); R = np.zeros(n)
    for m in notes:
        f = mtof(m)
        L += saw(f, n, -9) + 0.6 * saw(f, n, 4)
        R += saw(f, n, 9) + 0.6 * saw(f, n, -4)
    st = np.vstack([filt(L, cutoff), filt(R, cutoff)]) * e / len(notes)
    return st * vel

def bass(m, gate, vel=1.0, cutoff=750):
    n = int((gate + 0.15) * SR)
    e = adsr(n, 0.004, 0.12, 0.55, 0.04, gate)
    f = mtof(m)
    body = filt(saw(f, n) + 0.5 * saw(f, n, 7), cutoff)
    sub = np.sin(2 * np.pi * (f / 2) * np.arange(n) / SR)
    return np.tanh(1.4 * (body + 0.9 * sub)) * e * vel

def pluck(m, vel=1.0, cutoff=3200):
    n = int(0.32 * SR)
    e = adsr(n, 0.002, 0.08, 0.0, 0.05, 0.12)
    x = saw(mtof(m), n) - saw(mtof(m), n, 0, phase0=0.25)       # hollow pulse
    return filt(x, cutoff) * e * vel

def lead(m, gate, vel=1.0):
    n = int((gate + 0.5) * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) / 0.2, 0, 1)
    f = mtof(m) * vib
    x = saw(f, n, -6) + saw(f, n, 6) + 0.4 * saw(f * 2, n)
    e = adsr(n, 0.015, 0.3, 0.75, 0.25, gate)
    return filt(x, 4200) * e * vel * 0.5


# ------------------------------------------------------------ the song
CH = {"Am": [57, 60, 64], "F": [53, 57, 60], "C": [55, 60, 64], "G": [55, 59, 62],
      "Dm": [53, 57, 62], "Em": [55, 59, 64]}
ROOT = {"Am": 45, "F": 41, "C": 48, "G": 43, "Dm": 50, "Em": 40}
P1 = ["Am", "F", "C", "G"]
P2 = ["Dm", "F", "Am", "G"]
MELODY = [  # (bar in 4-bar loop, beat, length, midi) over Am F C G
    (0, 0, 1, 69), (0, 1, 1, 72), (0, 2, 1.5, 76), (0, 3.5, .5, 74),
    (1, 0, 1, 72), (1, 1, .5, 74), (1, 1.5, .5, 72), (1, 2, 2, 69),
    (2, 0, 1, 67), (2, 1, 1, 72), (2, 2, 1, 76), (2, 3, 1, 79),
    (3, 0, 1.5, 77), (3, 1.5, .5, 76), (3, 2, 1, 74), (3, 3, 1, 71),
]

def compose(intro_end, boss, outro, total, cuts, out_wav):
    N = max(1, round((boss - intro_end) / 2.0))
    bar = (boss - intro_end) / N
    beat = bar / 4
    t0 = intro_end - 2 * bar
    B_BODY, B_BOSS = 2, 2 + N
    B_OUT = round((outro - t0) / bar)
    bpm = 60 / beat
    print(f"{out_wav}: {bpm:.2f} BPM, bar {bar:.4f}s, body {N} bars, boss bars {B_BOSS}-{B_OUT}")

    M = Mix(total)
    T = lambda b, bt=0.0: t0 + (b * 4 + bt) * beat
    hum = lambda: 1 + rng.uniform(-0.06, 0.06)

    def chord_for(b):
        if b >= B_BOSS:
            return P1[(b - B_BOSS) % 4]
        if b < B_BODY:
            return "Am" if b % 2 == 0 else "F"
        return (P2 if ((b - B_BODY) // 8) % 2 == 1 and b < B_BOSS - 4 else P1)[(b - B_BODY) % 4]

    for b in range(0, B_OUT):
        ch = chord_for(b)
        intro, build, drop = b < B_BODY, B_BOSS - 4 <= b < B_BOSS, b >= B_BOSS
        late_build = b >= B_BOSS - 2 and not drop

        # pad
        if intro:
            cut = 500 + 900 * b
            M.add(T(b), pad(CH[ch], bar, cut, attack=1.2 if b == 0 else 0.3, vel=0.55),
                  "dry", send=0.35)
        else:
            cut = 1500 if not build else 1500 + 700 * (b - (B_BOSS - 4))
            if drop:
                cut = 2600
            gate = bar - (0.5 * beat if b == B_BOSS - 1 else 0)
            M.add(T(b), pad(CH[ch] + ([CH[ch][0] + 12] if drop else []), gate, cut, vel=0.5),
                  "duck", send=0.3)

        # drums
        if not intro and not late_build:
            for k in range(4):
                M.add(T(b, k), kick(hum()), "dry")
                M.kick_duck(T(b, k), depth=0.65 if drop else 0.55)
        if b >= B_BODY + 4 and not late_build:
            for k in (1, 3):
                M.add(T(b, k), snare(0.55 * hum()), "dry", send=0.22)
        if not intro and not late_build:
            steps = 16 if drop else 8
            for s in range(steps):
                pos = s * 4 / steps
                if not drop and s % 2 == 0:
                    continue
                v = (0.32 if s % 2 else 0.18) * hum()
                M.add(T(b, pos), hat(False, v), "dry", pan=0.25)
            if drop or (b - B_BODY) % 2 == 1:
                for k in (0.5, 1.5, 2.5, 3.5) if drop else (3.5,):
                    M.add(T(b, k), hat(True, 0.16), "dry", pan=-0.2, send=0.1)
        if late_build:
            first = b == B_BOSS - 2
            hits = [i * 0.5 for i in range(8)] if first else \
                   [i * 0.25 for i in range(8)] + [2 + i * 0.125 for i in range(12)]
            for h in hits:
                prog = ((0 if first else 4) + h) / 8
                M.add(T(b, h), snare(0.12 + 0.5 * prog ** 1.5), "dry", send=0.18)

        # bass
        if not intro and not late_build:
            r = ROOT[ch]
            for e8 in range(8):
                m = r + (12 if drop and e8 % 2 == 1 else 0)
                M.add(T(b, e8 * 0.5), bass(m, beat * 0.42, 0.55 * hum(), 900 if drop else 700), "duck")

        # arp (enters after 4 body bars)
        if b >= B_BODY + 4:
            tones = CH[ch] + [CH[ch][0] + 12, CH[ch][1] + 12]
            pattern = [0, 1, 2, 3, 4, 3, 2, 1]
            for s in range(16):
                if b == B_BOSS - 1 and s >= 14:
                    continue
                m = tones[pattern[s % 8]] + 12
                p = -0.35 if s % 2 else 0.35
                sig = pluck(m, 0.33 * hum(), 2400 if not drop else 3600)
                M.add(T(b, s * 0.25), sig, "duck", pan=p, send=0.18)
                for k in range(1, 4):            # ping-pong delay, 3/16 note
                    M.add(T(b, s * 0.25 + 0.75 * k), sig * 0.42 ** k, "duck",
                          pan=-p if k % 2 else p)

        # lead melody in the boss section
        if drop:
            loop_bar = (b - B_BOSS) % 4
            for lb, bt, ln, m in MELODY:
                if lb == loop_bar:
                    M.add(T(b, bt), lead(m, ln * beat * 0.92, 0.75), "duck", pan=0.05, send=0.3)

    # transitions
    M.add(T(B_BODY - 1), riser(bar, 0.35), "dry", send=0.2)
    M.add(T(B_BODY), crash(0.5), "dry", pan=0.15, send=0.3)
    M.add(T(B_BOSS - 2), riser(2 * bar - 0.5 * beat, 0.55), "dry", send=0.25)
    M.add(T(B_BOSS), crash(0.75), "dry", pan=0.15, send=0.35)
    M.add(T(B_BOSS), boom(0.9), "dry")
    M.add(T(B_BOSS), kick(1.0), "dry")
    for c in cuts:
        M.add(c - 0.74, whoosh(0.22), "dry", send=0.25)

    # outro: one last hit, then the chord rings out
    to = T(B_OUT)
    M.add(to, crash(0.55), "dry", send=0.35)
    M.add(to, kick(1.0), "dry")
    M.add(to, boom(0.6), "dry")
    M.add(to, pad(CH["Am"] + [69], total - to, 2200, attack=0.02, vel=0.6), "dry", send=0.45)
    M.add(to, bass(ROOT["Am"], 1.2, 0.5), "dry")

    out = M.render(total)
    pcm = (out.T * 32767 * 0.95).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    full = [4.0, 17.066667, 6.7, 14.533333, 12.0, 6.966667, 18.7, 9.466667, 12.766667, 11.866667, 3.5]
    starts = np.cumsum([0] + full)
    full_cuts = [starts[2], starts[3], starts[3] + 7.166667, starts[4], starts[5],
                 starts[6], starts[7], starts[8]]
    compose(starts[1], starts[9], starts[10], starts[11], full_cuts, "music_full.wav")

    li = [3.0, 11.0, 6.7, 7.166667, 7.366667, 11.866667, 3.5]
    ls = np.cumsum([0] + li)
    compose(ls[1], ls[5], ls[6], ls[7], [ls[2], ls[3], ls[4]], "music_linkedin.wav")
