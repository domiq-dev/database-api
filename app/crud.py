from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Conversation
from .schemas import UserCreate, ConversationCreate

async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(**user.dict())
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def create_conversation(db: AsyncSession, convo: ConversationCreate):
    db_convo = Conversation(**convo.dict())
    db.add(db_convo)
    await db.commit()
    await db.refresh(db_convo)
    return db_convo
