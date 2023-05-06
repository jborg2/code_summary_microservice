from fastapi import APIRouter, BackgroundTasks, HTTPException
from models import AnalyseRepoData
from db import tasks_collection
import uuid
from util import create_summary

router = APIRouter()

@router.post("/analyze_repo")
async def analyse_repo(background_tasks: BackgroundTasks, data: AnalyseRepoData):
    task_id = str(uuid.uuid4())
    repo_url = f"https://github.com/{data.username}/{data.repo_name}"
    data_dict = {
        "access_token": data.access_token,
        "repo_url": repo_url,
        "username": data.username,
        "repo_name": data.repo_name,
        "access_token": data.access_token
    }
    background_tasks.add_task(create_summary, task_id, data_dict)
    return {"message": "Started analyzing the repository and generating documentation.", "taskID": task_id}