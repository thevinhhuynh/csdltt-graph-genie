#!/usr/bin/env python3
# Run the bug cases (bug_cases/<dbms>/*.json) against a server and check whether each bug appears on that version.
# The backend comes from the "dbms" field of the JSON file:
#   neo4j      Bolt driver
#   tinkerpop  Gremlin Server + cypher-for-gremlin: Cypher is translated with EXPLAIN, then the Gremlin
#              runs through the standard processor (tinkerpop/cypher_client.py), which enforces the timeout
#
# usage:
#   python bug_cases/run_bug_cases.py bug_cases/neo4j/logic_bugs.json --uri bolt://127.0.0.1:17687
#   python bug_cases/run_bug_cases.py bug_cases/neo4j/*.json --uri bolt://127.0.0.1:7687 --id NEO4J-L1
#   python bug_cases/run_bug_cases.py bug_cases/tinkerpop/*.json --reference-uri bolt://127.0.0.1:7687
#
# Neo4j servers holding several databases (Enterprise): a case runs on the database named like its dataset
# (pole, cybersecurity, recommendations) when it exists, otherwise on the default database (--database overrides).
#
# Verdicts:
#   BUG REPRODUCED   the oracle of the case is violated on this server
#   NOT REPRODUCED   the oracle holds (bug absent / fixed on this version)
#   FALSE POSITIVE   (false_positive cases) the results differ but the reference DBMS differs the same way
#   SKIPPED          the server does not hold the dataset the case needs
#   INCONCLUSIVE     both performance queries hit the timeout or the transaction memory limit
#   ERROR            the case could not be evaluated (e.g. a logic case whose query fails)

import os
import sys
import json
import time
import argparse
import datetime
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))

# labels that identify each dataset of the paper
DATASET_MARKERS = {
    "recommendations": ["Movie", "User", "Genre"],
    "pole": ["PostCode", "Crime"],
    "cybersecurity": ["Computer", "Domain", "HighValue"],
}

DEFAULT_URIS = {"neo4j": "bolt://127.0.0.1:7687", "tinkerpop": "ws://127.0.0.1:8182/gremlin"}

VERDICT_COLORS = {"BUG REPRODUCED": "\033[91m", "NOT REPRODUCED": "\033[92m", "FALSE POSITIVE": "\033[96m",
                  "SKIPPED": "\033[93m", "INCONCLUSIVE": "\033[93m", "ERROR": "\033[93m"}

def scalar(value, rows):
    if value is not None and not isinstance(value, (bool, int, float, str)):
        return "<{} row(s)>".format(rows)
    return value

class Neo4jBackend:
    def __init__(self, uri, user, password, database=None):
        from neo4j import GraphDatabase
        self.uri = uri
        self.forced_database = database
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session(database="system") as session:
            self.databases = [r["name"] for r in session.run(
                "SHOW DATABASES YIELD name, currentStatus WHERE currentStatus = 'online' AND name <> 'system' RETURN name")]

    def database_for(self, dataset):
        if self.forced_database:
            return self.forced_database
        return dataset if dataset in self.databases else None

    def version(self):
        with self.driver.session() as session:
            record = session.run("CALL dbms.components() YIELD name, versions, edition WHERE name = 'Neo4j Kernel' "
                                 "RETURN versions[0] AS v, edition AS e").single()
            return "{} ({})".format(record["v"], record["e"])

    def has_label(self, label, database=None):
        with self.driver.session(database=database) as session:
            return session.run("MATCH (n:`{}`) RETURN count(n) > 0 AS ok".format(label)).single()["ok"]

    def setup(self, statements, database=None):
        with self.driver.session(database=database) as session:
            for statement in statements:
                session.run(statement).consume()

    def execute(self, query, timeout, database=None):
        """Run one query. Returns {result, rows, ms, error, timeout}; result is the first column of the first row."""
        from neo4j import Query
        start = time.time()
        try:
            with self.driver.session(database=database) as session:
                records = list(session.run(Query(query, timeout=timeout)))
            ms = (time.time() - start) * 1000
            value = records[0][0] if records else None
            return {"result": scalar(value, len(records)), "rows": len(records), "ms": round(ms, 1), "error": None, "timeout": False}
        except Exception as e:
            ms = (time.time() - start) * 1000
            message = str(e).split("\n")[0]
            timeout_hit = "timeout" in message.lower() or "terminated" in message.lower()
            return {"result": None, "rows": None, "ms": round(ms, 1), "error": None if timeout_hit else message[:400],
                    "timeout": timeout_hit}

    def close(self):
        self.driver.close()

class TinkerPopBackend:
    CYPHER_NULL = "  cypher.null"  # null marker of cypher-for-gremlin translations

    def __init__(self, uri, user, password, database=None):
        sys.path.insert(0, os.path.join(HERE, "..", "tinkerpop"))
        from urllib.parse import urlparse
        from cypher_client import new_client, translate
        self.uri = uri
        parsed = urlparse(uri)
        self.client = new_client(parsed.hostname, parsed.port or 8182)
        self.translate = translate
        self.databases = []

    # a Gremlin Server exposes a single graph here
    def database_for(self, dataset):
        return None

    def version(self):
        return "TinkerPop {} + cypher-for-gremlin".format(self.client.submit("Gremlin.version()").all().result()[0])

    def has_label(self, label, database=None):
        return self.client.submit("g.V().hasLabel(l).limit(1).count()", {"l": label}).all().result()[0] > 0

    def setup(self, statements, database=None):
        for statement in statements:
            self.client.submit(statement).all().result()

    def execute(self, query, timeout, database=None):
        """Translate the Cypher query with EXPLAIN, then run the Gremlin with a server-side timeout."""
        start = time.time()
        gremlin = None
        try:
            gremlin = self.translate(self.client, query)
            start = time.time()
            rows = self.client.submit(gremlin, request_options={"evaluationTimeout": int(timeout * 1000)}).all().result()
            ms = (time.time() - start) * 1000
            value = list(rows[0].values())[0] if rows else None
            if value == self.CYPHER_NULL:
                value = None
            return {"result": scalar(value, len(rows)), "rows": len(rows), "ms": round(ms, 1), "error": None,
                    "timeout": False, "gremlin": gremlin}
        except Exception as e:
            ms = (time.time() - start) * 1000
            message = str(e).split("\n")[0]
            timeout_hit = message.startswith("598") or "evaluationTimeout" in message
            return {"result": None, "rows": None, "ms": round(ms, 1), "error": None if timeout_hit else message[:400],
                    "timeout": timeout_hit, "gremlin": gremlin}

    def close(self):
        self.client.close()

BACKENDS = {"neo4j": Neo4jBackend, "tinkerpop": TinkerPopBackend}

def has_dataset(backend, dataset, cache):
    if dataset not in cache:
        database = backend.database_for(dataset)
        cache[dataset] = all(backend.has_label(label, database) for label in DATASET_MARKERS[dataset])
    return cache[dataset]

def timed(backend, query, timeout, repeat, database=None):
    """Run a performance query `repeat` times and keep the median time (stops repeating after a timeout or error)."""
    runs = []
    for _ in range(repeat):
        out = backend.execute(query, timeout, database)
        runs.append(out)
        if out["timeout"] or out["error"]:
            break
    out = dict(runs[-1])
    out["ms"] = round(statistics.median(r["ms"] for r in runs), 1)
    out["runs_ms"] = [r["ms"] for r in runs]
    return out

def evaluate(case, oracle, threshold, base, mutated, reference):
    """Return (verdict, detail) following the oracle of the case file."""
    if oracle == "equal":
        if base["error"] or mutated["error"] or base["timeout"] or mutated["timeout"]:
            return "ERROR", "truy vấn lỗi/timeout: base={} mutated={}".format(base["error"] or base["timeout"], mutated["error"] or mutated["timeout"])
        if base["result"] == mutated["result"]:
            return "NOT REPRODUCED", "kết quả bằng nhau: {}".format(base["result"])
        detail = "kết quả khác nhau: {} ≠ {}".format(base["result"], mutated["result"])
        if case.get("false_positive"):
            # the difference is expected by the query semantics; a reference DBMS must differ the same way
            if reference is None:
                return "FALSE POSITIVE", detail + " (đúng ngữ nghĩa theo mô tả case; thêm --reference-uri để đối chiếu)"
            if (reference["base"]["result"], reference["mutated"]["result"]) == (base["result"], mutated["result"]):
                return "FALSE POSITIVE", detail + " (hệ đối chiếu cũng trả {} / {})".format(reference["base"]["result"], reference["mutated"]["result"])
        return "BUG REPRODUCED", detail
    if oracle == "no_error":
        failed = [(name, out["error"]) for name, out in (("base", base), ("mutated", mutated)) if out and out["error"]]
        if failed:
            return "BUG REPRODUCED", "; ".join("{} lỗi: {}".format(n, e[:160]) for n, e in failed)
        timed_out = [name for name, out in (("base", base), ("mutated", mutated)) if out and out["timeout"]]
        if timed_out:
            return "ERROR", "timeout: {}".format(", ".join(timed_out))
        return "NOT REPRODUCED", "không có lỗi (base={}{})".format(
            base["result"], ", mutated={}".format(mutated["result"]) if mutated else "")
    if oracle == "time_ratio":
        # both queries hit the server's transaction memory limit: no timing can be compared
        if all(out["error"] and "MemoryPoolOutOfMemoryError" in out["error"] for out in (base, mutated)):
            return "INCONCLUSIVE", "cả hai câu vượt giới hạn bộ nhớ giao dịch của server (MemoryPoolOutOfMemoryError)"
        if base["error"] or mutated["error"]:
            return "ERROR", "truy vấn lỗi: base={} mutated={}".format(base["error"], mutated["error"])
        if base["timeout"] and mutated["timeout"]:
            return "INCONCLUSIVE", "cả hai câu đều vượt {:.0f}s, chưa đo được tỉ lệ".format(base["ms"] / 1000)
        # a timed-out query took at least the timeout, so the ratio is a lower bound
        slow, fast = (base, mutated) if base["ms"] >= mutated["ms"] else (mutated, base)
        ratio = slow["ms"] / max(fast["ms"], 1.0)
        bound = "≥ " if slow["timeout"] else ""
        detail = "base={}{:.0f}ms mutated={}{:.0f}ms tỉ lệ {}{:.1f}x (ngưỡng {}x)".format(
            "≥ " if base["timeout"] else "", base["ms"], "≥ " if mutated["timeout"] else "", mutated["ms"], bound, ratio, threshold)
        return ("BUG REPRODUCED" if ratio > threshold else "NOT REPRODUCED"), detail
    return "ERROR", "oracle không hỗ trợ: {}".format(oracle)

def paper_match(case, base, mutated):
    expected = case.get("paper_result")
    if not expected or "base" not in expected or not isinstance(expected.get("base"), int):
        return None
    return base["result"] == expected["base"] and (mutated is None or mutated["result"] == expected.get("mutated"))

def run_file(backend, spec, path, args, dataset_cache, reference):
    oracle = spec["oracle"]
    threshold = spec.get("threshold", 5)
    print("\n=== {} ({} case, oracle={}) ===".format(os.path.basename(path), len(spec["cases"]), oracle))
    results = []
    for case in spec["cases"]:
        if args.id and case["id"] not in args.id:
            continue
        database = backend.database_for(case["dataset"])
        row = {"id": case["id"], "issue": case["issue"], "affected_version": case["affected_version"], "dataset": case["dataset"],
               "database": database, "base_query": case["base_query"], "mutated_query": case.get("mutated_query")}
        if not has_dataset(backend, case["dataset"], dataset_cache):
            row.update(verdict="SKIPPED", detail="server không có dataset '{}'".format(case["dataset"]))
        else:
            backend.setup(case.get("setup", []), database)
            if oracle == "time_ratio":
                # run the expected-fast query first so a timeout of the slow one cannot hide it
                order = ("mutated", "base") if case.get("expected_slow") == "base" else ("base", "mutated")
                outs = {name: timed(backend, case["{}_query".format(name)], args.perf_timeout, args.repeat, database) for name in order}
                base, mutated = outs["base"], outs["mutated"]
            else:
                base = backend.execute(case["base_query"], args.timeout, database)
                mutated = backend.execute(case["mutated_query"], args.timeout, database) if case.get("mutated_query") else None
            ref = None
            if reference is not None and oracle != "time_ratio" and has_dataset(reference, case["dataset"], {}):
                ref_db = reference.database_for(case["dataset"])
                ref = {"base": reference.execute(case["base_query"], args.timeout, ref_db),
                       "mutated": reference.execute(case["mutated_query"], args.timeout, ref_db) if case.get("mutated_query") else None}
            verdict, detail = evaluate(case, oracle, threshold, base, mutated, ref)
            row.update(verdict=verdict, detail=detail, base=base, mutated=mutated, reference=ref,
                       paper_match=paper_match(case, base, mutated))
        color = VERDICT_COLORS.get(row["verdict"], "")
        extra = "  (khớp số liệu bài báo)" if row.get("paper_match") else ""
        if row.get("reference") and spec["oracle"] != "time_ratio" and not case.get("false_positive"):
            r = row["reference"]
            extra += "  [đối chiếu: base={}{}]".format(
                r["base"]["result"] if not r["base"]["error"] else "lỗi",
                ", mutated={}".format(r["mutated"]["result"] if not r["mutated"]["error"] else "lỗi") if r["mutated"] else "")
        print("{:10} {:14} {}{:15}\033[0m {}{}".format(case["id"], case["issue"][:14], color, row["verdict"], row["detail"], extra))
        results.append(row)
    return {"file": path, "kind": spec["kind"], "oracle": oracle, "results": results}

def connect(dbms, uri, user, password, database=None):
    try:
        backend = BACKENDS[dbms](uri, user, password, database)
        return backend, backend.version()
    except Exception as e:
        sys.exit("Không kết nối được {}: {}".format(uri, str(e).split("\n")[0]))

def main():
    parser = argparse.ArgumentParser(description="Kiểm chứng các bug trong bài báo GraphGenie trên một server (Neo4j hoặc TinkerPop)")
    parser.add_argument("files", nargs="+", help="file JSON trong bug_cases/neo4j/ hoặc bug_cases/tinkerpop/")
    parser.add_argument("--uri", help="mặc định: bolt://127.0.0.1:7687 (neo4j), ws://127.0.0.1:8182/gremlin (tinkerpop)")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="12344321")
    parser.add_argument("--database", help="Neo4j: chạy mọi case trên database này (mặc định: tự chọn theo dataset)")
    parser.add_argument("--reference-uri", help="Neo4j dùng làm hệ đối chiếu (đáp án tham khảo) cho case logic/internal/false positive")
    parser.add_argument("--timeout", type=float, default=120, help="timeout (giây) cho case logic/internal")
    parser.add_argument("--perf-timeout", type=float, default=900, help="timeout (giây) cho case hiệu năng")
    parser.add_argument("--repeat", type=int, default=1, help="số lần đo mỗi câu hiệu năng, lấy trung vị")
    parser.add_argument("--id", nargs="*", help="chỉ chạy các case có id này")
    parser.add_argument("--out", default=os.path.join(HERE, "results"))
    args = parser.parse_args()

    specs = [(path, json.load(open(path, encoding="utf-8"))) for path in args.files]
    dbms_set = {spec["dbms"] for _, spec in specs}
    if len(dbms_set) != 1:
        sys.exit("Các file phải cùng một hệ quản trị, đang có: {}".format(", ".join(sorted(dbms_set))))
    dbms = dbms_set.pop()
    uri = args.uri or DEFAULT_URIS[dbms]
    backend, version = connect(dbms, uri, args.user, args.password, args.database)
    print("Server: {} @ {}{}".format(version, uri, "  databases: {}".format(", ".join(backend.databases)) if len(backend.databases) > 1 else ""))
    reference, ref_version = (None, None)
    if args.reference_uri:
        reference, ref_version = connect("neo4j", args.reference_uri, args.user, args.password)
        print("Đối chiếu: Neo4j {} @ {}".format(ref_version, args.reference_uri))

    dataset_cache = {}
    report = {"run_at": datetime.datetime.now().isoformat(timespec="seconds"), "dbms": dbms, "server": uri, "version": version,
              "reference": {"server": args.reference_uri, "version": ref_version} if reference else None,
              "files": [run_file(backend, spec, path, args, dataset_cache, reference) for path, spec in specs]}
    backend.close()
    if reference:
        reference.close()

    os.makedirs(args.out, exist_ok=True)
    tag = version.split(" ")[1] if dbms == "tinkerpop" else version.split(" ")[0]
    out = os.path.join(args.out, "{}_{}_{}.json".format(dbms, tag, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    json.dump(report, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False, default=str)
    counts = {}
    for f in report["files"]:
        for r in f["results"]:
            counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\nTổng kết: {}".format(", ".join("{}={}".format(k, v) for k, v in sorted(counts.items()))))
    print("Đã lưu: {}".format(out))

if __name__ == "__main__":
    main()
