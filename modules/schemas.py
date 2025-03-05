from pydantic import BaseModel, Field, RootModel
from typing import List, Optional

class PrintElement(BaseModel):
    type: str = Field(
        ...,
        description="The type of element to print. Possible values: 'headline_1', 'headline_2', 'image', 'message'."
    )
    text: Optional[str] = Field(
        None,
        description="The text to print, required for 'headline_1', 'headline_2', and 'message'."
    )
    url: Optional[str] = Field(
        None,
        description="The URL of the image to print, required for 'image'."
    )

class PrintRequest(BaseModel):
    print_elements: List[PrintElement] = Field(
        ...,
        description="A list of elements to print, such as headlines, messages, or images."
    )
    print_as_image: Optional[bool] = False

# Specific data models
class AlertSchema(BaseModel):
    type: str  # "follower", "subscriber", "raid", "donation"
    user: str
    size: Optional[int] = None  # Only for "raid"

class GoalSchema(BaseModel):
    text: str
    current: int
    target: int

class IconSchema(BaseModel):
    id: str # html id
    action: str  # "add" or "remove"
    name: str  # e.g., "fa-bar"

class HtmlSchema(BaseModel):
    content: str
    lifetime: Optional[int] = 0  # Default lifetime is 0

class ClickableObject(BaseModel):
    action: str # add/remove
    object_id: str  # Unique identifier for the object
    x: int
    y: int
    width: int
    height: int
    iconClass: Optional[str] = None  # Optional FontAwesome class
    html: Optional[str] = None

# Alternative model with predefined optional fields (for stricter validation)
class OverlayMessage(BaseModel):
    alert: Optional[AlertSchema] = None
    message: Optional[str] = None
    goal: Optional[GoalSchema] = None
    icon: Optional[IconSchema] = None
    html: Optional[HtmlSchema] = None
    clickable: Optional[ClickableObject] = None

# user click data
class ClickData(BaseModel):
    user_id: str
    x: int
    y: int
    object_id: str = None  # Optional: Track which object was clicked

class ChatMessageRequest(BaseModel):
    message: str

# Admin Buttons
class AdminButtonCreate(BaseModel):
    label: str
    action: str
    data: Optional[str] = "{}"  # Default to empty JSON object
