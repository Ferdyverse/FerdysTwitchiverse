from sqlalchemy.orm import Session
from ..base import ScheduledMessage, ScheduledMessagePool
import datetime

def get_scheduled_messages(db: Session):
    now = datetime.datetime.utcnow()
    return db.query(ScheduledMessage).filter(ScheduledMessage.enabled == True, ScheduledMessage.next_run <= now).all()

def add_scheduled_message(db: Session, category: str, interval: int):
    new_schedule = ScheduledMessage(category=category, interval=interval, next_run=datetime.datetime.utcnow())
    db.add(new_schedule)
    db.commit()
    return new_schedule

def get_random_message_from_category(db: Session, category: str):
    messages = db.query(ScheduledMessagePool.message).filter(ScheduledMessagePool.category == category).all()
    return random.choice(messages)[0] if messages else None
