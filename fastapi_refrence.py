# Fast api code of basic crud operations

import asyncio
import time
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Cookie, Query, Path, Body, Response, status
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, PlainTextResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr, HttpUrl, constr, field_validator,StringConstraints
from typing import List, Optional, Dict, Union, Any, Annotated, TypeVar, Generic
from datetime import datetime
import io
import csv
import json

T = TypeVar('T')

app = FastAPI(title="FastAPI Advanced CRUD Operations", version="1.0.0")

# Advanced Pydantic models with validations
class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class UserBase(BaseModel):
    email: EmailStr
    username:Annotated[str, StringConstraints(min_length=3, max_length=50)]
    website: Optional[HttpUrl] = None

    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('must be alphanumeric')
        return v

class Item(BaseModel):
    name: str
    description: str
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    tags: List[str] = []
    location: Optional[Location] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

# Custom response model
class ResponseModel(BaseModel, Generic[T]):
    data: Optional[T] = None
    message: str
    status: bool = True

class ErrorResponse(BaseModel):
    message: str
    status: bool = False


# 1. Complex Query Parameters with Union and Annotated
@app.get("/search")
async def search(
    query: Annotated[
        Union[str, List[str]], 
        Query(description="Search query string or list of strings")
    ],
    filter_type: Annotated[
        str, 
        Query(enum=['category', 'tag', 'location'])
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1
) -> ResponseModel[List[dict]]:
    result = {"query": query, "filter_type": filter_type, "page": page}
    return ResponseModel(data=[result], message="Search results")

# 2. File Operations with Different Response Types
@app.post("/files")
async def handle_files(
    files: Annotated[List[UploadFile], File(description="Multiple files to upload")],
    format: Annotated[str, Query(enum=['json', 'csv', 'stream'])] = 'json'
):
    file_info = [{"filename": file.filename, "content_type": file.content_type} for file in files]
    
    if format == 'json':
        return JSONResponse(content={"files": file_info})
    
    elif format == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["filename", "content_type"])
        writer.writeheader()
        writer.writerows(file_info)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=files.csv"}
        )
    
    else:  # stream
        async def file_generator():
            for file in files:
                contents = await file.read()
                yield contents
        
        return StreamingResponse(file_generator(), media_type="application/octet-stream")

# 3. Complex Path Parameters with Enhanced Response
@app.get(
    "/items/{item_id}", 
    responses={
        200: {"model": ResponseModel[Item]},
        404: {"model": ResponseModel[None]},
        302: {"description": "Redirect to another item"}
    },
    response_model=None
)
async def get_item(

    item_id: Annotated[int, Path(title="Item ID", ge=1)],
    response: Response,
    detailed: Annotated[bool, Query()] = False
) -> Union[ResponseModel[Item], RedirectResponse]:
    if item_id == 999:  # Example redirect
        print("Redirecting to /items/1")
        return RedirectResponse(url="/items/1")
    
    # Example item
    item = Item(
        name="Test Item",
        description="Description",
        price=10.5,
        stock=100,
        location=Location(lat=40.7128, lng=-74.0060)
    )
    
    response.headers["X-Custom-Header"] = "Custom Value"
    return ResponseModel(data=item, message="Item retrieved successfully")

# 4. Complex Form Data with Multiple Response Types. Note: you can not use body with file upload as it will be changed to form data which can not be used with body
@app.post("/submit",response_model=None)
async def submit_form(
    email: Annotated[EmailStr, Form()],
    username: Annotated[str, Form()],
    website: Annotated[Optional[HttpUrl], Form()] = None,
    files: Annotated[Optional[List[UploadFile]], File()] = None,
    response_type: Annotated[str, Form(enum=['json', 'text', 'file'])] = 'json'
) -> Union[JSONResponse, PlainTextResponse, FileResponse]:
    user_data=UserBase(email=email, username=username, website=website)
    content = {
        "user": jsonable_encoder(user_data),
        "files": [file.filename for file in (files or [])]
    }
    
    if response_type == 'json':
        return JSONResponse(
            content=content,
            status_code=status.HTTP_201_CREATED
        )
    elif response_type == 'text':
        return PlainTextResponse(
            content=json.dumps(content, indent=2),
            status_code=status.HTTP_201_CREATED
        )
    else:  # file
        return FileResponse(
            path="sample.txt",
            filename="response.txt",
            media_type="text/plain"
        )

# 5. Streaming Response Example
@app.get("/stream")
async def stream_data(stream_type: str = Query(..., enum=['sse', 'bytes', 'iterator', 'async_iterator','json'])):
    """
    Different types of streaming responses in FastAPI:
    - SSE (Server-Sent Events): Used by OpenAI ChatGPT, Anthropic Claude (text/event-stream)
    - Bytes Stream: Used by Google Gemini (application/octet-stream) 
    - Iterator: Simple streaming of data chunks
    - Async Iterator: Async version of iterator streaming
    """
    
    async def sse_generator():
        # Server-Sent Events stream (used by ChatGPT/Claude)
        for i in range(5):
            data = {"message": f"SSE message {i}", "timestamp": time.time()}
            # \n\n is used to separate the events
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
            
    async def bytes_generator():
        # Bytes stream (used by Gemini)
        for i in range(5):
            data = f"Bytes chunk {i}".encode('utf-8') 
            yield data
            await asyncio.sleep(1)
            
    def iterator_generator():
        # Simple iterator stream
        for i in range(5):
            yield f"Iterator message {i}"
            time.sleep(1)
    def json_generator():
        for i in range(5):
            yield json.dumps({"message": f"JSON message {i}", "timestamp": time.time()}) + "\n"
            time.sleep(1)
            
    async def async_iterator_generator():
        # Async iterator stream
        for i in range(5):
            yield f"Async Iterator message {i}"
            await asyncio.sleep(1)

    if stream_type == 'sse':
        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream"
        )
    elif stream_type == 'bytes':
        return StreamingResponse(
            bytes_generator(),
            media_type="application/octet-stream"
        )
    elif stream_type == 'iterator':
        return StreamingResponse(
            iterator_generator(),
            media_type="text/plain"
        )
    elif stream_type == 'json':
        return StreamingResponse(
            json_generator(),
            media_type="application/x-ndjson"
        )
    else:  # async_iterator
        return StreamingResponse(
            async_iterator_generator(),
            media_type="text/plain"
        )

# 6. Error Handling with Custom Response
@app.get("/error-demo",responses={
             400: {"model": ErrorResponse},
             422: {"model": ErrorResponse}
         })
async def error_demo(error_type: str = Query(..., enum=['client', 'server', 'custom']))->JSONResponse:
    if error_type == 'client':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Item not found", "status": False}
        )
    elif error_type == 'server':
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Server error demonstration", "status": False}
        )
        
    else:
        return JSONResponse(
            status_code=status.HTTP_418_IM_A_TEAPOT,
            content={"message": "I'm a teapot!"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

