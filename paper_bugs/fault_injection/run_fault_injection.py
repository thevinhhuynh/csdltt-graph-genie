#!/usr/bin/env python3
# Fault injection experiment: assume ("giả định") bugs of the classes reported in the GraphGenie paper,
# inject them into a layer in front of a correct Neo4j, run GraphGenie's real generator/mutator,
# then check that bug_classifier.py puts every detection in the class of the injected bug.
# Run from this folder (it has its own graphgenie.ini): python run_fault_injection.py [base_query_num]

import os
import re
import sys
import json
import time
import random
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from neo4j import GraphDatabase, Query
from schema_scanner import Neo4jSchemaScanner
from query_generator import RandomCypherGenerator
from query_mutator import CypherQueryMutator
from bug_classifier import classify, KINDS, CAUSES, path_of, is_cyclic

URI, AUTH = "bolt://127.0.0.1:7687", ("neo4j", "12344321")
PERF_THRESHOLD = 5

# Assumed bugs. Each is triggered by a syntactic feature, like the real bugs in the paper,
# so a base query and its equivalent mutation can trigger it differently.
# The first field is the expected classification (kind, cause); cause None = any cause accepted.
FAULTS = {
    "F1": (("LOGIC", "COUNTING"), "count(id(x)) đếm thừa 1 (giống redisgraph#2744)",
           lambda q: "count(id(" in q, lambda r: r + 1 if isinstance(r, int) and r > 0 else r),
    "F2": (("LOGIC", "SYMMETRIC_VLE"), "đường đi độ dài biến bắt đầu bằng cạnh '<-' bị đếm gấp đôi (giống redisgraph#2865, T1)",
           lambda q: "*" in path_of(q) and re.match(r"\(\w*(:\w+)?\)<-", path_of(q)) is not None, lambda r: r * 2 if isinstance(r, int) else r),
    "F3": (("LOGIC", "EXPAND_INTO"), "mẫu có chu trình (biến lặp) bị đếm thiếu 1 (giống neo4j#12991)",
           lambda q: is_cyclic(path_of(q)),
           lambda r: r - 1 if isinstance(r, int) and r > 0 else r),
    "F4": (("INTERNAL", None), "CALL { } lồng OPTIONAL MATCH gây lỗi nội bộ (giống neo4j#12968)",
           lambda q: "CALL {" in q and "OPTIONAL" in q, None),
    "F5": (("PERF", None), "OPTIONAL MATCH không có WITH chạy chậm thêm 600ms (giống neo4j#13034)",
           lambda q: q.startswith("OPTIONAL") and " WITH " not in q and "CALL {" not in q, None),
}

def execute(driver, query):
    fired = [f for f, (_, _, trig, _) in FAULTS.items() if trig(query)]
    start = time.time()
    try:
        if "F4" in fired:
            raise RuntimeError("Injected internal error (F4)")
        with driver.session() as s:
            rows = s.run(Query(query, timeout=20)).data()
        result = list(rows[0].values())[0] if rows else None
        for f in fired:
            mutate = FAULTS[f][3]
            if mutate:
                result = mutate(result)
        if "F5" in fired:
            time.sleep(0.6)
        return {"result": result, "error": None, "ms": (time.time()-start)*1000, "fired": fired}
    except Exception as e:
        timeout = "timeout" in str(e).lower() or "terminated" in str(e).lower()
        return {"result": None, "error": None if timeout else str(e)[:200], "timeout": timeout,
                "ms": (time.time()-start)*1000, "fired": fired}

def main():
    base_num = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    random.seed(2024)
    os.chdir(HERE)
    scanner = Neo4jSchemaScanner("127.0.0.1", 7687, *AUTH)
    labels, edges, props, matrix = scanner.scan()
    gen = RandomCypherGenerator(labels, edges, props, matrix)
    mut = CypherQueryMutator(labels, edges, props, matrix)
    gen.init()
    driver = GraphDatabase.driver(URI, auth=AUTH)
    detections, executed = [], 0
    for i in range(base_num):
        q = gen.random_query_generator()
        out = execute(driver, q); executed += 1
        if out.get("timeout"):
            continue
        eq, _ = mut.generate_equivalent_queries(q)
        for q2 in eq:
            out2 = execute(driver, q2); executed += 1
            if out2.get("timeout"):
                continue
            ratio = max(out["ms"], out2["ms"]) / max(min(out["ms"], out2["ms"]), 1.0)
            predicted = classify(q, q2, out, out2, ratio, PERF_THRESHOLD)
            if predicted is None:
                continue
            # ground truth: the injected fault(s) that fired on exactly one side of the pair
            truth = sorted(set(out["fired"]) ^ set(out2["fired"]))
            if predicted[0] == "PERF" and "F5" not in truth:
                continue  # timing noise of the real database, not an injected fault
            expected = [FAULTS[f][0] for f in truth]
            correct = any(predicted[0] == k and (c is None or predicted[1] == c) for k, c in expected)
            detections.append({"base": q, "mutated": q2, "base_out": out, "mut_out": out2, "ratio": round(ratio, 1),
                               "injected": truth, "predicted": list(predicted), "correct": correct})
        print("base {}/{}: {} detections so far".format(i+1, base_num, len(detections)), flush=True)
    driver.close()

    summary = {}
    for d in detections:
        key = "+".join(d["injected"]) or "(none)"
        s = summary.setdefault(key, {"total": 0, "correct": 0, "predicted": {}})
        s["total"] += 1
        s["correct"] += d["correct"]
        label = "/".join(d["predicted"])
        s["predicted"][label] = s["predicted"].get(label, 0) + 1
    report = {"run_at": datetime.datetime.now().isoformat(timespec="seconds"), "base_queries": base_num,
              "executed_queries": executed, "faults": {k: {"expected": v[0], "description": v[1]} for k, v in FAULTS.items()},
              "kinds": KINDS, "causes": CAUSES, "summary": summary, "detections": detections}
    os.makedirs("results", exist_ok=True)
    json.dump(report, open("results/fault_injection_results.json", "w"), indent=2, ensure_ascii=False, default=str)
    print("\nexecuted {} queries, {} detections".format(executed, len(detections)))
    for key, s in sorted(summary.items()):
        print("  injected {:30} total={:4} correct={:4} predicted={}".format(key, s["total"], s["correct"], s["predicted"]))

if __name__ == "__main__":
    main()
