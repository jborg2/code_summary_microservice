from motor.motor_asyncio import AsyncIOMotorClient
import config
from config import MONGO_URL, MONGO_DB_NAME, MONGO_PROJECT_COLLECTION_NAME, MONGO_REPO_COLLECTION_NAME, MONGO_TASK_COLLECTION_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]

projects_collection = db[MONGO_PROJECT_COLLECTION_NAME]
repos_collection = db[MONGO_REPO_COLLECTION_NAME]
tasks_collection = db[MONGO_TASK_COLLECTION_NAME]