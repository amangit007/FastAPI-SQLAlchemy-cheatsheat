from sqlalchemy import Column, Integer, String, Table, ForeignKey, case, func, select
from sqlalchemy.orm import relationship, declarative_base, joinedload, load_only

Base = declarative_base()

# Association Table
request_training = Table(
    'request_training',
    Base.metadata,
    Column('request_id', Integer, ForeignKey('requests.id'), primary_key=True),
    Column('training_id', Integer, ForeignKey('trainings.id'), primary_key=True)
)

class Request(Base):
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    trainings = relationship("Training", secondary=request_training, back_populates="requests")

class Training(Base):
    __tablename__ = "trainings"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    duration = Column(Integer)
    requests = relationship("Request", secondary=request_training, back_populates="trainings")


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./relation.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
# Base.metadata.create_all(bind=engine)


from pydantic import BaseModel
from typing import List, Optional

class TrainingBase(BaseModel):
    title: str
    duration: Optional[int] = None

class RequestBase(BaseModel):
    name: str
    description: Optional[str] = None

class TrainingCreate(TrainingBase):
    pass

class RequestCreate(RequestBase):
    pass


   
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

app = FastAPI()

# Database connection dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/trainings/")
def create_training(training: TrainingCreate, db: Session = Depends(get_db)):
    db_training = Training(**training.model_dump())
    db.add(db_training)
    db.commit()
    db.refresh(db_training)
    return db_training

@app.post("/requests/")
def create_request(request: RequestCreate, db: Session = Depends(get_db)):
    db_request = Request(**request.model_dump())
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request

@app.post("/requests/{request_id}/trainings/{training_id}")
def associate_request_training(request_id: int, training_id: int, db: Session = Depends(get_db)):
    request = db.query(Request).filter(Request.id == request_id).first()
    training = db.query(Training).filter(Training.id == training_id).first()
    
    if not request or not training:
        raise HTTPException(status_code=404, detail="Request or Training not found")
    
    request.trainings.append(training)
    db.commit()
    return {"message": "Association created successfully"}

@app.get("/requests/")
def get_all_requests(db: Session = Depends(get_db)):
    # Short way to load joined data
    # requests = (
    #     db.query(Request)
    #     .options(
    #         load_only(Request.id, Request.name),
    #         joinedload(Request.trainings).load_only(Training.id, Training.title)
    #     )
    #     .all()
    # )

    # Postgres data loading
    query = (
        select(
            Request.id,
            Request.name,
            func.coalesce(
                func.json_agg(
                    case(
                        (Training.id.is_not(None),
                        func.json_build_object(
                            'id', Training.id,
                            'title', Training.title
                        ))
                    )
                ).filter(Training.id.is_not(None)),
                '[]'
            ).label("trainings")
        )
        .outerjoin(request_training, Request.id == request_training.c.request_id)
        .join(Training, request_training.c.training_id == Training.id)
        .group_by(Request.id)
    )
    
    # Execute the query and fetch results
    results = db.execute(query).scalars().all()
    
    # Convert results to list of dictionaries
    return results


@app.get("/sample/")
def sample(db: Session = Depends(get_db)):
    data=db.query(Request).filter(Request.id == 1).first()
    train=db.query(Training).filter(Training.id == 3).first()
    data.trainings.remove(train)
    db.commit()
    return {"message": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
