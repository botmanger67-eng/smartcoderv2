# smartbot-ai-companion  

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)  
![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-blue)  
![License](https://img.shields.io/badge/license-MIT-green)  

**Multimodal AI Telegram bot with memory and project mode.**  
Built with Python, DeepSeek API, and a stack of modern tools to deliver an intelligent, context‑aware assistant right inside Telegram.

---

## Description

`smartbot-ai-companion` is a Telegram bot that leverages the **DeepSeek** language model to understand and respond to text, voice, and project‑related queries. It maintains a persistent conversation history (memory) using SQLite, supports text‑to‑speech output via **gTTS**, and can manage GitHub repositories through **PyGithub** – making it ideal for developers who want an AI companion that remembers context and helps with code projects.

---

## Features

- **Multimodal interaction** – text messages, voice input (Telegram voice messages), and text‑to‑speech replies.
- **Conversation memory** – stores chat history in SQLite, allowing the AI to recall previous context.
- **Project mode** – interact with your GitHub repositories: list, search, create issues, and more.
- **Powered by DeepSeek** – fast, capable, and cost‑effective LLM.
- **Secure configuration** – all API keys and tokens stored in a `.env` file, not in the code.
- **Simple, extensible structure** – easy to add new features or modify existing ones.

---

## Tech Stack

| Component          | Technology                                   |
|--------------------|----------------------------------------------|
| Language           | Python 3.9+                                  |
| Telegram Framework | [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) |
| AI Model           | [DeepSeek API](https://deepseek.com/)        |
| Database           | SQLite (via `sqlite3`)                       |
| Voice Output       | [gTTS](https://github.com/pndurette/gTTS)    |
| GitHub Integration | [PyGithub](https://github.com/PyGithub/PyGithub) |
| Environment        | `python-dotenv`                              |

---

## Installation

### Prerequisites

- Python 3.9 or higher
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A DeepSeek API key (from [DeepSeek platform](https://platform.deepseek.com/))
- (Optional) A GitHub personal access token with appropriate scopes for project mode

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/smartbot-ai-companion.git
   cd smartbot-ai-companion
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy the `.env.example` file to `.env` and fill in your tokens:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your credentials:
   ```ini
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   DEEPSEEK_API_KEY=your_deepseek_api_key
   GITHUB_TOKEN=your_github_token   # optional
   ```

5. **Run the bot:**
   ```bash
   python bot.py
   ```

---

## Usage

Once the bot is running, start a chat with your Telegram bot.  
- **Text messages** – send any message; the bot will reply using DeepSeek, keeping the conversation history.  
- **Voice messages** – send a voice message; the bot will transcribe it, process the query, and reply with text (and optionally a spoken response).  
- **Project mode commands** (if GitHub token is configured):  
  - `/projects` – list your repositories  
  - `/repo <name>` – get details of a specific repository  
  - `/issue <repo> <title>` – create a new issue  
  - `/help` – show available commands  

**Note:** The bot’s memory is per‑chat, so each conversation remains independent.

---

## Project Structure

```
smartbot-ai-companion/
├── bot.py                # Telegram bot entry point – handlers and dispatcher
├── ai_handler.py         # Communication with DeepSeek API, prompt management
├── config.py             # Environment variables and app configuration
├── database.py           # SQLite database connection and memory operations
├── github_manager.py     # GitHub API interactions (PyGithub)
├── utils.py              # Helper functions (logging, text‑to‑speech, etc.)
├── requirements.txt      # Python dependencies
├── .env.example          # Template for environment variables
└── README.md             # This file
```

- **bot.py** – Sets up the `Application` from `python-telegram-bot`, registers handlers for text, voice, and commands.  
- **ai_handler.py** – Formats prompts, sends requests to DeepSeek, and returns responses.  
- **config.py** – Loads `TELEGRAM_BOT_TOKEN`, `DEEPSEEK_API_KEY`, `GITHUB_TOKEN`, and other settings from the `.env` file.  
- **database.py** – Creates/connects to SQLite, stores and retrieves conversation history per user.  
- **github_manager.py** – Provides methods to list repos, get repo details, create issues, etc.  
- **utils.py** – Contains shared utilities such as logging setup, file handling for voice messages, and gTTS conversion.  

---

## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for details.

---

> **Built with ❤️ for the Telegram community**  
> If you encounter any issues or have feature requests, please open an [issue](https://github.com/your-username/smartbot-ai-companion/issues).