import asyncio
import os
from datetime import datetime
from summaries import generate_documentation, clone_repo

from db import tasks_collection
from models import AnalyseRepoData


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
    local_dir = os.path.join(data["username"], data["repo_name"])

    await asyncio.to_thread(clone_repo, data["repo_url"], local_dir)
    summary = {
        "_id": task_id,
        "repo_id": data["repo_id"], # Add repo_id to the summary
        "repo_url": data["repo_url"],
        "username": data["username"],
        "repo_name": data["repo_name"],
        "failed_summaries": {},
        "completed_summaries": {},
        "edges": {},
        "summaries": {},
        "status": "started",
        "created_at": datetime.utcnow()  # Add creation timestamp
    }
    await tasks_collection.insert_one(summary)
    await generate_documentation(data.openai_token, task_id, local_dir)