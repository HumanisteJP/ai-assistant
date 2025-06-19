# Yata-Agent

Yata-Agent is a Discord bot that records voice channel conversations, transcribes them, and saves the minutes to Google Docs.

This project is a refactored version of the original Yata_legacy, built with a modern, scalable, and testable architecture.

## Architecture

The application follows a clean, layered architecture to ensure separation of concerns and maintainability.

- **Cogs (Interface Layer)**: Handles Discord commands and user interactions.
- **Services (Business Logic Layer)**: Implements the core application logic.
- **Data (Data Access Layer)**: Manages data persistence with a database (SQLite).

Dependency Injection (DI) is used throughout the application, managed by a lightweight `container`, to decouple components and facilitate testing.

## Features

- **/record_start**: Starts recording in the user's voice channel.
- **/record_stop**: Stops recording, processes the audio, and uploads the minutes to Google Docs.
- **/setup**: Configures server-specific settings, like the Google Drive folder ID.
- **/google_auth**: Initiates the Google Account authentication process via DM.

## Setup and Installation

### 1. Prerequisites

- Python 3.11+
- `uv` (recommended for environment management)

### 2. Clone the Repository

```bash
git clone <repository_url>
cd yata-agent
```

### 3. Create a Virtual Environment

It is highly recommended to use a virtual environment.

```bash
uv venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
```

### 4. Install Dependencies

Install the required Python packages using `uv`.

```bash
uv pip sync pyproject.toml
```

### 5. Create `.env` File

The application requires several environment variables for API keys and configuration. Create a file named `.env` in the `yata-agent` directory by copying the example file.

```bash
cp .env.example .env
```

Now, open the `.env` file and fill in the values for the following variables:

- `DISCORD_TOKEN`: Your Discord Bot Token.
- `OPENAI_API_KEY`: Your OpenAI API Key for transcription (Whisper).
- `CLIENT_SECRETS_JSON`: The content of your `client_secrets.json` from Google Cloud Console, pasted as a single-line string.
- `REDIRECT_URI`: The OAuth 2.0 redirect URI configured in your Google Cloud project (e.g., `http://localhost:8000/oauth2callback`).
- `DB_PATH`: The path to the SQLite database file (e.g., `yata_agent.db`).

### 6. Run the Bot

Once the setup is complete, you can run the bot.

```bash
python src/main.py
```

The bot and the FastAPI server for the OAuth callback will start simultaneously.

## Running Tests

To run the test suite, use `pytest`.

```bash
pytest
```
