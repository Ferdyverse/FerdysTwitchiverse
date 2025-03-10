import logging
import json
import os
import config
from fastapi.responses import HTMLResponse
from modules.websocket_handler import broadcast_message
from database.crud.todos import save_todo, get_todos
from routes.hub import show_hub

logger = logging.getLogger("uvicorn.error.chat_commands")

COMMAND_RESPONSES_FILE = config.COMMAND_RESPONSES_FILE
COMMANDS = {}
ALIASES = {}

# Load responses from file (if exists)
if os.path.exists(COMMAND_RESPONSES_FILE):
    with open(COMMAND_RESPONSES_FILE, "r", encoding="utf-8") as f:
        COMMAND_RESPONSES = json.load(f)
else:
    COMMAND_RESPONSES = {}

for cmd, data in COMMAND_RESPONSES.items():
    if isinstance(data, dict) and "aliases" in data:
        for alias in data["aliases"]:
            ALIASES[alias] = cmd  # Map alias to main command

def save_command_responses():
    """Save COMMAND_RESPONSES to JSON file."""
    with open(COMMAND_RESPONSES_FILE, "w", encoding="utf-8") as f:
        json.dump(COMMAND_RESPONSES, f, indent=4)

async def handle_command(bot, command_name: str, params: str, event):
    """Handles function-based commands and key-value responses with alias support."""

    command_name = ALIASES.get(command_name, command_name)

    if command_name in COMMAND_RESPONSES:
        response = COMMAND_RESPONSES[command_name]["response"]
        await bot.send_message(f"@{event.user.display_name} {response}")
        logger.info(f"💬 Responded with predefined message: {response}")
        return

    handler_function = COMMANDS.get(command_name)

    if callable(handler_function):
        logger.info(f"📢 Executing command: !{command_name} from {event.user.display_name}")
        await handler_function(bot, params, event)
    else:
        logger.warning(f"⚠️ Unknown command: !{command_name} (no handler found)")

# ─── Command Handlers ───────────────────────────────────────────────

async def command_todo(bot, params: str, event):
    """Handles the !todo command."""
    if not params:
        await bot.send_message(f"❌ @{event.user.display_name}, bitte gib eine ToDo-Beschreibung an!")
        return

    result = save_todo(params, event.user.id, event.user.display_name)

    if result:
        await bot.send_message(f"✅ ToDo hinzugefügt: {params} (ID: {result})")
    else:
        await bot.send_message("❌ Fehler beim Speichern des ToDos!")

COMMANDS["todo"] = command_todo

async def command_todos(bot, params: str, event):
    """Handles the !todos command to list all active ToDos in chat."""

    todos = get_todos(status="pending")  # Fetch only pending ToDos

    if not todos:
        await bot.send_message("✅ Aktuell sind keine offenen ToDos vorhanden!")
        return

    todo_list = [f"#{todo['_id']} - {todo['text']} (by {todo['username']})" for todo in todos]

    # Send in chunks (Twitch chat limit: ~500 chars per message)
    message = "📝 **Aktuelle ToDos:**\n\n" + "\n\n".join(todo_list)
    if len(message) > 500:
        chunks = []
        current_chunk = "📝 **Aktuelle ToDos:**\n"

        for todo in todo_list:
            if len(current_chunk) + len(todo) + 2 > 500:  # +2 for newline and safety
                chunks.append(current_chunk.strip())
                current_chunk = ""

            current_chunk += todo + "\n"

        chunks.append(current_chunk.strip())  # Add the last chunk

        for chunk in chunks:
            await bot.send_message(chunk)
    else:
        await bot.send_message(message)

COMMANDS["todos"] = command_todos
