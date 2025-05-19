# Database Clear Feature

## Overview

The Database Clear feature provides a way to remove all data from the Neo4j database while optionally preserving schema elements like constraints and indexes. This functionality is useful for administrators who need to reset the database to a clean state, such as when performing testing or when needing to remove ingested repositories.

## Implementation Details

### API Endpoints

- `POST /v1/database/clear`: Clears all data from the database. Requires admin privileges.
  - Request parameters:
    - `confirm`: Boolean, must be `true` to confirm the operation
    - `preserve_schema`: Boolean, when `true`, preserves constraints and indexes

### Service Client

The CLI's `ServiceClient` class includes a `clear_database` method to interact with the database clear API endpoint:

```python
def clear_database(self, confirm: bool = False) -> Dict[str, Any]:
    """
    Clear all data from the database by executing a delete query.
    
    This is a destructive operation that will delete all nodes and relationships in
    the database. It requires admin privileges. Schema constraints and indexes will remain.
    
    Args:
        confirm: Whether the operation has been confirmed. Must be True to proceed.
        
    Returns:
        Dictionary with status information
        
    Raises:
        ServiceError: If the clear operation fails
        ValueError: If the operation is not confirmed
    """
```

### GUI

The GUI includes a Database Manager component within the Configuration page that allows administrators to:

1. View database management options
2. Clear the database with confirmation
3. Choose whether to preserve schema elements

## Security Considerations

- The database clear operation is restricted to users with admin privileges
- Confirmation is required through the `confirm` parameter to prevent accidental data loss
- The GUI requires users to type "CLEAR DATABASE" to confirm the operation

## Integration

The feature is integrated into both:
1. The CLI through the `ServiceClient` class
2. The GUI through the Configuration page
3. The API through a secured endpoint requiring admin privileges

## Usage

### CLI

```bash
# Import the client
from codestory.cli.client import ServiceClient

# Create a client
client = ServiceClient()

# Clear the database (requires admin privileges)
result = client.clear_database(confirm=True)
print(result)
```

### API

```bash
# Using curl
curl -X POST http://localhost:8000/v1/database/clear \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{"confirm": true, "preserve_schema": true}'
```

### GUI

Navigate to the Configuration page and scroll down to the Database Management section. Click the "Clear Database" button, confirm the operation by typing "CLEAR DATABASE", and click the "Clear Database" button again.