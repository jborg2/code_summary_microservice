from fastapi import FastAPI
from routes import project_routes, repo_routes, task_routes

app = FastAPI()

app.include_router(project_routes.router)
app.include_router(repo_routes.router)
app.include_router(task_routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=32)