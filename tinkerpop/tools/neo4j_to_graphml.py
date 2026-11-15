#!/usr/bin/env python3
# Export the Neo4j graph (loaded from data/recommendations-50.dump) to a GraphML file readable by TinkerGraph
# usage: python tools/neo4j_to_graphml.py [output] [bolt_uri] [username] [password]

import sys
from xml.sax.saxutils import escape, quoteattr
from neo4j import GraphDatabase

# TinkerPop allows a single vertex label -> keep the first match in this list
LABEL_PRIORITY = ["Movie", "User", "Genre", "Actor", "Director", "Person"]

def pick_label(labels):
    for label in LABEL_PRIORITY:
        if label in labels:
            return label
    return sorted(labels)[0] if labels else "vertex"

def graphml_type(v):
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int): return "long"
    if isinstance(v, float): return "double"
    return "string"

def graphml_value(v):
    if isinstance(v, bool): return "true" if v else "false"
    return str(v)

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/recommendations.graphml"
    uri = sys.argv[2] if len(sys.argv) > 2 else "bolt://127.0.0.1:7687"
    username = sys.argv[3] if len(sys.argv) > 3 else "neo4j"
    password = sys.argv[4] if len(sys.argv) > 4 else "12344321"

    driver = GraphDatabase.driver(uri, auth=(username, password))
    with driver.session() as s:
        nodes = s.run("MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props").data()
        edges = s.run("MATCH (a)-[r]->(b) RETURN elementId(r) AS id, elementId(a) AS src, elementId(b) AS dst, "
                      "type(r) AS type, properties(r) AS props").data()
    driver.close()

    # TinkerGraph (tinkergraph-empty.properties) expects Long ids -> map Neo4j elementIds to 1..N
    node_ids = {n["id"]: i for i, n in enumerate(nodes, 1)}

    # property key -> type; conflicting types fall back to string
    keys = {}
    for dom, items in (("node", nodes), ("edge", edges)):
        for it in items:
            for k, v in it["props"].items():
                t = graphml_type(v)
                keys[(dom, k)] = t if keys.get((dom, k), t) == t else "string"

    with open(out, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        f.write('<key id="labelV" for="node" attr.name="labelV" attr.type="string"/>\n')
        f.write('<key id="labelE" for="edge" attr.name="labelE" attr.type="string"/>\n')
        for (dom, k), t in keys.items():
            f.write('<key id={} for="{}" attr.name={} attr.type="{}"/>\n'.format(
                quoteattr(dom[0] + "_" + k), dom, quoteattr(k), t))
        f.write('<graph id="G" edgedefault="directed">\n')
        for n in nodes:
            f.write('<node id="{}"><data key="labelV">{}</data>'.format(node_ids[n["id"]], escape(pick_label(n["labels"]))))
            for k, v in n["props"].items():
                f.write('<data key={}>{}</data>'.format(quoteattr("n_" + k), escape(graphml_value(v))))
            f.write('</node>\n')
        for i, e in enumerate(edges, 1):
            f.write('<edge id="{}" source="{}" target="{}"><data key="labelE">{}</data>'.format(
                i, node_ids[e["src"]], node_ids[e["dst"]], escape(e["type"])))
            for k, v in e["props"].items():
                f.write('<data key={}>{}</data>'.format(quoteattr("e_" + k), escape(graphml_value(v))))
            f.write('</edge>\n')
        f.write('</graph>\n</graphml>\n')
    print("Exported {} nodes, {} edges -> {}".format(len(nodes), len(edges), out))

if __name__ == "__main__":
    main()
