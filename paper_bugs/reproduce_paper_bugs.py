#!/usr/bin/env python3
# Reproduce the bugs reported in the GraphGenie paper (ICSE'24, Table 3, Listings 3-7)
# on the old GDBMS versions (Docker) and re-check them on the current Neo4j.
# Queries come from the paper and artifacts/reproducing_bugs/*/reproduce.py,
# plus the cypher-for-gremlin bug found by this project on TinkerPop (T1).
# Servers are started by setup_servers.sh. Run from the project's .venv:
# usage: python reproduce_paper_bugs.py [results/reproduce_results.json]

import os
import sys
import json
import time
import datetime
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REDIS_DATASET = os.path.join(HERE, "..", "artifacts", "reproducing_bugs", "redisgraph", "dataset.txt")

NEO4J_AUTH = ("neo4j", "12344321")
SERVERS = {
    "neo4j-4.4.12": "bolt://127.0.0.1:37687",    # POLE dataset
    "neo4j-5.1.0": "bolt://127.0.0.1:17687",     # recommendations-50
    "neo4j-5.4.0": "bolt://127.0.0.1:27687",     # recommendations-50
    "neo4j-2026.09": "bolt://127.0.0.1:7687",    # current version (Neo4j Desktop), recommendations-50
    "redisgraph-2.10.15": ("127.0.0.1", 16379),  # synthetic dataset from artifacts/reproducing_bugs/redisgraph
    "falkordb-latest": ("127.0.0.1", 26379),     # RedisGraph successor, same synthetic dataset
    "neo4j-oracle": "bolt://127.0.0.1:47687",    # clean Neo4j latest with the synthetic dataset, reference answers for R1-R4
    "agensgraph-v2.13.0": "agensgraph-v2-13-0",  # docker container, graph t: 100 edges (:n)-[:e]->(:n)
    "agensgraph-v2.14.1": "agensgraph-v2-14-1",
    "tinkerpop-3.4.13": ("127.0.0.1", 8182),     # Gremlin Server + cypher-for-gremlin 1.0.4, recommendations-50
}

# id, issue, kind, GQT rule, buggy server, regression server, Q, Q' ('' when Q alone raises the error)
BUGS = [
    ("N1", "neo4j#12968", "internal error", "RenameVariables", "neo4j-4.4.12", None,
     "OPTIONAL MATCH p=(n)-->()--()-->()--()--()-->()<--(n) RETURN id(n) SKIP 2 LIMIT 1",
     "OPTIONAL MATCH p=(a)-->()--()-->()--()--()-->()<--(a) RETURN id(a) SKIP 2 LIMIT 1"),
    ("N2", "neo4j#12988", "internal error", "(base query)", "neo4j-5.1.0", "neo4j-2026.09",
     "OPTIONAL MATCH p=shortestPath((a:User)-[:IN_GENRE*]-(c:Genre)) RETURN DISTINCT p", ""),
    ("N3", "neo4j#12991", "logic", "MoveLabelPredicate", "neo4j-5.1.0", "neo4j-2026.09",
     "OPTIONAL MATCH (s1)-[s0:DIRECTED]-()<-[s2:ACTED_IN]-(s1) RETURN count(s1)",
     "OPTIONAL MATCH (s1)-[s0]-()<-[s2:ACTED_IN]-(s1) WHERE s0:DIRECTED RETURN count(s1)"),
    ("N4", "neo4j#12996", "logic", "CountOtherName", "neo4j-5.1.0", "neo4j-2026.09",
     "MATCH (a)-[b:RATED]->(c) RETURN count(a) SKIP 1",
     "MATCH (a)-[b:RATED]->(c) RETURN count(b) SKIP 1"),
    ("N5", "neo4j (artifact 5.4.0)", "internal error", "RedundantPredicate", "neo4j-5.4.0", "neo4j-2026.09",
     "MATCH (a:User)-[*1..2]-(b:Genre) WHERE id(b)>=0.0 AND id(a)>=0.0 AND id(b)>=0.0 RETURN count(b) ORDER BY 1", ""),
    ("R1", "redisgraph#2744", "logic", "CountIdProperty", "redisgraph-2.10.15", None,
     "MATCH ()-[a]-() RETURN count((a))",
     "MATCH ()-[a]-() RETURN count(id(a))"),
    ("R2", "redisgraph#2858", "logic", "(named path)", "redisgraph-2.10.15", None,
     "MATCH (c)--()--(c) RETURN count(c)",
     "MATCH p=(c)--()--(c) RETURN count(c)"),
    ("R3", "redisgraph#2859", "logic", "RedundantPredicate", "redisgraph-2.10.15", None,
     "MATCH (s1:A)--(s0:B)--(s2:A)<--()<--(s3:A)<--(s4:A)--(s5:A) WHERE s2=s5 RETURN count(s1)",
     "MATCH (s1:A)--(s0:B)--(s2:A)<--()<--(s3:A)<--(s4:A)--(s5:A) WHERE s2=s5 AND id(s0)>=0 RETURN count(s1)"),
    ("R4", "redisgraph#2865", "logic", "SymmetricPattern", "redisgraph-2.10.15", None,
     "MATCH (s1:B)-[*1..2]-(s3:A) RETURN count(s1)",
     "MATCH (s3:A)-[*1..2]-(s1:B) RETURN count(s1)"),
    ("A1", "agensgraph#609", "logic (error)", "PatternPartition", "agensgraph-v2.13.0", "agensgraph-v2.14.1",
     "MATCH (a)-[*1..1]->(b) RETURN count(a)",
     "MATCH (a),(a)-[*1..1]->(b) RETURN count(a)"),
    ("T1", "cypher-for-gremlin (this project)", "logic", "SymmetricPattern", "tinkerpop-3.4.13", "neo4j-2026.09",
     "MATCH (g:Genre)<-[*0..1]-(h)<-[*1..1]-(u:User) WHERE h IS NOT NULL RETURN count(h)",
     "MATCH (u:User)-[*1..1]->(h)-[*0..1]->(g:Genre) WHERE h IS NOT NULL RETURN count(h)"),
    # R5 crashes the server, keep it last
    ("R5", "redisgraph#3071", "internal error (crash)", "(base query)", "redisgraph-2.10.15", "falkordb-latest",
     "MATCH (n) RETURN count(elementId(n))", ""),
]
for i, bug in enumerate(BUGS):
    if bug[0] in ("R1", "R2", "R3", "R4"):
        BUGS[i] = bug[:5] + ("falkordb-latest",) + bug[6:]
ORACLE = {"R1": "neo4j-oracle", "R2": "neo4j-oracle", "R3": "neo4j-oracle", "R4": "neo4j-oracle"}

def run_neo4j(uri, query):
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(uri, auth=NEO4J_AUTH)
    start = time.time()
    try:
        with driver.session() as session:
            records = list(session.run(query))
            value = records[0][0] if records else None
            if value is not None and not isinstance(value, (int, float, str)):
                value = "<{} row(s)>".format(len(records))
            return {"result": value, "error": None, "ms": round((time.time()-start)*1000, 1)}
    except Exception as e:
        return {"result": None, "error": "{}: {}".format(type(e).__name__, str(e).split("\n")[0][:300]), "ms": round((time.time()-start)*1000, 1)}
    finally:
        driver.close()

def run_redisgraph(addr, query):
    import redis
    start = time.time()
    try:
        r = redis.Redis(host=addr[0], port=addr[1], socket_timeout=60)
        reply = r.execute_command("GRAPH.QUERY", "test", query)
        rows = reply[1] if len(reply) > 1 else []
        value = rows[0][0] if rows else None
        return {"result": value, "error": None, "ms": round((time.time()-start)*1000, 1)}
    except Exception as e:
        return {"result": None, "error": "{}: {}".format(type(e).__name__, str(e)[:300]), "ms": round((time.time()-start)*1000, 1)}

def run_agensgraph(container, query):
    start = time.time()
    p = subprocess.run(["docker", "exec", container, "psql", "-U", "postgres", "-tA", "-c", "SET graph_path = t; " + query],
                       capture_output=True, text=True, timeout=120)
    ms = round((time.time()-start)*1000, 1)
    if p.returncode != 0 or "ERROR" in p.stderr:
        return {"result": None, "error": p.stderr.strip().split("\n")[0][:300], "ms": ms}
    lines = [l for l in p.stdout.strip().split("\n") if l and l != "SET"]
    return {"result": int(lines[-1]) if lines and lines[-1].lstrip("-").isdigit() else (lines[-1] if lines else None), "error": None, "ms": ms}

def run_tinkerpop(addr, query):
    sys.path.insert(0, os.path.join(HERE, "..", "tinkerpop"))
    from cypher_client import new_client, translate
    client = new_client(*addr)
    start = time.time()
    try:
        rows = client.submit(translate(client, query)).all().result()
        return {"result": list(rows[0].values())[0] if rows else None, "error": None, "ms": round((time.time()-start)*1000, 1)}
    except Exception as e:
        return {"result": None, "error": "{}: {}".format(type(e).__name__, str(e)[:300]), "ms": round((time.time()-start)*1000, 1)}
    finally:
        client.close()

def run(server, query):
    target = SERVERS[server]
    if server.startswith(("redisgraph", "falkordb")):
        return run_redisgraph(target, query)
    if server.startswith("agensgraph"):
        return run_agensgraph(target, query)
    if server.startswith("tinkerpop"):
        return run_tinkerpop(target, query)
    return run_neo4j(target, query)

# (re)load the synthetic RedisGraph dataset: R5 crashes the server, so every run starts from a fresh container
def prepare_oracle():
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(SERVERS["neo4j-oracle"], auth=NEO4J_AUTH)
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
        session.run(open(REDIS_DATASET).read()).consume()
    driver.close()

def prepare_redis():
    import redis
    for server in ("redisgraph-2.10.15", "falkordb-latest"):
        r = redis.Redis(host=SERVERS[server][0], port=SERVERS[server][1])
        r.execute_command("GRAPH.QUERY", "test", "MATCH (n) DETACH DELETE n")
        r.execute_command("GRAPH.QUERY", "test", open(REDIS_DATASET).read())

def verdict(kind, q, q2):
    if "crash" in kind:
        return "BUG" if q["error"] and q["error"].startswith("ConnectionError") else "NO CRASH"
    if q2 is None:
        return "BUG" if q["error"] else "OK"
    if q["error"] or q2["error"]:
        return "BUG" if bool(q["error"]) != bool(q2["error"]) or kind.startswith("internal") else "ERROR"
    return "BUG" if q["result"] != q2["result"] else "OK"

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "results/reproduce_results.json"
    prepare_redis()
    prepare_oracle()
    results = []
    for bug_id, issue, kind, rule, buggy, regression, query, mutated in BUGS:
        for server, role in ((buggy, "buggy version"), (regression, "current version"), (ORACLE.get(bug_id), "oracle (Neo4j)")):
            if server is None:
                continue
            q = run(server, query)
            q2 = run(server, mutated) if mutated else None
            v = verdict(kind, q, q2)
            results.append({"id": bug_id, "issue": issue, "kind": kind, "rule": rule, "server": server, "role": role,
                            "Q": query, "Q2": mutated, "Q_out": q, "Q2_out": q2, "verdict": v})
            print("{:3} {:22} {:20} {:16} -> {:5} | Q={} {} | Q'={} {}".format(
                bug_id, issue, server, role, v,
                q["result"], ("ERR " + q["error"][:70]) if q["error"] else "",
                (q2 or {}).get("result"), ("ERR " + q2["error"][:70]) if q2 and q2["error"] else ""))
    with open(out, "w") as f:
        json.dump({"run_at": datetime.datetime.now().isoformat(timespec="seconds"), "results": results}, f, indent=2, ensure_ascii=False, default=str)
    print("saved", out)

if __name__ == "__main__":
    main()
