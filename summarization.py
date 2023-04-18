from call_graph_generator import get_call_graph_from_repo
from node import Flavor
import openai
import pickle
import tqdm
import json 

openai_key = "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"
openai.api_key = openai_key

def run_chatgpt_prompt(code, subcalls):
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
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
                {"role": "system", "content": "You are a code summarization assistant."},
                {"role": "user", "content": prompt}
            ]
    )    

    return completion['choices'][0]['message']['content']



def run_summary(graph, node, chain=[]):
    for subcall in graph.nodes[node]["subcalls"]:
        if subcall.flavor == Flavor.METHOD:
            if graph.nodes[subcall]["summary"] is None and subcall.name != node.name and subcall not in chain:
                print("SC: ", type(subcall))
                run_summary(graph, subcall, [node] + chain)
    subcalls = {}
    for subsubcall in graph.nodes[node]["subcalls"]:
        if subsubcall.flavor == Flavor.METHOD:
            subcalls[subsubcall] = graph.nodes[subsubcall]["summary"]
    
    code = "".join(open(graph.nodes[node]["file"]).readlines()[node.ast_node.lineno - 1:node.ast_node.end_lineno+1])
    graph.nodes[node]["summary"] = run_chatgpt_prompt(code, subcalls)
    
def constrcut_replace_maps(nodes):
    replace_map = {}
    for node in nodes:
        if node.flavor == Flavor.METHOD:
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
    
def summarize_repo(repo_dir, load_from_file=True):
    if load_from_file:
        with open('my_dict.pickle', 'rb') as f:
            graph = pickle.load(f)
            cm = constrcut_replace_maps(graph)
            
            for file in cm:
                repl_map = generate_replace_file(file, cm[file])
                with open(file.replace(".py", "")+"replaced.py", "w") as f:
                    f.write(repl_map)

                

        return graph
    graph, file_map = get_call_graph_from_repo(repo_dir)

    for node in tqdm.tqdm(graph.nodes.keys()):
        if node.flavor == Flavor.METHOD:
            run_summary(graph, node)

    with open('my_dict.pickle', 'wb') as f:
        pickle.dump(graph.nodes, f)
    return graph

def generate_docs():
    summarize_repo(".")




summarize_repo(".")