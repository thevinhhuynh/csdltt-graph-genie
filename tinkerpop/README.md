# GraphGenie trên TinkerPop

Chạy GraphGenie trên **Apache TinkerPop (Gremlin Server + TinkerGraph)** mà **không sửa code gốc** ở thư mục cha.
GraphGenie sinh truy vấn Cypher; plugin [cypher-for-gremlin](https://github.com/opencypher/cypher-for-gremlin)
trên Gremlin Server dịch Cypher sang Gremlin.

```
main_tinkerpop.py ──Cypher──► Gremlin Server 3.4.13 + cypher-for-gremlin 1.0.4 ──Gremlin──► TinkerGraph
                   (ws://127.0.0.1:8182/gremlin, processor="cypher")
```

`main_tinkerpop.py` import lại `Testing`, `RandomCypherGenerator`, `CypherQueryMutator`, `SchemaScanner` từ thư mục gốc,
nên mọi thay đổi ở generator/mutator gốc đều tự áp dụng cho TinkerPop.

## Cấu trúc

| File | Vai trò |
|---|---|
| `graphgenie.ini` | Cấu hình riêng: `graphdb = tinkerpop`, port 8182, log ghi vào `./logs/` |
| `main_tinkerpop.py` | Lớp `TinkerPopTesting` (kế thừa `Testing` của `main.py`) |
| `gremlin_schema_scanner.py` | Quét label/property/ma trận kết nối bằng Gremlin |
| `cypher_client.py` | Client gremlinpython gửi được `processor="cypher"`; dịch Cypher bằng `EXPLAIN` |
| `tools/neo4j_to_graphml.py` | Xuất dữ liệu từ Neo4j (đã load `data/recommendations-50.dump`) ra GraphML |
| `tools/check_connection.py` | Kiểm tra kết nối Gremlin + Cypher |
| `server/` | Dockerfile, cấu hình Gremlin Server, script nạp dữ liệu khi khởi động |

## Các bước chạy

Tất cả lệnh chạy **trong thư mục `tinkerpop/`**.

**1. Cài thư viện** (dùng chung `.venv` của project)
```bash
../.venv/bin/pip install -r requirements.txt
```

**2. Chuyển dữ liệu Neo4j → GraphML** (cần Neo4j đang chạy, đã load `recommendations-50.dump`)
```bash
../.venv/bin/python tools/neo4j_to_graphml.py
# tham số tuỳ chọn: [output] [bolt_uri] [username] [password]
```

**3. Build và chạy Gremlin Server**
```bash
docker build -f server/Dockerfile -t graphgenie-gremlin .
docker run -d --name gremlin -p 8182:8182 graphgenie-gremlin
docker logs -f gremlin   # chờ "Loaded vertices: ..." và "Channel started at port 8182"
```
Khi đổi dữ liệu: chạy lại bước 2, rồi `docker rm -f gremlin` và build/run lại.

Dockerfile dựng Gremlin Server từ `eclipse-temurin:8-jre` (đa kiến trúc) thay vì image `tinkerpop/gremlin-server`
vì image chính thức chỉ có amd64: trên Mac Apple Silicon phải chạy giả lập, chậm hơn ~2 lần (median 4.5s so với 0.8s/query).

**4. Kiểm tra kết nối và schema**
```bash
../.venv/bin/python tools/check_connection.py
../.venv/bin/python gremlin_schema_scanner.py
```

**5. Chạy GraphGenie**
```bash
../.venv/bin/python main_tinkerpop.py
```
Vòng lặp test chạy vô hạn (giống bản Neo4j), dừng bằng `Ctrl+C`. Kết quả nằm ở `logs/testing.log`, `logs/bug.log`, `logs/exception.log`.
Thư viện gremlinpython in stack trace của server ra màn hình mỗi khi query lỗi, có thể bỏ qua vì lỗi đã được ghi vào `exception.log`.

## Cách thực thi mỗi query (tránh treo)

`CypherOpProcessor` của plugin **không áp dụng `evaluationTimeout`**: một query nặng (ví dụ
`MATCH (a)-[]->(b:Genre)-[*0..1]-(b:Genre) ...`) có thể chạy mãi, làm GraphGenie đứng ở dòng `node num: ... tested vectors: ...`.
Vì vậy `main_tinkerpop.py` chạy mỗi query qua 2 bước:

1. Gửi `EXPLAIN <cypher>` tới processor `cypher` → nhận câu Gremlin đã dịch (không thực thi).
2. Gửi câu Gremlin qua processor chuẩn → server dừng query sau 30s (lỗi 598, không ghi vào `exception.log`, giống timeout của Neo4j).

`Query Time` chỉ tính bước 2. Nếu server từng bị treo bởi query cũ: `docker restart gremlin`.

## Khác biệt so với Neo4j cần lưu ý khi phân tích

- **Label:** node Neo4j nhiều label (`Person:Actor`) chỉ giữ 1 label theo `LABEL_PRIORITY` trong `tools/neo4j_to_graphml.py`.
  Với recommendations-50, mọi `Person` đều là Actor/Director nên label `Person` biến mất; 487 node `Actor:Director:Person` thành `Actor`.
  Kết quả: Actor 15443, Director 3604, Movie 9125, User 671, Genre 20 (tổng 28863 node, 166261 cạnh, khớp Neo4j).
- **Property:** kiểu list/date được chuyển thành chuỗi.
- **ID:** đánh số lại 1..N (TinkerGraph mặc định yêu cầu id kiểu Long).
- **Luật biến đổi:** với `graphdb != neo4j`, code gốc tự bỏ luật `CALL {}` wrapper và dùng luật `count(*)`, không dùng ma trận kết nối khi sinh query.
- **Thời gian truy vấn** đo phía client (gồm độ trễ mạng), không so trực tiếp với số liệu Neo4j.

## Hiệu năng trên dữ liệu thật (recommendations-50)

- Thời gian mỗi query: median ~0.8s, max ~4.5s (timeout server 30s).
- Mỗi base query sinh ~30 query biến đổi → khoảng **2 base query / phút** (~120/giờ).
  Tốc độ mỗi query gần ngang các lần chạy Neo4j trước đó (median 325–1200ms, thời gian đo phía server).
- Chương trình không tự dừng (`max_testing_query_num` không được code gốc dùng). Để có số mẫu ngang các lần chạy Neo4j
  (~215 base query, ~7000 query) cần chạy **khoảng 2 giờ**:
  `caffeinate -i ../.venv/bin/python main_tinkerpop.py > logs/stdout.txt 2>&1 & P=$!; sleep 7200; kill $P`

## Kết quả chạy thử (đồ thị mẫu 3 node, 25 giây)

- 50 base query, ~1430 equivalent, ~144 restricted query.
- `exception.log`: lỗi `java.lang.String cannot be cast to ...Element` lặp lại, là lỗi dịch của cypher-for-gremlin.
- `bug.log`: cặp `RETURN DISTINCT count(x)` (0) và `RETURN count(*)` (1) trên `OPTIONAL MATCH` không khớp gì.
  Đây là **báo động giả do luật `count(*)`**: theo ngữ nghĩa Cypher, `OPTIONAL MATCH` không khớp vẫn trả về 1 dòng null,
  nên `count(*) = 1` và `count(x) = 0` là đúng. Cần lọc các trường hợp này khi phân loại bug.
