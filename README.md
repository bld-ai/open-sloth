# OpenSloth

**A Telegram bot that manages Google Sheets using AI — just talk to it in plain English.**

OpenSloth reads your sheet structure, understands the data, and intelligently adds/updates rows without asking you for every detail. It supports multiple LLM providers and works with any Google Sheet you share with it.

## Features

- **Multi-Model Support** — OpenAI, Claude, Gemini, or Ollama (local)
- **Intelligent Data Entry** — Reads your sheet structure and auto-fills fields (priority, dates, status, etc.)
- **Dynamic Sheets** — Works with any Google Sheet shared with the bot's service account
- **Multi-Tab Support** — Reads and writes across multiple worksheet tabs
- **Conversation History** — Remembers context from your last 10 messages
- **User Access Control** — Restrict by Telegram username or user ID
- **Docker Deployment** — Single command deploy

## Quick Start

### 1. Create a Telegram Bot

- Message [@BotFather](https://t.me/botfather) on Telegram
- Run `/newbot` and follow the prompts
- Copy the bot token

### 2. Get an LLM API Key

Pick one provider:

| Provider | Get API Key | Model Example |
|----------|------------|---------------|
| OpenAI | [platform.openai.com](https://platform.openai.com/) | `gpt-4-turbo` |
| Anthropic | [console.anthropic.com](https://console.anthropic.com/) | `claude-3-5-sonnet-20241022` |
| Google | [aistudio.google.com](https://aistudio.google.com/) | `gemini-pro` |
| Ollama | [ollama.com](https://ollama.com/) (local, no key needed) | `llama3` |

### 3. Set Up Google Sheets Access

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable the **Google Sheets API**
3. Create a **Service Account** and download the JSON key as `credentials.json`
4. Share your Google Sheet with the service account email (found in `credentials.json`)

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4-turbo
GOOGLE_SHEET_ID=your_sheet_id_from_the_url
```

### 5. Deploy

```bash
docker compose up -d
```

That's it. Message your bot on Telegram.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | Yes |
| `LLM_PROVIDER` | `openai`, `anthropic`, `google`, or `ollama` | Yes |
| `LLM_API_KEY` | API key for your chosen provider | Yes (except Ollama) |
| `LLM_MODEL` | Model name (e.g. `gpt-4-turbo`, `claude-3-5-sonnet-20241022`) | Yes |
| `LLM_BASE_URL` | Custom endpoint (for Ollama or proxies) | No |
| `GOOGLE_SHEET_ID` | Default Google Sheet ID from the URL | Yes |
| `GOOGLE_CREDENTIALS_FILE` | Path to service account JSON | No (`/app/credentials.json`) |
| `ALLOWED_USERS` | Comma-separated Telegram usernames/IDs (empty = allow all) | No |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | No (`INFO`) |
| `POLL_INTERVAL` | Telegram polling interval in seconds | No (`1.0`) |

### How It Works

When you ask the bot to add a task, it:

1. Reads the sheet to understand column headers and existing data
2. Intelligently fills in all fields — priority (next number), person, date, status
3. Calls `add_row` immediately without asking you for details

You don't need to specify priority, assignee, dates, etc. The bot figures it out from existing data patterns.

## Usage

### Commands

- `/start` — Welcome message
- `/help` — Show usage examples

### Examples

```
"Show me all tasks"
"What's in the priorities tab?"
"Add a task: Fix the login bug"
"Update task 3 status to Done"
"Search for tasks assigned to John"
"Delete row 5 from priorities"
```

## Architecture

```
Telegram User
    |
    v
Telegram Bot (python-telegram-bot v22+)
    |
    v
Agent (agentic tool-calling loop)
    |
    v
LLM Provider (OpenAI / Claude / Gemini / Ollama)
    |                           |
    v                           v
Tool Calls               Natural Language
(read_sheet,              Response
 add_row, etc.)
    |
    v
Google Sheets Client (gspread)
    |
    v
Google Sheets API
```

The agent runs a loop — the LLM can chain multiple tool calls (e.g. `read_sheet` then `add_row`) in a single user interaction.

## Project Structure

```
OpenSloth/
├── src/
│   ├── main.py                  # Entry point
│   ├── agent/
│   │   ├── agent.py             # Agentic loop with conversation history
│   │   └── prompts.py           # System prompt and function definitions
│   ├── bot/
│   │   ├── telegram_bot.py      # Bot setup and polling
│   │   └── handlers.py          # /start, /help, message handlers
│   ├── llm/
│   │   ├── base.py              # Abstract LLM provider
│   │   ├── factory.py           # Provider factory
│   │   ├── openai_provider.py   # OpenAI implementation
│   │   ├── anthropic_provider.py # Claude implementation
│   │   ├── google_provider.py   # Gemini implementation
│   │   └── ollama_provider.py   # Ollama implementation
│   ├── sheets/
│   │   ├── sheets_client.py     # Google Sheets CRUD operations
│   │   └── models.py            # Data models
│   ├── config/
│   │   └── settings.py          # Pydantic settings
│   └── utils/
│       ├── logger.py            # Loguru setup
│       └── errors.py            # Error handling
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── credentials.json             # Google service account key (not committed)
```

## Development

### Local (without Docker)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python -m src.main
```

### Server Deployment

```bash
# Copy files to server
scp -r . yourserver:/opt/opensloth/

# On the server
cd /opt/opensloth
docker compose up -d

# View logs
docker compose logs -f opensloth

# Redeploy after changes
docker compose down && docker compose build --no-cache && docker compose up -d
```

## Troubleshooting

**Bot doesn't respond**
- `docker compose ps` — check it's running
- `docker compose logs -f opensloth` — check for errors
- Verify your `TELEGRAM_BOT_TOKEN` is correct

**Google Sheets auth fails**
- Make sure `credentials.json` is in the project root
- Share the sheet with the service account email (the `client_email` in credentials.json)
- Verify `GOOGLE_SHEET_ID` matches the ID in your sheet's URL

**Bot reads the sheet but doesn't add rows**
- Check logs for tool call chain — it should show `read_sheet` followed by `add_row`
- Make sure `LLM_MODEL` supports function calling (e.g. `gpt-4-turbo`, not `gpt-3.5-turbo`)

