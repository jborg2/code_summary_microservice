from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

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
    access_token: str
    username: str
    repo_name: str
    local_dir: str

class PushToGithubData(BaseModel):
    token: str
    local_dir: str
    branch: Optional[str] = "autodocs"
    username: str
    access_token: str


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
    print(data)
    local_dir = os.path.join(data["username"], data["repo_name"])

    await asyncio.to_thread(clone_repo, data["repo_url"], local_dir)
    summary = {
        "task_id": task_id,
        "repo_url": data["repo_url"],
        "username": data["username"],
        "repo_name": data["repo_name"],
        "failed_summaries":{},
        "completed_summaries": {},
        "edges": {},
        "summaries":{},
        "status": "started"
    }
    await collection.insert_one(summary)
    await generate_documentation(task_id, local_dir) 


@app.post("/analyse_repo")
async def analyse_repo(background_tasks: BackgroundTasks, data: AnalyseRepoData):
    task_id = str(uuid.uuid4())
    repo_url = f"https://github.com/{data.username}/{data.repo_name}"
    data_dict = {
        "pat": data.access_token,
        "repo_url": repo_url,
        "username": data.username,
        "repo_name": data.repo_name,
        "access_token": data.access_token
    }
    background_tasks.add_task(create_summary, task_id, data_dict)
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

@app.get("/get_summaries_and_edges/{task_id}")
async def get_summaries_and_edges(task_id: str):
    task = await collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    summaries = task.get("summaries", {})
    edges = task.get("edges", {})

    return {"summaries": summaries, "edges": edges}

@app.get("/tasks_by_user/{user_name}")
async def get_tasks_by_user(user_name: str):
    tasks = await collection.find({"username": user_name}).to_list(None)
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for the specified user")

    tasks_info = [{"task_id": task["task_id"], "repo_name": task["repo_name"]} for task in tasks]

    return tasks_info

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=32)
