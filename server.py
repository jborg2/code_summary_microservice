from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import os

from motor.motor_asyncio import AsyncIOMotorClient

# Import the necessary functions from your previous code
from summarization import *

app = FastAPI()

# MongoDB Configuration
MONGO_URL = "mongodb://admin:admin_password@localhost:27017"
MONGO_DB_NAME = "summary_db"
MONGO_COLLECTION_NAME = "summaries"

# Database client
client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]


class AnalyseRepoData(BaseModel):
    pat: str
    repo_url: str
    username: str
    repo_name: str


class PushToGithubData(BaseModel):
    pat: str
    repo_url: str
    local_dir: str
    branch: Optional[str] = "autodocs"
    username: str


async def create_summary(task_id: str, data: AnalyseRepoData):
    local_dir = os.path.join(data.username, data.repo_name)
    clone_repo(data.repo_url, local_dir)
    generate_documentation(local_dir)

    '''
    Schema overview:
        - task_id: Unique ID for the task
        - repo_url: URL of the repository
        - username: Username of the user
        - repo_name: Name of the repository
        - completed_summaries: Dictionary of completed summaries
            - key: file name
            - value: summary
        - failed_summaries: Dictionary of failed summaries
            - key: file name
            - value: error message
        - method_summaries: Dictionary of method summaries
            - key: method name
            - value: summary
        - call_graph: Call graph of the repository
        - status: Status of the task
            - started: Task has started
            - completed: Task has completed
            - failed: Task has failed
            - in_progress: Task is in progress
            - cancelled: Task has been cancelled
    '''
    summary = {
        "task_id": task_id,
        "repo_url": data.repo_url,
        "username": data.username,
        "repo_name": data.repo_name,
        "completed_summaries": {},
        "failed_summaries": {},
        "method_summaires" : {},
        "call_graph" : {},
        "status": "started",
        
    }

    await collection.insert_one(summary)


@app.post("/analyse_repo")
async def analyse_repo(background_tasks: BackgroundTasks, data: AnalyseRepoData):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(create_summary, task_id, data)
    return {"message": "Started analyzing the repository and generating documentation.", "taskID": task_id}

@app.post("/push_to_github")
async def push_to_github(data: PushToGithubData):
    try:
        push_documentation_to_github(data.pat, data.repo_url, data.local_dir, data.username, data.branch)
        return {"message": "Successfully pushed the documentation to the GitHub repository."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/get_task/{task_id}")
async def get_task(task_id: str):
    task = await collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
