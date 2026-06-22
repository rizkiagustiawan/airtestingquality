# Design Spec: Scientifically-Backed Enhancements for AirQ Web GIS

> Based on research papers collected on 23 June 2026
> All implementations strictly follow peer-reviewed scientific methods

---

## Overview

Five enhancements to the AirQ Web GIS platform, each grounded in published research papers. No feature violates scientific principles; all algorithms and methods are sourced from peer-reviewed literature.

---

## 1. Forecasting Engine v2: Hybrid Trend + Meteorological Model

**Scientific Basis:**
- Du et al. (2019) - "Deep air quality forecasting using hybrid deep learning framework" - 593 citations
- Qiao et al. (2019) - "The Forecasting of PM2.5 Using a Hybrid Model Based on Wavelet Transform" - 195 citations
- Freeman et al. (2018) - "Forecasting air quality time series using deep learning" - 350 citations

**Current State:** `forecast_engine.py` uses simple Gaussian noise on base values. No real trend analysis.

**Enhancement:**
- Add time-series decomposition (trend + seasonal + residual) based on classical decomposition methods
- Add autoregressive component using exponential weighted moving average (EWMA)
- Add meteorological correlation factors (wind speed/direction, mixing height, stability class)
- Keep it lightweight (no PyTorch/TF dependency) using NumPy/SciPy only
- Expose `/api/forecast/v2` endpoint with enhanced predictions

**Key Formula (from Du et al. 2019):**
```
C(t+1) = α·C_trend(t) + β·C_seasonal(t) + γ·C_met(t) + δ·C_residual(t)
```
Where α+β+γ+δ=1, weights optimized via cross-validation on historical data.

---

## 2. QA/QC Pipeline v2: Automated Quality Control

**Scientific Basis:**
- Schmidt et al. (2023) - "System for automated Quality Control (SaQC)" - 44 citations
- Faybishenko et al. (2022) - "Challenging problems of QA/QC of meteorological time series data" - 65 citations
- D'Amore et al. (2015) - "Data quality through a web-based QA/QC system" - 46 citations

**Current State:** `qa_qc.py` has basic range checks and spike detection (>300% jump). Missing: drift detection, consistency checks, temporal plausibility.

**Enhancement (per SaQC framework):**
- **Range check** (existing) - physical bounds validation
- **Spike detection** (enhanced) - Z-score based (threshold=3σ) instead of fixed 300%
- **Drift detection** - detect gradual sensor drift using rolling mean comparison
- **Flatline detection** - detect stuck sensors (same value repeated N times)
- **Temporal consistency** - check if rate of change is physically plausible
- **Cross-pollutant consistency** - check known pollutant relationships (e.g., PM2.5 < PM10)
- Add data quality flag codes per WMO standards

---

## 3. ISPU ML Classifier

**Scientific Basis:**
- Ridho & Mahalisa (2023) - "Analisis Klasifikasi Dataset ISPU di Masa Pandemi menggunakan SVM" - 14 citations
- Sajiwo & Rahmat (2024) - "Klasifikasi ISPU Menggunakan XGBoost dengan SMOTE" - 21 citations
- Oktaviani & Hustinawati (2021) - "Prediksi rata-rata zat berbahaya berdasarkan ISPU menggunakan LSTM" - 28 citations

**Current State:** `ispu_calculator.py` uses breakpoint interpolation (correct per PermenLHK 14/2020). No ML classification.

**Enhancement:**
- Add SVM-based ISPU category classifier (Baik/Sedang/Tidak Sehat/Sangat Tidak Sehat/Berbahaya)
- Add feature engineering: hour, day_of_week, pollutant concentrations, meteorological parameters
- Train on synthetic data matching ISPU breakpoint distributions
- Provide confidence scores for each classification
- Expose `/api/ispu/classify` endpoint

**Key: SVM with RBF kernel (Ridho et al. 2023):**
```
K(x, x') = exp(-γ||x - x'||²)
```

---

## 4. Health Impact Assessment (HIA)

**Scientific Basis:**
- Conti et al. (2017) - "A review of AirQ Models and their applications" - 164 citations
- Liu et al. (2019) - "Ambient Particulate Air Pollution and Daily Mortality in 652 Cities" - 1,667 citations
- Chen et al. (2020) - "Long-term exposure to PM and all-cause and cause-specific mortality" - 1,021 citations
- WHO (2021) - Global Air Quality Guidelines

**Current State:** No health impact assessment module exists.

**Enhancement (based on WHO AirQ+ methodology):**
- Calculate attributable proportion (AP) of health effects from PM2.5, PM10, NO2, O3
- Use concentration-response functions (CRR) from WHO guidelines
- Estimate excess mortality and morbidity risks
- Add hazard quotient (HQ) for non-carcinogenic risk assessment
- Expose `/api/health-impact` endpoint

**Key Formula (WHO AirQ+):**
```
AP = 1 - exp(-β × (C - C₀))
```
Where β = concentration-response coefficient, C = measured concentration, C₀ = counterfactual (WHO guideline).

---

## 5. Source Apportionment with Bivariate Polar Plots

**Scientific Basis:**
- Demirarslan & Zeybek (2022) - "Conventional air pollutant source determination using bivariate polar plot" - 9 citations
- Grange (2019) - "Development of Data Analytic Approaches for Air Quality Data" - PhD thesis
- Agustine et al. (2017) - "Application of open air model (R package) to analyze air pollution data" - 27 citations

**Current State:** `met_data.py` has basic polar plot. No bivariate analysis or source apportionment.

**Enhancement:**
- Add bivariate polar plot with concentration-weighted wind direction
- Add pollution rose (concentration by direction, not just frequency)
- Add local vs regional source estimation using wind speed stratification
- Add source identification heuristics (high conc at low wind = local; high conc at high wind = regional)
- Expose `/api/openair/source-apportionment` endpoint

---

## Implementation Order

1. **Forecasting Engine v2** - enhances existing module, no new dependencies
2. **QA/QC Pipeline v2** - enhances existing module, no new dependencies
3. **ISPU ML Classifier** - new module, uses scikit-learn (lightweight)
4. **Health Impact Assessment** - new module, pure Python/NumPy
5. **Source Apportionment** - enhances existing met_data.py

All implementations: zero new heavy dependencies (no PyTorch, no TensorFlow). Only NumPy/SciPy/scikit-learn.
