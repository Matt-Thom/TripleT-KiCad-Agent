# Troubleshooting Guide

## "Error: I'm having trouble thinking right now"

This error usually means the Backend cannot connect to the AI Provider (Google, OpenAI, Anthropic).

### Common Causes & Fixes

1.  **Invalid API Key:**
    *   Check your `.env` file or the **Settings** page.
    *   Ensure the key matches the provider you selected.
    *   *Google Gemini Users:* Ensure you have enabled the **Generative Language API** in your Google Cloud Console for the project associated with the key.

2.  **Model Not Found (404):**
    *   If using Gemini, ensure your API key has access to the selected model (e.g., `gemini-1.5-flash`).
    *   Some keys are restricted to specific regions or services.

3.  **Backend Not Reloading:**
    *   If you changed the key in `.env` manually, restart the backend terminal:
        ```powershell
        Ctrl+C
        uv run uvicorn backend.main:app --reload
        ```

### Diagnostic Steps
1.  Check the backend terminal logs for detailed error messages (e.g., `AuthenticationError`, `NotFoundError`).
2.  Verify your key works with a simple `curl` command (see online docs for your provider).
