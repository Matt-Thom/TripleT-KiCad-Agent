# TripleT KiCad Agent - Project Plan

## Overview
The TripleT KiCad Agent is an AI-powered engineering assistant designed to bridge the gap between high-level system requirements and physical PCB design. Unlike a simple chatbot, this agent acts as a co-designer that understands electronics theory, component availability, and KiCad's file structures.

### Core Mission
To enable designers to describe complex electronic systems in natural language—such as "Build a USB-C PD power delivery interface" or "Design a 915MHz telemetry radio circuit"—and have the agent handle the tedious tasks of part selection, datasheet analysis, and initial schematic drafting.

### Key Capabilities
*   **System-Level Design:** Translating high-level requirements into functional blocks and component choices.
*   **Intelligent Part Selection:** Querying real-time stock and specifications from suppliers like LCSC, DigiKey, and Mouser.
*   **Programmatic Schematic Generation:** Directly generating KiCad `.kicad_sch` files via Python, allowing the user to immediately open and refine the design in the KiCad GUI.
*   **Expert Knowledge Retrieval:** Using Retrieval-Augmented Generation (RAG) to provide verified design patterns, decoupling strategies, and DRC-compliant implementations.

### Strategic Approach
The project is built for **AI-native development**, meaning the codebase and architecture are designed to be easily navigated and extended by AI agents. It prioritizes a local-first architecture (FastAPI/React) to ensure low latency and direct access to the user's KiCad workspace, while maintaining a robust CI/CD pipeline and rigorous testing standards.

## Status
**Phase:** Planning & Requirements Gathering

## 1. Architecture & Tech Stack

### Core Philosophy: "The Hybrid Assistant"
To balance powerful AI processing with KiCad's desktop nature, we will use a **Local Web Server** architecture.
1.  **The Brain (Server):** A local Python server (FastAPI) handling the AI logic, database, and API calls.
2.  **The Face (UI):** A React-based web interface.
3.  **The Hands (Integration):** A lightweight KiCad Plugin that simply connects the running KiCad instance to the local server (e.g., to load generated files or read the current open project).

### Technology Stack
*   **Environment Manager:** `uv` (Fast Python package installer/resolver).
*   **Backend:** Python 3.12+ with **FastAPI**.
*   **Frontend:** React (TypeScript) + Tailwind CSS (served via FastAPI or standalone Vite dev server during dev).
*   **Database:** SQLite (with `SQLAlchemy` or `Tortoise-ORM`) for storing user preferences, chat history, and cached part data.
*   **AI/LLM:** Integration with OpenAI/Anthropic APIs (initially) via `LiteLLM` or `LangChain`.
*   **KiCad Interface:**
    *   **Generation:** `kicad-sch-api` (for generating visual `.kicad_sch` files) or `skidl` (for logical netlists). *Decision: Focus on `kicad-sch-api` so users get a visual schematic.*
    *   **Live Control:** `kicad-python` (KiCad 9 IPC) for future live updates, but file generation is safer for MVP.

## 2. Capability Roadmap

### Phase 1: The "Part & Datasheet" Expert (MVP)
*   **Goal:** Chat with the agent to find parts and get implementation advice.
*   **Features:**
    *   Chat Interface.
    *   Component Search (DigiKey API + `jlcsearch` for LCSC/JLCPCB).
    *   "Save to Project": Save found parts to a local "Bill of Materials" (BOM) database.

### Phase 2: The "Schematic Drafter"
*   **Goal:** "Create a power supply for this 5V rail."
*   **Features:**
    *   Agent generates a `.kicad_sch` file using `kicad-sch-api`.
    *   User manually imports/opens this sheet in KiCad.
    *   Verification: Basic electrical rule checks (e.g., "Did you forget a decoupling capacitor?").

### Phase 3: The "KiCad Native" (Plugin Integration)
*   **Goal:** Seamless workflow inside KiCad.
*   **Features:**
    *   A KiCad Plugin button opens the Web UI in a floating window.
    *   One-click "Insert into Schematic" (requires advanced KiCad scripting/IPC).

### Phase 4: The "PCB Auto-Router" (Future)
*   **Goal:** "Place and route this schematic on a 2-layer board."
*   **Challenges:** PCB layout involves complex spatial reasoning and physics (impedance, thermal) which is significantly harder than schematic connectivity.
*   **Features:**
    *   Algorithmic placement suggestions (grouping components by schematic function).
    *   Programmatic generation of `.kicad_pcb` files (footprints, board outline).
    *   Assisted routing or integration with external routing engines.

## 3. Standards & Development Rules

### Coding Standards (AI Guardrails)
*   **Python:**
    *   Strict Type Hinting (`mypy` compliant).
    *   Style: `Ruff` (replaces Black/Isort/Flake8).
    *   Docstrings: Google Style.
*   **Frontend:**
    *   TypeScript for all components.
    *   Functional Components with Hooks.
*   **Testing:**
    *   Backend: `pytest` with coverage requirements.
    *   Frontend: `Vitest` or `Jest`.
*   **Version Control:**
    *   Branches: `main` (Stable), `dev` (Testing/Integration).
    *   Commits: Conventional Commits (e.g., `feat: add lcsc search`).

## 4. Training & Context (RAG vs. Fine-Tuning)
We will NOT train (fine-tune) a model initially. We will use **RAG (Retrieval-Augmented Generation)**.

*   **The Problem:** LLMs don't memorize every datasheet or KiCad file format quirk.
*   **The Solution:**
    1.  **Library of Knowledge:** We will maintain a `vector database` (or simple JSON store initially) of:
        *   Standard schematic patterns (Buck converters, LDOs, MCU decoupling).
        *   `kicad-sch-api` code examples.
    2.  **Workflow:**
        *   User asks: "Design a 3.3V LDO circuit."
        *   System retrieves: A proven LDO schematic pattern + Datasheet data for a specific part (e.g., AMS1117).
        *   LLM generates: The Python code to build that specific circuit.

## 5. Next Steps
1.  **Initialize Project:** Setup `git`, `uv` environment, and directory structure.
2.  **Prototype "Part Search":** Build a simple script to query LCSC/DigiKey.
3.  **Prototype "Schematic Gen":** Write a script using `kicad-sch-api` to generate a simple "Resistor + LED" schematic to prove viability.