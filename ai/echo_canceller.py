import numpy as np
from collections import deque
from typing import Optional

SAMPLE_RATE = 16000


class AcousticEchoCanceller:
    def __init__(self, filter_length: int = 2048, mu: float = 0.005, sample_rate: int = SAMPLE_RATE):
        self.filter_length = filter_length
        self.mu = mu
        self.sample_rate = sample_rate
        self.filter_weights = np.zeros(filter_length, dtype=np.float64)
        self.ref_buffer = np.zeros(filter_length, dtype=np.float64)
        self.double_talk_frames = 0
        self.hold_frames = 0
        self.adaptation_enabled = True
        self.ema_error = 0.0
        self.ema_ref = 0.0

    def process(self, mic_samples: np.ndarray, ref_samples: np.ndarray) -> np.ndarray:
        if len(mic_samples) == 0:
            return mic_samples
        if len(ref_samples) > self.filter_length:
            ref_samples = ref_samples[-self.filter_length:]

        self.ref_buffer = np.roll(self.ref_buffer, -len(ref_samples))
        self.ref_buffer[-len(ref_samples):] = ref_samples

        output = np.zeros_like(mic_samples, dtype=np.float64)
        mic_f = mic_samples.astype(np.float64)
        ref_f = ref_samples.astype(np.float64)

        ref_power = np.dot(ref_f, ref_f) / max(len(ref_f), 1)
        mic_power = np.dot(mic_f, mic_f) / max(len(mic_f), 1)

        is_double_talk = False
        if ref_power > 1.0 and mic_power > 0.5:
            ratio = mic_power / max(ref_power, 1e-10)
            is_double_talk = ratio > 2.0

        if is_double_talk:
            self.double_talk_frames += 1
            self.hold_frames = max(self.hold_frames, int(0.05 * self.sample_rate / max(len(mic_samples), 1)) + 1)
            self.adaptation_enabled = False
        else:
            self.double_talk_frames = 0
            if self.hold_frames > 0:
                self.hold_frames -= 1
            else:
                self.adaptation_enabled = True

        echo_est = np.dot(self.filter_weights[:len(ref_f)], ref_f)
        error = mic_f - echo_est

        if self.adaptation_enabled and ref_power > 0.5:
            norm = ref_power * len(ref_f) + 1e-10
            step = self.mu / max(norm, 1e-10)
            delta = step * error * ref_f
            max_delta = 0.01
            delta = np.clip(delta, -max_delta, max_delta)
            min_len = min(len(self.filter_weights), len(delta))
            self.filter_weights[:min_len] += delta[:min_len]

        self.ema_error = 0.95 * self.ema_error + 0.05 * np.mean(np.abs(error))
        self.ema_ref = 0.95 * self.ema_ref + 0.05 * ref_power

        echo_attenuation = -20 * np.log10(max(self.ema_error / max(self.ema_ref, 1e-10), 1e-10))
        min_attenuation_db = 6.0
        if echo_attenuation < min_attenuation_db and not is_double_talk:
            residual_gain = 1.0 - (min_attenuation_db - echo_attenuation) / 20.0
            residual_gain = max(0.3, min(1.0, residual_gain))
            output = error * residual_gain
        else:
            output = error

        max_val = np.max(np.abs(output))
        if max_val > 32767:
            output = output / max_val * 32767

        return output.astype(np.int16)

    def reset(self):
        self.filter_weights.fill(0)
        self.ref_buffer.fill(0)
        self.double_talk_frames = 0
        self.hold_frames = 0
        self.adaptation_enabled = True
        self.ema_error = 0.0
        self.ema_ref = 0.0
