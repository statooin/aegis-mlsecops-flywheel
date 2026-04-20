# Aegis: The MLSecOps Evaluation Flywheel 🛡️🔄

**Automated infrastructure for LLM Guardrails & Continuous Evaluation.**

[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![PyRIT](https://img.shields.io/badge/Framework-PyRIT%200.12.1-orange.svg)](https://github.com/microsoft/pyrit)
[![Proxy](https://img.shields.io/badge/Engine-Envoy%20%7C%20WASM-blue.svg)](#)
[![Infrastructure](https://img.shields.io/badge/Deploy-Docker%20%7C%20Compose-2496ED.svg)](#)

## 🎯 The "Day 2 Operations" Challenge
In enterprise environments, deploying LLM guardrails is only the first step. The real challenge is **Day 2 Operations**: maintaining the efficacy of these guardrails against rapidly evolving prompt injection techniques and jailbreaks without disrupting legitimate business traffic.

**Aegis** solves this by implementing an automated **MLSecOps Flywheel**:
1. **Attack:** Autonomous Red Teaming using Microsoft PyRIT to discover vulnerability vectors.
2. **Evaluate:** Alignment checks against an independent LLM-Judge (Gemini Pro) to measure False Positive/Negative rates.
3. **Strengthen:** Continuous feedback loop to tune Envoy Proxy WASM filters and ML-classifier weights.

---

## 🏗️ High-Performance Architecture

Aegis is built with a decoupled, cloud-native architecture optimized for sub-millisecond latency and high concurrency:

* **Aegis Gateway (Data Plane):** An **Envoy Proxy** layer utilizing **C++ WASM filters** for real-time payload inspection and heuristic blocking.
* **ML-Inference Worker:** A PyTorch/LiteLLM backend executing deep semantic classification of prompts.
* **Evaluation Framework (Control Plane):** A custom orchestration engine built on **PyRIT 0.12.1 architecture**, automating the security testing lifecycle.
* **Telemetry Hub:** In-memory state management (DuckDB) capturing granular metrics on which specific security echelon triggered a block.

---

## 🚀 Quick Start

### Prerequisites
* Python 3.11+
* Docker & Docker Compose
* Google Gemini API Key (used for the LLM Judge)

### 1. Environment Setup
```bash
git clone [https://github.com/YOUR_USERNAME/aegis-mlsecops-flywheel.git](https://github.com/YOUR_USERNAME/aegis-mlsecops-flywheel.git)
cd aegis-mlsecops-flywheel

# Configure your environment
export GEMINI_API_KEY="your_api_key_here"
```

### 2. SRE Lab Deployment
The project is containerized for deterministic execution and reproducibility:

```bash
# Build the evaluation container with pinned dependencies
docker build --no-cache -t aegis-eval .

# Run the infrastructure test suite
docker run --env-file .env aegis-eval main.py --mode static --limit 10
```

---

## 📊 Evaluation Modes

Aegis supports two distinct operational modes for continuous security validation:

### 1. Static Mode (Regression Testing)
Validates the current gateway configuration against a known dataset of benign and malicious prompts, comparing the gateway's verdict against the LLM Judge.
```bash
python3 main.py --mode static --url http://gateway:8080 --limit 50
```

### 2. Autonomous Red Teaming (Exploration)
Deploys an adversarial LLM to dynamically generate novel jailbreaks, actively attempting to bypass the gateway's current defense echelons.
```bash
python3 main.py --mode redteam --limit 5
```

---

## 🗺️ SRE & Infrastructure Roadmap

- [ ] **eBPF Integration:** Implement kernel-level packet inspection to mitigate infrastructure-layer exploits before they reach the proxy.
- [ ] **Dynamic Control Plane:** Enable zero-downtime weight updates for the WASM filters via Envoy's xDS API.
- [ ] **Kubernetes Native:** Develop a Custom Resource Definition (CRD) and K8s Operator to deploy Aegis as a native sidecar container.

---

## 👨‍💻 Author

**Ilya Averyanov** *Senior Site Reliability Engineer | Security & AI Infrastructure* Specializing in highly available, secure, and observable cloud-native ecosystems.
