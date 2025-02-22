import logging

logger = logging.getLogger("uvicorn.error.function_registry")

FUNCTION_REGISTRY = {}

def register_function(name, func):
    """Registers a function globally for all event queues."""
    FUNCTION_REGISTRY[name] = func
    logger.info(f"🔹 Registered function: {name}")

def get_function(name):
    """Retrieves a function from the registry."""
    return FUNCTION_REGISTRY.get(name, None)
