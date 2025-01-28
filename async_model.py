from sqlalchemy import TIMESTAMP, Column, Integer, String, Table, ForeignKey, case, func, select, text
from sqlalchemy.orm import relationship, declarative_base, joinedload, load_only
from sqlalchemy.ext.asyncio import  create_async_engine, async_sessionmaker
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
    group=Column(String, nullable=True)
    trainings = relationship("Training", secondary=request_training, back_populates="requests")

class Training(Base):
    __tablename__ = "trainings"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    duration = Column(Integer)
    requests = relationship("Request", secondary=request_training, back_populates="trainings")



SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./relation.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,echo=True
)
async_session = async_sessionmaker(engine, expire_on_commit=False)