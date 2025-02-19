import logging
import json
import os
import config
from modules.db_manager import get_todos, save_todo, get_scheduled_messages, remove_scheduled_message, add_scheduled_message, get_messages_from_pool, add_message_to_pool


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

def check_access_rights(event, required_role: str = "mod") -> bool:
    """
    Check if the user has the required access rights.

    Parameters:
        - event (EventData): The Twitch chat event.
        - required_role (str): The minimum role required.
            Possible values: "broadcaster", "mod", "vip".

    Returns:
        - True if the user meets or exceeds the required role.
        - False otherwise.
    """
    user_name = event.user.name.lower()
    channel_name = event.chat.channel_name.lower()

    # Broadcaster has full access
    if user_name == channel_name:
        return True

    # Moderator access (includes broadcaster)
    if required_role == "mod":
        return event.user.mod

    # VIP access (includes mod & broadcaster)
    if required_role == "vip":
        return event.user.mod or event.user.vip

    # Default: No access
    return False


async def handle_command(bot, command_name: str, params: str, event):
    """Handles both function-based commands and key-value responses, with alias support."""

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
        await bot.send_message(f"❌ Unknown command: !{command_name}")


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
    message = f"📜 **Verfügbare Commands:**\n{command_list}"

    try:
        await bot.send_whisper(event.user.name, message)
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

async def command_print(bot, params: str, event):
    """Handles the !print command."""
    await bot.send_message(f"🖨️ {event.user.display_name} says: {params}")
COMMANDS["print"] = command_print

async def command_todo(bot, params: str, event):
    """Handles the !todo command."""
    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, benutze die Kanalpunkte um ToDos hinzuzufügen")
        logger.warning(f"⚠️ Unauthorized attempt: {event.user.display_name} tried to add a todo.")
        return

    save_todo(params, event.user.display_name)
    await bot.send_message(f"✅ TODO added: {params}")
COMMANDS["todo"] = command_todo

async def command_todos(bot, params: str, event):
    """Handles the !todos command to list all active ToDos in chat with newlines."""

    todos = get_todos()  # Fetch ToDos using the function

    if not todos:
        await bot.send_message("✅ Aktuell sind keine offenen ToDos vorhanden!")
        return

    # Format ToDos with viewer info
    todo_list = [f"#{todo['id']}: {todo['text']} (by {todo['username']})" for todo in todos]

    # Send in chunks (Twitch chat limit: ~500 chars per message)
    message = "📝 **Aktuelle ToDos:**\n" + "\n".join(todo_list)
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

async def command_listschedules(bot, params: str, event):
    """Zeigt alle geplanten Nachrichten an."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to manage schedules.")
        return

    messages = get_scheduled_messages()
    if not messages:
        await bot.send_message("✅ No scheduled messages found.")
        return

    schedule_list = [f"#{msg.id}: {msg.message} (every {msg.interval}s)" for msg in messages]
    message = "📅 **Scheduled Messages:**\n" + "\n".join(schedule_list)

    await bot.send_message(message)
COMMANDS["listschedules"] = command_listschedules


async def command_addschedule(bot, params: str, event):
    """Ermöglicht Moderatoren und dem Broadcaster, geplante Nachrichten hinzuzufügen."""

    if not check_access_rights(event, "mod"):  # Nur Mods & Broadcaster
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to manage schedules.")
        return

    try:
        parts = params.split(" ", 1)
        interval = int(parts[0])  # Erste Zahl als Intervall (in Sekunden)
        message = parts[1]  # Rest als Nachricht

        add_scheduled_message(message, interval)
        await bot.send_message(f"✅ Scheduled message added! Will repeat every {interval} seconds.")

    except (ValueError, IndexError):
        await bot.send_message("❌ Usage: !addschedule <interval in seconds> <message>")
COMMANDS["addschedule"] = command_addschedule

async def command_removeschedule(bot, params: str, event):
    """Löscht eine geplante Nachricht nach ID (nur Mods)."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to manage schedules.")
        return

    try:
        message_id = int(params)
        if remove_scheduled_message(message_id):
            await bot.send_message(f"✅ Scheduled message #{message_id} removed.")
        else:
            await bot.send_message(f"❌ No scheduled message found with ID {message_id}.")
    except ValueError:
        await bot.send_message("❌ Usage: !removeschedule <message ID>")

COMMANDS["removeschedule"] = command_removeschedule

async def command_addschedulepool(bot, params: str, event):
    """Fügt eine geplante Nachricht aus einer Kategorie hinzu (nur Mods)."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to manage schedules.")
        return

    try:
        parts = params.split(" ", 1)
        interval = int(parts[0])  # Erste Zahl als Intervall (in Sekunden)
        category = parts[1]  # Name der Kategorie

        add_scheduled_message(category, interval)
        await bot.send_message(f"✅ Scheduled message from category '{category}' every {interval} seconds.")
    except (ValueError, IndexError):
        await bot.send_message("❌ Usage: !addschedulepool <interval in seconds> <category>")

COMMANDS["addschedulepool"] = command_addschedulepool


async def command_addtopool(bot, params: str, event):
    """Fügt eine Nachricht zu einer bestehenden Kategorie hinzu (nur Mods)."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to modify message pools.")
        return

    try:
        category, message = params.split(" ", 1)
        add_message_to_pool(category, message)
        await bot.send_message(f"✅ Added message to category '{category}'!")
    except ValueError:
        await bot.send_message("❌ Usage: !addtopool <category> <message>")

COMMANDS["addtopool"] = command_addtopool

async def command_listpool(bot, params: str, event):
    """Listet alle Nachrichten in einer Kategorie auf (nur Mods)."""

    if not check_access_rights(event, "mod"):
        await bot.send_message(f"⛔ @{event.user.display_name}, you don't have permission to list message pools.")
        return

    messages = get_messages_from_pool(params)

    if not messages:
        await bot.send_message(f"✅ No messages found for category '{params}'.")
        return

    message_list = [f"#{msg.id}: {msg.message}" for msg in messages]

    for i in range(0, len(message_list), 5):
        await bot.send_message("\n".join(message_list[i:i + 5]))

COMMANDS["listpool"] = command_listpool
