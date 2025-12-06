import numpy as np
from .filters import bandpass_filter, notch_filter
from .artefact_detection import detect_blink_artefacts
try:
    from sklearn.decomposition import FastICA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class EEGCleaner:
    def __init__(self, config):
        self.config = config
        self.fs = config.get('sampling_rate', 256)
        self.low = config.get('bandpass_low', 1.0)
        self.high = config.get('bandpass_high', 40.0)
        self.notch = config.get('notch_freq', 50.0)

    def clean(self, data):
        """
        Applies standard cleaning pipeline.
        """
        # 1. Bandpass
        filtered = bandpass_filter(data, self.low, self.high, self.fs)
        
        # 2. Notch
        filtered = notch_filter(filtered, self.notch, self.fs)
        
        # 3. ICA-based artefact reduction (when available)
        cleaned = self.apply_ica(filtered)
        
        return cleaned

    def apply_ica(self, data):
        """
        Runs a basic ICA decomposition and removes components
        with unusually large amplitude (often dominated by blinks
        or other gross noise). Falls back to the input data if ICA
        is not available or the data is not suitable.
        """
        if not SKLEARN_AVAILABLE:
            return data

        arr = np.asarray(data)
        if arr.ndim == 1 or min(arr.shape) < 2:
            # Need at least two channels/components for meaningful ICA
            return arr

        # Normalise shape to (n_samples, n_channels) for FastICA
        if arr.shape[0] > arr.shape[1]:
            # Assume (n_samples, n_channels)
            X = arr
            transpose_back = False
        else:
            # Assume (n_channels, n_samples)
            X = arr.T
            transpose_back = True

        n_samples, n_channels = X.shape
        if n_channels < 2:
            return arr

        n_components = min(self.config.get("ica_components", n_channels), n_channels)

        try:
            ica = FastICA(n_components=n_components, random_state=0)
            S = ica.fit_transform(X)  # Independent components: (n_samples, n_components)

            # Heuristic: zero out components with very large peak-to-peak range
            ptp = S.max(axis=0) - S.min(axis=0)
            threshold = np.median(ptp) * 3.0
            high_amp_components = np.where(ptp > threshold)[0]
            if high_amp_components.size > 0:
                S[:, high_amp_components] = 0

            X_clean = ica.inverse_transform(S)

            if transpose_back:
                return X_clean.T
            return X_clean
        except Exception:
            # If ICA fails for any reason, fall back gracefully
            return arr

    def remove_artefacts(self, data, artefacts):
        """
        Zeroes out artefact regions.
        """
        cleaned = data.copy()
        for start, end in artefacts:
            start_idx = int(start * self.fs)
            end_idx = int(end * self.fs)
            cleaned[start_idx:end_idx] = 0 # Simple zeroing, better to interpolate
        return cleaned
