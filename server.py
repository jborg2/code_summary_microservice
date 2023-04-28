from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import asyncio

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

def format_directory_tree(summaries):
    tree = {}
    for key, value in summaries.items():
        user_repo, file_name = key.rsplit('/', 1)
        new_file_name = file_name.replace('_', '.')
        if user_repo not in tree:
            tree[user_repo] = {}
        tree[user_repo][new_file_name] = value
    return tree

async def create_summary(task_id: str, data: AnalyseRepoData):
    local_dir = os.path.join(data.username, data.repo_name)

    await asyncio.to_thread(clone_repo, data.repo_url, local_dir)
    summary = {
        "task_id": task_id,
        "repo_url": data.repo_url,
        "username": data.username,
        "repo_name": data.repo_name,
        "failed_summaries":{},
        "completed_summaries": {},
        "status": "started"
    }
    await collection.insert_one(summary)
    await generate_documentation(task_id, local_dir)  

    print(f'Generating summary for {data.repo_url}')


@app.post("/analyse_repo")
async def analyse_repo(background_tasks: BackgroundTasks, data: AnalyseRepoData):
    task_id = str(uuid.uuid4())
    background_tasks.add_task(create_summary, task_id, data)
    return {"message": "Started analyzing the repository and generating documentation.", "taskID": task_id}

def push_to_github(data: PushToGithubData):
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

@app.get("/get_directory_tree/{task_id}")
async def get_directory_tree(task_id: str):
    task = await collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    completed_summaries = format_directory_tree(task["completed_summaries"])
    failed_summaries = format_directory_tree(task["failed_summaries"])
    return {"completed_summaries": completed_summaries, "failed_summaries": failed_summaries}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=32)
