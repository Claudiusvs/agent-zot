"""
Connection validator for Zotero API with user-friendly error messages.

Provides helpful, actionable error messages when Zotero connection fails.
"""

import os
from typing import Optional


def get_connection_error_message(exception: Exception) -> Optional[str]:
    """
    Generate user-friendly error message for Zotero connection errors.

    Args:
        exception: The caught exception

    Returns:
        Formatted error message string if it's a known connection error, None otherwise
    """
    error_str = str(exception)

    if "Connection refused" in error_str or "Errno 61" in error_str:
        zotero_local = os.getenv("ZOTERO_LOCAL", "").lower()
        return (
            "❌ Cannot connect to Zotero local API (http://localhost:23119)\n\n"
            "Possible solutions:\n"
            "1. ✅ START ZOTERO - The Zotero application must be running\n"
            "2. ⏰ WAIT A FEW SECONDS - Zotero's API server may still be starting up\n"
            "3. ⚙️  CHECK SETTINGS - Ensure Zotero Preferences > Advanced > 'Enable HTTP server' is ON\n"
            "4. 🌐 USE WEB API - Set ZOTERO_LOCAL=false in config to use Zotero's web API instead\n\n"
            f"Current configuration: ZOTERO_LOCAL={zotero_local}\n\n"
            "See README.md for detailed configuration instructions."
        )

    elif "database is locked" in error_str:
        return (
            "❌ Zotero database is locked\n\n"
            "This usually means:\n"
            "• Zotero is currently performing a sync or indexing operation\n"
            "• Another process is accessing the database\n\n"
            "Solutions:\n"
            "1. ⏰ WAIT - Let Zotero finish its current operation (usually 30-60 seconds)\n"
            "2. 🔄 RESTART - Close and restart Zotero\n"
            "3. 🌐 USE WEB API - Set ZOTERO_LOCAL=false in config to avoid database locks"
        )

    elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
        return (
            "❌ Zotero API request timed out\n\n"
            "This may mean:\n"
            "• Zotero is processing a large library\n"
            "• Network connection issues (if using web API)\n"
            "• System resource constraints\n\n"
            "Solutions:\n"
            "1. ⏰ RETRY - Try the request again\n"
            "2. 📉 REDUCE LOAD - Use smaller batch sizes or query limits\n"
            "3. 🔄 RESTART ZOTERO - Close and restart Zotero"
        )

    # Not a recognized connection error
    return None


def validate_connection(exception: Exception) -> str:
    """
    Validate Zotero connection and return appropriate error message.

    Raises a new exception with a user-friendly message if it's a connection error,
    otherwise re-raises the original exception.

    Args:
        exception: The caught exception

    Returns:
        User-friendly error message

    Raises:
        Exception: Either the original exception or a new one with friendly message
    """
    friendly_message = get_connection_error_message(exception)

    if friendly_message:
        # Known connection error - raise with friendly message
        raise Exception(friendly_message) from exception
    else:
        # Unknown error - re-raise original
        raise exception
