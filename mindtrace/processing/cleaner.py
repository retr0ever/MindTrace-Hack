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
    
    def compute_ica_details(self, data, start_time: float = None, end_time: float = None):
        """
        Compute ICA component details on-demand for a given dataset.
        This method performs ICA decomposition and analyzes components without storing
        the full component data, only computing statistics.
        
        Args:
            data: Input data (same format as clean() method expects)
            start_time: Optional start time in seconds for range analysis
            end_time: Optional end time in seconds for range analysis
            
        Returns:
            Dictionary with ICA component details, or None if ICA cannot be applied
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'ICA not available (sklearn not installed)'}

        arr = np.asarray(data)
        if arr.ndim == 1 or min(arr.shape) < 2:
            return {'error': 'ICA requires at least 2 channels'}

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
            return {'error': 'ICA requires at least 2 channels'}

        n_components = min(self.config.get("ica_components", n_channels), n_channels)

        try:
            ica = FastICA(n_components=n_components, random_state=0)
            S = ica.fit_transform(X)  # Independent components: (n_samples, n_components)

            # Calculate statistics for each component
            ptp = S.max(axis=0) - S.min(axis=0)
            mean_amp = np.mean(np.abs(S), axis=0)
            std_amp = np.std(S, axis=0)
            max_amp = np.max(np.abs(S), axis=0)
            
            threshold = np.median(ptp) * 3.0
            high_amp_components = np.where(ptp > threshold)[0]
            
            # Build component details (only statistics, not full component data)
            component_details = []
            for i in range(n_components):
                was_removed = i in high_amp_components
                component_details.append({
                    'component_id': i,
                    'removed': was_removed,
                    'peak_to_peak': float(ptp[i]),
                    'mean_amplitude': float(mean_amp[i]),
                    'std_amplitude': float(std_amp[i]),
                    'max_amplitude': float(max_amp[i]),
                    'threshold': float(threshold),
                    'reason': 'High amplitude artefact (peak-to-peak > 3x median)' if was_removed else 'Retained (within normal amplitude range)'
                })
            
            # Calculate time range if provided
            time_range_info = None
            if start_time is not None and end_time is not None:
                start_idx = int(start_time * self.fs)
                end_idx = int(end_time * self.fs)
                start_idx = max(0, min(start_idx, n_samples - 1))
                end_idx = max(start_idx + 1, min(end_idx, n_samples))
                
                time_range_info = {
                    'start_seconds': start_time,
                    'end_seconds': end_time,
                    'duration_seconds': end_time - start_time,
                    'start_sample': start_idx,
                    'end_sample': end_idx,
                    'num_samples': end_idx - start_idx
                }
            
            return {
                'n_components': n_components,
                'n_samples': n_samples,
                'n_channels': n_channels,
                'threshold': float(threshold),
                'components_removed': high_amp_components.tolist(),
                'components_retained': [i for i in range(n_components) if i not in high_amp_components],
                'component_details': component_details,
                'sampling_rate': self.fs,
                'total_duration_seconds': n_samples / self.fs,
                'time_range': time_range_info
            }
        except Exception as e:
            return {'error': f'ICA computation failed: {str(e)}'}

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
