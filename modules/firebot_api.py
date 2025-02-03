import requests
import logging
import httpx

logger = logging.getLogger("uvicorn.error.firebot")

class FirebotAPI:
    """
    A class to interact with the Firebot API.

    Allows fetching Twitch usernames, triggering commands, retrieving variables,
    playing sounds, and more.
    """

    def __init__(self, base_url="http://localhost:7472/api/v1"):
        """
        Initialize the Firebot API client.

        :param base_url: The base URL of the Firebot API (default: localhost)
        """
        self.base_url = base_url

    def get_username(self, user_id: str) -> str:
        """
        Fetch the Twitch username from Firebot API using a Twitch User ID.

        :param user_id: The Twitch User ID to lookup
        :return: The Twitch username (or None if not found)
        """
        try:
            response = requests.get(f"{self.base_url}/viewers/{user_id}")

            if response.status_code == 200:
                data = response.json()
                username = data.get("username")

                if username:
                    logger.info(f"✅ Found username for ID {user_id}: {username}")
                    return username
                else:
                    logger.warning(f"⚠️ Firebot API did not return a username for ID {user_id}")
                    return "Unknown"
            else:
                logger.warning(f"⚠️ Firebot API returned {response.status_code}: {response.text}")

        except requests.RequestException as e:
            logger.error(f"❌ Firebot API request failed: {e}")

        return None  # Return None if there was an error or no username found

    def trigger_command(self, command_name: str) -> bool:
        """
        Trigger a Firebot command manually.

        :param command_name: The Firebot command to trigger
        :return: True if successful, False otherwise
        """
        try:
            response = requests.post(f"{self.base_url}/commands/trigger", json={"command": command_name})

            if response.status_code == 200:
                logger.info(f"✅ Successfully triggered command: {command_name}")
                return True
            else:
                logger.warning(f"⚠️ Firebot API returned {response.status_code}: {response.text}")

        except requests.RequestException as e:
            logger.error(f"❌ Firebot API request failed: {e}")

        return False

    def get_variables(self) -> dict:
        """
        Retrieve all stored Firebot variables.

        :return: Dictionary containing Firebot variables
        """
        try:
            response = requests.get(f"{self.base_url}/variables")

            if response.status_code == 200:
                logger.info(f"✅ Retrieved Firebot variables")
                return response.json()
            else:
                logger.warning(f"⚠️ Firebot API returned {response.status_code}: {response.text}")

        except requests.RequestException as e:
            logger.error(f"❌ Firebot API request failed: {e}")

        return {}  # Return empty dict if request fails

    def play_sound(self, sound_name: str) -> bool:
        """
        Play a sound effect using Firebot.

        :param sound_name: The name of the sound effect to play
        :return: True if successful, False otherwise
        """
        try:
            response = requests.post(f"{self.base_url}/soundboard", json={"sound": sound_name})

            if response.status_code == 200:
                logger.info(f"✅ Successfully played sound: {sound_name}")
                return True
            else:
                logger.warning(f"⚠️ Firebot API returned {response.status_code}: {response.text}")

        except requests.RequestException as e:
            logger.error(f"❌ Firebot API request failed: {e}")

        return False

    async def run_effect_list(self, list_id: str, data: dict = None) -> bool:
        """Triggers a Firebot effect list asynchronously."""
        async with httpx.AsyncClient() as client:
            try:
                logger.info(f"📡 Sending request to Firebot for effect: {list_id}, Data: {data}")

                if data is not None:
                    response = await client.post(
                        f"{self.base_url}/effects/preset/{list_id}",
                        json=data,
                        headers={ "Content-Type": "application/json" }
                    )
                else:
                    response = await client.get(f"{self.base_url}/effects/preset/{list_id}")

                logger.info(f"🔥 Response Status: {response.status_code}, Response Body: {response.text}")

                if response.status_code == 200:
                    logger.info(f"✅ Successfully triggered effect list: {list_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Firebot API returned {response.status_code}: {response.text}")
                    return False

            except httpx.RequestError as e:
                logger.error(f"❌ Firebot API request failed: {e}")
                return False
