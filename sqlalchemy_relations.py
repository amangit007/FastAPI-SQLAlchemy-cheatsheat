from model import Request, Training, SessionLocal
from sqlalchemy import Column, Integer, String, Table, ForeignKey, case, func, select, text
from sqlalchemy.orm import relationship, declarative_base, joinedload, load_only
# Create tables
# Base.metadata.create_all(bind=engine)
import logging
from colorlog import ColoredFormatter
import json
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
# Set up the tracer

# Create a resource with service name
resource = Resource.create({"service.name": "my-fastapi-service"})

# Initialize TracerProvider with the resource
tracer_provider = TracerProvider(resource=resource)

# Create and register console exporter
console_exporter = ConsoleSpanExporter()
span_processor = BatchSpanProcessor(console_exporter)
tracer_provider.add_span_processor(span_processor)

# Set the global tracer provider
trace.set_tracer_provider(tracer_provider)
# Add this logging configuration after your imports
# def setup_logger():
#     """Set up the logger with color formatting"""
#     formatter = ColoredFormatter(
#         "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(message)s",
#         datefmt=None,
#         reset=True,
#         log_colors={
#             'DEBUG':    'cyan',
#             'INFO':     'green',
#             'WARNING':  'yellow',
#             'ERROR':    'red',
#             'CRITICAL': 'red,bg_white',
#         }
#     )

#     logger = logging.getLogger()
#     handler = logging.StreamHandler()
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     logger.setLevel(logging.INFO)


# # Add this line before creating the FastAPI app
# setup_logger()


# class CustomJSONFormatter(logging.Formatter):
#     def format(self, record):
#         record_dict = {
#             "timestamp": self.formatTime(record),
#             "level": record.levelname,
#             "message": record.getMessage(),
#             "correlation_id": getattr(record, "correlation_id", None),
#             "aws_request_id": getattr(record, "aws_request_id", None)
#         }
#         return json.dumps(record_dict)
# def setup_logger():
#     logger = logging.getLogger()
#     handler = logging.StreamHandler()
#     handler.setFormatter(CustomJSONFormatter())
#     logger.addHandler(handler)
#     logger.setLevel(logging.INFO)
#     return logger
# logger = setup_logger()

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
FastAPIInstrumentor.instrument_app(app)

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
    # Fetching data using sqlalchemy
    results = (
        db.query(Request)
        .options(
            load_only(Request.id, Request.name),
            joinedload(Request.trainings).load_only(Training.id, Training.title)
        )
        .all()
    )

    # msg={"message": "Association created successfully"}
    # logger.info(
    #     [r.to_dict() if hasattr(r, 'to_dict') else r.__dict__ for r in results],
    #     extra={
    #         "correlation_id": "corr-1234",
    #         "aws_request_id": "aws-req22323"
    #     }
    # )
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
    
    # pre_results = db.execute(query).fetchall()

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