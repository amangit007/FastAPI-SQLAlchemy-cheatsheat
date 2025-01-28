from contextlib import asynccontextmanager
from datetime import datetime
import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP, delete, func,select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel

# Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Create async session maker
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Create Base class
Base = declarative_base()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

class Item(Base):
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

# Async dependency to get database session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Test endpoint
@app.get("/items")
async def read_items(db: AsyncSession = Depends(get_db)):
    result = (await db.scalars(select(Item))).all()
    return result

class ItemCreate(BaseModel):
    name: str
    description: str

@app.post("/itemscreate")
async def create_item(item: ItemCreate, db: AsyncSession = Depends(get_db)):
    item_dict = item.model_dump()
    item_dict["is_active"] = True
    
    new_item = Item(**item_dict)
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    return new_item


@app.put("/items/{item_id}")
async def update_item(item_id: int, item: ItemCreate, db: AsyncSession = Depends(get_db)):
    # Check if item exists
    result = await db.execute(select(Item).where(Item.id == item_id))
    existing_item = result.scalar_one_or_none()
    
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Filter out None values from update data
    update_data = {k: v for k, v in item.model_dump().items() if v is not None}
    
    if update_data:
        # Update the item
        await db.execute(
            update(Item)
            .where(Item.id == item_id)
            .values(**update_data)
        )
        await db.commit()
    
    # Fetch and return updated item
    result = await db.execute(select(Item).where(Item.id == item_id))
    updated_item = result.scalar_one()
    return updated_item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    # Check if item exists
    result = await db.execute(select(Item).where(Item.id == item_id))
    existing_item = result.scalar_one_or_none()
    
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Delete the item
    await db.execute(delete(Item).where(Item.id == item_id))
    await db.commit()
    
    return {"message": f"Item {item_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
