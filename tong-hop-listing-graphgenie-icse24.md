# Tổng hợp và phân loại các câu truy vấn trong GraphGenie — ICSE 2024

Tài liệu này tổng hợp và phân loại toàn bộ câu truy vấn trong các **Listing 1–10** của bài báo *Detecting Logic Bugs in Graph Database Management Systems via Injective and Surjective Graph Query Transformation*. Các truy vấn minh họa riêng trong Table 1 không được tính vào danh sách này.

## 1. Quy ước

- `Q`: truy vấn gốc.
- `Q′`: truy vấn biến đổi (follow-up query).
- **Equivalent**: kỳ vọng `Result(Q′) = Result(Q)`.
- **Variant**: kỳ vọng kết quả của hai truy vấn có quan hệ tập con hoặc tập cha.
- **Performance**: so sánh thời gian thực thi thay vì kết quả truy vấn.

## 2. Tổng hợp theo từng Listing

| Listing | Truy vấn và biến đổi chính | Quy tắc/lớp | Quan hệ kỳ vọng | Kết quả và phân loại |
|---|---|---|---|---|
| **1** | `Q: MATCH (s1:B)-[*1..2]-(s3:A) RETURN count(s1)`; `Q′`: đảo thứ tự hai đầu thành `(s3:A)…(s1:B)` | **SymmetricPattern**, Structure-GQT | Tương đương | RedisGraph trả `204` và `238` → **logic bug** |
| **2** | Hai cặp truy vấn: đường đi hai cạnh `(a)-[]-(b)-[]-(c)` được rút thành `(a)-[]-(b)`; một cặp dùng `count(a)`, cặp còn lại dùng `count(DISTINCT a)` | **InducedSubgraph**, Structure-GQT | Variant | Không trình bày bug; minh họa rằng cùng biến đổi mẫu đồ thị nhưng `RETURN` khác nhau có thể làm đổi chiều quan hệ tập con/tập cha |
| **3** | `count((a))` được biến đổi thành `count(id(a))` trên cùng mẫu `()-[a]-()` | **CountIdProperty**, Property-GQT | Tương đương | RedisGraph trả `20.000` và `39.993` → **logic bug đếm cạnh** |
| **4** | `MATCH (a:A)-[*1..2]-(b:B)` được đảo thành `(b:B)-[*1..2]-(a:A)` | **SymmetricPattern**, Structure-GQT | Tương đương | `204` và `238` → **logic bug RedisGraph**; thực chất là cùng trường hợp với Listing 1 |
| **5** | Đổi biến của đường đi vòng từ `n` sang `a`; đồng thời có tổ hợp `SKIP/LIMIT` | **RenameVariables**, Non-GQT | Truy vấn tương đương về mẫu | Q chạy được, Q′ phát sinh exception → **Neo4j internal error**, liên quan toán tử `Expand(Into)` |
| **6** | Chuyển kiểu cạnh `s0:DIRECTED` từ G-Pattern sang `WHERE s0:DIRECTED` | **MoveLabelPredicate**, Property-GQT | Tương đương | Neo4j trả `43` và `491` → **logic bug xử lý kiểu cạnh/predicate** |
| **7** | `MATCH (a)-[*1..1]->(b)` được phân tách thành `MATCH (a),(a)-[*1..1]->(b)` | **PatternPartition**, Structure-GQT | Tương đương | Q trả `100`, Q′ báo `column "a" does not exist` → bài báo xếp là **AgensGraph logic/parsing bug** |
| **8** | Q vòng `(a)-[]-(a)`; ba truy vấn TLP dùng `p`, `NOT p`, `p IS NULL`; GraphGenie mở vòng thành `(a)-[]-(b) WHERE a=b` | **UnfoldCyclicPattern**, Structure-GQT | Tương đương | TLP thấy `200 = 200+0+0` nên bỏ sót; GraphGenie thấy `200 ≠ 16` → **logic bug mà GDBMeter bỏ sót** |
| **9** | Truy vấn đường đi dài được bọc thành `CALL { Q } RETURN X` | **AddCallWrapper**, Non-GQT | Quan hệ hiệu năng | Q mất `4.642.011 ms`, Q′ mất `5.984 ms` → Q′ nhanh hơn khoảng **776 lần**, phát hiện **Neo4j performance bug** |
| **10** | Truy vấn có `ORDER BY … SKIP … LIMIT` được đặt trong `OPTIONAL {Q}` | Wrapper/Non-GQT | Quan hệ hiệu năng | Q mất `100 ms`, Q′ mất `201.384 ms` → chậm hơn khoảng **2.014 lần**, do kế hoạch truy vấn xấu khi kết hợp `ORDER BY` và `OPTIONAL` |

## 3. Phân loại theo loại phép biến đổi

### 3.1. Structure-GQT — biến đổi cấu trúc G-Pattern

- Listing 1 và 4: `SymmetricPattern`.
- Listing 2: `InducedSubgraph`.
- Listing 7: `PatternPartition`.
- Listing 8: `UnfoldCyclicPattern`.

Đây là nhóm kiểm thử trực tiếp cấu trúc node–edge của truy vấn đồ thị.

### 3.2. Property-GQT — biến đổi label, type hoặc property

- Listing 3: `CountIdProperty`.
- Listing 6: `MoveLabelPredicate`.

Nhóm này giữ cấu trúc tổng quát nhưng thay đổi cách biểu diễn thuộc tính hoặc kiểu cạnh.

### 3.3. Non-GQT — không trực tiếp thay đổi G-Pattern

- Listing 5: `RenameVariables`.
- Listing 9: `AddCallWrapper`.
- Listing 10: bọc truy vấn bằng `OPTIONAL`.

Nhóm này chủ yếu kiểm thử trình phân tích, lập kế hoạch và cơ chế thực thi truy vấn.

## 4. Phân loại theo loại vấn đề

| Loại | Listing |
|---|---|
| Minh họa phương pháp, không báo cáo bug | **2** |
| Logic bug – kết quả sai | **1, 3, 4, 6, 7, 8** |
| Internal/server error | **5** |
| Performance issue | **9, 10** |

## 5. Nhận xét tổng hợp

- Listing 1 và Listing 4 là hai cách trình bày của cùng một lỗi RedisGraph. Vì vậy, có **6 listing logic bug nhưng chỉ 5 trường hợp khác nhau**.
- Listing 7 trả về lỗi thực thi, nhưng bài báo vẫn gọi đây là logic bug của AgensGraph liên quan việc phân tích variable-length expression.
- Tổng cộng các Listing 1–10 trình bày **25 câu truy vấn**; Listing 2 có bốn truy vấn và Listing 8 có năm truy vấn.
- Tất cả truy vấn trong các listing đều được biểu diễn bằng **Cypher**, dù GraphGenie còn hỗ trợ Gremlin thông qua cơ chế chuyển đổi.
- Các listing cho thấy GraphGenie không chỉ phát hiện sai lệch kết quả mà còn tìm được lỗi nội bộ và vấn đề hiệu năng của GDBMS.

## 6. Nguồn tham khảo

1. Yuancheng Jiang, Jiahao Liu, Jinsheng Ba, Roland H.C. Yap, Zhenkai Liang, Manuel Rigger. *Detecting Logic Bugs in Graph Database Management Systems via Injective and Surjective Graph Query Transformation*. ICSE 2024. [Bản PDF](https://yuanchengjiang.github.io/docs/GraphGenie-ICSE24.pdf).
2. [DOI: 10.1145/3597503.3623307](https://doi.org/10.1145/3597503.3623307).
3. [ICSE 2024 Research Track](https://conf.researchr.org/details/icse-2024/icse-2024-research-track/20/Detecting-Logic-Bugs-in-Graph-Database-Management-Systems-via-Injective-and-Surjectiv).
