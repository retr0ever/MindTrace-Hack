"""
EEG Data Analyzer - Extracts meaningful insights from cleaned EEG data
"""
import numpy as np
from scipy import signal as scipy_signal
from scipy.fft import rfft, rfftfreq


class EEGAnalyzer:
    """Analyzes cleaned EEG data to extract meaningful neuroscience insights."""

    def __init__(self, sampling_rate=256):
        """
        Initialize the EEG analyzer.

        Args:
            sampling_rate: Sampling frequency in Hz (default: 256)
        """
        self.fs = sampling_rate

        # Standard EEG frequency bands
        self.bands = {
            'delta': (0.5, 4),    # Deep sleep
            'theta': (4, 8),      # Drowsiness, meditation
            'alpha': (8, 13),     # Relaxed wakefulness
            'beta': (13, 30),     # Active thinking, focus
            'gamma': (30, 45)     # High-level cognition
        }

    def analyze(self, raw_data, cleaned_data):
        """
        Perform comprehensive analysis of EEG data.

        Args:
            raw_data: Original unprocessed EEG data
            cleaned_data: Cleaned EEG data after processing

        Returns:
            Dictionary containing analysis results and insights
        """
        results = {}

        # 1. Signal Quality Metrics
        results['snr_improvement'] = self._calculate_snr_improvement(raw_data, cleaned_data)
        results['noise_reduction'] = self._calculate_noise_reduction(raw_data, cleaned_data)

        # 2. Frequency Band Analysis
        results['band_powers'] = self._analyze_frequency_bands(cleaned_data)
        results['dominant_band'] = self._get_dominant_band(results['band_powers'])

        # 3. Artefact Detection
        results['artefacts_detected'] = self._detect_remaining_artefacts(cleaned_data)

        # 4. Pattern Recognition
        results['patterns'] = self._identify_patterns(cleaned_data, results['band_powers'])

        # 5. Clinical Indicators (basic heuristics)
        results['indicators'] = self._assess_clinical_indicators(results['band_powers'],
                                                                  results['dominant_band'])

        return results

    def _calculate_snr_improvement(self, raw, cleaned):
        """Calculate signal-to-noise ratio improvement."""
        raw_arr = np.asarray(raw).flatten()
        cleaned_arr = np.asarray(cleaned).flatten()

        # Use variance as a proxy for signal power
        raw_power = np.var(raw_arr)
        cleaned_power = np.var(cleaned_arr)
        noise_removed = raw_power - cleaned_power

        if raw_power > 0:
            snr_db = 10 * np.log10(cleaned_power / (noise_removed + 1e-10))
            return max(0, min(snr_db, 20))  # Cap between 0-20 dB for realistic values
        return 0

    def _calculate_noise_reduction(self, raw, cleaned):
        """Calculate percentage of noise reduction."""
        raw_arr = np.asarray(raw).flatten()
        cleaned_arr = np.asarray(cleaned).flatten()

        raw_power = np.var(raw_arr)
        cleaned_power = np.var(cleaned_arr)

        if raw_power > 0:
            reduction = ((raw_power - cleaned_power) / raw_power) * 100
            return max(0, min(reduction, 100))
        return 0

    def _analyze_frequency_bands(self, data):
        """Analyze power in different EEG frequency bands."""
        data_arr = np.asarray(data).flatten()

        # Compute power spectral density
        freqs, psd = scipy_signal.welch(data_arr, fs=self.fs, nperseg=min(256, len(data_arr)))

        band_powers = {}
        for band_name, (low, high) in self.bands.items():
            # Find indices corresponding to this frequency band
            idx = np.logical_and(freqs >= low, freqs <= high)
            # Integrate power in this band
            band_power = np.trapz(psd[idx], freqs[idx]) if np.any(idx) else 0
            band_powers[band_name] = float(band_power)

        # Normalize to percentages
        total_power = sum(band_powers.values())
        if total_power > 0:
            band_powers = {k: (v / total_power) * 100 for k, v in band_powers.items()}

        return band_powers

    def _get_dominant_band(self, band_powers):
        """Identify the dominant frequency band."""
        if not band_powers:
            return 'unknown'
        return max(band_powers, key=band_powers.get)

    def _detect_remaining_artefacts(self, data):
        """Detect any remaining artefacts in cleaned data."""
        data_arr = np.asarray(data).flatten()

        # Simple threshold-based detection
        threshold = 3 * np.std(data_arr)
        artefact_indices = np.where(np.abs(data_arr) > threshold)[0]

        # Count distinct artefact events (grouped by proximity)
        if len(artefact_indices) == 0:
            return 0

        # Group artefacts that are close together (within 0.5 seconds)
        gap_threshold = int(0.5 * self.fs)
        gaps = np.diff(artefact_indices)
        num_artefacts = 1 + np.sum(gaps > gap_threshold)

        return int(num_artefacts)

    def _identify_patterns(self, data, band_powers):
        """Identify notable patterns in the EEG data."""
        patterns = []

        # Check for strong alpha rhythm (normal relaxed state)
        if band_powers.get('alpha', 0) > 40:
            patterns.append('strong_alpha_rhythm')

        # Check for elevated theta (drowsiness or meditation)
        if band_powers.get('theta', 0) > 30:
            patterns.append('elevated_theta')

        # Check for high beta (stress or active thinking)
        if band_powers.get('beta', 0) > 35:
            patterns.append('high_beta_activity')

        # Check for abnormal delta in waking state
        if band_powers.get('delta', 0) > 40:
            patterns.append('elevated_delta')

        return patterns

    def _assess_clinical_indicators(self, band_powers, dominant_band):
        """
        Provide basic clinical insights based on frequency patterns.

        Note: These are simplified heuristics for demonstration.
        Real clinical diagnosis requires expert interpretation.
        """
        indicators = []

        # Normal patterns
        if dominant_band == 'alpha' and band_powers.get('alpha', 0) > 35:
            indicators.append({
                'type': 'normal',
                'description': 'Healthy resting state with strong alpha rhythm'
            })

        # Theta dominance (could indicate drowsiness or cognitive load)
        if dominant_band == 'theta':
            indicators.append({
                'type': 'attention',
                'description': 'Elevated theta activity may indicate drowsiness or deep concentration'
            })

        # Beta dominance (active cognition or stress)
        if dominant_band == 'beta' and band_powers.get('beta', 0) > 40:
            indicators.append({
                'type': 'cognitive',
                'description': 'High beta activity suggests active thinking or increased alertness'
            })

        # Delta in waking (could be pathological if excessive)
        if band_powers.get('delta', 0) > 45:
            indicators.append({
                'type': 'anomaly',
                'description': 'Elevated delta waves during waking state - may warrant further investigation'
            })

        # Reduced alpha (could indicate anxiety or cognitive load)
        if band_powers.get('alpha', 0) < 15:
            indicators.append({
                'type': 'attention',
                'description': 'Reduced alpha power may indicate heightened alertness or anxiety'
            })

        # Gamma activity (high-level processing)
        if band_powers.get('gamma', 0) > 15:
            indicators.append({
                'type': 'cognitive',
                'description': 'Notable gamma activity associated with complex cognitive processing'
            })

        return indicators

    def generate_summary_text(self, analysis_results):
        """
        Generate human-readable summary from analysis results.

        Args:
            analysis_results: Dictionary from analyze() method

        Returns:
            String summary of the analysis
        """
        parts = []

        # Signal quality
        snr = analysis_results.get('snr_improvement', 0)
        noise_red = analysis_results.get('noise_reduction', 0)
        parts.append(f"Signal quality improved by {snr:.1f} dB with {noise_red:.1f}% noise reduction.")

        # Dominant frequency band
        dominant = analysis_results.get('dominant_band', 'unknown')
        band_powers = analysis_results.get('band_powers', {})
        if dominant != 'unknown':
            power = band_powers.get(dominant, 0)
            parts.append(f"Dominant frequency band: {dominant} ({power:.1f}% of total power).")

        # Brain state interpretation
        if dominant == 'alpha':
            parts.append("This suggests a relaxed, wakeful state with good attentional capacity.")
        elif dominant == 'beta':
            parts.append("This indicates active cognitive processing or focused attention.")
        elif dominant == 'theta':
            parts.append("This may reflect drowsiness, meditation, or memory processing.")
        elif dominant == 'delta':
            parts.append("Elevated slow-wave activity detected - typical in deep sleep but unusual in waking states.")

        # Clinical indicators
        indicators = analysis_results.get('indicators', [])
        if indicators:
            for indicator in indicators[:2]:  # Limit to top 2 for brevity
                parts.append(indicator['description'] + '.')

        # Artefacts
        artefacts = analysis_results.get('artefacts_detected', 0)
        if artefacts == 0:
            parts.append("No significant artefacts detected in the cleaned signal.")
        else:
            parts.append(f"{artefacts} residual artefact event(s) detected and may require manual review.")

        return ' '.join(parts)
