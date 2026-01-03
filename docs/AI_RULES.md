# AI Development Rules & Guidelines

## Core Mandates
1.  **Documentation First:** usage of tools, APIs, and architectural decisions must be documented immediately. If you add a feature, update the relevant `docs/*.md` file. **Never leave documentation out of sync with code.**
2.  **KiCad 9 Native:** All file generation and scripting must target **KiCad 9.0+**. Do not rely on deprecated KiCad 6/7/8 patterns unless strictly necessary for compatibility libraries.
3.  **Local-First:** The architecture prioritizes running locally on the user's machine. Cloud calls (AI, Part Search) are the exception, not the rule.

## Coding Standards

### Python (Backend)
*   **Version:** Python 3.12+
*   **Type Hints:** Strict typing required for all function signatures. Use `mypy` to verify.
*   **Style:** Follow `Ruff` defaults (which subsume Black/Isort/Flake8).
*   **Docstrings:** Google Style docstrings for all modules, classes, and public functions.
*   **Testing:** `pytest` is the standard. All new endpoints/logic must have accompanying tests.

### TypeScript (Frontend)
*   **Framework:** React + Tailwind CSS (v4).
*   **Strict Mode:** Enabled. No `any` types unless absolutely unavoidable.
*   **Components:** Functional components with Hooks.

### Version Control
*   **Commits:** Follow Conventional Commits specification.
    *   `feat: ...` for new features.
    *   `fix: ...` for bug fixes.
    *   `docs: ...` for documentation updates.
    *   `chore: ...` for maintenance.
*   **Branches:**
    *   `main`: Stable release.
    *   `dev`: Integration branch.
    *   `feature/*`: Individual feature branches.

## Security & Safety
*   **Secret Management:**
    *   **NEVER** commit API keys, passwords, or tokens to version control.
    *   All secrets must be stored in a `.env` file, which is strictly ignored by `.gitignore`.
    *   Use `.env.example` to document required keys without including values.
*   **Dependency Safety:** Verify all new Python/Node dependencies are reputable before adding them.
*   **Code Execution:** The AI Agent is a "Co-Pilot". Any generated code (especially schematic generation) must be transparent and verifiable by the user.

## Architectural Patterns
*   **RAG over Fine-tuning:** Use Retrieval-Augmented Generation for specialized knowledge.
    *   **The Cookbook:** All schematic generation logic must rely on verified snippets from `backend/knowledge/patterns/`.
    *   **Fact Checking:** The AI must use the `datasheet_reader` tool (when available) to verify pinouts and values against manufacturer specs.
*   **Unified Part Model:** All part data (from LCSC, DigiKey, etc.) must be normalized to the internal `Part` schema before being used by the application.

## Knowledge Management
*   **Pattern Storage:** Common circuit designs (e.g., USB-C input) must be saved as Python scripts in `backend/knowledge/patterns/`.
*   **No Hallucinations:** If a pattern does not exist, the Agent must either:
    1.  Search for a similar verified pattern.
    2.  Explicitly state it is generating a "Best Effort" design and request user verification.
