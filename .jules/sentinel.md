## 2025-02-12 - Information Leakage in API Error Handling
**Vulnerability:** API endpoints were catching generic exceptions and returning `str(e)` directly to the client in the 500 response.
**Learning:** This pattern is common when developers prioritize quick debugging over security. It can leak database connection strings, file paths, or logic details.
**Prevention:** Always catch exceptions, log them server-side with `exc_info=True`, and return a generic "Internal Server Error" message to the client.
