import obsws_python as obs
import logging
import json

logger = logging.getLogger("uvicorn.error.obs")


class OBSController:
    def __init__(self, host="localhost", port=4455, password=""):
        self.host = host
        self.port = port
        self.password = password
        self.client = None

    async def initialize(self):
        """Initialize and connect the OBS WebSocket client."""
        if self.client is None:
            self.client = obs.ReqClient(
                host=self.host, port=self.port, password=self.password
            )
            logger.info("OBS started!")

    async def disconnect(self):
        """Disconnect from the OBS WebSocket server."""
        if self.client is not None:
            self.client.disconnect()
            self.client = None

    async def switch_scene(self, scene_name):
        """Switch to a specified scene."""
        await self.initialize()
        return self.client.set_current_program_scene(scene_name)

    async def set_source_visibility(
        self, scene_id=None, source_name=None, visibility=True
    ):
        """Set the visibility of a source within a specific scene."""
        await self.initialize()
        if scene_id == None:
            current_scene = await self.get_current_scene()
            scene_id = current_scene.id

        result = self.client.set_scene_item_enabled(scene_id, source_name, visibility)
        logger.info(result)
        return result

    async def get_current_scene(self):
        await self.initialize()
        response = self.client.get_current_program_scene()
        return {"name": response.scene_name, "id": response.scene_uuid}

    async def get_scene_items(self, scene_name=None):
        if scene_name == None:
            current_scene = await self.get_current_scene()
            scene_name = current_scene.name

        items = self.client.get_scene_item_list(scene_name)
        for item in items:
            logger.info(vars)
        logger.info(vars(items))

    async def get_current_scene_items(self):
        """Fetch all items in the current program scene, including group items."""
        try:
            scene_response = self.client.get_current_program_scene()
            scene_name = scene_response.current_program_scene_name

            items_response = self.client.get_scene_item_list(scene_name)
            scene_items = items_response.scene_items

            response_data = {"scene_name": scene_name, "items": []}

            for item in scene_items:
                item_id = item["sceneItemId"]
                item_name = item["sourceName"]
                is_group = item["isGroup"]

                item_data = {
                    "id": item_id,
                    "name": item_name,
                    "is_group": is_group,
                    "sub_items": [],
                }

                # If the item is a group, fetch its sub-items
                if is_group:
                    item_data["sub_items"] = self.get_group_items(item_name)

                response_data["items"].append(item_data)

            return json.dumps(response_data, indent=4)  # Return JSON
        except Exception as e:
            print(f"❌ Error getting scene items: {e}")
            return json.dumps({"error": str(e)})

    def get_group_items(self, group_name):
        """Fetch all items inside a group."""
        try:
            group_response = self.client.get_group_scene_item_list(group_name)
            group_items = group_response.scene_items

            sub_items = [
                {"id": sub_item["sceneItemId"], "name": sub_item["sourceName"]}
                for sub_item in group_items
            ]
            return sub_items
        except Exception as e:
            print(f"❌ Error getting items in group '{group_name}': {e}")
            return []

    async def toggle_scene_item_visibility(self, scene_name, item_id, enable=True):
        """Enable or disable a scene item in OBS."""
        try:
            self.client.set_scene_item_enabled(
                scene_name=scene_name, scene_item_id=item_id, scene_item_enabled=enable
            )
            print(
                f"✅ {'Enabled' if enable else 'Disabled'} item {item_id} in {scene_name}"
            )
        except Exception as e:
            print(f"❌ Error toggling item {item_id}: {e}")

    async def find_scene_item(self, item_name):
        """Search for a specific item in all scenes and return full details including visibility."""
        try:
            # Get all scenes
            scenes_response = self.client.get_scene_list()
            all_scenes = scenes_response.scenes

            found_items = []

            for scene in all_scenes:
                scene_name = scene["sceneName"]
                scene_id = scene["sceneIndex"]

                # Get all scene items
                items_response = self.client.get_scene_item_list(scene_name)
                scene_items = items_response.scene_items

                for item in scene_items:
                    if (
                        item["sourceName"].lower() == item_name.lower()
                    ):  # Case-insensitive match
                        item_id = item["sceneItemId"]
                        is_visible = self.get_scene_item_visibility(scene_name, item_id)

                        found_items.append(
                            {
                                "scene": scene_name,
                                "scene_id": scene_id,
                                "id": item_id,
                                "name": item["sourceName"],
                                "is_group": item["isGroup"],
                                "visible": is_visible,
                            }
                        )

                        # If it's a group, check inside the group
                        if item["isGroup"]:
                            group_items = self.get_group_items(item["sourceName"])
                            for group_item in group_items:
                                if group_item["name"].lower() == item_name.lower():
                                    group_item_id = group_item["id"]
                                    group_is_visible = self.get_scene_item_visibility(
                                        scene_name, group_item_id
                                    )

                                    found_items.append(
                                        {
                                            "scene": scene_name,
                                            "scene_id": scene_id,
                                            "id": group_item_id,
                                            "name": group_item["name"],
                                            "is_group": False,
                                            "visible": group_is_visible,
                                        }
                                    )

            if not found_items:
                print(f"🔍 Item '{item_name}' not found in any scene.")
                return None

            return found_items  # List of found items with scene details & visibility

        except Exception as e:
            print(f"❌ Error searching for item '{item_name}': {e}")
            return None

    def get_scene_item_visibility(self, scene_name, item_id):
        """Get the visibility state of a scene item."""
        try:
            self.client.get_scene_item_enabled(scene_name, item_id)
            return True
        except Exception as e:
            print(f"❌ Error getting visibility for '{scene_name}' item {item_id}: {e}")
            return False

    async def toggle_source(self, item_name: str):
        state = self.set_source_visibility(source_name=item_name)
        return state
