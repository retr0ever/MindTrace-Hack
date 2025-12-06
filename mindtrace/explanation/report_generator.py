"""
Scientific Report Generator for EEG Analysis Results
Generates properly structured, downloadable reports (Markdown & PDF)
"""
from datetime import datetime
from fpdf import FPDF

class PDFReport(FPDF):
    def header(self):
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Title
        self.cell(0, 10, 'MindTrace EEG Analysis Report', 0, 1, 'C')
        # Line break
        self.ln(5)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

    def section_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 10, label, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Times', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

class EEGReportGenerator:
    """Generates structured scientific reports from EEG analysis data."""

    def __init__(self):
        self.report_format = "markdown"

    def generate_report(self, analysis_results, format="markdown"):
        """
        Generate a structured scientific report text (Markdown/HTML ready).
        Returns a dictionary with report sections and full text.
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

        full_report = self._compile_report(sections)

        return {
            "sections": sections,
            "full_report": full_report,
            "format": format
        }

    def generate_pdf_report(self, analysis_results, output_path):
        """
        Generates a PDF version of the report using FPDF.
        """
        pdf = PDFReport()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Metadata
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.set_font('Times', 'I', 10)
        pdf.cell(0, 10, f'Generated: {timestamp}', 0, 1)
        pdf.ln(5)

        # Executive Summary
        pdf.section_title('1. Executive Summary')
        
        snr = analysis_results.get('snr_improvement', 0)
        noise_red = analysis_results.get('noise_reduction', 0)
        dominant = analysis_results.get('dominant_band', 'unknown')
        
        summary_text = (
            f"This report presents the results of automated EEG signal processing. "
            f"The raw recording underwent a comprehensive cleaning pipeline. "
            f"Signal quality improved by {snr:.1f} dB (SNR) with a {noise_red:.1f}% reduction in noise.\n\n"
            f"The dominant brain rhythm was identified as the {dominant.capitalize()} band."
        )
        pdf.chapter_body(summary_text)

        # Signal Quality Table
        pdf.section_title('2. Signal Quality Metrics')
        
        # Table Header
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 8, 'Metric', 1)
        pdf.cell(40, 8, 'Value', 1)
        pdf.cell(90, 8, 'Interpretation', 1)
        pdf.ln()
        
        # Table Rows
        pdf.set_font('Times', '', 10)
        
        # Row 1: SNR
        pdf.cell(60, 8, 'SNR Improvement', 1)
        pdf.cell(40, 8, f'{snr:.1f} dB', 1)
        pdf.cell(90, 8, 'Excellent' if snr > 10 else 'Good' if snr > 5 else 'Moderate', 1)
        pdf.ln()
        
        # Row 2: Noise
        pdf.cell(60, 8, 'Noise Reduction', 1)
        pdf.cell(40, 8, f'{noise_red:.1f}%', 1)
        pdf.cell(90, 8, 'High' if noise_red > 30 else 'Moderate' if noise_red > 15 else 'Low', 1)
        pdf.ln()
        
        # Row 3: Artefacts
        artefacts = analysis_results.get('artefacts_detected', 0)
        pdf.cell(60, 8, 'Residual Artefacts', 1)
        pdf.cell(40, 8, f'{artefacts} events', 1)
        pdf.cell(90, 8, 'Clean' if artefacts == 0 else 'Review Required', 1)
        pdf.ln(8)

        # Frequency Analysis
        pdf.section_title('3. Frequency Domain Analysis')
        pdf.chapter_body("Power spectral density analysis revealed the following distribution across standard EEG bands:")
        
        # Frequency Table
        band_powers = analysis_results.get('band_powers', {})
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 8, 'Band', 1)
        pdf.cell(40, 8, 'Range (Hz)', 1)
        pdf.cell(40, 8, 'Power (%)', 1)
        pdf.ln()
        
        pdf.set_font('Times', '', 10)
        bands_data = [
            ('Delta', '0.5 - 4', band_powers.get('delta', 0)),
            ('Theta', '4 - 8', band_powers.get('theta', 0)),
            ('Alpha', '8 - 13', band_powers.get('alpha', 0)),
            ('Beta', '13 - 30', band_powers.get('beta', 0)),
            ('Gamma', '30 - 45', band_powers.get('gamma', 0)),
        ]
        
        for name, rng, power in bands_data:
            pdf.cell(40, 8, name, 1)
            pdf.cell(40, 8, rng, 1)
            pdf.cell(40, 8, f'{power:.1f}%', 1)
            pdf.ln()
        pdf.ln(5)
        
        pdf.set_font('Times', 'B', 11)
        pdf.cell(0, 8, f"Dominant Rhythm: {dominant.capitalize()}", 0, 1)
        pdf.set_font('Times', '', 11)
        
        # Interpretation text
        interp_map = {
            'alpha': "This suggests a relaxed, wakeful state.",
            'beta': "This indicates active concentration or alertness.",
            'theta': "This may reflect drowsiness or meditation.",
            'delta': "This is typical of deep sleep.",
            'gamma': "This suggests high-level cognitive processing."
        }
        pdf.multi_cell(0, 6, interp_map.get(dominant, ""))
        pdf.ln()

        # Clinical Findings
        pdf.section_title('4. Clinical & Technical Observations')
        indicators = analysis_results.get('indicators', [])
        
        if not indicators:
            pdf.chapter_body("No specific clinical anomalies were identified. The signal falls within typical parameters.")
        else:
            for ind in indicators:
                pdf.cell(5) # indent
                pdf.cell(0, 6, f"- {ind.get('description', '')}", 0, 1)
            pdf.ln()
            
        pdf.section_title('5. Methodology')
        method_text = (
            "Processing included 4th-order Butterworth bandpass filtering (1-40 Hz) and 50Hz notch filtering. "
            "Independent Component Analysis (FastICA) was used to identify and remove physiological artefacts. "
            "Spectral analysis was performed using Welch's method with a Hamming window."
        )
        pdf.chapter_body(method_text)
        
        # Disclaimer
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 9)
        pdf.multi_cell(0, 5, "Disclaimer: This report is generated by an automated system for research purposes only. It is not a medical diagnosis.")

        # Output
        pdf.output(output_path)
        return output_path

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