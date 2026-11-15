# Bộ câu hỏi và trả lời dự kiến

**Đề tài:** Kiểm chứng lỗi trong bài báo GraphGenie (ICSE 2024) trên Neo4j và TinkerPop

> **Cách dùng:** đọc kỹ các câu đánh dấu ⭐ (gần như chắc chắn bị hỏi).
> Khi trả lời, theo đúng thứ tự: **trả lời thẳng → đưa bằng chứng (một con số) → dừng lại.**

---

## Mục lục

| Nhóm | Chủ đề | Câu |
|---|---|---|
| A | Bài báo và phương pháp | 1 – 5 |
| B | Cách kiểm chứng | 6 – 10 |
| C | TinkerPop | 11 – 13 |
| D | Báo động giả | 14 – 15 |
| E | Hạn chế và độ tin cậy số liệu | 16 – 18 |
| F | Đóng góp của nhóm | 19 – 20 |
| G | Kiến thức nền: ngôn ngữ truy vấn, kiểm thử biến hình | 21 – 25 |
| H | Giải thích chi tiết từng lỗi | 26 – 30 |
| I | Số liệu, thước đo và bằng chứng | 31 – 36 |
| | Bảng số liệu tra nhanh, mẹo trả lời | cuối tệp |

---

## A. Bài báo và phương pháp

### ⭐ Câu 1. Ý tưởng chính của bài báo là gì?

Lỗi logic khó phát hiện vì **không biết đáp án đúng**.

GraphGenie biến đổi mẫu đồ thị của truy vấn Q thành Q' có **quan hệ kết quả biết trước** (bằng nhau, lớn hơn hoặc nhỏ hơn).
Nếu kết quả thực tế vi phạm quan hệ đó thì hệ quản trị có lỗi.

Đây là kiểm thử biến hình, áp dụng lên **cấu trúc mẫu đồ thị** chứ không chỉ lên điều kiện lọc.

---

### ⭐ Câu 2. "Đơn ánh" và "toàn ánh" trong tên bài báo nghĩa là gì?

Đó là cách bài báo xác định quan hệ giữa kết quả của Q và Q' dựa trên ánh xạ giữa hai mẫu đồ thị:

| Loại ánh xạ giữa hai mẫu | Quan hệ kết quả phải thoả |
|---|---|
| **Song ánh** (vừa đơn ánh vừa toàn ánh) | Hai mẫu tương đương → kết quả **bằng nhau** |
| Chỉ **đơn ánh** hoặc chỉ **toàn ánh** | Kết quả câu này **chứa hoặc được chứa** trong câu kia (ví dụ: thêm điều kiện thì kết quả không được nhiều hơn) |

Nhóm tập trung kiểm chứng loại **"bằng nhau"** vì đây là loại tìm ra các lỗi được báo cáo.

---

### Câu 3. GraphGenie khác gì GDBMeter và Grand?

| Công cụ | Cách làm | Hạn chế |
|---|---|---|
| **GDBMeter** | Chia điều kiện lọc thành đúng / sai / null | Không biến đổi mẫu đồ thị |
| **Grand** | Chạy cùng truy vấn trên nhiều hệ rồi so sánh | Dễ báo nhầm khi các hệ có ngữ nghĩa khác nhau: hơn 80% trong 30 cảnh báo lấy mẫu là giả |
| **GraphGenie** | Biến đổi chính mẫu đồ thị trên **cùng một hệ** | – |

Trong 24 giờ, GraphGenie tìm được **42.609** trường hợp nghi lỗi (sau khi lọc trùng), so với **151** của GDBMeter.

---

### Câu 4. Bài báo tìm được bao nhiêu lỗi?

**19 lỗi chưa từng biết** (Bảng 3 của bài báo):

| Hệ quản trị | Số lỗi |
|---|---|
| Neo4j | 5 |
| RedisGraph | 5 |
| AgensGraph | 3 |
| Các hệ Gremlin | 6 |

Trong đó **9 đã sửa** và **3 được xác nhận**. Ngoài ra có **6 vấn đề hiệu năng** trên Neo4j (Bảng 4).

---

### Câu 5. Các luật biến đổi gồm những nhóm nào?

| Nhóm luật | Ví dụ |
|---|---|
| Biến đổi cấu trúc mẫu | Đảo chiều đường đi, tách mẫu, mở chu trình |
| Biến đổi thuộc tính và nhãn | Chuyển nhãn vào WHERE, đổi biểu thức trong `count` |
| Biến đổi không thuộc mẫu | Thêm điều kiện luôn đúng, đổi tên biến, bọc trong `CALL {}` |

Trong kết quả của nhóm, **cả 3 nhóm luật đều tìm ra lỗi**.

---

## B. Cách kiểm chứng

### ⭐ Câu 6. Làm sao biết kết quả nào là đúng?

**Không cần biết.** Hai câu tương đương mà khác kết quả thì chắc chắn có ít nhất một câu sai.

Khi cần biết đáp án đúng, nhóm dùng **Neo4j phiên bản mới làm đối chứng**.
Ví dụ #12991: bản mới trả **491** cho cả hai câu, vậy 43 là sai.

---

### ⭐ Câu 7. Lỗi đã được sửa rồi thì kiểm chứng để làm gì?

1. **Chứng minh số liệu của bài báo là thật và tái lập được.** Nhóm ra 43 và 491, khớp chính xác bài báo.
2. **Phát hiện điều bài báo không nói:** lỗi #12996 và #12988 **vẫn còn trên 5.4.0** dù báo cáo lỗi đã đóng từ tháng 1/2023.
3. **Trên TinkerPop**, các lỗi nhóm tìm được **vẫn còn ở thời điểm hiện tại**.

---

### Câu 8. Làm sao đảm bảo chạy đúng phiên bản và đúng dữ liệu như bài báo?

- **Phiên bản:** lấy đúng phiên bản ghi trong từng báo cáo lỗi trên GitHub, chạy trong Docker (4.4.12, 5.1.0, 5.4.0).
- **Dữ liệu:** dùng đúng bộ dữ liệu của báo cáo lỗi (recommendations, POLE, cybersecurity). Bộ cybersecurity có **953 nút**, khớp số bài báo ghi.
- **Kiểm tra tự động:** chương trình kiểm tra bộ dữ liệu trước khi chạy; sai bộ dữ liệu thì **bỏ qua** chứ không kết luận.

---

### Câu 9. Kết quả có tái lập được không? Người khác kiểm tra thế nào?

Có. Mỗi ca được ghi trong tệp JSON kèm nguồn (vị trí trong bài báo, báo cáo lỗi nào).
Chỉ cần **một lệnh** là chạy lại được, và mỗi lần chạy đều lưu kết quả kèm phiên bản và thời điểm:

```bash
python bug_cases/run_bug_cases.py bug_cases/neo4j/*.json
```

Nhóm có thể chạy minh hoạ ngay tại chỗ.

---

### Câu 10. Bài báo có 19 lỗi, sao nhóm chỉ kiểm 8 ca Neo4j?

Bộ ca chính tập trung vào Neo4j theo phạm vi đồ án: 7 lỗi bài báo nêu, cộng 1 biến thể.
Ngoài bộ ca này, nhóm đã tái hiện thêm **6/6 lỗi** của RedisGraph và AgensGraph. Hai phát hiện đáng chú ý:

| Hệ | Phát hiện |
|---|---|
| **FalkorDB** (hệ kế thừa RedisGraph) | **Vẫn còn** lỗi #2744: đếm ra 50, đáp án đúng là 90 |
| **AgensGraph** v2.14.1 (bản mới nhất) | **Vẫn còn** lỗi #609, dù báo cáo lỗi đã đóng năm 2025 |

---

## C. TinkerPop

### ⭐ Câu 11. Lỗi TinkerPop là lỗi của bộ dịch chứ đâu phải của TinkerPop?

**Đúng, và nhóm nói rõ điều này.**

- **Bằng chứng:** viết tay câu Gremlin tương đương thì kết quả đúng.
- **Bài báo cũng thừa nhận:** 6 lỗi Gremlin được xếp vào nhóm "chưa xác nhận" vì bộ dịch có thể dịch sai.
- **Ý nghĩa thực tế:** người dùng truy vấn TinkerPop bằng Cypher sẽ nhận kết quả sai, nên đây vẫn là lỗi thật.

---

### ⭐ Câu 12. Vì sao kết quả bị gấp đôi?

```
Q : MATCH (g:Genre)<-[*0..1]-(h)<-[*1..1]-(u:User) RETURN count(h)   → 265517
Q': MATCH (u:User)-[*1..1]->(h)-[*0..1]->(g:Genre) RETURN count(h)   → 531034  (sai)
```

Bộ dịch sinh câu Gremlin có lệnh `emit()` dành cho đoạn đường thứ hai, nhưng lại đặt ngay sau đoạn thứ nhất.
Gremlin gắn `emit()` vào đoạn đứng trước nó, nên **mỗi đường đi bị phát ra hai lần**.

Rút gọn câu lỗi cho thấy lỗi **chỉ xảy ra khi `[*1..1]` đứng ngay trước `[*0..1]`**.

---

### Câu 13. Dữ liệu TinkerPop khác Neo4j, so sánh có công bằng không?

Số nút và cạnh **khớp tuyệt đối**: 28.863 nút và 166.261 cạnh. Chỉ khác ở chỗ mỗi đỉnh giữ một nhãn.

- Nhóm chỉ kết luận dựa trên so sánh **hai câu trên cùng một hệ**.
- Khi đối chiếu với Neo4j, chỉ dùng các ca **không bị ảnh hưởng** bởi khác biệt nhãn (Genre, User, Movie giống hệt ở hai hệ).

---

## D. Báo động giả

### ⭐ Câu 14. Báo động giả là gì? Vì sao 67/68 cảnh báo là giả?

**Báo động giả** là khi công cụ báo có lỗi nhưng hệ quản trị trả đúng.

```
Q : OPTIONAL MATCH (a:Actor)<--(g:Genre) RETURN count(g)   → 0
Q': OPTIONAL MATCH (a:Actor)<--(g:Genre) RETURN count(*)   → 1
```

GraphGenie cho rằng `count(g)` và `count(*)` tương đương. Nhưng khi `OPTIONAL MATCH` không khớp, kết quả vẫn có **một dòng chứa null**:

| Biểu thức | Cách đếm | Kết quả |
|---|---|---|
| `count(g)` | Bỏ qua null | **0** |
| `count(*)` | Đếm số dòng | **1** |

Cả hai đều đúng, **Neo4j cũng trả 0 và 1**. Lỗi nằm ở chính luật biến đổi của GraphGenie.

> Ví dụ đời thường: hỏi "bao nhiêu bạn mang ô?" và "bao nhiêu bạn đi học?". Hai con số khác nhau không có nghĩa là lớp trưởng đếm sai, mà vì hai câu hỏi vốn khác nhau.

---

### ⭐ Câu 15. Vậy GraphGenie có đáng tin không?

**Có, nhưng phải kiểm chứng.**

- Trên Neo4j, luật gây báo động giả này **không được bật**, và tác giả đã rút gọn, kiểm tra từng trường hợp trước khi báo cáo.
- Trên TinkerPop, luật này được bật nên sinh báo động giả.
- Nhóm chỉ ra đúng luật gây lỗi và đề xuất cách sửa: **không áp dụng `count(*)` cho truy vấn có `OPTIONAL MATCH`**. Đây là đóng góp cải tiến của nhóm.

---

## E. Hạn chế và độ tin cậy số liệu

### ⭐ Câu 16. Vì sao ca hiệu năng P1 chưa kết luận được?

| Môi trường | Kết quả |
|---|---|
| GraphGenieLab | Cả hai câu vượt giới hạn bộ nhớ giao dịch **716,8 MiB** sau khoảng 2 giây |
| Docker (Neo4j 2026.10) | Cả hai câu vượt **120 giây** |

Câu bọc `CALL {}` vốn chỉ mất **5,7 giây** trên bản cũ, nay cũng nặng như câu gốc, tức là **khoảng chênh lệch đã không còn**.
Muốn đo chính xác thì phải tăng bộ nhớ cho máy chủ.

---

### Câu 17. Thời gian đo trên TinkerPop gồm cả độ trễ mạng, có chính xác không?

Độ trễ mạng nội bộ chỉ vài mili giây, trong khi chênh lệch là **9,6 giây so với 4 mili giây** (hơn 2000 lần), nên không ảnh hưởng kết luận.
Nhóm còn **đo 3 lần và lấy trung vị** để loại nhiễu.

---

### Câu 18. Có lỗi nào đã gửi cho nhà phát triển chưa?

**Chưa.** Các lỗi TinkerPop là phát hiện của nhóm và chưa được báo cáo. Đây là bước tiếp theo trong hướng phát triển.

---

## F. Đóng góp của nhóm

### ⭐ Câu 19. Nhóm đóng góp gì so với bài báo?

| # | Đóng góp | Bằng chứng |
|---|---|---|
| 1 | Kiểm chứng độc lập | Tái hiện 8/8 ca Neo4j, khớp số liệu bài báo |
| 2 | Phát hiện lỗi còn tồn tại sau khi báo cáo lỗi đã đóng | Neo4j 5.4.0, FalkorDB, AgensGraph v2.14.1 |
| 3 | Phát hiện tệp tái hiện của tác giả ghi nhầm số báo cáo lỗi | Ghi #12991, đúng là #13041 |
| 4 | Mở rộng sang TinkerPop | 3 lỗi của bộ dịch, nguyên nhân giải thích tới mức câu Gremlin |
| 5 | Phát hiện báo động giả | 67/68 cảnh báo, chỉ ra luật gây lỗi và cách sửa |
| 6 | Công cụ kiểm chứng | Bộ ca JSON và chương trình chạy lại bằng một lệnh |

---

### Câu 20. Hướng phát triển tiếp theo là gì?

- Sửa luật `count(*)` của GraphGenie.
- Báo cáo lỗi bộ dịch lên kho mã cypher-for-gremlin.
- Tăng bộ nhớ máy chủ để đo lại ca P1.
- Kiểm thử Gremlin trực tiếp, không qua bộ dịch.
- Mở rộng bộ ca cho các hệ khác như Memgraph và JanusGraph.

---

## G. Kiến thức nền: ngôn ngữ truy vấn, kiểm thử biến hình

### ⭐ Câu 21. Cypher, Gremlin có phải là SQL không? Có dùng chung một ngôn ngữ không?

**Không.** Đây là ba ngôn ngữ khác nhau:

| | SQL | Cypher | Gremlin |
|---|---|---|---|
| Dùng cho | CSDL quan hệ (bảng) | CSDL đồ thị | CSDL đồ thị |
| Hệ dùng | MySQL, PostgreSQL… | Neo4j, RedisGraph, AgensGraph | TinkerPop, JanusGraph, HugeGraph |
| Cách viết | Mô tả bảng kết quả | **Vẽ mẫu đồ thị** cần tìm | **Viết từng bước duyệt** đồ thị |

Các câu trong đồ án (`MATCH … RETURN count(…)`) là **Cypher**, nên gọi là "câu truy vấn Cypher", không gọi là "câu SQL".

---

### ⭐ Câu 22. TinkerPop đang nhận câu giống Cypher mà?

Đó là nhờ **bộ dịch cypher-for-gremlin** cài thêm trên máy chủ. TinkerPop **chỉ chạy Gremlin**:
- Gửi câu Cypher thẳng cho TinkerPop thì báo lỗi cú pháp `startup failed`.
- Gửi qua bộ dịch thì chạy được; log máy chủ ghi liền hai dòng `Cypher: MATCH …` rồi `Gremlin: g.V()…`.

```
GraphGenie ──Cypher──► [bộ dịch] ──Gremlin──► TinkerPop
Neo4j:      Cypher ──────────────────────────► Neo4j (chạy trực tiếp)
```

---

### Câu 23. Vì sao dùng Neo4j làm đáp án đối chiếu cho TinkerPop?

Neo4j chạy Cypher **trực tiếp, không qua dịch**, và là hệ gốc phát triển Cypher. Cùng một câu Cypher mà Neo4j trả đúng, TinkerPop trả sai, thì câu Cypher không sai, lỗi nằm ở bước dịch. Neo4j đóng vai **"người phiên dịch chuẩn"**.

---

### ⭐ Câu 24. Kiểm thử biến hình là gì?

Bài báo định nghĩa ở **trang 11**: từ đầu vào I và kết quả O, sinh đầu vào mới I' rồi kiểm tra một **quan hệ biến hình** giữa O và O'.

Nói dễ hiểu: **không hỏi "kết quả có đúng không", mà hỏi "hai kết quả có khớp nhau như lẽ ra phải khớp không"**.

> Ví dụ: kiểm tra cái cân mà không có quả cân mẫu. Cân túi A, cân túi B, rồi cân chung. Cân chung phải bằng tổng, nếu không là cân hỏng, dù không biết túi nặng bao nhiêu.

Trong GraphGenie: Q là câu gốc, Q' là câu biến đổi; quan hệ là **=**, **≤** hoặc **≥**. Neo4j trả 43 và 491 cho hai câu phải bằng nhau, nên chắc chắn có lỗi.

**Điểm yếu:** nếu luật biến đổi không thật sự tương đương thì báo nhầm (67/68 cảnh báo trên TinkerPop); nếu hệ sai giống nhau ở cả hai câu thì bỏ sót.

---

### Câu 25. Giải thích kỹ đơn ánh, toàn ánh, song ánh trên mẫu đồ thị?

Bài báo (trang 3–4) biến mẫu đồ thị thành **tập cạnh có hướng** (cạnh vô hướng tính là 2 cạnh), coi Q là miền, Q' là đích:

| Ánh xạ tập cạnh Q → Q' | Ý nghĩa | Quan hệ kết quả | Ví dụ |
|---|---|---|---|
| **Song ánh** | Mỗi cạnh khớp đúng một cạnh, không thừa | Q' **=** Q | Đảo chiều, mở chu trình, tách mẫu |
| **Chỉ toàn ánh** | Q' chặt hơn | Q' **≤** Q | Thêm hướng cho cạnh, thêm kiểu cạnh |
| **Chỉ đơn ánh** | Q' có thêm cạnh | Q' **≥** Q | Thêm nút, thêm cạnh vào mẫu |

Lưu ý: chiều ≤ hay ≥ còn phụ thuộc phần RETURN (`count(a)` hay `count(DISTINCT a)`), xem Listing 2 trang 5.

---

## H. Giải thích chi tiết từng lỗi

### ⭐ Câu 26. Vì sao chỉ đổi tên biến mà Neo4j bị lỗi (#12968)?

Hai câu chỉ khác tên biến `n` và `a`. Dùng `EXPLAIN` trên Neo4j 4.4.12 cho thấy **kế hoạch thực thi đổi điểm xuất phát**:

| | Biến `n` | Biến `a` |
|---|---|---|
| Bước quét đầu tiên | `AllNodesScan: n` (bắt đầu từ n) | `AllNodesScan: anon_11` (bắt đầu từ nút không tên) |

Mẫu là một vòng khép kín nên nhiều điểm xuất phát có chi phí ngang nhau; tên biến ảnh hưởng lựa chọn. Kế hoạch mới đi qua **Expand(Into)** theo thứ tự khác; kết hợp `SKIP`/`LIMIT` thì rơi đúng trường hợp bài báo nói Expand(Into) xử lý sai (trang 7, Bug 3).

*Quy tắc chọn kế hoạch chính xác nằm trong mã nguồn Neo4j, nhóm chỉ quan sát được kết quả.*

---

### ⭐ Câu 27. ExecutionFailed nghĩa là gì?

Mã đầy đủ: `Neo.DatabaseError.Statement.ExecutionFailed`. Neo4j chia lỗi làm ba loại:

| Loại | Lỗi của ai |
|---|---|
| ClientError | Người dùng viết sai |
| TransientError | Tạm thời, hết tài nguyên (ví dụ hết bộ nhớ ở P1) |
| **DatabaseError** | **Chính hệ quản trị** |

Trả về `DatabaseError` nghĩa là **Neo4j tự nhận lỗi ở phía mình**. ExecutionFailed chỉ là "vỏ bọc"; nguyên nhân cụ thể nằm ở message đi kèm (I1: đóng tài nguyên, I2: kế hoạch mất `shortestPath`, I3: tràn chỉ số mảng).

---

### Câu 28. "Tràn chỉ số mảng" (#13041) là gì?

Thông báo: `arraycopy: last destination index 2 out of bounds for object array[1]`.
Bên trong Neo4j chuẩn bị **mảng 1 ô** nhưng cố chép tới **ô số 2**, giống như tủ chỉ có 1 ngăn mà cất đồ vào ngăn số 2.

Lỗi xuất hiện chỉ vì thêm điều kiện luôn đúng `id(x) >= 0.0`, nên câu hoàn toàn hợp lệ. Neo4j đã xác nhận và sửa; bản hiện tại trả 23.

---

### Câu 29. Các lỗi trên Neo4j 5.4.0 thuộc đơn ánh hay toàn ánh?

**Không loại nào, tất cả là song ánh** (hoặc không cần biến đổi):

| Ca | Luật | Mẫu đồ thị | Loại |
|---|---|---|---|
| L2 #12996 | Đổi biến trong `count` | Không đổi | Song ánh |
| I3 #13041 | Thêm điều kiện luôn đúng | Không đổi | Song ánh |
| P2 #13034 | Thêm `OPTIONAL` | Không đổi | Song ánh |
| I2 #12988 | Không có, câu gốc đã lỗi | – | Không áp dụng |

Luật không đụng mẫu, nên mỗi cạnh ánh xạ sang chính nó: vừa đơn ánh vừa toàn ánh. Khớp Bảng 1 của bài báo (loại "Equivalent").

---

### Câu 30. Vì sao TP-I1 (WITH a) chạy được mà TP-I1 (WITH \*) lỗi, dù cả hai đều có `has('~id')`?

Theo `explain()` (thứ tự bước sau khi TinkerPop tối ưu):
- `WITH a`: bước lọc null `IsStep(neq('  cypher.null'))` đứng **trước** `HasStep`, nên dòng null bị loại trước.
- `WITH *`: bộ dịch chèn `project`/`select` vào giữa, bước lọc null bị đẩy **sau** `HasStep`, nên `has()` gặp chuỗi null giả và lỗi.

---

## I. Số liệu, thước đo và bằng chứng

### ⭐ Câu 31. Bài báo tìm được bao nhiêu lỗi trên Neo4j? Ở trang nào?

| Nội dung | Trang |
|---|---|
| **5 lỗi** (2 logic + 3 nội bộ), đều đã sửa | 6, Bảng 3 |
| Giải thích chi tiết #12968 (Listing 5) và #12991 (Listing 6) | 7 |
| **6 vấn đề hiệu năng**, giải thích chi tiết #12973 (Listing 9) và #13034 (Listing 10) | 10, Bảng 4 |

Ba lỗi còn lại (#12996, #12988, #13041) **không có trong bài báo**; nhóm tìm từ mã tái hiện của tác giả và danh sách issue của tác giả trên GitHub.

---

### ⭐ Câu 32. Ca P1 nhóm đo "≥ 120 giây", bài báo có công bố không? Có thuyết phục không?

Bài báo công bố câu gốc chạy **4.642.011 ms (~77 phút)**, câu bọc `CALL {}` **5.984 ms**, chênh **776 lần** (Bảng 4, Listing 9, trang 10).

Nhóm dừng ở 120 giây vì **đã đủ kết luận**: giống chạy đua, một người về đích sau 6 giây, người kia đến giây 120 chưa về thì chắc chắn chậm hơn **ít nhất 21 lần**, vượt xa ngưỡng 5 lần. Câu bọc `CALL {}` của nhóm chạy **5,7 giây**, gần như trùng 6 giây của bài báo, chứng tỏ đúng môi trường.

---

### Câu 33. Bài báo dùng thước đo nào?

| Câu hỏi nghiên cứu | Thước đo |
|---|---|
| Tìm lỗi mới | Số lỗi theo trạng thái (Bảng 3) |
| So với Grand | Tỉ lệ báo động giả (>80% trên 30 mẫu) |
| So với GDBMeter | Số trường hợp nghi lỗi sau lọc trùng trong 24 giờ (42.609 so với 151) |
| Đóng góp từng nhóm luật | Số trường hợp nghi lỗi theo nhóm luật (Hình 7) |
| Lỗi hiệu năng | Tỉ lệ thời gian, ngưỡng 5 lần / 2 lần |

Bài báo **không đo** độ phủ mã, độ chính xác/độ phủ lỗi, hay thời gian tìm ra lỗi đầu tiên.

---

### ⭐ Câu 34. Ngưỡng 5 lần là gì? Vì sao chọn 5?

- Thời gian chạy không bao giờ bằng nhau tuyệt đối (bộ nhớ đệm, biên dịch truy vấn, nhiễu), nên cần **khoảng cho phép**.
- Câu tương đương: **câu chậm ≤ câu nhanh × 5** (Phương trình 3, trang 10). Câu biến thể dùng ngưỡng **2 lần** theo một chiều.
- Chọn 5 theo thực nghiệm, **cân bằng báo nhầm và bỏ sót**, thận trọng hơn mức 2 lần của AMOEBA. Các lỗi thật đều chênh 10 đến khoảng 1.000 lần.

Ví dụ báo nhầm nếu đo 1 lần: 117 ms so với 19 ms (6,2 lần) do lần đầu phải biên dịch; đo 3 lần lấy trung vị thì chỉ khoảng 1 lần.

Lưu ý: mã nguồn GraphGenie (`time_checking`) chỉ báo khi câu biến đổi **nhanh hơn** câu gốc và chạy trên 50 ms; chương trình của nhóm xét **cả hai chiều**, đúng Phương trình 3.

---

### ⭐ Câu 35. Làm sao tin được L2, I2 vẫn còn trên 5.4.0?

Xem `bug_cases/evidence/evidence_L2_I2_20261113-114229.log`. Chạy bằng **cypher-shell, công cụ chính thức của Neo4j**, không qua chương trình của nhóm:
1. Phiên bản: image `neo4j:5.4.0-community`, mã băm cố định, build 2023-02-09; Neo4j tự báo `5.4.0`.
2. L2: `count(a) SKIP 1` → rỗng, `count(b) SKIP 1` → **100004**.
3. I2: **log của chính máy chủ Neo4j** ghi `ERROR … ExecutionFailed`, trùng giây với lúc chạy.
4. Đối chứng trên Neo4j hiện tại: cả hai đúng.
5. GitHub: hai báo cáo lỗi đóng tháng 1/2023, trước ngày build image.

File có mã băm SHA-256 để chứng minh không bị sửa: `shasum -a 256 -c …sha256` trả `OK`.

---

### ⭐ Câu 36. Làm sao chứng minh 3 lỗi TinkerPop là do bộ dịch?

Xem `bug_cases/evidence/evidence_tinkerpop_20261113-121017.log`. **Cô lập biến**: cùng máy chủ, cùng dữ liệu, chỉ thay câu Gremlin.

| Lỗi | Bản dịch của bộ dịch | Gremlin viết đúng, cùng TinkerGraph |
|---|---|---|
| Logic | 531.034 (sai) | 265.517; **chỉ dời `times(1)`** cũng ra 265.517 |
| Nội bộ | Lỗi ép kiểu tại `HasStep` | Trả 0 bình thường |
| Hiệu năng | 10.871 ms (bắt đầu từ 28.863 đỉnh) | 10 ms (bắt đầu từ 671 đỉnh User) |

Biến duy nhất thay đổi là câu Gremlin do bộ dịch sinh ra, nên lỗi nằm ở bộ dịch.

---

## Bảng số liệu tra nhanh

| Nội dung | Số liệu |
|---|---|
| Bộ dữ liệu recommendations | 28.863 nút, 166.261 cạnh (giống nhau ở Neo4j và TinkerPop) |
| Lỗi #12991 trên Neo4j 5.1.0 | 43 so với 491 (khớp bài báo) |
| Lỗi #12996 trên 5.1.0 và 5.4.0 | Rỗng so với 100004 |
| Hiệu năng #12973 trên 4.4.12 | ≥ 120 giây so với 5,7 giây (≥ 21 lần); bài báo: 776 lần |
| Hiệu năng #13034 trên 5.4.0 | 0,47 giây so với 118 giây (254 lần); bài báo: khoảng 2000 lần |
| Lỗi logic TinkerPop | 265.517 so với 531.034 (gấp đôi) |
| Hiệu năng TinkerPop | Chênh 2.284 lần và 6.214 lần |
| Cảnh báo GraphGenie trên TinkerPop | 68 cặp nghi lỗi (67 báo động giả), 316 lỗi nội bộ (cùng một lỗi), 36 cảnh báo hiệu năng |
| GraphGenieLab | Neo4j 2026.09, 3 cơ sở dữ liệu; giới hạn bộ nhớ giao dịch 716,8 MiB |
| RedisGraph / AgensGraph | 6/6 lỗi tái hiện; FalkorDB còn #2744; AgensGraph v2.14.1 còn #609 |
| Bài báo | 19 lỗi chưa từng biết, 9 đã sửa, 3 được xác nhận; 6 vấn đề hiệu năng |

---

## Mẹo khi trả lời

1. **Không biết thì nói thẳng** *"nhóm chưa kiểm tra điểm này"*, đừng đoán.
2. **Luôn kèm một con số** (43 và 491, 8/8, 67/68): con số thuyết phục hơn lời giải thích.
3. **Câu hỏi khó** (câu 11, 15, 16): thừa nhận hạn chế trước, rồi mới nói phần nhóm đã làm được.
4. **Trả lời ngắn**, dừng lại sau khi đưa bằng chứng; nếu thầy muốn nghe thêm, thầy sẽ hỏi tiếp.
