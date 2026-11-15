#!/usr/bin/env python3
# Rule-based classifier for GraphGenie detections. Like the paper (Section 6.1), a detection is classified on two axes:
#   kind  - what the symptom is (logic bug, internal error, performance issue, false positive)
#   cause - the root-cause class, inferred from the query pair (the paper's classes + the false positive seen in this project)
# It only looks at the query pair and their outputs, never at which fault was injected.

import re

KINDS = {
    "LOGIC": "Lỗi logic (kết quả sai)",
    "INTERNAL": "Lỗi nội bộ (internal error / crash)",
    "PERF": "Vấn đề hiệu năng",
    "FALSE_POSITIVE": "Báo động giả (truy vấn biến đổi không tương đương)",
}

# cause id -> (name, example bugs)
CAUSES = {
    "OPTIONAL_SEMANTICS": ("Ngữ nghĩa OPTIONAL MATCH + count(*)", "67 cặp trong tinkerpop/logs/bug.log"),
    "COUNTING": ("Đếm quan hệ/thuộc tính sai (Incorrect Relationship Counting)", "Bug 1 redisgraph#2744, neo4j#12996"),
    "EXPAND_INTO": ("Chu trình / ràng buộc hai đầu (Expand(Into))", "Bug 3 neo4j#12968, Bug 4 neo4j#12991"),
    "PARTITION": ("Tách mẫu / parse đường đi độ dài biến (PatternPartition)", "Bug 5 agensgraph#609"),
    "SYMMETRIC_VLE": ("Mẫu đối xứng / đường đi độ dài biến", "Bug 2 redisgraph#2865, T1 cypher-for-gremlin"),
    "OTHER": ("Khác: cần phân tích tay", "neo4j#12988 (shortestPath), redisgraph#3071 (elementId)"),
}

def path_of(query):
    m = re.search(r"MATCH (?:\w+=)?(.*?)(?: WHERE | WITH | RETURN |\) RETURN )", query)
    return m.group(1) if m else ""

def node_vars(path):
    return re.findall(r"\((\w*)", path)

def count_target(query):
    m = re.search(r"RETURN (?:DISTINCT )?count\((.*?)\)(?: |$|;)", query)
    return m.group(1) if m else None

# a variable repeated inside one comma-separated part is a cycle; sharing a variable between parts is a partition
def is_cyclic(path):
    for part in path.split(","):
        names = [v for v in node_vars(part) if v]
        if len(names) != len(set(names)):
            return True
    return False

def cause_of(q, q2):
    p, p2 = path_of(q), path_of(q2)
    if p == p2 and count_target(q) != count_target(q2):
        return "COUNTING"
    if "," in p2 and "," not in p:
        return "PARTITION"
    if is_cyclic(p) or is_cyclic(p2) or re.search(r"WHERE .*?\b(\w+)=(?!\1\b)\w+\b", q2):
        return "EXPAND_INTO"
    v, v2 = node_vars(p), node_vars(p2)
    if v != v[::-1] and v[::-1] == v2:
        return "SYMMETRIC_VLE"
    if "*" in p or "*" in p2:
        return "SYMMETRIC_VLE"
    return "OTHER"

def classify(q, q2, out, out2, perf_ratio=None, threshold=5):
    """Return (kind, cause) for a suspicious pair, or None when the pair is consistent.
    q/out: base query and its output {result, error}; q2/out2: mutated query (q2 == q for a single failing query)."""
    err, err2 = out.get("error"), out2.get("error")
    if bool(err) != bool(err2):
        return "INTERNAL", cause_of(q, q2)
    r, r2 = out.get("result"), out2.get("result")
    if r == r2:
        if perf_ratio is not None and perf_ratio > threshold:
            return "PERF", cause_of(q, q2)
        return None
    if "OPTIONAL" in q and {count_target(q), count_target(q2)} & {"*", "1"} and {r, r2} == {0, 1}:
        return "FALSE_POSITIVE", "OPTIONAL_SEMANTICS"
    return "LOGIC", cause_of(q, q2)
