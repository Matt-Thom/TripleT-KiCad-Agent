## 2025-01-14 - Information Leakage via Error Handling
**Vulnerability:** The application was catching exceptions in endpoints and returning `str(e)` as the HTTP 500 error detail. This could expose internal implementation details, stack traces, or sensitive data contained in exception messages to the client.
**Learning:** Developers often expose error details for debugging convenience, but this violates the "Fail Securely" principle. A generic error message should be returned to the client, while detailed errors should be logged server-side.
**Prevention:**
1. Implemented a global exception handler in FastAPI that catches all unhandled exceptions.
2. The handler logs the full exception with stack trace using `logging.error(..., exc_info=True)`.
3. The handler returns a generic "Internal Server Error" JSON response.
4. Specific endpoints catch known exceptions and re-raise generic 500 errors after logging the specifics.
