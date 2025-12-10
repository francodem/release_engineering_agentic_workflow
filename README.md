# Release Engineering Agentic Workflow Demo

This repository contains a demo of an agentic workflow system that automates release engineering processes. The system integrates n8n workflows with a Microsoft Teams emulator to demonstrate automated deployment approval workflows and CI/CD pipeline execution.

## Overview

The demo consists of three main components:

1. **n8n Workflow (`re_agent.json`)**: An AI-powered agent workflow that:
   - Monitors Microsoft Teams posts for deployment approval
   - Checks for SCRUM Master approval messages
   - Triggers GitHub Actions workflows when approval is granted
   - Monitors workflow execution status

2. **Teams Emulator (`app.py`)**: A FastAPI-based Microsoft Teams emulator that:
   - Provides a REST API for posts and replies
   - Includes a web UI for managing posts and replies
   - Simulates Microsoft Teams communication channels

3. **CI/CD Pipeline (`lint.yml`)**: A GitHub Actions workflow that:
   - Runs Python code linting using Black
   - Validates code formatting
   - Serves as a test pipeline for the release engineering workflow

## Prerequisites

- Docker installed and running
- Python 3.10+ (for running the Teams emulator)
- n8n account (or use the provided Docker setup)
- Network access to the Teams emulator API from the n8n container

## Setup Instructions

### Step 1: Run n8n with Docker

Create a Docker volume for n8n data persistence and run the n8n container:

```bash
docker volume create n8n_data && \
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -e GENERIC_TIMEZONE="America/Los_Angeles" \
  -e TZ="America/Los_Angeles" \
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
  -e N8N_RUNNERS_ENABLED=true \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n:1.121.3
```

After running this command, n8n will be accessible at `http://localhost:5678`.

### Step 2: Import the n8n Workflow

1. Open n8n in your browser at `http://localhost:5678`
2. Navigate to **Workflows** → **Import from File**
3. Select the file: `src/n8n/re_agent.json`
4. The workflow will be imported with all nodes and connections

### Step 3: Run the Teams Emulator

1. Navigate to the Teams emulator directory:
   ```bash
   cd src/emulation/teams
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Get your machine's IP address (required for n8n to access the API):
   ```bash
   # On macOS/Linux:
   ifconfig | grep "inet " | grep -v 127.0.0.1
   
   # On Windows:
   ipconfig
   ```
   Note the IP address (e.g., `192.168.0.214`)

4. Run the Teams emulator API server:
   ```bash
   python app.py
   ```
   
   The server will start on `http://0.0.0.0:8000` (accessible from all network interfaces).

5. Verify the API is running:
   - Open `http://localhost:8000` in your browser to see the Teams emulator UI
   - Or test the API: `curl http://localhost:8000/api/posts`

### Step 4: Configure n8n Workflow with Teams Emulator IP

1. In n8n, open the imported workflow `re_agent.json`
2. Find the first agent node: **"TA-01 - Get Microsoft Teams post ID"**
3. Update the URL parameter to use your machine's IP address:
   - Change `http://192.168.0.214:8000/api/posts` to `http://<YOUR_IP>:8000/api/posts`
   - Replace `<YOUR_IP>` with the IP address you obtained in Step 3.3

4. Similarly, update the **"TA-01 - Get Microsoft Teams post replies"** node:
   - The base URL should be: `http://<YOUR_IP>:8000/api/posts/<POST_ID>/replies`

### Step 5: Execute the Workflow

1. In n8n, activate the workflow (toggle the switch in the top right)
2. Open the chat interface for the workflow
3. Send the following JSON message to start the workflow:

```json
{
  "command": "start",
  "conversation_thread_title": "M190.0.0 Google Vertex AI Release"
}
```

4. The workflow will:
   - Query the Teams emulator for posts matching the conversation thread title
   - Retrieve replies to check for SCRUM Master approval
   - If approval is found, trigger the GitHub Actions workflow
   - Monitor the workflow execution status

## Teams Emulator API

The Teams emulator provides the following REST API endpoints:

### Posts

- `GET /api/posts` - Get all posts (summary only)
- `GET /api/posts/full` - Get all posts with replies
- `GET /api/posts/{post_id}` - Get a specific post with replies
- `POST /api/posts` - Create a new post
- `PUT /api/posts/{post_id}` - Update a post
- `DELETE /api/posts/{post_id}` - Delete a post

### Replies

- `GET /api/posts/{post_id}/replies` - Get all replies for a post
- `POST /api/posts/{post_id}/replies` - Create a reply to a post
- `POST /api/replies` - Create a reply (with post_id in body)
- `PUT /api/replies/{reply_id}` - Update a reply
- `DELETE /api/replies/{reply_id}` - Delete a reply

### Example: Creating a Reply

```bash
curl -X POST "http://localhost:8000/api/posts/<POST_ID>/replies" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "SCRUM Master",
    "role": "SCRUM Master",
    "message": "Approved. Please proceed with the deployment."
  }'
```

## CI/CD Pipeline

The repository includes a GitHub Actions workflow (`.github/workflows/lint.yml`) that:

- Runs on manual trigger (`workflow_dispatch`)
- Sets up Python 3.13
- Installs dependencies from `src/emulation/teams/requirements.txt`
- Runs Black linter to check code formatting
- Fails if code formatting issues are found

### Running the Lint Pipeline

The lint pipeline can be triggered manually from the GitHub Actions tab, or it can be triggered by the n8n workflow when a deployment is approved.

## Workflow Architecture

The n8n workflow consists of multiple AI agents:

1. **TA-01 (Teams Agent)**: 
   - Retrieves Microsoft Teams post IDs
   - Fetches replies to posts
   - Determines if SCRUM Master approval exists

2. **GAWA-01 (GitHub Actions Workflow Agent)**:
   - Triggers GitHub Actions workflows
   - Monitors workflow execution status
   - Retrieves workflow logs on failure

3. **Jira Agent** (if configured):
   - Creates Jira tickets
   - Monitors ticket status

## Sample Data

The Teams emulator initializes with sample data:

- **Post**: "M190.0.0 Google Vertex AI Release" by Cristina M. (Program Manager)
- **Reply**: Approval message from Alexa A. (SCRUM Master)

This sample data allows you to test the workflow immediately after setup.

## Troubleshooting

### n8n cannot reach Teams emulator

- Ensure the Teams emulator is running on `0.0.0.0:8000` (not `127.0.0.1`)
- Verify the IP address in n8n matches your machine's IP
- Check firewall settings if running on different machines
- Test connectivity: `curl http://<YOUR_IP>:8000/api/posts` from the n8n container

### Workflow not finding posts

- Verify the conversation thread title matches exactly (case-sensitive)
- Check the Teams emulator UI at `http://localhost:8000` to see available posts
- Ensure the post exists in the emulator database

### GitHub Actions workflow not triggering

- Verify GitHub credentials are configured in n8n
- Check that the component_id matches a valid GitHub repository
- Ensure the workflow file exists in the target repository

## Development

### Teams Emulator Development

The Teams emulator is built with:
- FastAPI for the API server
- Uvicorn as the ASGI server
- Pydantic for data validation
- Jinja2 for templating

To modify the emulator:
1. Edit `src/emulation/teams/app.py`
2. Restart the server
3. Changes will be reflected immediately (reload enabled)

### Adding New Workflows

To add new workflows to the n8n agent:
1. Export the workflow from n8n
2. Update `src/n8n/re_agent.json`
3. Document the new workflow in this README

## License

[Add your license information here]

## Contributing

[Add contributing guidelines here]

