# FastAPI Dev Container with Radicale Integration

A development environment for FastAPI applications with Radicale CalDAV/CardDAV server integration using VS Code Dev Containers.

## Features

- **Python 3.11** with FastAPI framework
- **Radicale** CalDAV/CardDAV server integration
- **Hot reload** development server
- **Code formatting** with Black
- **Linting** with Flake8
- **Import sorting** with isort
- **Type checking** with mypy
- **Testing** with pytest
- **Git integration** with GitHub CLI

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- [VS Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Quick Start

1. **Setup Radicale**: Run the setup script to create default users
   ```bash
   python setup_radicale.py
   ```

2. **Start Services**: Use Docker Compose to start both FastAPI and Radicale
   ```bash
   docker-compose up -d
   ```

3. **Access the Services**:
   - FastAPI: http://localhost:8000
   - Radicale: http://localhost:5232
   - API Documentation: http://localhost:8000/docs

## Radicale Integration

### Default Users
- `admin:admin`
- `user1:password1`
- `user2:password2`

### API Endpoints

#### Radicale Status
- `GET /radicale/status` - Check Radicale connection status

#### Calendar Management
- `GET /radicale/calendars` - Get all calendars
- `POST /radicale/calendars/{calendar_name}/events` - Create calendar event
- `GET /radicale/calendars/{calendar_name}/events` - Get calendar events

#### Contact Management
- `GET /radicale/addressbooks` - Get address books
- `POST /radicale/addressbooks/{addressbook_name}/contacts` - Create contact

### Example Usage

#### Create a Calendar Event
```bash
curl -X POST "http://localhost:8000/radicale/calendars/default/events" \
     -H "Content-Type: application/json" \
     -d '{
       "summary": "Team Meeting",
       "description": "Weekly team sync",
       "start": "2024-01-15T10:00:00",
       "end": "2024-01-15T11:00:00",
       "location": "Conference Room A"
     }'
```

#### Create a Contact
```bash
curl -X POST "http://localhost:8000/radicale/addressbooks/default/contacts" \
     -H "Content-Type: application/json" \
     -d '{
       "first_name": "John",
       "last_name": "Doe",
       "email": "john.doe@example.com",
       "phone": "+1-555-123-4567",
       "organization": "Acme Corp"
     }'
```

#### Check Radicale Status
```bash
curl "http://localhost:8000/radicale/status"
```

## API Endpoints

### Base Endpoints
- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### Items API
- `GET /items` - Get all items
- `GET /items/{item_id}` - Get a specific item
- `POST /items` - Create a new item
- `PUT /items/{item_id}` - Update an existing item
- `DELETE /items/{item_id}` - Delete an item

### Radicale API
- `GET /radicale/status` - Check Radicale connection
- `GET /radicale/calendars` - List calendars
- `POST /radicale/calendars/{name}/events` - Create event
- `GET /radicale/calendars/{name}/events` - List events
- `GET /radicale/addressbooks` - List address books
- `POST /radicale/addressbooks/{name}/contacts` - Create contact

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Setup Radicale
python setup_radicale.py

# Start Radicale (in separate terminal)
docker run -d -p 5232:5232 -v $(pwd)/radicale_data:/data tomsquest/docker-radicale:latest

# Start FastAPI
python main.py
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

Set these environment variables to customize the integration:

```bash
RADICALE_URL=http://localhost:5232
RADICALE_USERNAME=admin
RADICALE_PASSWORD=admin
```

### Radicale Configuration

The Radicale configuration is in `radicale_config/config`. You can modify:

- Authentication type
- Storage backend
- Logging level
- Server settings

## Troubleshooting

### Radicale Connection Issues

1. **Check if Radicale is running**:
   ```bash
   curl http://localhost:5232
   ```

2. **Verify credentials**:
   - Default: `admin:admin`
   - Check `radicale_data/users` file

3. **Check logs**:
   ```bash
   docker-compose logs radicale
   ```

### FastAPI Issues

1. **Check FastAPI logs**:
   ```bash
   docker-compose logs fastapi
   ```

2. **Verify environment variables**:
   ```bash
   docker-compose exec fastapi env | grep RADICALE
   ```

## Project Structure

```
.
├── .devcontainer/          # Dev container configuration
├── main.py                # FastAPI application with Radicale integration
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # FastAPI container definition
├── setup_radicale.py      # Radicale setup script
├── radicale_config/       # Radicale configuration
│   └── config            # Radicale config file
├── radicale_data/         # Radicale data directory
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Next Steps

- Add authentication and authorization
- Implement calendar sharing
- Add contact synchronization
- Set up backup and restore
- Add monitoring and metrics
- Implement webhook notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

```bash
# Rebuild the container
Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

### Environment Variables

Add environment variables to the `.devcontainer/devcontainer.json` file:

```json
{
  "remoteEnv": {
    "DATABASE_URL": "postgresql://user:password@localhost/db",
    "API_KEY": "your-api-key"
  }
}
```

## Troubleshooting

### Container Build Issues

If the container fails to build:

1. Check Docker is running
2. Ensure you have enough disk space
3. Try rebuilding: `Ctrl+Shift+P` → "Dev Containers: Rebuild Container"

### Port Forwarding

The container forwards port 8000 by default. If you need additional ports:

1. Add them to the `forwardPorts` array in `.devcontainer/devcontainer.json`
2. Rebuild the container

### Performance Issues

If the container is slow:

1. Increase Docker memory allocation in Docker Desktop settings
2. Use volume mounts for large datasets instead of copying files

## Next Steps

- Add database integration (PostgreSQL, SQLite, etc.)
- Implement authentication and authorization
- Add background tasks with Celery
- Set up CI/CD pipelines
- Add monitoring and logging
- Implement caching with Redis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE). 