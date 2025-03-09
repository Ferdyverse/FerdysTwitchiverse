import json
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.session import get_db
from database.base import AdminButton

async def get_admin_buttons(db: AsyncSession = Depends(get_db)):
    """Retrieve all admin buttons ordered by position asynchronously."""
    result = await db.execute(select(AdminButton).order_by(AdminButton.position))
    return result.scalars().all()

async def add_admin_button(label: str, action: str, data: dict, prompt: bool, db: AsyncSession = Depends(get_db)):
    """Add a new admin button asynchronously."""
    try:
        button_data = json.dumps(data) if isinstance(data, dict) else "{}"
        new_button = AdminButton(label=label, action=action, data=button_data, prompt=prompt)

        db.add(new_button)
        await db.commit()
        await db.refresh(new_button)

        return await get_admin_buttons(db)  # Return updated list of buttons
    except Exception as e:
        print(f"❌ Error adding admin button: {e}")
        await db.rollback()
        return None

async def update_admin_button(button_id: int, label: str, action: str, data: dict, prompt: bool, db: AsyncSession = Depends(get_db)):
    """Update an existing admin button asynchronously."""
    result = await db.execute(select(AdminButton).filter(AdminButton.id == button_id))
    button = result.scalars().first()

    if not button:
        return None  # Button not found

    try:
        button_data = json.dumps(data) if isinstance(data, dict) else "{}"

        button.label = label
        button.action = action
        button.data = button_data
        button.prompt = prompt

        await db.commit()
        await db.refresh(button)

        return await get_admin_buttons(db)  # Return updated list of buttons
    except Exception as e:
        print(f"❌ Error updating admin button: {e}")
        await db.rollback()
        return None

async def remove_admin_button(button_id: int, db: AsyncSession = Depends(get_db)):
    """Remove an admin button asynchronously."""
    result = await db.execute(select(AdminButton).filter(AdminButton.id == button_id))
    button = result.scalars().first()

    if not button:
        return None  # Button not found

    try:
        await db.delete(button)
        await db.commit()
        return await get_admin_buttons(db)  # Return updated list of buttons
    except Exception as e:
        print(f"❌ Error removing admin button: {e}")
        await db.rollback()
        return None

async def reorder_admin_buttons(updated_buttons: list, db: AsyncSession = Depends(get_db)):
    """Update the order of admin buttons asynchronously."""
    try:
        for button_data in updated_buttons:
            result = await db.execute(select(AdminButton).filter(AdminButton.id == button_data["id"]))
            button = result.scalars().first()
            if button:
                button.position = button_data["position"]

        await db.commit()
        return True
    except Exception as e:
        print(f"❌ Error reordering admin buttons: {e}")
        await db.rollback()
        return False
