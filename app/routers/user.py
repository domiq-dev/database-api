# user.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import UserCreate
from app.crud import create_user

router = APIRouter()

@router.post("/users/")
async def new_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)
