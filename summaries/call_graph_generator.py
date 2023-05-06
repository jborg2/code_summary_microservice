from .analyzer import CallGraphVisitor
from .visgraph import VisualGraph
import os

def list_files(dir):
    files = []
    for item in os.listdir(dir):
        path = os.path.join(dir, item)
        if os.path.isfile(path) and path.endswith('.py'):
            files.append(path)
        elif os.path.isdir(path):
            files.extend(list_files(path))
    return files

def get_call_graph_from_repo(repo_path):
    v = CallGraphVisitor(list_files(repo_path))
    graph_options = {
            "draw_defines": True,
            "draw_uses": True,
            "colored": True,
            "grouped_alt": False,
            "grouped": False,
            "nested_groups": False,
            "annotated": True,
    }

    graph, file_map = VisualGraph.from_visitor(v, options=graph_options)

    return graph, file_map