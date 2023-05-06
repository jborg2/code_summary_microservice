from fastapi import APIRouter, HTTPException
from db import tasks_collection, repos_collection
from util import format_directory_tree

router = APIRouter()

@router.get("/get_task/{task_id}")
async def get_task(task_id: str):
    task = await tasks_collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/get_directory_tree/{task_id}")
async def get_directory_tree(task_id: str):
    task = await tasks_collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    completed_summaries = format_directory_tree(task["completed_summaries"])
    failed_summaries = format_directory_tree(task["failed_summaries"])
    return {"completed_summaries": completed_summaries, "failed_summaries": failed_summaries}

@router.get("/get_summaries_and_edges/{task_id}")
async def get_summaries_and_edges(task_id: str):
    task = await tasks_collection.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    summaries = task.get("summaries", {})
    edges = task.get("edges", {})

    return {"summaries": summaries, "edges": edges}

@router.get("/repos_by_project/{project_id}")
async def get_repos_by_project(project_id: str):
    repos = await repos_collection.find({"project_id": project_id}).to_list(None)
    if not repos:
        raise HTTPException(status_code=404, detail="No repos found for the specified project")

    repos_info = [{"repo_id": repo["_id"], "repo_url": repo["repo_url"]} for repo in repos]

    return repos_info

@router.get("/tasks_by_repo/{repo_id}")
async def get_tasks_by_repo(repo_id: str):
    tasks = await tasks_collection.find({"repo_id": repo_id}).sort("created_at", -1).to_list(None)
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for the specified repo")

    tasks_info = [{"task_id": task["task_id"], "repo_name": task["repo_name"], "created_at": task["created_at"]} for task in tasks]

    return tasks_info

@router.get("/tasks_by_user/{user_name}")
async def get_tasks_by_user(user_name: str):
    tasks = await tasks_collection.find({"username": user_name}).to_list(None)
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for the specified user")

    tasks_info = [{"task_id": task["task_id"], "repo_name": task["repo_name"]} for task in tasks]

    return tasks_info