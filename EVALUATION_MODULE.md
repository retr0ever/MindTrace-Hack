# Evaluation Module Documentation

## Overview

The evaluation module provides comprehensive assessment of the EEG processing pipeline and algorithms. It evaluates both the **performance** (speed, efficiency) and **quality** (signal improvement, noise reduction, preservation) of the processing pipeline.

## Features

### 1. Performance Metrics
- **Processing Time**: Measures execution time for each pipeline step
- **Throughput**: Samples processed per second
- **Efficiency Score**: Overall processing efficiency rating (0-100)

### 2. Signal Quality Metrics
- **SNR Improvement**: Signal-to-Noise Ratio improvement in dB
- **Noise Reduction**: Percentage of noise removed
- **Signal Preservation**: How much of the original signal is retained (correlation-based)
- **RMSE**: Root Mean Square Error between raw and cleaned data
- **Dynamic Range Preservation**: Preservation of signal amplitude range

### 3. Filter Effectiveness
- **Bandpass Filter**: 
  - Out-of-band noise reduction
  - In-band signal preservation
- **Notch Filter**: 
  - 50 Hz line noise reduction
- **Overall Filter Score**: Combined effectiveness rating

### 4. Frequency Domain Analysis
- **Dominant Frequency**: Main frequency component before and after processing
- **Frequency Shift**: Change in dominant frequency (should be minimal)
- **Power Preservation**: Total spectral power retained
- **Spectral Correlation**: Correlation between raw and cleaned frequency spectra

### 5. Statistical Validation
- **Normality Tests**: Shapiro-Wilk test for data distribution
- **Variance Ratio**: Change in signal variance
- **Mean Preservation**: Preservation of signal mean
- **Skewness & Kurtosis**: Preservation of higher-order statistics
- **Statistical Integrity Score**: Overall statistical preservation rating

### 6. Artefact Removal Metrics
- **Artefact Detection**: Count of artefacts in raw vs cleaned data
- **Artefact Reduction**: Percentage of artefacts removed
- **Peak Amplitude Reduction**: Reduction in maximum signal amplitude
- **Artefact Power Reduction**: Reduction in power from artefact regions

### 7. Pipeline Health Assessment
- **Health Score**: Overall pipeline health (0-100)
- **Issue Detection**: Identifies problems like NaN values, clipping, over-filtering
- **Warnings**: Flags potential issues like under-filtering
- **Status**: Overall health status (healthy/degraded/unhealthy)

### 8. Overall Evaluation Score
A weighted composite score (0-100) combining all metrics:
- Signal Quality: 30%
- Filter Effectiveness: 25%
- Frequency Domain: 15%
- Artefact Removal: 15%
- Statistical Validation: 10%
- Pipeline Health: 5%

## Usage

### In Code

```python
from mindtrace.processing.evaluator import PipelineEvaluator

# Initialize evaluator
evaluator = PipelineEvaluator(sampling_rate=256)

# Run evaluation
results = evaluator.evaluate_pipeline(
    raw_data=raw_eeg_data,
    cleaned_data=cleaned_eeg_data,
    processing_times={'initial_clean': 0.5, 'ica': 1.2},
    pipeline_steps=['initial_clean', 'ica']
)

# Generate report
report = evaluator.generate_evaluation_report(results)
print(report)
```

### Via MindTraceAgent

The evaluation is automatically run after initial cleaning:

```python
agent = MindTraceAgent(config)
agent.load_data(data)
agent.initial_clean()  # Evaluation runs automatically

# Access results
evaluation_results = agent.evaluation_results
overall_score = evaluation_results['overall_score']

# Get formatted report
report = agent.get_evaluation_report()
```

### Via Web API

#### Get Evaluation Results (JSON)
```bash
GET /api/evaluation
```

Returns comprehensive evaluation metrics as JSON.

#### Get Evaluation Report (HTML)
```bash
GET /api/evaluation/report
```

Returns formatted evaluation report in HTML format.

#### Run Evaluation Manually
```bash
POST /api/evaluation/run
```

Manually trigger evaluation (useful after custom processing steps).

#### Download Evaluation Report
```bash
GET /download/evaluation-report
```

Downloads the evaluation report as a Markdown file.

## Evaluation Results Structure

```python
{
    'timestamp': float,  # Unix timestamp
    'data_info': {
        'duration_seconds': float,
        'samples': int,
        'sampling_rate': float,
        'raw_mean': float,
        'raw_std': float,
        # ... more data statistics
    },
    'performance_metrics': {
        'total_time': float,
        'samples_per_second': float,
        'efficiency_score': float,
        'performance_rating': {'score': float, 'rating': str}
    },
    'signal_quality_metrics': {
        'snr_db': float,
        'noise_reduction_percent': float,
        'rmse': float,
        'correlation': float,
        'signal_preservation_score': float,
        'quality_rating': {'score': float, 'rating': str}
    },
    'filter_effectiveness': {
        'bandpass_effectiveness': {...},
        'notch_effectiveness': {...},
        'overall_filter_score': float
    },
    'frequency_domain_metrics': {
        'raw_dominant_frequency': float,
        'cleaned_dominant_frequency': float,
        'frequency_shift_hz': float,
        'total_power_preservation': float,
        'spectral_correlation': float
    },
    'statistical_validation': {
        'variance_ratio': float,
        'mean_preservation': float,
        'statistical_integrity_score': float
    },
    'artefact_metrics': {
        'artefacts_detected_raw': int,
        'artefacts_detected_cleaned': int,
        'artefact_reduction_percent': float
    },
    'pipeline_health': {
        'health_score': float,
        'issues': list,
        'warnings': list,
        'status': str
    },
    'overall_score': float  # 0-100 composite score
}
```

## Interpretation Guide

### Overall Score
- **80-100**: Excellent - Pipeline performing very well
- **60-79**: Good - Pipeline performing well with minor improvements possible
- **40-59**: Moderate - Pipeline working but has room for improvement
- **0-39**: Poor - Pipeline may have issues, review recommended

### Signal Quality Rating
- **Excellent**: High SNR improvement (>15 dB), good noise reduction (>60%), high preservation (>85%)
- **Good**: Moderate improvements across all metrics
- **Moderate**: Some improvement but could be better
- **Poor**: Minimal or negative improvements

### Pipeline Health Status
- **Healthy**: No issues detected, score ≥ 80
- **Degraded**: Some warnings, score 50-79
- **Unhealthy**: Issues detected, score < 50

## Best Practices

1. **Run evaluation after each major processing step** to track improvements
2. **Compare evaluations** across different parameter settings
3. **Monitor pipeline health** to catch issues early
4. **Use evaluation results** to optimize filter parameters
5. **Track overall score trends** over multiple datasets

## Integration Points

The evaluation module is integrated into:
- `MindTraceAgent.initial_clean()` - Automatic evaluation after cleaning
- `MindTraceAgent.run_evaluation()` - Manual evaluation trigger
- `web_app.py` - API endpoints for web interface
- Upload and command endpoints - Include evaluation summary in results

## Future Enhancements

Potential additions:
- Ground truth comparison (when available)
- Comparative evaluation across multiple algorithms
- Visualization of evaluation metrics
- Historical evaluation tracking
- Automated parameter optimization based on evaluation scores

