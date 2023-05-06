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

@router.get("/get_project/{project_id}")
async def get_project(project_id: str):
    project = await projects_collection.find_one({"_id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    repos = await repos_collection.find({"project_id": project_id}).to_list(length=100)
    if len(repos) > 0:
        ret_repo = repos[0]
    else:
        ret_repo = None

    most_recent_task = await tasks_collection.find_one({"repo_id": ret_repo["_id"]}, sort=[("created_at", -1)])
    all_tasks = await tasks_collection.find({"repo_id": ret_repo["_id"]}, sort=[("created_at", -1)]).to_list(length=100)

    ret_dto = {
        "project_id": project_id,
        "username": project["username"],
        "repo_name": project["repo_name"],
        "repo_url": ret_repo["repo_url"],
        "repo_id": str(ret_repo["_id"]),
        "most_recent_task": {
            "task_id": str(most_recent_task["_id"]),
            "completed": most_recent_task["completed_summaries"],
            "failed": most_recent_task["failed_summaries"],
            "method_summaries" : most_recent_task["summaries"]
        },
        "all_tasks": [str(task["_id"]) for task in all_tasks]
    }
    if project:
        return ret_dto
    else:
        raise HTTPException(status_code=404, detail="Project not found")

@router.get("/get_projects_by_user/{username}")
async def get_project_by_user(username: str):
    projects = await projects_collection.find({"username": username}).to_list(length=100)
    return [{"project_id": project["_id"], "username": project["username"], "repo_name": project["repo_name"]} for project in projects]
