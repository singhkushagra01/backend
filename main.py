from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import jwt
from datetime import datetime, timedelta
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel

app = FastAPI()
security = HTTPBasic()
serializer = URLSafeSerializer("your_secret_key_here")

class UserSignup(BaseModel):
    username: str
    password: str
    role: str = "client"

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.file_sharing
users_collection = db.users
files_collection = db.files

# Authentication function
async def authenticate(credentials: HTTPBasicCredentials):
    user = await users_collection.find_one({"username": credentials.username, "password": credentials.password, "role":"ops"})
    return user

# Dependency for authentication
async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = await authenticate(credentials)
    if user:
        return user
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials or unauthorized")

# Endpoint for Ops user login
@app.post('/ops/login')
async def ops_login(user: dict = Depends(get_current_user)):
    return {"message": "Login successful for Ops user"}

# Endpoint for Ops user upload
@app.post('/ops/upload')
async def ops_upload(files: UploadFile = File(...), user: dict = Depends(get_current_user)):
    filename, file_extension = os.path.splitext(files.filename)
    allowed_extensions = ['.pptx', '.docx', '.xlsx']
    if file_extension.lower() not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")
    # Create directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    # Save file
    file_id = str(uuid.uuid4())
    file_path = os.path.join("uploads", f"{file_id}_{filename}{file_extension}")
    with open(file_path, "wb") as buffer:
        buffer.write(await files.read())
    # Add file information to the database
    await files_collection.insert_one({"filename": files.filename, "file_id": file_id, "user_id": str(user["_id"])})
    return {"message": "File uploaded successfully", "file_id": file_id}



SECRET_KEY = 'jivnjernvkebnkenfierwbgirwgihbrihbv'
def generate_secure_url(file_id: str) -> str:
    payload = {
        "file_id": file_id,
        "exp": datetime.utcnow() + timedelta(hours=1)  # URL expiration time (e.g., 1 hour)
    }
    # Generate JWT token with payload and secret key
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    # Construct the URL with the token as a query parameter
    secure_url = f"/download-file/{file_id}?token={token}"
    return secure_url

# Authentication function for Client Users
async def authenticate_client(credentials: HTTPBasicCredentials):
    user = await users_collection.find_one({"username": credentials.username, "password": credentials.password, "role": "client"})
    return user

# Dependency for Client User authentication
async def get_client_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = await authenticate_client(credentials)
    if user:
        return user
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials or unauthorized")

# Endpoint for Client User login
@app.post('/client/login')
async def client_login(user: dict = Depends(get_client_user)):
    return {"message": "Login successful for Client User"}

# Endpoint to list all uploaded files for Client Users
@app.get('/client/list_uploaded_files')
async def list_uploaded_files(user: dict = Depends(get_client_user)):
    # Execute the query and retrieve the files
    files_cursor = files_collection.find()
    files = await files_cursor.to_list(length=None)
    # Extract relevant information from each file
    uploaded_files = [{"filename": file["filename"], "file_id": file["file_id"]} for file in files]
    return {"uploaded_files": uploaded_files}


# Endpoint to download a file with a secure encrypted URL
@app.get('/client/download/{file_id}')
async def download_file(file_id: str, user: dict = Depends(get_client_user)):
    file = await files_collection.find_one({"file_id": file_id})
    if file:
        # Generate secure encrypted URL for downloading the file
        # This part depends on how you want to generate the URL
        secure_url = generate_secure_url(file_id)
        return {"download-link": f"127.0.0.1:8000"+secure_url, "message": "Success"}
    else:
        raise HTTPException(status_code=404, detail="File not found")

@app.post("/client/signup")
async def signup(user_info: UserSignup):
    # Check if user already exists in MongoDB
    existing_user = await users_collection.find_one({"username": user_info.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    # Generate token with user information
    token = serializer.dumps({"username": user_info.username, "password": user_info.password})
    # Encrypt the token to create a secure URL
    encrypted_url = f"http://127.0.0.1:8000/client/verify?token={token}"
    return {"url": encrypted_url, "message": "Success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
