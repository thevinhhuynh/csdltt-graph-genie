#!/usr/bin/env python3
# Minh hoạ lỗi đếm gấp đôi (TP-L1): lấy NGUYÊN VĂN câu Gremlin do bộ dịch cypher-for-gremlin sinh ra,
# chỉ dời đúng một cụm ".times(1)" ra sau ".repeat(...)", chạy cả hai trên cùng TinkerGraph và so với Neo4j.
# Chạy từ thư mục gốc project: .venv/bin/python bug_cases/evidence/demo_doi_cho_times.py

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tinkerpop"))
from cypher_client import new_client, translate
from neo4j import GraphDatabase

CYPHER = "MATCH (u:User)-[*1..1]->(h)-[*0..1]->(g:Genre) RETURN count(h)"
WRONG_PART = ".times(1).repeat(__.outE().inV()).as('h')"
FIXED_PART = ".repeat(__.outE().inV()).times(1).as('h')"

client = new_client("127.0.0.1", 8182)
translated = translate(client, CYPHER)
assert WRONG_PART in translated, "bản dịch không chứa đoạn cần dời"
fixed = translated.replace(WRONG_PART, FIXED_PART, 1)

def run(query):
    rows = client.submit(query).all().result()
    return list(rows[0].values())[0]

print("Câu Cypher:", CYPHER)
print()
print("1) Câu Gremlin do BỘ DỊCH sinh ra (nguyên văn):")
print("   " + translated)
print("   => kết quả:", run(translated))
print()
print("2) Cùng câu đó, CHỈ dời '.times(1)' ra sau '.repeat(...)':")
print("   " + fixed)
print("   => kết quả:", run(fixed))
print()
print("   Chỗ khác nhau duy nhất:")
print("     bộ dịch : " + WRONG_PART)
print("     đã dời  : " + FIXED_PART)
print()
with GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "12344321")) as driver:
    with driver.session() as session:
        print("3) Neo4j chạy câu Cypher trực tiếp (đối chứng): =>", session.run(CYPHER).single()[0])
client.close()
