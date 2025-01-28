from async_model import Request, Training, request_training,async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, Integer, String, Table, ForeignKey, case, func, select, text
from sqlalchemy.orm import relationship, declarative_base, joinedload, load_only
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


   
from fastapi import FastAPI, Depends, HTTPException, status

from typing import List

app = FastAPI()

# Async dependency to get database session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# @app.post("/trainings/")
# def create_training(training: TrainingCreate, db: Session = Depends(get_db)):
#     db_training = Training(**training.model_dump())
#     db.add(db_training)
#     db.commit()
#     db.refresh(db_training)
#     return db_training

# @app.post("/requests/")
# def create_request(request: RequestCreate, db: Session = Depends(get_db)):

    
#     db_request = Request(**request.model_dump())
#     db.add(db_request)
#     db.commit()
#     db.refresh(db_request)
#     return db_request

# @app.post("/requests/{request_id}/trainings/{training_id}")
# def associate_request_training(request_id: int, training_id: int, db: Session = Depends(get_db)):
#     request = db.query(Request).filter(Request.id == request_id).first()
#     training = db.query(Training).filter(Training.id == training_id).first()
    
#     if not request or not training:
#         raise HTTPException(status_code=404, detail="Request or Training not found")
    
#     request.trainings.append(training)
#     db.commit()
#     return {"message": "Association created successfully"}

@app.get("/requests/")
async def get_all_requests(db: AsyncSession = Depends(get_db)):
    # Fetching data using sqlalchemy
    try : 
        query = (
            select(Request)
            .options(
                load_only(Request.id, Request.name),
                joinedload(Request.trainings).load_only(Training.id, Training.title)
                )
            )

    # Execute the query
        results = await db.execute(query)
    # Unpack the results
        results = results.unique().scalars().all()
        # Fetching all requests data using text sql Query
        # query = text("""
        #     SELECT 
        #         r.id as request_id,
        #         r.name as request_name,
        #         t.id as training_id,
        #         t.title as training_title
        #     FROM requests r
        #     LEFT JOIN request_training rt ON r.id = rt.request_id
        #     LEFT JOIN trainings t ON rt.training_id = t.id
        #     ORDER BY r.id
        # """)
        
        # # Add await here
        # result = await db.execute(query)
        # # Fetch all results
        # pre_results = result.fetchall()

        # results = []
        # for row in pre_results:
        #     results.append(dict(row._mapping))


        # query = (
        #     select(
        #         Request.id,
        #         Request.name,
        #         func.coalesce(
        #             func.json_agg(
        #                 case(
        #                     (Training.id.is_not(None),
        #                     func.json_build_object(
        #                         'id', Training.id,
        #                         'title', Training.title
        #                     ))
        #                 )
        #             ).filter(Training.id.is_not(None)),
        #             '[]'
        #         ).label("trainings")
        #     )
        #     .outerjoin(request_training, Request.id == request_training.c.request_id)
        #     .join(Training, request_training.c.training_id == Training.id)
        #     .group_by(Request.id)
        # )
        
        # # Execute the query and fetch results
        # results = db.execute(query).scalars().all()
        
        # Convert results to list of dictionaries
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg":str(e)}
        )




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)