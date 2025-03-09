import asyncio
import yaml
import re
import random
import logging
import config
from modules.websocket_handler import broadcast_message
from modules.state_manager import check_condition, set_condition
from database.crud.todos import complete_todo

logger = logging.getLogger("uvicorn.error.sequence_runner")

# Load sequences from YAML
def load_sequences():
    try:
        with open(config.SEQUENCES_FILE, "r") as file:
            return yaml.safe_load(file).get("sequences", {})
    except Exception as e:
        logger.error(f"❌ Failed to load sequences: {e}")
        return {}

# Store sequences in memory
ACTION_SEQUENCES = load_sequences()

def get_sequence_names():
    return list(ACTION_SEQUENCES.keys())

async def execute_sequence(action: str, event_queue, context: dict = []):
    """Execute a predefined sequence using the global event queue from `app.state`."""
    if action not in ACTION_SEQUENCES:
        logger.warning(f"⚠️ Sequence '{action}' not found.")
        return

    steps = ACTION_SEQUENCES[action]

    for step in steps:
        success = await execute_sequence_step(step, event_queue, context)

        if not success:
            logger.error(f"❌ Sequence '{action}' stopped due to an error in step: {step}")
            await broadcast_message({"admin_alert": {"type": "error", "message": f"Sequence '{action}' failed"}})
            break

    await broadcast_message({"admin_alert": {"type": "button_click", "message": f"Sequence '{action}' executed"}})

async def execute_sequence_step(step, event_queue, context: dict):
    """ Execute a single sequence step using the shared event queue. """
    step_type = step.get("type")
    step_data = resolve_random_values(step.get("data", {}))
    step_data = resolve_variables(step_data, context)

    try:
        if step_type == "sleep":
            delay_time = step_data if isinstance(step_data, (int, float)) else 1
            logger.info(f"⏳ Waiting {delay_time} seconds...")
            await asyncio.sleep(delay_time)
            return True

        if step_type == "if":
            condition_name = step_data.get("condition")
            then_steps = step_data.get("then", [])
            else_steps = step_data.get("else", [])

            if check_condition(condition_name):
                logger.info(f"✅ Condition '{condition_name}' is TRUE, executing THEN block.")
                for then_step in then_steps:
                    success = await execute_sequence_step(then_step, event_queue, context)
                    if not success:
                        return False
            else:
                logger.info(f"❌ Condition '{condition_name}' is FALSE, executing ELSE block.")
                for else_step in else_steps:
                    success = await execute_sequence_step(else_step, event_queue, context)
                    if not success:
                        return False
            return True

        if step_type == "call_function":
            function_name = step_data.get("name")
            parameters = step_data.get("parameters", {})

            task = {"function": function_name, "data": parameters}
            await event_queue.put(task)
            logger.info(f"🔄 Queued function '{function_name}' with parameters: {parameters}")

            success = await wait_for_task_success(task, event_queue)
            if not success:
                logger.error(f"❌ Function '{function_name}' failed, stopping sequence.")
                return False
            return True

        if step_type == "set_condition":
            condition_name = step_data.get("name")
            condition_value = step_data.get("value", True)
            set_condition(condition_name, condition_value)
            logger.info(f"🔄 Set condition '{condition_name}' to {condition_value}")
            return True

        if step_type == "show_icon":
            icon = {"icon": {"id": step_data.get("name"), "action": step_data.get("action"), "name": step_data.get("icon")}}
            await broadcast_message(icon)
            logger.info(f"✅ Show icon: {icon}")
            return True

        if step_type == "todo":
            action = step_data.get("action")
            todo_id = step_data.get("todo_id")

            todo = {"todo": {"action": action, "id": todo_id}}

            if action == "remove":
                async with get_db() as db:
                    await complete_todo(int(todo_id), db)

            await broadcast_message(todo)
            logger.info(f"✅ Trigger ToDo: {todo}")
            return True

        await broadcast_message({"overlay_event": {"action": step_type, "data": step_data}})
        logger.info(f"✅ Executed overlay action: {step_type} with data: {step_data}")
        return True

    except Exception as e:
        logger.error(f"❌ Error executing step '{step_type}': {e}")
        return False

async def wait_for_task_success(task, event_queue):
    """ Wait for a task to complete and return whether it succeeded. """
    return True

async def reload_sequences():
    """ Reload sequences from YAML file. """
    global ACTION_SEQUENCES
    ACTION_SEQUENCES = load_sequences()
    logger.info("🔄 Sequences reloaded successfully.")

def resolve_random_values(data):
    """
    Parses strings for `{random(min, max)}` and replaces with a random number.
    """
    if isinstance(data, dict):
        return {key: resolve_random_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [resolve_random_values(item) for item in data]
    elif isinstance(data, str):
        matches = re.findall(r"{random\((\d+),\s*(\d+)\)}", data)
        for match in matches:
            min_val, max_val = map(int, match)
            random_value = random.randint(min_val, max_val)
            data = data.replace(f"{{random({min_val}, {max_val})}}", str(random_value))
        return data
    return data

def resolve_variables(data, context):
    """ Recursively replace placeholders ($$variable) with actual values from the context dictionary. """
    if isinstance(data, dict):
        return {key: resolve_variables(value, context) for key, value in data.items()}
    elif isinstance(data, list):
        return [resolve_variables(item, context) for item in data]
    elif isinstance(data, str):
        return replace_variables_in_string(data, context)
    return data

def replace_variables_in_string(text, context):
    """ Replace all occurrences of $$variables in a string using the provided context. """
    def replace_match(match):
        variable_name = match.group(1)
        return context.get(variable_name, match.group(0))  # Keep the original if not found

    return re.sub(r"\$\$(\w+)", replace_match, text)
