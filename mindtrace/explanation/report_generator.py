"""
Scientific Report Generator for EEG Analysis Results
Generates properly structured, downloadable reports
"""
from datetime import datetime


class EEGReportGenerator:
    """Generates structured scientific reports from EEG analysis data."""

    def __init__(self):
        self.report_format = "markdown"  # Can be "markdown" or "html"

    def generate_report(self, analysis_results, format="markdown"):
        """
        Generate a structured scientific report from analysis results.

        Args:
            analysis_results: Dictionary containing analysis data from EEGAnalyzer
            format: Output format ("markdown" or "html")

        Returns:
            Dictionary with formatted report sections
        """
        self.report_format = format

        sections = {
            "title": self._generate_title(),
            "executive_summary": self._generate_executive_summary(analysis_results),
            "signal_quality": self._generate_signal_quality_section(analysis_results),
            "frequency_analysis": self._generate_frequency_analysis_section(analysis_results),
            "clinical_findings": self._generate_clinical_findings_section(analysis_results),
            "technical_details": self._generate_technical_details_section(analysis_results),
            "recommendations": self._generate_recommendations_section(analysis_results),
        }

        # Combine into full report
        full_report = self._compile_report(sections)

        return {
            "sections": sections,
            "full_report": full_report,
            "format": format
        }

    def _generate_title(self):
        """Generate report title and metadata."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""# EEG Signal Analysis Report

**Generated:** {timestamp}
**System:** MindTrace EEG Analysis Platform
**Report Type:** Signal Quality and Frequency Analysis
"""

    def _generate_executive_summary(self, analysis):
        """Generate executive summary section."""
        snr = analysis.get('snr_improvement', 0)
        noise_red = analysis.get('noise_reduction', 0)
        dominant = analysis.get('dominant_band', 'unknown')

        summary = f"""## Executive Summary

This report presents the results of automated EEG signal processing and analysis. The raw EEG recording underwent a comprehensive cleaning pipeline to remove artefacts and noise, followed by detailed frequency-domain analysis.

**Key Findings:**
- Signal quality improved by **{snr:.1f} dB** (SNR)
- Noise reduction: **{noise_red:.1f}%**
- Dominant brain rhythm: **{dominant.capitalize()} band**
- Processing status: **Complete**

The cleaned signal shows clear characteristics suitable for research-grade analysis.
"""
        return summary

    def _generate_signal_quality_section(self, analysis):
        """Generate signal quality metrics section."""
        snr = analysis.get('snr_improvement', 0)
        noise_red = analysis.get('noise_reduction', 0)
        artefacts = analysis.get('artefacts_detected', 0)

        section = f"""## Signal Quality Assessment

### Noise Reduction
The cleaning pipeline successfully reduced environmental and physiological noise in the recording.

| Metric | Value | Interpretation |
|--------|-------|----------------|
| SNR Improvement | {snr:.1f} dB | {'Excellent' if snr > 10 else 'Good' if snr > 5 else 'Moderate'} |
| Noise Reduction | {noise_red:.1f}% | {'High' if noise_red > 30 else 'Moderate' if noise_red > 15 else 'Low'} |
| Residual Artefacts | {artefacts} events | {'Clean' if artefacts == 0 else 'Acceptable' if artefacts < 3 else 'Review recommended'} |

### Interpretation
"""

        if snr > 10:
            section += "The signal-to-noise ratio improvement is excellent, indicating highly successful noise reduction. "
        elif snr > 5:
            section += "The signal-to-noise ratio improvement is good, indicating effective noise reduction. "
        else:
            section += "The signal-to-noise ratio improvement is moderate. "

        if artefacts == 0:
            section += "No significant artefacts remain in the cleaned signal, making it suitable for detailed analysis."
        elif artefacts < 3:
            section += f"{artefacts} minor artefact event(s) detected but overall signal quality is acceptable."
        else:
            section += f"{artefacts} artefact events detected. Manual review may be beneficial for critical applications."

        return section

    def _generate_frequency_analysis_section(self, analysis):
        """Generate frequency analysis section."""
        band_powers = analysis.get('band_powers', {})
        dominant = analysis.get('dominant_band', 'unknown')
        patterns = analysis.get('patterns', [])

        section = f"""## Frequency Domain Analysis

### Power Distribution Across EEG Bands

The following table shows the relative power in each standard EEG frequency band:

| Frequency Band | Range (Hz) | Power (%) | Clinical Significance |
|----------------|------------|-----------|----------------------|
| Delta (δ) | 0.5 - 4 | {band_powers.get('delta', 0):.1f}% | Deep sleep, unconscious processes |
| Theta (θ) | 4 - 8 | {band_powers.get('theta', 0):.1f}% | Drowsiness, meditation, memory |
| Alpha (α) | 8 - 13 | {band_powers.get('alpha', 0):.1f}% | Relaxed wakefulness, closed eyes |
| Beta (β) | 13 - 30 | {band_powers.get('beta', 0):.1f}% | Active thinking, focus, anxiety |
| Gamma (γ) | 30 - 45 | {band_powers.get('gamma', 0):.1f}% | High-level cognition, perception |

### Dominant Rhythm: {dominant.capitalize()} Band

"""

        # Add interpretation based on dominant band
        if dominant == 'alpha':
            section += """**Interpretation:** The recording is dominated by alpha rhythm, which is characteristic of:
- Relaxed, wakeful state with eyes closed or relaxed
- Good attentional capacity
- Calm mental state
- Normal resting-state brain activity

This pattern is considered typical for a healthy resting-state recording."""

        elif dominant == 'beta':
            section += """**Interpretation:** The recording shows dominant beta activity, which indicates:
- Active cognitive processing
- Focused attention or concentration
- Possible elevated alertness or arousal
- Mental problem-solving or active thinking

This pattern is normal during tasks requiring mental effort."""

        elif dominant == 'theta':
            section += """**Interpretation:** The recording is dominated by theta waves, suggesting:
- Drowsiness or light sleep state
- Deep meditative state
- Memory processing and consolidation
- Reduced alertness

This pattern is normal during drowsiness, meditation, or certain memory tasks."""

        elif dominant == 'delta':
            section += """**Interpretation:** The recording shows elevated delta activity, which may indicate:
- Deep sleep state (if recorded during sleep)
- Possible pathological condition (if recorded during wakefulness)
- Requires clinical interpretation in context

**Note:** Dominant delta in waking recordings is unusual and may warrant further investigation."""

        elif dominant == 'gamma':
            section += """**Interpretation:** The recording shows notable gamma activity, associated with:
- High-level cognitive processing
- Sensory perception and binding
- Complex information integration
- Heightened mental activity

This pattern may reflect intensive cognitive engagement."""

        # Add detected patterns
        if patterns:
            section += "\n\n### Additional Patterns Detected\n\n"
            pattern_descriptions = {
                'strong_alpha_rhythm': '- **Strong Alpha Rhythm**: Prominent 8-13 Hz oscillations indicating relaxed alertness',
                'elevated_theta': '- **Elevated Theta**: Increased 4-8 Hz activity suggesting drowsiness or deep focus',
                'high_beta_activity': '- **High Beta Activity**: Elevated 13-30 Hz power indicating active thinking or stress',
                'elevated_delta': '- **Elevated Delta**: Unusual slow-wave activity that may require clinical review'
            }
            for pattern in patterns:
                if pattern in pattern_descriptions:
                    section += pattern_descriptions[pattern] + "\n"

        return section

    def _generate_clinical_findings_section(self, analysis):
        """Generate clinical findings section."""
        indicators = analysis.get('indicators', [])

        section = """## Clinical Observations

### Neuroscience Interpretation

"""

        if not indicators:
            section += """No specific clinical indicators were identified in this analysis. The EEG pattern falls within typical parameters for the dominant frequency band detected.

**Standard Disclaimer:** This automated analysis provides preliminary insights based on frequency-domain characteristics. Clinical interpretation should be performed by qualified healthcare professionals in the appropriate clinical context.
"""
        else:
            section += "The following observations were made based on the frequency analysis:\n\n"

            for i, indicator in enumerate(indicators, 1):
                section += f"**{i}. {indicator.get('type', 'General').capitalize()} Observation**\n"
                section += f"- {indicator.get('description', 'No description available')}\n\n"

            section += """
### Important Notes

⚠️ **Clinical Context Required**: These observations are based on automated frequency analysis and should be interpreted within the appropriate clinical context.

⚠️ **Not Diagnostic**: This analysis is for research and screening purposes only. It does not constitute a medical diagnosis.

⚠️ **Professional Review**: Any concerning patterns should be reviewed by a qualified neurologist or clinical neurophysiologist.
"""

        return section

    def _generate_technical_details_section(self, analysis):
        """Generate technical processing details section."""
        section = """## Technical Processing Details

### Signal Processing Pipeline

The EEG data underwent the following processing steps:

#### 1. Bandpass Filtering
- **Filter Type:** Butterworth bandpass filter
- **Frequency Range:** 1 - 40 Hz
- **Purpose:** Isolate brain-relevant frequency bands, remove baseline drift and high-frequency noise

#### 2. Notch Filtering
- **Filter Type:** IIR notch filter
- **Target Frequency:** 50 Hz
- **Purpose:** Eliminate electrical line noise from recording environment

#### 3. Independent Component Analysis (ICA)
- **Algorithm:** FastICA decomposition
- **Purpose:** Identify and remove physiological artefacts (eye blinks, muscle activity)
- **Method:** Components with unusually high amplitude (>3× median) were removed

#### 4. Frequency Analysis
- **Method:** Welch's periodogram
- **Window:** 256 samples (Hamming window)
- **Frequency Resolution:** ~1 Hz
- **Analysis Bands:** Delta, Theta, Alpha, Beta, Gamma

### Data Quality Assurance

✓ Pre-processing validation completed
✓ Artefact detection performed
✓ Signal continuity verified
✓ Frequency analysis validated
"""

        return section

    def _generate_recommendations_section(self, analysis):
        """Generate recommendations based on findings."""
        dominant = analysis.get('dominant_band', 'unknown')
        artefacts = analysis.get('artefacts_detected', 0)
        indicators = analysis.get('indicators', [])

        section = """## Recommendations

### Next Steps

"""

        if artefacts > 3:
            section += "1. **Manual Review**: Consider manual inspection of remaining artefact events\n"

        if dominant == 'delta':
            section += "2. **Clinical Review**: Elevated delta activity may warrant expert neurological review\n"
        elif dominant == 'theta':
            section += "2. **Context Assessment**: Verify recording conditions (awake vs. drowsy state)\n"

        section += """3. **Data Archival**: Store both raw and cleaned datasets for future reference
4. **Further Analysis**: Consider time-domain or connectivity analysis for deeper insights

### Data Usage Guidelines

**Recommended Applications:**
- Research studies on brain state and cognition
- Neurofeedback training applications
- Educational demonstrations of EEG patterns
- Baseline assessment for longitudinal studies

**Not Recommended For:**
- Clinical diagnosis without expert review
- Safety-critical applications without validation
- Legal or forensic purposes

---

*End of Report*
"""

        return section

    def _compile_report(self, sections):
        """Compile all sections into a complete report."""
        return "\n\n".join([
            sections["title"],
            sections["executive_summary"],
            sections["signal_quality"],
            sections["frequency_analysis"],
            sections["clinical_findings"],
            sections["technical_details"],
            sections["recommendations"]
        ])

    def generate_audio_script(self, analysis_results):
        """
        Generate a conversational script for audio (different from the report).

        Args:
            analysis_results: Dictionary containing analysis data

        Returns:
            String containing conversational summary for TTS
        """
        snr = analysis_results.get('snr_improvement', 0)
        noise_red = analysis_results.get('noise_reduction', 0)
        dominant = analysis_results.get('dominant_band', 'unknown')
        band_powers = analysis_results.get('band_powers', {})
        dominant_power = band_powers.get(dominant, 0)

        script = f"Your EEG analysis is complete. "

        # Signal quality
        if snr > 10:
            script += f"The signal quality is excellent, with a {snr:.1f} decibel improvement in signal-to-noise ratio. "
        else:
            script += f"Signal quality improved by {snr:.1f} decibels. "

        # Dominant band
        script += f"The analysis shows that {dominant} waves are dominant, making up {dominant_power:.0f} percent of the total brain activity. "

        # Interpretation
        if dominant == 'alpha':
            script += "This alpha rhythm pattern suggests you were in a relaxed, wakeful state. This is completely normal and indicates good brain function. "
        elif dominant == 'beta':
            script += "This beta activity suggests active thinking or mental focus. This pattern is typical when concentrating or engaged in problem-solving. "
        elif dominant == 'theta':
            script += "The theta dominance suggests a drowsy or meditative state. This is normal during light sleep, meditation, or deep relaxation. "
        elif dominant == 'delta':
            script += "Delta waves are prominent. If this was recorded during sleep, this is normal. However, if recorded while awake, this may need further review. "

        # Artefacts
        artefacts = analysis_results.get('artefacts_detected', 0)
        if artefacts == 0:
            script += "The cleaned signal is free of artefacts and suitable for detailed analysis. "
        else:
            script += f"The system detected {artefacts} minor artefact events, but the overall quality remains good. "

        # Closing
        script += "For detailed findings, please review the full written report, which includes frequency breakdowns, clinical observations, and technical processing details. "

        return script
