from fastapi import APIRouter, BackgroundTasks, HTTPException
from models import CreateProjectData
from db import projects_collection, repos_collection, tasks_collection
import uuid
from util import create_summary
 
router = APIRouter()

@router.post("/create_project")
async def create_project(data: CreateProjectData, background_tasks: BackgroundTasks):
    project_id = str(uuid.uuid4())
    repo_url = f"https://github.com/{data.username}/{data.repo_name}"
    project_data = {
        "_id": project_id,
        "username": data.username,
        "repo_name": data.repo_name
    }
    await projects_collection.insert_one(project_data)
    repo_id = str(uuid.uuid4())
    repo_data = {
        "_id": repo_id,
        "project_id": project_id,
        "repo_url": repo_url
    }
    await repos_collection.insert_one(repo_data)

    # Analyze repo in the background after creating it
    task_id = str(uuid.uuid4())
    data_dict = {
        "access_token": data.access_token,
        "repo_url": repo_url,
        "username": data.username,
        "repo_name": data.repo_name,
        "access_token": data.access_token,
        "repo_id": repo_id  # Add repo_id to data_dict
    }
    background_tasks.add_task(create_summary, task_id, data_dict)

    return {"message": "Project created successfully.", "projectID": project_id}