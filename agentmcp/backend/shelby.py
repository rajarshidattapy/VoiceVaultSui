"""
Compatibility wrapper for the old Shelby module name.

The storage implementation was renamed to `walrus.py`.
New code should import from `backend.walrus` / `walrus`.

This wrapper is kept for backward compatibility only.
"""

# Import Walrus functions (the new backend storage)
from walrus import FileNotFoundError
from walrus import download_from_shelby
from walrus import upload_to_shelby
from walrus import verify_walrus_access as verify_access  # Renamed function
from walrus import delete_from_walrus  # New function name

# Legacy aliases
verify_shelby_access = verify_access
delete_from_shelby = delete_from_walrus
