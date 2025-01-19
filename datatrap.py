from contextlib import asynccontextmanager
from datetime import datetime
import os
from typing import Dict, Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Boolean, create_engine, Column, Integer, String,TIMESTAMP,func, not_, or_, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker, Session
from pydantic import BaseModel
# Initialize FastAPI app


# Database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    yield
    # Base.metadata.drop_all(bind=engine)
    # if os.path.exists("./test.db"):
    #     os.remove("./test.db")


app = FastAPI(lifespan=lifespan)
class Item(Base):
    __tablename__ = "items"
    
    id: Mapped[int] = mapped_column(Integer,primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String,index=True)
    description: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())



# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test endpoint
@app.get("/items")
def read_items(db: Session = Depends(get_db)):
    # with query
    #items = db.query(Item).all()
    # with select
    items = db.execute(select(Item)).scalars().all()
    return items

class ItemCreate(BaseModel):
    name: str
    description: str

@app.post("/itemscreate")
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
   # Convert to dict and add is_active
    item_dict = item.model_dump()
    item_dict["is_active"] = True
    
    # Create new Item with the modified dict
    print(type(item_dict))
    new_item = Item(**item_dict)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

@app.put("/items/{item_id}")
def update_item(item_id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update only provided fields
    update_data = item.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

class ItemResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "arbitrary_types_allowed": True
    }

@app.patch("/items/bulk-update")
def update_multiple_items(items: Dict[int, ItemUpdate], db: Session = Depends(get_db)):
    updated_items = []
    not_found_ids = []
    
    for item_id, update_data in items.items():
        db_item = db.query(Item).filter(Item.id == item_id).first()
        if not db_item:
            not_found_ids.append(item_id)
            continue
            
        # Update provided fields
        item_data = update_data.model_dump(exclude_unset=True)
        for key, value in item_data.items():
            setattr(db_item, key, value)
        updated_items.append(db_item)
    
    if not_found_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Items with ids {not_found_ids} not found"
        )
    
    db.commit()
    
    # Convert SQLAlchemy objects to Pydantic models
    response_items = [ItemResponse.model_validate(item) for item in updated_items]
    
    return {
        "message": f"Successfully updated {len(updated_items)} items",
        "updated_items": response_items
    }






