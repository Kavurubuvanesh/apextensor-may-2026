# AeroMind: Real-Time Granite Race Copilot 🏎️🧠

**IBM SkillsBuild AI Builders Challenge (May Innovation Challenge)**

[![IBM Granite](https://img.shields.io/badge/IBM-Granite-blue.svg)](https://github.com/ibm-granite)
[![Langflow](https://img.shields.io/badge/Orchestration-Langflow-orange.svg)](https://www.langflow.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![TORCS](https://img.shields.io/badge/Simulation-TORCS-red.svg)](#)

## 🏁 Overview
In high-speed motorsport, races are won in milliseconds. Modern F1 teams generate terabytes of telemetry data, but human race engineers can only process a fraction of it in real-time. 

**AeroMind** is a "Dual-Brain" AI Copilot that bridges the gap between high-frequency edge physics and enterprise-grade Generative AI. By decoupling a 50Hz local physics engine from the high-latency reasoning of **IBM Granite**, AeroMind processes live track telemetry to provide real-time, actionable tactical advice without ever interrupting the car's survival loop. 

This project successfully orchestrates a C++ racing simulator (TORCS) with an 8-billion parameter LLM, achieving flawless, 0-damage laps across unknown tracks.

---

## 🏎️ The Engineering Challenge
1. **The LLM Latency Trap:** Standard LLMs are too slow to drive a car directly. A 15-second inference delay at 135 km/h means the car travels over 500 meters entirely blind.
2. **Data Overload:** A single car produces thousands of data points per second (wheel slip, radar proximity, aerodynamic load). 
3. **Dynamic Environments:** Hardcoded racing bots cannot adapt to unpredictable opponent behavior or track blockages.

## 🛠️ The AeroMind Architecture (Our Solution)
We solved the latency trap by engineering an asynchronous Edge-to-Cloud architecture with a built-in safety reflex:

1. **The Reflex Brain (Edge / Python):** A custom local agent connected to the TORCS engine handles real-time survival (aerodynamic traction control, PID steering dampening, and emergency collision avoidance) at 50 FPS.
2. **The Strategist Brain (Cloud / IBM Granite):** Using **Langflow**, the system ingests live JSON telemetry streams (track radar, opponent proximity, wheel slip). 
3. **The Rulebook (RAG / Docling):** We utilize **Docling** to parse racing strategy PDFs into a vector database, grounding Granite's responses. Granite analyzes the telemetry and outputs plain-English tactical commands (e.g., *"Track is clear, push SPEED 135 and maintain TARGET_LANE 0.0"*).
4. **The Latency Override:** If the AI takes too long to respond and the car approaches a hairpin, the Edge Brain detects the wall via radar and automatically overrides the LLM, slamming the brakes to ensure 0-damage survival.

---

## 🚀 IBM Technology Stack

* **IBM Granite (granite3-dense:8b):** Acts as the core reasoning engine for the Copilot, providing strategic insights based on JSON telemetry. Run locally via Ollama to minimize network latency.
* **Langflow:** Orchestrates the real-time data ingestion, prompt synthesis, and RAG pipeline.
* **Docling:** Parses complex F1 strategy documents into structured, AI-ready data to ground the Granite model's racing logic.

---

## 📈 Performance Results
AeroMind is track-agnostic. It does not memorize layouts; it drives purely on live LLM strategy and edge-radar reflexes.
* **Track:** CG Speedway 1 & E-Track 2
* **Top Speed:** 122 km/h (Aerodynamic equilibrium limit)
* **Collision Rate:** 0 Damages across multiple test sessions.

---

## 💻 Local Setup & Execution

### Prerequisites
* Python 3.10+
* TORCS (The Open Racing Car Simulator)
* Ollama (with `granite3-dense:8b` pulled)
* Langflow

### 1. Start the Brain (Langflow & Ollama)
Terminal 1: Bypass auth and start Langflow
> export LANGFLOW_SKIP_AUTH_AUTO_LOGIN=true  # (Use $env: for Windows PowerShell)
> python -m langflow run

Terminal 2: Start the IBM Granite Model
> ollama run granite3-dense:8b

*Note: Import the provided flow into Langflow and upload `AeroMind_Strategy.txt` to the Docling node.*

### 2. Start the Race (Edge Engine)
Terminal 3: Launch the TORCS wrapper
> python torcs_jm_par.py

*The TORCS client will boot, and the terminal will output live radio transmissions from Granite.*

---

## 👥 Team
**Buvanesh Kavuru**
Lead Systems Engineer 
*B.Tech in Computer Science and Engineering (AI & ML Specialization)* | *KIIT DU*