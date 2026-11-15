# Bộ case lỗi từ bài báo GraphGenie (ICSE'24): Neo4j và TinkerPop

Mỗi file JSON chứa **một loại lỗi**, kèm câu truy vấn Cypher để tự kiểm chứng.
`run_bug_cases.py` đọc file JSON, chạy trên một server và kết luận lỗi có xuất hiện trên phiên bản đó hay không.
Script tự chọn cách kết nối theo trường `"dbms"` của file (`neo4j` hoặc `tinkerpop`).

```
bug_cases/
├── run_bug_cases.py
├── neo4j/
│   ├── logic_bugs.json          lỗi logic (Bảng 3)         oracle: kết quả hai câu phải bằng nhau
│   ├── internal_errors.json     lỗi nội bộ (Bảng 3)        oracle: truy vấn hợp lệ không được báo lỗi
│   └── performance_issues.json  hiệu năng (Listing 9, 10)  oracle: hai câu tương đương không chênh quá 5 lần
├── tinkerpop/
│   ├── logic_bugs.json          lỗi logic của bộ dịch cypher-for-gremlin
│   ├── internal_errors.json     ClassCastException của bộ dịch
│   ├── performance_issues.json  cặp đối xứng chênh hàng nghìn lần
│   └── false_positives.json     báo động giả của GraphGenie (luật count(*))
└── results/                     kết quả mỗi lần chạy (JSON)
```

## Danh sách case Neo4j

| ID | Issue | Loại | Luật GQT | Phiên bản lỗi | Dataset | Nguồn |
|---|---|---|---|---|---|---|
| NEO4J-L1 | #12991 | logic | MoveLabelPredicate | 5.1.0 (sửa ở 5.2) | recommendations | Listing 6, Bug 4 |
| NEO4J-L2 | #12996 | logic | CountOtherName | 5.1.0 | recommendations | artifact |
| NEO4J-I1 | #12968 | internal | RenameVariables | 4.4.12 | POLE | Listing 5, Bug 3 |
| NEO4J-I2 | #12988 | internal | – | 5.1.0 | recommendations | artifact |
| NEO4J-I3 | #13041 | internal | RedundantPredicate | 5.4.0 | cybersecurity | issue gốc |
| NEO4J-I3b | #13041 | internal | RedundantPredicate | 5.4.0 | recommendations | artifact (biến thể) |
| NEO4J-P1 | #12973 | hiệu năng | AddCallWrapper | 4.4.12 (sửa ở 5.4) | POLE | Listing 9 |
| NEO4J-P2 | #13034 | hiệu năng | thêm OPTIONAL | 5.4.0 | cybersecurity | Listing 10 |

Mỗi case có: `issue`, `url`, `cause` (nguyên nhân gốc theo bài báo), `gqt_rule`, `affected_version`, `fixed_version`/`fix_note`
(trích lời nhà phát triển trên GitHub), `dataset`, `base_query`, `mutated_query`, `paper_result`, `explanation`.

## Danh sách case TinkerPop

Bài báo (Bảng 3) chỉ ghi "Gremlin-DBs: 6 lỗi logic chưa xác nhận" mà **không công bố câu truy vấn**; chú thích 10 nói
plugin cypher-for-gremlin có thể dịch sai. Các case dưới đây do đồ án tự tìm bằng GraphGenie (`tinkerpop/logs/`),
rồi rút gọn và đối chiếu với Neo4j. Môi trường: Gremlin Server 3.4.13 + cypher-for-gremlin 1.0.4, TinkerGraph nạp recommendations
(xem `tinkerpop/README.md`).

| ID | Loại | Luật GQT | Nguyên nhân | Nguồn |
|---|---|---|---|---|
| TP-L1 | logic | SymmetricPattern | Bộ dịch đặt `emit()` sai chỗ khi `[*1..1]` đứng trước `[*0..1]`, mỗi đường đi bị đếm 2 lần | bug.log (nguyên văn) |
| TP-L1b | logic | SymmetricPattern | Như TP-L1, bản rút gọn | rút gọn |
| TP-I1 | internal | RedundantPredicate | OPTIONAL MATCH không khớp + `WITH *` + `id()`: id() áp lên hằng chuỗi `'  cypher.null'` | rút gọn từ 252 câu lỗi |
| TP-I2 | internal | RedundantPredicate | Như TP-I1 (thông báo "String cannot be cast to Element") | exception.log (nguyên văn) |
| TP-P1 | hiệu năng | SymmetricPattern | Bộ dịch duyệt từ nút viết đầu tiên: bắt đầu từ `()` quét 28863 đỉnh, từ `(:User)` chỉ 671 | testing.log |
| TP-P2 | hiệu năng | SymmetricPattern | Như TP-P1, có đường đi `[*1..1]`, xuất phát từ `(:Genre)` | testing.log |
| TP-F1 | báo động giả | count(*) | OPTIONAL MATCH không khớp: `count(x)`=0, `count(*)`=1 là đúng ngữ nghĩa | bug.log (67/68 cặp) |

## Cách chạy

```bash
# Neo4j: một file
python bug_cases/run_bug_cases.py bug_cases/neo4j/logic_bugs.json --uri bolt://127.0.0.1:17687

# Neo4j: nhiều file, chỉ một vài case
python bug_cases/run_bug_cases.py bug_cases/neo4j/*.json --uri bolt://127.0.0.1:7687 --id NEO4J-L1 NEO4J-I2

# TinkerPop (mặc định ws://127.0.0.1:8182/gremlin), đối chiếu với Neo4j Desktop, đo hiệu năng 3 lần lấy trung vị
python bug_cases/run_bug_cases.py bug_cases/tinkerpop/*.json --reference-uri bolt://127.0.0.1:7687 --repeat 3 --perf-timeout 120

# tuỳ chọn khác: --user neo4j --password 12344321 --timeout 120 --out bug_cases/results
```

- `--reference-uri`: chạy cùng câu truy vấn trên một Neo4j để làm đáp án tham khảo (in `[đối chiếu: ...]`).
  Cần cho case báo động giả: chỉ kết luận FALSE POSITIVE khi hệ đối chiếu cũng trả kết quả y hệt.
- `--repeat N`: đo mỗi câu hiệu năng N lần, lấy trung vị (lần chạy đầu của Neo4j còn tốn thời gian biên dịch câu truy vấn).
- Với TinkerPop, kết quả lưu thêm câu Gremlin đã dịch (`base.gremlin`, `mutated.gremlin`) để phân tích nguyên nhân.

Kết luận cho từng case:

| Kết luận | Ý nghĩa |
|---|---|
| `BUG REPRODUCED` | Oracle bị vi phạm: lỗi xuất hiện trên phiên bản này |
| `NOT REPRODUCED` | Oracle thoả: không có lỗi (đã sửa hoặc phiên bản không bị ảnh hưởng) |
| `FALSE POSITIVE` | Case báo động giả: kết quả khác nhau nhưng đúng ngữ nghĩa (hệ đối chiếu cũng trả y hệt) |
| `SKIPPED` | Server không chứa dataset case cần (nhận diện qua nhãn: Movie/User/Genre, PostCode/Crime, Computer/Domain/HighValue) |
| `INCONCLUSIVE` | Case hiệu năng: cả hai câu đều vượt timeout hoặc vượt giới hạn bộ nhớ giao dịch của server |
| `ERROR` | Không đánh giá được (ví dụ câu của case logic bị lỗi) |

Case hiệu năng chạy câu dự kiến nhanh trước. Nếu câu chậm bị timeout thì tỉ lệ ghi là cận dưới (`≥`),
nên `--perf-timeout 120` đã đủ kết luận cho cả hai case trên phiên bản lỗi.

## Server cần có

**Cách nhanh nhất: GraphGenieLab (Neo4j Desktop 2026.09 enterprise, cổng 7687)** chứa đủ 3 dataset trong 3 database:
`neo4j` (recommendations), `pole`, `cybersecurity`. Script tự chọn database trùng tên với dataset của case
(không có thì dùng database mặc định; `--database` để ép một database), nên một lệnh chạy được cả 8 case:

```bash
python bug_cases/run_bug_cases.py bug_cases/neo4j/*.json --uri bolt://127.0.0.1:7687 --perf-timeout 120 --repeat 3
```

Cách thêm database vào một Neo4j Enterprise (DBMS vẫn chạy, database `neo4j` không bị ảnh hưởng):
`CREATE DATABASE pole` → `STOP DATABASE pole` → `bin/neo4j-admin database load pole --from-stdin --overwrite-destination=true < pole-50.dump`
→ `START DATABASE pole` (dump trong `paper_bugs/downloads/`).

Các phiên bản cũ (để tái hiện lỗi) dựng bằng `bash paper_bugs/setup_servers.sh` (Docker). Mỗi server Neo4j Community chỉ chứa một dataset.

| Server | Cổng | Dataset | Dùng cho |
|---|---|---|---|
| neo4j 5.1.0 | 17687 | recommendations | L1, L2, I2, I3b |
| neo4j 5.4.0 | 27687 | recommendations | L1, L2, I2, I3b |
| neo4j 5.4.0 | 28687 | cybersecurity | I3, P2 |
| neo4j 4.4.12 | 37687 | POLE | I1, P1 |
| Neo4j Desktop 2026.09 (GraphGenieLab) | 7687 | recommendations, pole, cybersecurity | kiểm tra hồi quy, cả 8 case |
| neo4j latest (2026.10.1) | 48687 / 49687 | POLE / cybersecurity | kiểm tra hồi quy |

Nếu container Neo4j bị kill (exit 137) thì khi `docker start` lại sẽ báo "Neo4j is already running".
Khi đó xoá container và tạo lại trên cùng volume (dữ liệu không mất), ví dụ:
`docker rm -f neo4j-5-4-0 && docker run -d --name neo4j-5-4-0 -p 27687:7687 -v neo4j-5-4-0-data:/data -e NEO4J_AUTH=neo4j/12344321 neo4j:5.4.0-community`

## Kết quả kiểm chứng Neo4j (10/11/2026)

| Case | 4.4.12 | 5.1.0 | 5.4.0 | Mới nhất (2026.09 / 2026.10) |
|---|---|---|---|---|
| L1 #12991 | – | **BUG** 43 ≠ 491 (khớp bài báo) | không lỗi (491) | không lỗi |
| L2 #12996 | – | **BUG** None ≠ 100004 | **BUG** None ≠ 100004 | không lỗi |
| I1 #12968 | **BUG** câu đổi tên lỗi ExecutionFailed | – | – | không lỗi |
| I2 #12988 | – | **BUG** ExecutionFailed | **BUG** ExecutionFailed | không lỗi |
| I3 #13041 | – | – | **BUG** arraycopy out of bounds | không lỗi |
| I3b #13041 | – | **BUG** arraycopy out of bounds | **BUG** arraycopy out of bounds | không lỗi |
| P1 #12973 | **BUG** ≥ 120s so với 5,7s (≥ 21x) | – | – | INCONCLUSIVE: cả hai câu > 120s (2026.10), cả hai vượt giới hạn bộ nhớ 716,8 MiB (GraphGenieLab) |
| P2 #13034 | – | – | **BUG** 0,47s so với 118s (254x) | không lỗi (1,8x) |

Nhận xét:
- Tất cả 8 case đều tái hiện được trên phiên bản lỗi mà issue báo cáo.
- #12996 và #12988 vẫn còn trên 5.4.0 dù issue đã đóng tháng 1/2023, tức là bản sửa chỉ có từ phiên bản sau 5.4.0.
- #12991 không còn trên 5.4.0, đúng với xác nhận "fixed in 5.2" của nhà phát triển.
- P1 trên bản mới nhất: khoảng chênh lệch không còn đo được, nhưng câu bọc `CALL {}` (5,7s trên 4.4.12) cũng chạy quá 120s
  (Docker 2026.10) và vượt giới hạn bộ nhớ giao dịch 716,8 MiB sau khoảng 2s (GraphGenieLab, heap 1 GiB): hai câu nặng như nhau.
  Muốn đo được cần tăng `dbms.memory.transaction.total.max` và heap trong cài đặt của DBMS, rồi chạy lại với `--perf-timeout 900`.
- Kiểm chứng đầy đủ 8 case trên GraphGenieLab (10/11/2026): 7 NOT REPRODUCED, P1 INCONCLUSIVE.
- Mỗi lần chạy lưu một file trong `results/neo4j_<phiên bản>_<thời điểm>.json`.

## Kết quả kiểm chứng TinkerPop (10/11/2026)

Server: TinkerPop 3.4.13 + cypher-for-gremlin 1.0.4. Đối chiếu: Neo4j Desktop 2026.09. Đo hiệu năng 3 lần, lấy trung vị.

| Case | TinkerPop | Neo4j (đối chiếu) | Kết luận |
|---|---|---|---|
| TP-L1 | 265517 ≠ **531034** | 265517 = 265517 | BUG REPRODUCED |
| TP-L1b | 265517 ≠ **531034** | 265517 = 265517 | BUG REPRODUCED |
| TP-I1 | base = 0, mutated **ClassCastException** | 0 / 0 | BUG REPRODUCED |
| TP-I2 | **ClassCastException** | 0 | BUG REPRODUCED |
| TP-P1 | 9592ms so với 4ms (**2284x**) | cả hai < 120ms | BUG REPRODUCED |
| TP-P2 | 23611ms so với 4ms (**6214x**) | cả hai < 40ms | BUG REPRODUCED |
| TP-F1 | 0 ≠ 1 | 0 ≠ 1 (giống hệt) | FALSE POSITIVE |

Nhận xét:
- Cả 3 loại lỗi (logic, nội bộ, hiệu năng) đều nằm ở **bộ dịch cypher-for-gremlin**, không phải TinkerGraph:
  Gremlin viết tay tương đương cho kết quả đúng (TP-L1) và Neo4j chạy được tất cả câu.
- TP-I2: thông báo chi tiết chỉ có ở vài lần lỗi đầu; sau đó JVM bỏ thông báo nên log ghi `java.lang.ClassCastException`.
  302 lỗi chung và 14 lỗi chi tiết trong `exception.log` là cùng một lỗi.
- Đúng như cảnh báo của bài báo (chú thích 10): kiểm thử TinkerPop qua bộ dịch dễ cho ra lỗi của chính bộ dịch và báo động giả.
