#!/usr/bin/env python3
"""
Ωmegα Knowledge Graph Explorer
Usage: python omega_kg_explorer.py <search_term>
       python omega_kg_explorer.py --list-nodes
       python omega_kg_explorer.py --list-edges
       python omega_kg_explorer.py --layer <MYELIN|ADCCL|AEON|AEGIS>
"""

import json
import argparse
import sys
from pathlib import Path

KG_FILE = Path(__file__).parent / "omega_equation_knowledge_graph.json"


def load_graph():
    if not KG_FILE.exists():
        print(f"Error: {KG_FILE} not found.")
        sys.exit(1)
    with open(KG_FILE, encoding="utf-8") as f:
        return json.load(f)


def find_nodes(kg, query):
    q = query.lower()
    return [
        n for n in kg["nodes"]
        if q in n["id"].lower()
        or q in n["label"].lower()
        or q in n.get("description", "").lower()
        or q in n.get("type", "").lower()
    ]


def edges_for_node(kg, node_id):
    return [e for e in kg["edges"] if e["source"] == node_id or e["target"] == node_id]


def layer_nodes(kg, layer_name):
    layer_id = layer_name.lower()
    owned = {
        e["source"] for e in kg["edges"]
        if e["relation"] == "owned_by" and e["target"].lower() == layer_id
    }
    layer_node = next((n for n in kg["nodes"] if n["id"].lower() == layer_id), None)
    results = [n for n in kg["nodes"] if n["id"] in owned]
    if layer_node:
        results = [layer_node] + results
    return results


def print_node(node, kg, show_edges=True):
    print("\n" + "=" * 56)
    print(f"  {node['label']}  (id: {node['id']})")
    print(f"  type: {node['type']}  |  status: {node['status']}")
    print("-" * 56)
    print(f"  {node['description']}")
    if show_edges:
        edges = edges_for_node(kg, node["id"])
        if edges:
            print("\n  Relationships:")
            for e in edges:
                direction = "→" if e["source"] == node["id"] else "←"
                other = e["target"] if e["source"] == node["id"] else e["source"]
                print(f"    {direction} [{e['relation']}] {other}")
    print("=" * 56)


def main():
    parser = argparse.ArgumentParser(
        description="Ωmegα Canonical Equation Knowledge Graph Explorer"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("query", nargs="?", help="Search term (node ID, label, or keyword)")
    group.add_argument("--list-nodes", action="store_true", help="List all nodes")
    group.add_argument("--list-edges", action="store_true", help="List all edges")
    group.add_argument("--layer", metavar="NAME", help="Show all nodes owned by a layer (MYELIN, ADCCL, AEON, AEGIS)")
    args = parser.parse_args()

    kg = load_graph()
    print(f"\n  Ωmegα Knowledge Graph — {kg['title']}")
    print(f"  {len(kg['nodes'])} nodes  |  {len(kg['edges'])} edges\n")

    if args.list_nodes:
        for n in sorted(kg["nodes"], key=lambda x: x["type"]):
            print(f"  [{n['type']:20s}] {n['label']:30s}  {n['id']}")
        return

    if args.list_edges:
        for e in kg["edges"]:
            print(f"  {e['source']:20s} --[{e['relation']}]--> {e['target']}")
        return

    if args.layer:
        nodes = layer_nodes(kg, args.layer)
        if not nodes:
            print(f"  No layer found matching: {args.layer}")
            print("  Try: MYELIN, ADCCL, AEON, AEGIS")
            return
        for n in nodes:
            print_node(n, kg, show_edges=False)
        return

    if args.query:
        nodes = find_nodes(kg, args.query)
        if not nodes:
            print(f"  No nodes found matching: {args.query}")
            return
        for n in nodes:
            print_node(n, kg)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
