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
    *   **Generation:** `kicad-sch-api` (for generating visual `.kicad_sch` files).
    *   **Target Version:** **KiCad 9.0**.
    *   **Live Control:** `kicad-python` (KiCad 9 IPC) for future live updates.

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
    *   User manually imports/opens this sheet in KiCad 9.
    *   Verification: Basic electrical rule checks (e.g., "Did you forget a decoupling capacitor?").

### Phase 3: The "Agentic" Interface (Chat & Settings)
*   **Goal:** A centralized hub for interaction and configuration.
*   **Features:**
    *   Chat Interface with streaming responses (WebSockets or Polling).
    *   **Model Configuration:** A Settings page allowing the user to switch between models (Gemini 3, GPT-5.2, Claude 4.5) and manage API keys dynamically.
    *   System Prompt Customization (Future).

### Phase 4: The "Schematic Drafter" (Tool Use)
*   **Goal:** "Place and route this schematic on a 2-layer board."
*   **Challenges:** PCB layout involves complex spatial reasoning and physics (impedance, thermal) which is significantly harder than schematic connectivity.
*   **Features:**
    *   Algorithmic placement suggestions (grouping components by schematic function).
    *   Programmatic generation of `.kicad_pcb` files (footprints, board outline).
    *   Assisted routing or integration with external routing engines.

## 3. Standards & Development Rules
See [AI_RULES.md](docs/AI_RULES.md) for the complete list of coding standards, architectural guidelines, and documentation mandates.

## 4. AI Strategy: "The Librarian & The Engineer"

We will **NOT** train or fine-tune a custom model. Electronics design requires high precision and up-to-date component data, which static models struggle with. Instead, we use a **RAG (Retrieval-Augmented Generation) + Tool Use** approach.

### Why No Fine-Tuning?
1.  **Velocity of Data:** New components are released daily. A trained model is frozen in time.
2.  **Precision > Probability:** Electronics requires exact values (e.g., matching impedance). LLMs are probabilistic token predictors; relying on them for raw facts is dangerous.
3.  **State of the Art:** Current SOTA models (Claude 3.5 Sonnet, GPT-4o) already possess superior reasoning and coding capabilities than any smaller, fine-tuned model we could produce.

### The Strategy
*   **The Engineer (LLM):** Uses reasoning to connect systems. It writes Python code, doesn't manually place wires.
*   **The Librarian (RAG):** A curated local database (`backend/knowledge/`) containing:
    *   **The Cookbook:** Verified `kicad-sch-api` code snippets for common patterns (Buck Converters, MCU decoupling, USB-C ports).
    *   **The Datasheet Reader:** A tool that extracts "Typical Application" schematics from PDFs to ground the design in manufacturer specs.

### Implementation
1.  **Context Injection:** When a user asks for a "5V Regulator," the system retrieves the `LDO_Pattern.py` and `Buck_Converter_Pattern.py` snippets.
2.  **Tool Execution:** The LLM calls the `search_component` tool to find a real, in-stock part at LCSC/DigiKey.
3.  **Code Synthesis:** The LLM combines the *Pattern* (logic) with the *Component Data* (parameters) to generate the final KiCad schematic script.

## 5. Next Steps
1.  **Initialize Project:** Setup `git`, `uv` environment, and directory structure. (Completed)
2.  **Prototype "Schematic Gen":** Write a script using `kicad-sch-api` to generate a simple "Resistor + LED" schematic. (Completed)
3.  **Prototype "Part Search":** Build a simple script to query LCSC/DigiKey.
4.  **Knowledge Base:** Create the initial `backend/knowledge/patterns/` directory and populate it with a "Hello World" schematic pattern.