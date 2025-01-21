from pydantic import BaseModel, Field
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
