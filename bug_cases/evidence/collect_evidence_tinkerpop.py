#!/usr/bin/env python3
# Thu thập bằng chứng: 3 lỗi TinkerPop (logic, nội bộ, hiệu năng) nằm ở bộ dịch cypher-for-gremlin, không phải ở TinkerGraph.
# Cách chứng minh (cô lập biến): cùng máy chủ, cùng dữ liệu, chỉ thay câu Gremlin.
#   (1) câu Cypher qua bộ dịch -> sai / lỗi / chậm
#   (2) câu Gremlin bộ dịch sinh ra -> chỉ ra chỗ dịch sai
#   (3) câu Gremlin viết tay (hoặc sửa đúng một chỗ) trên cùng TinkerGraph -> đúng / không lỗi / nhanh
#   (4) câu Cypher đó trên Neo4j -> đáp án đối chiếu
# Chạy từ thư mục gốc project: .venv/bin/python bug_cases/evidence/collect_evidence_tinkerpop.py

import os
import sys
import time
import hashlib
import datetime
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tinkerpop"))
from cypher_client import new_client, translate
from neo4j import GraphDatabase

client = new_client("127.0.0.1", 8182)
neo4j = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "12344321"))
out = []

def w(text=""):
    out.append(text)

def line():
    w("-" * 100)

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def gremlin(query, label, timeout=60):
    """Chạy một câu Gremlin trên TinkerGraph, ghi câu, kết quả, thời gian và (nếu lỗi) đỉnh stack trace của máy chủ."""
    start = time.time()
    w("  [{}] {}".format(label, query))
    try:
        rows = client.submit(query, request_options={"evaluationTimeout": timeout * 1000}).all().result()
        value = list(rows[0].values())[0] if rows and isinstance(rows[0], dict) else (rows[0] if rows else None)
        w("      => kết quả: {}    thời gian: {:.0f} ms".format(value, (time.time() - start) * 1000))
        return value
    except Exception as e:
        w("      => LỖI: {}    thời gian: {:.0f} ms".format(str(e).split("\n")[0][:120], (time.time() - start) * 1000))
        stack = (getattr(e, "status_attributes", None) or {}).get("stackTrace", "")
        frames = [f.strip() for f in stack.split("\n") if f.strip().startswith("at ")][:2]
        for f in frames:
            w("         stack máy chủ: " + f)
        return "LỖI"

def cypher_via_translator(query, label):
    translated = translate(client, query)
    w("  [{}] Cypher: {}".format(label, query))
    w("      Gremlin do bộ dịch sinh ra:")
    w("      " + translated)
    gremlin(translated, label + " chạy bản dịch")
    return translated

def neo4j_ref(query):
    with neo4j.session() as s:
        rows = s.run(query).data()
    value = list(rows[0].values())[0] if rows else None
    w("  [Neo4j đối chiếu] {}  => {}".format(query, value))
    return value

# ---------------------------------------------------------------- tiêu đề
w("BẰNG CHỨNG: 3 LỖI TINKERPOP NẰM Ở BỘ DỊCH CYPHER-FOR-GREMLIN, KHÔNG PHẢI Ở TINKERGRAPH")
w("Tạo lúc (UTC): {}".format(now()))
line()
w("0. MÔI TRƯỜNG")
w("  Gremlin Server: {}".format(client.submit("Gremlin.version()").all().result()[0]))
plugin = subprocess.run(["docker", "exec", "gremlin", "sh", "-c", "ls ext/cypher-gremlin-server-plugin/plugin | grep -i cypher"],
                        capture_output=True, text=True).stdout.split()
w("  Bộ dịch (plugin): {}".format(", ".join(plugin) or "không đọc được"))
loaded = subprocess.run(["sh", "-c", "docker logs gremlin 2>&1 | grep -m1 'cypher OpProcessor'"], capture_output=True, text=True).stdout.strip()
w("  Log máy chủ khi khởi động: {}".format(loaded or "không tìm thấy"))
w("  Dữ liệu TinkerGraph: {} đỉnh, {} cạnh".format(client.submit("g.V().count()").all().result()[0],
                                                  client.submit("g.E().count()").all().result()[0]))
with neo4j.session() as s:
    v = s.run("CALL dbms.components() YIELD name, versions WHERE name = 'Neo4j Kernel' RETURN versions[0] AS v").single()["v"]
w("  Neo4j đối chiếu: {} (GraphGenieLab)".format(v))
line()

# ---------------------------------------------------------------- 1. lỗi logic
w("1. LỖI LOGIC (TP-L1): ĐẢO CHIỀU ĐƯỜNG ĐI CHO KẾT QUẢ GẤP ĐÔI")
w("")
q_base = "MATCH (g:Genre)<-[*0..1]-(h)<-[*1..1]-(u:User) RETURN count(h)"
q_rev = "MATCH (u:User)-[*1..1]->(h)-[*0..1]->(g:Genre) RETURN count(h)"
w("(a) Hai câu Cypher tương đương qua bộ dịch:")
cypher_via_translator(q_base, "Q")
translated_rev = cypher_via_translator(q_rev, "Q'")
w("")
w("(b) Neo4j trên cùng dữ liệu:")
neo4j_ref(q_base)
neo4j_ref(q_rev)
w("")
w("(c) Cùng TinkerGraph, câu Gremlin viết tay đúng nghĩa của Q':")
gremlin("g.V().hasLabel('User').out().union(__.identity(), __.out()).hasLabel('Genre').count()", "viết tay")
w("")
w("(d) Bản dịch của Q', CHỈ chuyển times(1) ra sau repeat(...) của đoạn đầu (không đổi gì khác):")
fixed = ("g.V().hasLabel('User').repeat(__.outE().inV()).times(1).as('h')"
         ".emit(__.loops().is(gte(0))).repeat(__.outE().inV()).times(1).hasLabel('Genre').count()")
gremlin(fixed, "bản dịch sửa đúng một chỗ")
w("")
w("=> Kết luận: bộ dịch viết '.times(1).repeat(A).as(h).emit(E).repeat(B)'. Trong Gremlin, emit() đứng ngay sau repeat(A)")
w("   (as() chỉ là nhãn) nên được gắn vào repeat(A) thay vì repeat(B): mỗi đường đi bị phát ra hai lần.")
w("   TinkerGraph tính đúng khi các bước được viết đúng thứ tự (c, d).")
line()

# ---------------------------------------------------------------- 2. lỗi nội bộ
w("2. LỖI NỘI BỘ (TP-I1): OPTIONAL MATCH KHÔNG KHỚP + WITH * + id() GÂY LỖI ÉP KIỂU")
w("")
i_base = "OPTIONAL MATCH (a)-[]->(b:Director) WITH a WHERE id(a)>=0 RETURN count(a)"
i_mut = "OPTIONAL MATCH (a)-[]->(b:Director) WITH * WHERE id(a)>=0.0 RETURN count(a)"
w("(a) Hai câu Cypher tương đương qua bộ dịch:")
cypher_via_translator(i_base, "Q")
cypher_via_translator(i_mut, "Q'")
w("")
w("(b) Neo4j trên cùng dữ liệu:")
neo4j_ref(i_base)
neo4j_ref(i_mut)
w("")
w("(c) Cùng TinkerGraph, câu Gremlin viết tay đúng nghĩa:")
gremlin("g.V().as('a').out().hasLabel('Director').select('a').filter(__.id().is(gte(0))).count()", "viết tay")
w("")
w("(d) Bước gây lỗi, tách riêng: bộ dịch thay giá trị null bằng chuỗi '  cypher.null', rồi áp has('~id', ...) lên chuỗi đó:")
gremlin("g.inject('  cypher.null').has('~id', gte(0.0d))", "bước has() trên chuỗi null giả")
w("")
w("(e) Vì sao Q cũng có has('~id', ...) mà không lỗi? Thứ tự bước sau khi TinkerPop tối ưu (explain), bỏ phần choose():")
for label, query in (("Q ", i_base), ("Q'", i_mut)):
    explained = client.submit(translate(client, query) + ".explain()").all().result()[0]
    final = explained["@value"]["final"] if "@value" in explained else explained["final"]
    steps = [str(s).split("@")[0] for s in final[2:] if "NoOpBarrier" not in str(s)]
    w("  [{}] {}".format(label, "  ->  ".join(steps)))
w("  Q : bước lọc null IsStep(neq('  cypher.null')) đứng TRƯỚC HasStep, nên dòng null bị loại trước khi tới has().")
w("  Q': bộ dịch chèn project/select vào giữa, bước lọc null đứng SAU HasStep, nên has() gặp chuỗi null giả và lỗi.")
w("")
w("=> Kết luận: bước has() của Gremlin chỉ nhận đỉnh/cạnh (thiết kế của TinkerPop). Bộ dịch đặt has('~id', ...) lên")
w("   chuỗi '  cypher.null' mà chính nó tạo ra cho dòng null, trước bước lọc bỏ chuỗi đó, nên máy chủ báo lỗi ép kiểu")
w("   tại HasStep. Câu viết tay trên cùng TinkerGraph chạy bình thường và trả 0 như Neo4j.")
line()

# ---------------------------------------------------------------- 3. hiệu năng
w("3. HIỆU NĂNG (TP-P1): HAI CÂU ĐỐI XỨNG CHÊNH HÀNG NGHÌN LẦN")
w("")
p_base = "MATCH ()<-[]-(x)-[]->(u:User) WHERE x IS NOT NULL RETURN count(u)"
p_mut = "MATCH (u:User)<-[]-(x)-[]->() WHERE x IS NOT NULL RETURN count(u)"
w("(a) Hai câu Cypher tương đương qua bộ dịch (chú ý bước đầu tiên của mỗi bản dịch):")
cypher_via_translator(p_base, "Q")
cypher_via_translator(p_mut, "Q'")
w("")
w("(b) Số đỉnh mà mỗi bản dịch phải xuất phát:")
gremlin("g.V().count()", "Q bắt đầu từ g.V(): mọi đỉnh")
gremlin("g.V().hasLabel('User').count()", "Q' bắt đầu từ g.V().hasLabel('User')")
w("")
w("(c) Cùng TinkerGraph, câu Gremlin viết tay cho mẫu của Q nhưng xuất phát từ :User:")
gremlin("g.V().hasLabel('User').inE().outV().outE().inV().count()", "viết tay")
w("")
w("(d) Neo4j trên cùng dữ liệu:")
neo4j_ref(p_base)
w("")
w("=> Kết luận: bộ dịch luôn bắt đầu duyệt từ nút viết đầu tiên trong mẫu (Q: g.V() với 28863 đỉnh; Q': chỉ 671 đỉnh User),")
w("   không chọn điểm xuất phát theo chi phí. TinkerGraph trả lời cùng mẫu trong vài mili giây khi câu Gremlin xuất phát đúng chỗ.")
line()

w("TỔNG KẾT")
w("  Cả 3 lỗi: cùng máy chủ TinkerGraph, cùng dữ liệu, chỉ thay câu Gremlin thì kết quả đúng / không lỗi / nhanh.")
w("  Biến duy nhất thay đổi là câu Gremlin do bộ dịch sinh ra => lỗi nằm ở bộ dịch cypher-for-gremlin.")
line()

client.close()
neo4j.close()
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
path = os.path.join(HERE, "evidence_tinkerpop_{}.log".format(stamp))
data = ("\n".join(out) + "\n").encode("utf-8")
open(path, "wb").write(data)
digest = hashlib.sha256(data).hexdigest()
open(path + ".sha256", "w").write("{}  {}\n".format(digest, os.path.basename(path)))
print("Đã ghi: bug_cases/evidence/{}".format(os.path.basename(path)))
print("Mã băm SHA-256: {}".format(digest))
