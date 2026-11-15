#!/usr/bin/env python3
# Reproduce the two Neo4j performance issues explained in the GraphGenie paper (Table 4, Listings 9 and 10)
# on the reported versions and re-check them on the latest Neo4j. Each query has a server-side timeout.
# usage: python reproduce_perf_issues.py [results/perf_results.json]

import sys
import json
import time
import datetime
from neo4j import GraphDatabase, Query

AUTH = ("neo4j", "12344321")
TIMEOUT_S = 900

PERF = [
    # id, issue, GQT rule, dataset, [(server label, bolt uri)], Q, Q'
    ("P1", "neo4j#12973", "AddCallWrapper", "POLE",
     [("neo4j-4.4.12", "bolt://127.0.0.1:37687"), ("neo4j-latest", "bolt://127.0.0.1:48687")],
     "MATCH p=(n1)--()<-[r1]-()--(r2:PostCode)--(n2)<--()-->()-->()<-[r3:POSTCODE_IN_AREA]-(n1) RETURN n2 AS X SKIP 6 LIMIT 2",
     "CALL { MATCH p=(n1)--()<-[r1]-()--(r2:PostCode)--(n2)<--()-->()-->()<-[r3:POSTCODE_IN_AREA]-(n1) RETURN n2 AS X SKIP 6 LIMIT 2 } RETURN X"),
    ("P2", "neo4j#13034", "OPTIONAL wrapper", "Cybersecurity",
     [("neo4j-5.4.0", "bolt://127.0.0.1:28687"), ("neo4j-latest", "bolt://127.0.0.1:49687")],
     "MATCH (s3:Computer)<--(s4:HighValue)-->(s0:Computer)-->(s2:User)--()-->(s1:User)<--() RETURN s3 ORDER BY id(s3) ASC SKIP 4 LIMIT 6",
     "OPTIONAL MATCH (s3:Computer)<--(s4:HighValue)-->(s0:Computer)-->(s2:User)--()-->(s1:User)<--() RETURN s3 ORDER BY id(s3) ASC SKIP 4 LIMIT 6"),
]

def timed(uri, query):
    driver = GraphDatabase.driver(uri, auth=AUTH)
    start = time.time()
    try:
        with driver.session() as session:
            rows = len(list(session.run(Query(query, timeout=TIMEOUT_S))))
        return {"ms": round((time.time()-start)*1000, 1), "rows": rows, "timeout": False, "error": None}
    except Exception as e:
        ms = round((time.time()-start)*1000, 1)
        is_timeout = "timeout" in str(e).lower() or "terminated" in str(e).lower()
        return {"ms": ms, "rows": None, "timeout": is_timeout, "error": None if is_timeout else str(e)[:300]}
    finally:
        driver.close()

def show(t):
    return (">{:.0f}s (timeout)".format(TIMEOUT_S) if t["timeout"] else "{:.0f}ms".format(t["ms"])) + (" ERR " + t["error"][:80] if t["error"] else "")

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "results/perf_results.json"
    results = []
    for pid, issue, rule, dataset, servers, q, q2 in PERF:
        for label, uri in servers:
            t1 = timed(uri, q2)   # run the fast one first so a timeout on Q does not hide it
            t0 = timed(uri, q)
            ratio = max(t0["ms"], t1["ms"]) / max(min(t0["ms"], t1["ms"]), 1.0)
            # the paper flags a performance issue when two equivalent queries differ by more than 5x
            flagged = ratio > 5
            results.append({"id": pid, "issue": issue, "rule": rule, "dataset": dataset, "server": label,
                            "Q": q, "Q2": q2, "Q_time": t0, "Q2_time": t1, "ratio": round(ratio, 1), "flagged": flagged})
            print("{} {} {:13} Q={} Q'={} ratio={:.1f}x {}".format(pid, issue, label, show(t0), show(t1), ratio,
                                                                   "PERF ISSUE" if flagged else "ok"), flush=True)
    with open(out, "w") as f:
        json.dump({"run_at": datetime.datetime.now().isoformat(timespec="seconds"), "timeout_s": TIMEOUT_S,
                   "results": results}, f, indent=2, ensure_ascii=False)
    print("saved", out)

if __name__ == "__main__":
    main()
