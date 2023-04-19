from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

import os
import shutil

# Import the necessary functions from your previous code
from summarization import *

app = FastAPI()

class AnalyseRepoData(BaseModel):
    pat: str
    repo_url: str
    username: str

class PushToGithubData(BaseModel):
    pat: str
    repo_url: str
    local_dir: str
    branch: Optional[str] = "autodocs"

@app.post("/analyse_repo")
def analyse_repo(data: AnalyseRepoData):
    try:
        local_dir = os.path.join(data.username, "cloned_repo")
        clone_repo(data.repo_url, local_dir)
        generate_documentation(local_dir)
        shutil.rmtree(local_dir)
        return {"message": "Successfully analyzed the repository and generated documentation."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/push_to_github")
def push_to_github(data: PushToGithubData):
    try:
        push_documentation_to_github(data.pat, data.repo_url, data.local_dir, data.branch)
        return {"message": "Successfully pushed the documentation to the GitHub repository."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)