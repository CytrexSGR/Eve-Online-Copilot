# EVE Co-Pilot API Documentation

Complete REST API documentation for EVE Co-Pilot.

## Base URL

- Development: `http://localhost:8000`
- Production: `http://77.24.99.81:8000`

## Authentication

All authenticated endpoints require a valid EVE SSO token. See [Authentication Guide](authentication.md).

## API Sections

- [Authentication](authentication.md) - EVE SSO OAuth2 flow
- [Shopping Lists](shopping.md) - Manage shopping lists and items
- [Market & Production](market.md) - Market analysis and production planning
- [War Room](war-room.md) - Combat intelligence and loss tracking
- [Character](character.md) - Character and corporation data
- [Navigation](navigation.md) - Route planning and cargo calculations

## Interactive Documentation

FastAPI provides interactive API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Response Format

All responses follow this structure:

### Success Response
```json
{
  "data": { ... },
  "status": "success"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "status": "error"
}
```

## Rate Limiting

ESI API rate limits apply:
- 150 requests/second (burst)
- Error limit budget system

## Status Codes

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `404 Not Found` - Resource not found
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `500 Internal Server Error` - Server error

## Common Parameters

### Pagination
```
?page=1&limit=50
```

### Filtering
```
?status=active&character_id=123
```

### Sorting
```
?sort=created_at&order=desc
```
