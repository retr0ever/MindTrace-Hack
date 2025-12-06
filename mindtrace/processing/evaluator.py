"""
EEG Processing Pipeline Evaluator

Comprehensive evaluation module for assessing:
1. Processing pipeline performance (timing, memory, efficiency)
2. Algorithm effectiveness (signal quality, noise reduction, preservation)
3. Filter performance (bandpass, notch, ICA)
4. Artefact detection accuracy
5. Statistical validation
"""
import numpy as np
import time
import sys
from scipy import signal as scipy_signal
from scipy.stats import pearsonr
from scipy.fft import rfft, rfftfreq
from typing import Dict, List, Tuple, Optional, Any
import warnings


class PipelineEvaluator:
    """
    Evaluates the EEG processing pipeline and algorithms.
    Provides comprehensive metrics for performance and quality assessment.
    """

    def __init__(self, sampling_rate: float = 256.0):
        """
        Initialize the evaluator.

        Args:
            sampling_rate: Sampling frequency in Hz
        """
        self.fs = sampling_rate
        self.evaluation_results = {}

    def evaluate_pipeline(
        self,
        raw_data: np.ndarray,
        cleaned_data: np.ndarray,
        processing_times: Optional[Dict[str, float]] = None,
        pipeline_steps: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive evaluation of the processing pipeline.

        Args:
            raw_data: Original unprocessed EEG data
            cleaned_data: Processed/cleaned EEG data
            processing_times: Optional dict of step_name -> time_taken (seconds)
            pipeline_steps: Optional list of pipeline step names

        Returns:
            Dictionary containing all evaluation metrics
        """
        raw_arr = np.asarray(raw_data).flatten()
        cleaned_arr = np.asarray(cleaned_data).flatten()

        if len(raw_arr) != len(cleaned_arr):
            raise ValueError("Raw and cleaned data must have the same length")

        results = {
            'timestamp': time.time(),
            'data_info': self._get_data_info(raw_arr, cleaned_arr),
            'performance_metrics': self._evaluate_performance(processing_times),
            'signal_quality_metrics': self._evaluate_signal_quality(raw_arr, cleaned_arr),
            'filter_effectiveness': self._evaluate_filters(raw_arr, cleaned_arr),
            'frequency_domain_metrics': self._evaluate_frequency_domain(raw_arr, cleaned_arr),
            'statistical_validation': self._statistical_validation(raw_arr, cleaned_arr),
            'artefact_metrics': self._evaluate_artefact_removal(raw_arr, cleaned_arr),
            'pipeline_health': self._assess_pipeline_health(raw_arr, cleaned_arr),
            'overall_score': 0.0  # Will be calculated
        }

        # Calculate overall score
        results['overall_score'] = self._calculate_overall_score(results)

        self.evaluation_results = results
        return results

    def _get_data_info(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Extract basic information about the data."""
        return {
            'duration_seconds': len(raw) / self.fs,
            'samples': len(raw),
            'sampling_rate': self.fs,
            'raw_mean': float(np.mean(raw)),
            'raw_std': float(np.std(raw)),
            'raw_min': float(np.min(raw)),
            'raw_max': float(np.max(raw)),
            'cleaned_mean': float(np.mean(cleaned)),
            'cleaned_std': float(np.std(cleaned)),
            'cleaned_min': float(np.min(cleaned)),
            'cleaned_max': float(np.max(cleaned)),
        }

    def _evaluate_performance(self, processing_times: Optional[Dict[str, float]]) -> Dict[str, Any]:
        """Evaluate processing performance metrics."""
        if processing_times is None:
            return {
                'total_time': None,
                'steps': {},
                'samples_per_second': None,
                'efficiency_score': None
            }

        total_time = sum(processing_times.values())
        total_samples = self.evaluation_results.get('data_info', {}).get('samples', 1)
        samples_per_second = total_samples / total_time if total_time > 0 else 0

        # Efficiency score: higher is better (more samples processed per second)
        # Normalize to 0-100 scale (assuming 100k samples/sec is excellent)
        efficiency_score = min(100, (samples_per_second / 100000) * 100)

        return {
            'total_time': total_time,
            'steps': processing_times,
            'samples_per_second': samples_per_second,
            'efficiency_score': efficiency_score,
            'performance_rating': self._rate_performance(efficiency_score)
        }

    def _evaluate_signal_quality(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Evaluate signal quality improvements."""
        # Signal-to-Noise Ratio (SNR)
        raw_power = np.var(raw)
        cleaned_power = np.var(cleaned)
        noise_power = raw_power - cleaned_power
        
        if noise_power > 0:
            snr_db = 10 * np.log10(cleaned_power / (noise_power + 1e-10))
        else:
            snr_db = float('inf') if cleaned_power > 0 else 0
        
        # Noise reduction percentage
        noise_reduction = ((raw_power - cleaned_power) / raw_power * 100) if raw_power > 0 else 0

        # Root Mean Square Error (RMSE) - lower is better for noise removal
        rmse = np.sqrt(np.mean((raw - cleaned) ** 2))

        # Correlation coefficient - measures signal preservation
        correlation, p_value = pearsonr(raw, cleaned)

        # Signal preservation score (how much of original signal is retained)
        # Use correlation as a proxy
        preservation_score = abs(correlation) * 100

        # Dynamic range preservation
        raw_range = np.max(raw) - np.min(raw)
        cleaned_range = np.max(cleaned) - np.min(cleaned)
        range_preservation = (cleaned_range / raw_range * 100) if raw_range > 0 else 0

        return {
            'snr_db': float(snr_db) if not np.isinf(snr_db) else 50.0,  # Cap at 50 dB
            'noise_reduction_percent': float(noise_reduction),
            'rmse': float(rmse),
            'correlation': float(correlation),
            'correlation_p_value': float(p_value),
            'signal_preservation_score': float(preservation_score),
            'dynamic_range_preservation': float(range_preservation),
            'quality_rating': self._rate_quality(snr_db, noise_reduction, preservation_score)
        }

    def _evaluate_filters(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Evaluate filter effectiveness."""
        # Frequency domain analysis
        raw_fft = np.abs(rfft(raw))
        cleaned_fft = np.abs(rfft(cleaned))
        freqs = rfftfreq(len(raw), 1/self.fs)

        # Check bandpass effectiveness (1-40 Hz should be preserved)
        bandpass_low, bandpass_high = 1.0, 40.0
        bandpass_mask = (freqs >= bandpass_low) & (freqs <= bandpass_high)
        out_of_band_mask = (freqs < bandpass_low) | (freqs > bandpass_high)

        # Power in band vs out of band
        in_band_power_raw = np.sum(raw_fft[bandpass_mask] ** 2)
        out_of_band_power_raw = np.sum(raw_fft[out_of_band_mask] ** 2)
        in_band_power_cleaned = np.sum(cleaned_fft[bandpass_mask] ** 2)
        out_of_band_power_cleaned = np.sum(cleaned_fft[out_of_band_mask] ** 2)

        # Bandpass effectiveness: how much out-of-band noise was removed
        out_of_band_reduction = ((out_of_band_power_raw - out_of_band_power_cleaned) / 
                                 (out_of_band_power_raw + 1e-10) * 100) if out_of_band_power_raw > 0 else 0

        # In-band preservation: how much signal was preserved in the target band
        in_band_preservation = (in_band_power_cleaned / (in_band_power_raw + 1e-10) * 100) if in_band_power_raw > 0 else 0

        # Notch filter effectiveness (50 Hz removal)
        notch_freq = 50.0
        notch_bandwidth = 2.0  # ±1 Hz around 50 Hz
        notch_mask = (freqs >= notch_freq - notch_bandwidth) & (freqs <= notch_freq + notch_bandwidth)
        
        notch_power_raw = np.sum(raw_fft[notch_mask] ** 2)
        notch_power_cleaned = np.sum(cleaned_fft[notch_mask] ** 2)
        notch_reduction = ((notch_power_raw - notch_power_cleaned) / 
                          (notch_power_raw + 1e-10) * 100) if notch_power_raw > 0 else 0

        return {
            'bandpass_effectiveness': {
                'out_of_band_reduction_percent': float(out_of_band_reduction),
                'in_band_preservation_percent': float(in_band_preservation),
                'score': float((out_of_band_reduction + in_band_preservation) / 2)
            },
            'notch_effectiveness': {
                'notch_reduction_percent': float(notch_reduction),
                'score': float(notch_reduction)
            },
            'overall_filter_score': float((out_of_band_reduction + in_band_preservation + notch_reduction) / 3)
        }

    def _evaluate_frequency_domain(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Evaluate frequency domain characteristics."""
        # Power spectral density
        raw_freqs, raw_psd = scipy_signal.welch(raw, fs=self.fs, nperseg=min(256, len(raw)//4))
        cleaned_freqs, cleaned_psd = scipy_signal.welch(cleaned, fs=self.fs, nperseg=min(256, len(cleaned)//4))

        # Dominant frequency
        raw_dominant_idx = np.argmax(raw_psd)
        cleaned_dominant_idx = np.argmax(cleaned_psd)
        raw_dominant_freq = raw_freqs[raw_dominant_idx]
        cleaned_dominant_freq = cleaned_freqs[cleaned_dominant_idx]

        # Frequency shift (should be minimal)
        freq_shift = abs(raw_dominant_freq - cleaned_dominant_freq)

        # Total power comparison
        total_power_raw = np.trapz(raw_psd, raw_freqs)
        total_power_cleaned = np.trapz(cleaned_psd, cleaned_freqs)
        power_preservation = (total_power_cleaned / (total_power_raw + 1e-10) * 100) if total_power_raw > 0 else 0

        # Spectral correlation
        # Interpolate to common frequency axis for comparison
        common_freqs = np.linspace(0, min(raw_freqs[-1], cleaned_freqs[-1]), 100)
        raw_psd_interp = np.interp(common_freqs, raw_freqs, raw_psd)
        cleaned_psd_interp = np.interp(common_freqs, cleaned_freqs, cleaned_psd)
        spectral_correlation, _ = pearsonr(raw_psd_interp, cleaned_psd_interp)

        return {
            'raw_dominant_frequency': float(raw_dominant_freq),
            'cleaned_dominant_frequency': float(cleaned_dominant_freq),
            'frequency_shift_hz': float(freq_shift),
            'total_power_preservation': float(power_preservation),
            'spectral_correlation': float(spectral_correlation),
            'frequency_stability_score': float(100 - min(100, freq_shift * 10))  # Penalize large shifts
        }

    def _statistical_validation(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Perform statistical validation tests."""
        # Normality test (Shapiro-Wilk for small samples, otherwise use Anderson-Darling)
        from scipy.stats import shapiro, anderson
        
        # Use Shapiro-Wilk for samples < 5000, otherwise skip (too slow)
        normality_raw = None
        normality_cleaned = None
        
        if len(raw) < 5000:
            try:
                _, p_raw = shapiro(raw[:min(5000, len(raw))])
                _, p_cleaned = shapiro(cleaned[:min(5000, len(cleaned))])
                normality_raw = float(p_raw)
                normality_cleaned = float(p_cleaned)
            except:
                pass

        # Variance ratio (F-test)
        var_raw = np.var(raw)
        var_cleaned = np.var(cleaned)
        variance_ratio = var_cleaned / (var_raw + 1e-10)

        # Mean preservation
        mean_raw = np.mean(raw)
        mean_cleaned = np.mean(cleaned)
        mean_preservation = 1 - abs(mean_cleaned - mean_raw) / (abs(mean_raw) + 1e-10)

        # Skewness and kurtosis preservation
        from scipy.stats import skew, kurtosis
        skew_raw = skew(raw)
        skew_cleaned = skew(cleaned)
        kurt_raw = kurtosis(raw)
        kurt_cleaned = kurtosis(cleaned)
        
        skew_preservation = 1 - abs(skew_cleaned - skew_raw) / (abs(skew_raw) + 1e-10)
        kurt_preservation = 1 - abs(kurt_cleaned - kurt_raw) / (abs(kurt_raw) + 1e-10)

        return {
            'normality_test_raw': normality_raw,
            'normality_test_cleaned': normality_cleaned,
            'variance_ratio': float(variance_ratio),
            'mean_preservation': float(mean_preservation * 100),
            'skewness_preservation': float(skew_preservation * 100),
            'kurtosis_preservation': float(kurt_preservation * 100),
            'statistical_integrity_score': float((mean_preservation + skew_preservation + kurt_preservation) / 3 * 100)
        }

    def _evaluate_artefact_removal(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Evaluate artefact detection and removal effectiveness."""
        # Detect artefacts in raw data
        threshold = 3 * np.std(raw)
        raw_artefacts = np.where(np.abs(raw) > threshold)[0]
        cleaned_artefacts = np.where(np.abs(cleaned) > threshold)[0]

        # Artefact reduction
        artefact_reduction = ((len(raw_artefacts) - len(cleaned_artefacts)) / 
                             (len(raw_artefacts) + 1e-10) * 100) if len(raw_artefacts) > 0 else 0

        # Peak amplitude reduction
        raw_peak = np.max(np.abs(raw))
        cleaned_peak = np.max(np.abs(cleaned))
        peak_reduction = ((raw_peak - cleaned_peak) / (raw_peak + 1e-10) * 100) if raw_peak > 0 else 0

        # Artefact power reduction
        artefact_mask_raw = np.abs(raw) > threshold
        artefact_mask_cleaned = np.abs(cleaned) > threshold
        
        artefact_power_raw = np.sum(raw[artefact_mask_raw] ** 2) if np.any(artefact_mask_raw) else 0
        artefact_power_cleaned = np.sum(cleaned[artefact_mask_cleaned] ** 2) if np.any(artefact_mask_cleaned) else 0
        
        artefact_power_reduction = ((artefact_power_raw - artefact_power_cleaned) / 
                                   (artefact_power_raw + 1e-10) * 100) if artefact_power_raw > 0 else 0

        return {
            'artefacts_detected_raw': int(len(raw_artefacts)),
            'artefacts_detected_cleaned': int(len(cleaned_artefacts)),
            'artefact_reduction_percent': float(artefact_reduction),
            'peak_amplitude_reduction': float(peak_reduction),
            'artefact_power_reduction': float(artefact_power_reduction),
            'artefact_removal_score': float((artefact_reduction + peak_reduction + artefact_power_reduction) / 3)
        }

    def _assess_pipeline_health(self, raw: np.ndarray, cleaned: np.ndarray) -> Dict[str, Any]:
        """Assess overall pipeline health and potential issues."""
        issues = []
        warnings_list = []

        # Check for data loss
        if np.any(np.isnan(cleaned)):
            issues.append('NaN values detected in cleaned data')
        
        if np.any(np.isinf(cleaned)):
            issues.append('Infinite values detected in cleaned data')

        # Check for over-filtering (signal too flat)
        cleaned_std = np.std(cleaned)
        raw_std = np.std(raw)
        if cleaned_std < raw_std * 0.1:
            warnings_list.append('Possible over-filtering: signal variance reduced by >90%')

        # Check for under-filtering (too much noise remaining)
        noise_estimate = np.std(raw - cleaned)
        if noise_estimate > raw_std * 0.5:
            warnings_list.append('Possible under-filtering: significant noise may remain')

        # Check for clipping
        if np.any(cleaned == np.max(cleaned)) and np.any(cleaned == np.min(cleaned)):
            if np.sum(cleaned == np.max(cleaned)) > len(cleaned) * 0.01:
                warnings_list.append('Possible clipping detected in cleaned signal')

        # Health score (0-100)
        health_score = 100
        health_score -= len(issues) * 20  # Major issues
        health_score -= len(warnings_list) * 5  # Minor warnings
        health_score = max(0, health_score)

        return {
            'health_score': float(health_score),
            'issues': issues,
            'warnings': warnings_list,
            'status': 'healthy' if health_score >= 80 else 'degraded' if health_score >= 50 else 'unhealthy'
        }

    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        """Calculate an overall evaluation score (0-100)."""
        weights = {
            'signal_quality': 0.30,
            'filter_effectiveness': 0.25,
            'frequency_domain': 0.15,
            'artefact_removal': 0.15,
            'statistical_validation': 0.10,
            'pipeline_health': 0.05
        }

        # Extract component scores
        signal_quality = results.get('signal_quality_metrics', {}).get('quality_rating', {}).get('score', 50)
        filter_score = results.get('filter_effectiveness', {}).get('overall_filter_score', 50)
        freq_stability = results.get('frequency_domain_metrics', {}).get('frequency_stability_score', 50)
        artefact_score = results.get('artefact_metrics', {}).get('artefact_removal_score', 50)
        statistical_score = results.get('statistical_validation', {}).get('statistical_integrity_score', 50)
        health_score = results.get('pipeline_health', {}).get('health_score', 50)

        overall = (
            signal_quality * weights['signal_quality'] +
            filter_score * weights['filter_effectiveness'] +
            freq_stability * weights['frequency_domain'] +
            artefact_score * weights['artefact_removal'] +
            statistical_score * weights['statistical_validation'] +
            health_score * weights['pipeline_health']
        )

        return float(overall)

    def _rate_performance(self, efficiency_score: float) -> Dict[str, Any]:
        """Rate processing performance."""
        if efficiency_score >= 80:
            rating = 'excellent'
        elif efficiency_score >= 60:
            rating = 'good'
        elif efficiency_score >= 40:
            rating = 'moderate'
        else:
            rating = 'poor'

        return {'score': efficiency_score, 'rating': rating}

    def _rate_quality(self, snr_db: float, noise_reduction: float, preservation: float) -> Dict[str, Any]:
        """Rate signal quality improvement."""
        # Combined score
        quality_score = (min(snr_db, 50) / 50 * 40 +  # SNR component (40%)
                        noise_reduction / 100 * 30 +    # Noise reduction (30%)
                        preservation / 100 * 30)        # Preservation (30%)

        if quality_score >= 80:
            rating = 'excellent'
        elif quality_score >= 60:
            rating = 'good'
        elif quality_score >= 40:
            rating = 'moderate'
        else:
            rating = 'poor'

        return {
            'score': float(quality_score),
            'rating': rating,
            'snr_db': float(snr_db),
            'noise_reduction': float(noise_reduction),
            'preservation': float(preservation)
        }

    def generate_evaluation_report(self, results: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a human-readable evaluation report.

        Args:
            results: Evaluation results dict (uses self.evaluation_results if None)

        Returns:
            Markdown-formatted report string
        """
        if results is None:
            results = self.evaluation_results

        if not results:
            return "No evaluation results available."

        report_lines = [
            "# EEG Processing Pipeline Evaluation Report\n",
            f"**Overall Score:** {results.get('overall_score', 0):.1f}/100\n",
            f"**Evaluation Time:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(results.get('timestamp', time.time())))}\n",
            "\n## Data Information\n"
        ]

        data_info = results.get('data_info', {})
        report_lines.extend([
            f"- Duration: {data_info.get('duration_seconds', 0):.2f} seconds",
            f"- Samples: {data_info.get('samples', 0):,}",
            f"- Sampling Rate: {data_info.get('sampling_rate', 0)} Hz",
        ])

        # Signal Quality
        report_lines.append("\n## Signal Quality Metrics\n")
        sq = results.get('signal_quality_metrics', {})
        report_lines.extend([
            f"- **SNR Improvement:** {sq.get('snr_db', 0):.2f} dB",
            f"- **Noise Reduction:** {sq.get('noise_reduction_percent', 0):.2f}%",
            f"- **Signal Preservation:** {sq.get('signal_preservation_score', 0):.2f}%",
            f"- **Correlation:** {sq.get('correlation', 0):.3f}",
            f"- **Quality Rating:** {sq.get('quality_rating', {}).get('rating', 'N/A')}",
        ])

        # Filter Effectiveness
        report_lines.append("\n## Filter Effectiveness\n")
        fe = results.get('filter_effectiveness', {})
        bp = fe.get('bandpass_effectiveness', {})
        notch = fe.get('notch_effectiveness', {})
        report_lines.extend([
            f"- **Bandpass Out-of-Band Reduction:** {bp.get('out_of_band_reduction_percent', 0):.2f}%",
            f"- **Bandpass In-Band Preservation:** {bp.get('in_band_preservation_percent', 0):.2f}%",
            f"- **Notch Filter Reduction (50 Hz):** {notch.get('notch_reduction_percent', 0):.2f}%",
            f"- **Overall Filter Score:** {fe.get('overall_filter_score', 0):.2f}/100",
        ])

        # Frequency Domain
        report_lines.append("\n## Frequency Domain Analysis\n")
        fd = results.get('frequency_domain_metrics', {})
        report_lines.extend([
            f"- **Dominant Frequency (Raw):** {fd.get('raw_dominant_frequency', 0):.2f} Hz",
            f"- **Dominant Frequency (Cleaned):** {fd.get('cleaned_dominant_frequency', 0):.2f} Hz",
            f"- **Frequency Shift:** {fd.get('frequency_shift_hz', 0):.3f} Hz",
            f"- **Power Preservation:** {fd.get('total_power_preservation', 0):.2f}%",
            f"- **Spectral Correlation:** {fd.get('spectral_correlation', 0):.3f}",
        ])

        # Artefact Removal
        report_lines.append("\n## Artefact Removal Metrics\n")
        am = results.get('artefact_metrics', {})
        report_lines.extend([
            f"- **Artefacts Detected (Raw):** {am.get('artefacts_detected_raw', 0)}",
            f"- **Artefacts Detected (Cleaned):** {am.get('artefacts_detected_cleaned', 0)}",
            f"- **Artefact Reduction:** {am.get('artefact_reduction_percent', 0):.2f}%",
            f"- **Peak Amplitude Reduction:** {am.get('peak_amplitude_reduction', 0):.2f}%",
        ])

        # Statistical Validation
        report_lines.append("\n## Statistical Validation\n")
        sv = results.get('statistical_validation', {})
        report_lines.extend([
            f"- **Variance Ratio:** {sv.get('variance_ratio', 0):.3f}",
            f"- **Mean Preservation:** {sv.get('mean_preservation', 0):.2f}%",
            f"- **Statistical Integrity Score:** {sv.get('statistical_integrity_score', 0):.2f}/100",
        ])

        # Pipeline Health
        report_lines.append("\n## Pipeline Health Assessment\n")
        ph = results.get('pipeline_health', {})
        report_lines.extend([
            f"- **Health Score:** {ph.get('health_score', 0):.2f}/100",
            f"- **Status:** {ph.get('status', 'unknown')}",
        ])
        
        issues = ph.get('issues', [])
        warnings = ph.get('warnings', [])
        if issues:
            report_lines.append("\n### Issues:")
            for issue in issues:
                report_lines.append(f"- ⚠️ {issue}")
        if warnings:
            report_lines.append("\n### Warnings:")
            for warning in warnings:
                report_lines.append(f"- ⚠️ {warning}")

        # Performance (if available)
        perf = results.get('performance_metrics', {})
        if perf.get('total_time'):
            report_lines.append("\n## Performance Metrics\n")
            report_lines.extend([
                f"- **Total Processing Time:** {perf.get('total_time', 0):.3f} seconds",
                f"- **Processing Speed:** {perf.get('samples_per_second', 0):,.0f} samples/second",
                f"- **Efficiency Score:** {perf.get('efficiency_score', 0):.2f}/100",
            ])

        return "\n".join(report_lines)

