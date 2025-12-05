import numpy as np
from scipy.signal import butter, lfilter, iirnotch

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def notch_filter(data, cutoff, fs, Q=30):
    nyq = 0.5 * fs
    freq = cutoff / nyq
    b, a = iirnotch(freq, Q)
    y = lfilter(b, a, data)
    return y
