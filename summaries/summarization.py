from .call_graph_generator import get_call_graph_from_repo
from .node import Flavor
import openai
import pickle
import tqdm
import os
import git
import shutil
import json 

openai_key = "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"
openai.api_key = openai_key

from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

MONGO_URL = "mongodb://admin:admin_password@localhost:27017"
MONGO_DB_NAME = "summary_db"
MONGO_COLLECTION_NAME = "tasks"

client = AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB_NAME]
collection = db[MONGO_COLLECTION_NAME]

async def run_chatgpt_prompt(code, subcalls):
    prompt = "Subcall defintions: \n"
    for subcall, val in subcalls.items():
        if val is not None:
            prompt += subcall.name + " " + val + "\n"
    prompt += "Method Code: \n"
    prompt += code + "\n"
    prompt += "Generate a summary that is no more than 5 sentances for the method"
    if len(subcalls.items()) > 0:
        prompt += " based on the subcall definitions provided above"
    prompt += "."

    # Wrap the synchronous call in asyncio.to_thread()
    completion = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a code summarization assistant."},
                {"role": "user", "content": prompt}
            ]
    )    

    return completion['choices'][0]['message']['content']


import asyncio

async def run_summary(task_id, graph, node, chain=[]):
    tasks = []
    graph.in_progress.add(node)
    if graph.nodes[node]["summary"] is not None:
        return
    
    for subcall in graph.nodes[node]["subcalls"]:
        if subcall.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
            if graph.nodes[subcall]["summary"] is None and subcall.name != node.name and subcall not in chain and node not in graph.in_progress:
                tasks.append(run_summary(task_id, graph, subcall, [node] + chain))

    # Run all tasks concurrently
    await asyncio.gather(*tasks)

    subcalls = {}
    for subsubcall in graph.nodes[node]["subcalls"]:
        if subsubcall.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
            subcalls[subsubcall] = graph.nodes[subsubcall]["summary"]

    code = "".join(open(graph.nodes[node]["file"]).readlines()[node.ast_node.lineno - 1:node.ast_node.end_lineno+1])
    graph.nodes[node]["summary"] = await run_chatgpt_prompt(code, subcalls)
    

    current_summaries = dict([(node.namespace + "." + node.name, graph.nodes[node]["summary"]) for node in graph.nodes if graph.nodes[node]["summary"] is not None])
    
    await collection.update_one({"task_id": task_id}, {"$set": {"summaries": current_summaries}})


    
def constrcut_replace_maps(nodes):
    replace_map = {}
    for node in nodes:
        if node.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
            file = nodes[node]["file"]
            if file not in replace_map:
                replace_map[file] = []
            replace_map[file].append((node.ast_node.lineno, node.ast_node.end_lineno, nodes[node]["summary"]))
    return replace_map

def generate_replace_file(file, replace_map):
    data = open(file).readlines()
    final_data = "".join(data.copy())
    for each in replace_map:
        start = each[0]
        end = each[1]
        summary = each[2]
        method_header = data[start - 1]
        repl = method_header + " " + summary
        final_data = final_data.replace("".join(data[start - 1 : end]), repl)
    return final_data

async def get_docfile(prompt):
    completion = await asyncio.to_thread(
        openai.ChatCompletion.create,
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a code summarization assistant."},
                {"role": "user", "content": f'{prompt}\n Generate a well-structured and comprehensive documentation in .md format for the following Python file, including code snippets and example usages when necessary. Choose which sections to add or hide based on the relevance of the content: '}
            ]
    )    

    return completion['choices'][0]['message']['content']

async def update_collection(task_id, update):
    await collection.update_one({"task_id": task_id}, {"$set": update})


async def summarize_repo(task_id, repo_dir, load_from_file=True):
    print("Repo_dir: ", repo_dir)
    autodocs_dir = os.path.join(repo_dir, "autodocs")
    if load_from_file:
        with open('my_dict.pickle', 'rb') as f:
            graph = pickle.load(f)
            file_map = constrcut_replace_maps(graph)
    else:
        graph, file_map = get_call_graph_from_repo(repo_dir)

    edges = {}

    def generate_edges(node, chain=[]):
        node_is_valid = node.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]
        if node_is_valid:
            if node.namespace+'.'+node.name not in edges:
                edges[node.namespace+'.'+node.name] = []
        for subcall in graph.nodes[node]["subcalls"]:
            if subcall.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
                if node_is_valid and subcall.namespace not in edges[node.namespace+'.'+node.name]:
                    edges[node.namespace+'.'+node.name].append(subcall.namespace+'.'+subcall.name)
        

    for node in graph.nodes.keys():
        generate_edges(node)

    await collection.update_one({"task_id": task_id}, {"$set": {"edges": edges}})

    for node in tqdm.tqdm(graph.nodes.keys()):
        print("running summaries")
        if node.flavor in [Flavor.METHOD, Flavor.FUNCTION, Flavor.CLASSMETHOD, Flavor.STATICMETHOD]:
            await run_summary(task_id, graph, node)

    with open('my_dict.pickle', 'wb') as f:
        pickle.dump(graph, f)

    repl_map = constrcut_replace_maps(graph.nodes)

    root = os.path.join(repo_dir, 'autodocs')
    if not os.path.exists(root):
        os.makedirs(root)

    print("Root: ", root)
    for file in file_map:
        #try:
        repl_data = generate_replace_file(file, repl_map[file])
        file_name = os.path.basename(file).replace(".py", ".md")
        root = os.path.join(repo_dir, 'autodocs')
        path = os.path.join(root, file_name)
        docs = await get_docfile(repl_data)
        print(f"outputting to: {path}")
        with open(path, "w") as f:
            f.write(docs)
        # Update the MongoDB document with the current progress for each file
        update_key = f"completed_summaries.{file.replace('.', '_')}"
        update = {
            update_key: docs
        }
        asyncio.get_event_loop().create_task(update_collection(task_id, update))
        #except Exception as e:
        #    print(f'Failed for {file} with error: {e}')
        #    # Update the MongoDB document with the failed file
        #    update_key = f"failed_summaries.{file.replace('.', '_')}"
        #    update = {
        #        update_key: str(e) or "Unknown error"
        #    }

        #    asyncio.get_event_loop().create_task(update_collection(task_id, update))

    # Update the MongoDB document with the status as completed
    update = {
        "status": "completed"
    }

    asyncio.get_event_loop().create_task(update_collection(task_id, update))


async def generate_docs():
    await summarize_repo(".")

def clone_repo(repo_url, local_dir):
    print(f'Cloning {repo_url} to {local_dir}')
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    try:
        git.Repo.clone_from(repo_url, local_dir)
        print("Cloned")
    except Exception as e:
        print(f"Error while cloning the repository: {e}")

def push_to_repo(repo_dir, branch, commit_message, pat, repo_url):
    try:
        print(repo_dir)
        repo = git.Repo(repo_dir)
        try:
            repo.git.checkout(branch)
        except git.exc.GitCommandError:
            repo.git.checkout('-b', branch)
        repo.git.add(A=True)
        repo.git.commit('-m', commit_message)
        repo.git.push("--force", f"https://{pat}@{repo_url[8:]}")
    except Exception as e:
        print(f"Error while pushing to the repository: {e}")

async def generate_documentation(task_id, local_dir):
    # Generate documentation
    graph = await summarize_repo(task_id, local_dir, load_from_file=False)
    print("AutoDocs Generated")
    return graph

def push_documentation_to_github(pat, repo_url, local_dir,username, access_token, branch="autodocs"):
    # Push the generated documentation to the repository
    local_dir = os.path.join(local_dir, username, repo_url[8:])
    commit_message = "AutoDocs"
    push_to_repo(local_dir, branch, commit_message, access_token, repo_url)
    print("AutoDocs Pushed to GitHub")

async def generate_docs_for_github_repo(pat, repo_url, username, branch="autodocs"):
    local_dir = os.path.join(username, repo_url[8:])
    print("localdir: ", local_dir)
    
    # Clone the repository
    print(f"Cloning Repo {repo_url}")
    clone_repo(repo_url, local_dir)

    # Generate documentation
    graph = await generate_documentation(local_dir)

    # Push the generated documentation to the repository
    push_documentation_to_github(pat, repo_url, local_dir, branch)

    # Clean up the local repository directory
    #shutil.rmtree(local_dir)

#github_token = "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"
#generate_docs_for_github_repo(github_token, "https://github.com/jborg2/code_summary_microservice")