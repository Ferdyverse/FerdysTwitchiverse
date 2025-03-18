import logging
import json
import os
import config
from fastapi.responses import HTMLResponse
from modules.websocket_handler import broadcast_message
from database.crud.todos import save_todo, get_todos
from modules.openai import generate_tts_audio, delete_tts_file, get_mp3_duration
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

def check_access_rights(event, level: str):
    """Checks if the user has the required permissions based on their role (without using badges)."""

    user_id = int(event._parsed["tags"].get("user-id", 0))  # Get user ID
    channel_id = int(config.TWITCH_CHANNEL_ID)  # Broadcaster's ID from config

    is_broadcaster = user_id == channel_id  # Compare user ID with broadcaster ID
    is_mod = event._parsed["tags"].get("mod") == "1"  # Check if user is a mod
    is_vip = event._parsed["tags"].get("vip") == "1"  # Check if user is a VIP (if available)

    if level == "mod":
        return is_broadcaster or is_mod
    elif level == "vip":
        return is_broadcaster or is_mod or is_vip
    elif level == "broadcaster":
        return is_broadcaster
    else:
        return False  # Default: No access

async def handle_command(bot, command_name: str, params: str, event):
    """Handles function-based commands and key-value responses with alias support."""

    command_name = ALIASES.get(command_name, command_name)

    logger.info(command_name)

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

async def command_commands(bot, params: str, event):
    """Handles the !commands command by whispering all available commands in a readable format."""

    # Get function-based commands
    function_commands = set(COMMANDS.keys())

    # Get JSON-based commands and their aliases
    json_commands = set(COMMAND_RESPONSES.keys())
    alias_commands = set(ALIASES.keys())

    # Combine all commands and sort
    all_commands = sorted(function_commands | json_commands | alias_commands)

    # Format list with newlines
    command_list = "\n".join([f"• {cmd}" for cmd in all_commands])

    # Prepare the message
    message = f"📜 Verfügbare Commands:\n{command_list}"

    try:
        await bot.send_message(message)
        logger.info(f"📩 Sent formatted command list to {event.user.name}")
    except Exception as e:
        logger.error(f"❌ Failed to send whisper: {e}")
        await bot.send_message(f"@{event.user.display_name}, Ich konnte dir leider keine Nachricht senden!")
COMMANDS["commands"] = command_commands

async def command_addresponse(bot, params: str, event):
    """Handles the !addresponse command, restricted to moderators & broadcaster."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, du besitzt nicht die notwendigen Rechte um Commands hinzuzufügen!")
        logger.warning(f"⚠️ Unauthorized attempt: {event.user.display_name} tried to add a command.")
        return

    try:
        command_name, response_text = params.split(" ", 1)
        command_name = command_name.lower()

        if command_name in COMMANDS:
            await bot.send_message(f"❌ Cannot override existing command function: !{command_name}")
            return

        COMMAND_RESPONSES[command_name] = response_text
        save_command_responses()
        await bot.send_message(f"✅ Command !{command_name} added.")

    except ValueError:
        await bot.send_message("❌ Usage: !addresponse <command> <response>")
COMMANDS["addresponse"] = command_addresponse


async def command_todo(bot, params: str, event):
    """Handles the !todo command."""
    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, benutze die Kanalpunkte um ToDos hinzuzufügen")
        logger.warning(f"⚠️ Unauthorized attempt: {event.user.display_name} tried to add a todo.")
        return

    if not params:
        await bot.send_message(f"❌ @{event.user.display_name}, bitte gib eine ToDo-Beschreibung an!")
        return

    result = save_todo(params, event.user.id, event.user.display_name)

    await broadcast_message({"todo": { "action": "create", "id": result.get("_id"), "text": result.get("text"), "username": result.get("username") }})

    if result:
        await bot.send_message(f"✅ ToDo hinzugefügt: {params}")
    else:
        await bot.send_message("❌ Fehler beim Speichern des ToDos!")
COMMANDS["todo"] = command_todo

async def command_todos(bot, params: str, event):
    """Handles the !todos command to list all active ToDos in chat."""

    todos = get_todos(status="pending")  # Fetch only pending ToDos

    if not todos:
        await bot.send_message("✅ Aktuell sind keine offenen ToDos vorhanden!")
        return

    todo_list = [f"- {todo['text']} (by {todo['username']})" for todo in todos]

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

async def command_hub(bot, params: str, event):
    """Handles the !hub command and filters text through show_hub."""

    if not params:
        await bot.send_message(f"⚠️ @{event.user.display_name}, bitte gib einen Text für den Hub an!")
        return

    hub_response = show_hub(params)  # Holt die HTMLResponse

    if isinstance(hub_response, HTMLResponse):
        hub_html = hub_response.body.decode("utf-8")  # Extrahiere den HTML-Code
    else:
        hub_html = str(hub_response)  # Falls kein HTMLResponse, konvertiere zu String

    await broadcast_message({"html": {"content": hub_html, "lifetime": 100000}})

    logger.info(f"✅ !hub processed: {params} -> {hub_html}")

COMMANDS["hub"] = command_hub


async def command_tts(bot, params: str, event):
    """Send TTS audio to the web overlay and delete it after playback."""

    if len(params) > 200:  # Limit text length
        await bot.send_message(f"⚠️ @{event.user.display_name} dein Text ist zu lang. Es sind maximal 200 Zeichen erlaubt!")
        return

    file_name = await generate_tts_audio(params)
    if file_name:
        file_path = os.path.join(config.TTS_AUDIO_PATH, file_name)
        duration = get_mp3_duration(file_path)
        await broadcast_message({"tts": {"file": file_name}})
        await delete_tts_file(file_path, duration)
    else:
        await bot.send_message(f"⚠️ @{event.user.display_name}, leider gab es ein Problem beim Generieren deiner Nachricht!")
COMMANDS["tts"] = command_tts
