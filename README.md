# Enterprise Air Quality Monitoring Dashboard

A scientifically rigorous, real-time Air Quality Monitoring dashboard designed for heavy industry (e.g., Mining, Smelting) and regional environmental monitoring. It bridges the gap between raw telemetry and regulatory compliance, ensuring adherence to Indonesian and Global Standards.

## Scientific Framework & Compliance
This software architecture is built strictly upon the latest regulatory frameworks and environmental engineering methodologies:
- **ISPU Calculation Engine:** Mathematically implements the *Indeks Standar Pencemar Udara* formula based on **PermenLHK No. 14 Tahun 2020**.
- **Indonesian Ambien Standards:** Incorporates compliance thresholding against **PP No. 22 Tahun 2021** (Lampiran VII - Baku Mutu Udara Ambien Nasional).
- **Global Standards:** Cross-references data against the stringent **WHO 2021 Global Air Quality Guidelines**.
- **Data Ingestion Readiness:** The pipeline architecture is designed to ingest standardized time-series data from US EPA **FRM (Federal Reference Method)** or **FEM (Federal Equivalent Method)** certified continuous sensors (CEMS/AQMS).

## Phase 1: Software Prototype (Current State)
To demonstrate the UX/UI and calculation capabilities without deploying physical hardware, the current application operates a `Local Data Generator`. 
This generator dynamically simulates realistic, constrained environmental telemetry (PM10, PM2.5, SO2, NO2, CO, O3) specific to locations in **Nusa Tenggara Barat (NTB)**, such as Sumbawa Barat and Mataram. This ensures zero downtime during portfolio demonstrations.

## Features
- **Theoretical Accuracy**: Conversions from `ppm/ppb` to `µg/m³` utilize standard thermodynamic conditions (25°C, 1 atm) as required by international benchmarking.
- **Real-Time Visualization**: Leaflet.js interactive maps and Chart.js high-performance visualizations.
- **Advanced UI/UX**: Professional dark-mode glassmorphism interface built for control-room operability.

## Tech Stack
- **Backend:** Python, FastAPI (High-performance API handling)
- **Frontend:** Vanilla JS, HTML, Custom CSS
- **Libraries:** Leaflet.js, Chart.js

## How to Run Locally
1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```
3. **View Dashboard:**
   Open your browser and navigate to: [http://127.0.0.1:8000/app/](http://127.0.0.1:8000/app/)
