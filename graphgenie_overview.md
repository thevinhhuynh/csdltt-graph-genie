# GraphGenie — Hiểu mục đích và cách hoạt động của dự án

Tài liệu này giải thích bằng tiếng Việt, dựa trên mã nguồn hiện có trong repository: `main.py`, `schema_scanner.py`, `query_generator.py`, `query_mutator.py` và `README.md`. Các ví dụ có nhãn `Person`, `Movie`, `ACTED_IN` chỉ dùng để minh họa; nhãn thực tế phụ thuộc dữ liệu của bạn.

## 1. Dự án này dùng để làm gì?

**GraphGenie là công cụ tự động tìm lỗi trong hệ quản trị cơ sở dữ liệu đồ thị.** Nó tạo truy vấn, biến đổi truy vấn, chạy chúng trên cơ sở dữ liệu và tìm các kết quả hoặc thời gian thực thi đáng nghi.

Ví dụ, hai truy vấn diễn đạt cùng một yêu cầu đếm nhưng trả về hai con số khác nhau. Nếu quy tắc biến đổi đúng và dữ liệu không thay đổi giữa hai lần chạy, sự khác biệt đó có thể chỉ ra lỗi xử lý truy vấn của hệ quản trị.

Trong repository này, GraphGenie chủ yếu kiểm thử **Cypher**, có các nhánh kết nối **Neo4j**, **RedisGraph** và **AgensGraph**. Nhánh Neo4j có bộ quét dữ liệu để hỗ trợ sinh truy vấn tự động; các hệ còn lại cần khai báo thông tin nhãn trong mã nguồn.

Đầu ra của một lần chạy là các truy vấn đã thử, kết quả, thời gian và những trường hợp cần điều tra. Đây là một công cụ nghiên cứu và kiểm thử: người dùng vẫn cần xác minh cảnh báo để kết luận có lỗi trong cơ sở dữ liệu.

## 2. Cơ sở dữ liệu đồ thị và Cypher là gì?

Cơ sở dữ liệu đồ thị biểu diễn dữ liệu bằng **nút**, **quan hệ giữa các nút** và **thuộc tính** của chúng. Nhãn nút giúp phân loại thực thể; kiểu quan hệ giúp diễn tả mối liên hệ.

Ví dụ, trong một đồ thị phim:

```text
(An:Person) ──ACTED_IN──▶ (Phim A:Movie)
(Bình:Person) ──ACTED_IN──▶ (Phim A:Movie)
```

Cypher là ngôn ngữ truy vấn đồ thị mà bộ sinh của dự án sử dụng. Một mẫu truy vấn minh họa:

```cypher
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
RETURN count(p)
```

`MATCH` tìm những lần khớp với mẫu người đóng phim. `p` và `m` là tên biến; `Person` và `Movie` là nhãn nút; `ACTED_IN` là kiểu quan hệ; mũi tên biểu diễn chiều quan hệ.

`count(p)` đếm số lần biến `p` có giá trị khác null trong kết quả khớp. **Nó không mặc định đếm số người khác nhau**: một người đóng nhiều phim có thể được đếm nhiều lần. Đếm người khác nhau sẽ cần `count(DISTINCT p)`.

Sự khác nhau giữa số dòng khớp, số nút khác nhau và giá trị null là lý do việc kiểm thử truy vấn đồ thị cần chú ý đến ngữ nghĩa.

## 3. Vì sao cần so sánh những truy vấn đã biến đổi?

Khi sinh một truy vấn ngẫu nhiên phức tạp, ta thường không biết trước kết quả đúng phải là bao nhiêu. Để tính đáp án chuẩn cho từng truy vấn, có thể phải viết thêm một bộ thực thi truy vấn đáng tin cậy.

GraphGenie dùng một cách khác: tạo truy vấn gốc `Q`, rồi tạo truy vấn `Q'` có quan hệ dự kiến với `Q`. Ta chưa cần biết con số đúng, nhưng biết hai kết quả **phải bằng nhau** hoặc **phải thỏa một quan hệ thứ tự**, nếu phép biến đổi đáp ứng điều kiện ngữ nghĩa của nó.

Cách này thường được gọi là **kiểm thử biến hình — metamorphic testing**. Quy tắc quan hệ giữa các kết quả đóng vai trò tiêu chí kiểm tra, thường gọi là **test oracle**.

Có thể hiểu đơn giản: thay vì hỏi “đáp án đúng là bao nhiêu?”, công cụ hỏi “hai cách viết liên quan với nhau có cho ra kết quả phù hợp với quan hệ đó không?”.

## 4. Hai nhóm truy vấn mà GraphGenie so sánh

### 4.1. Truy vấn tương đương

Nhóm này hướng đến các truy vấn có cùng kết quả với truy vấn gốc. Một phép biến đổi minh họa là chuyển nhãn từ mẫu nút sang điều kiện `WHERE`:

```cypher
// Truy vấn gốc
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
RETURN count(p)

// Cùng yêu cầu, chuyển nhãn Person vào WHERE
MATCH (p)-[:ACTED_IN]->(m:Movie)
WHERE p:Person
RETURN count(p)
```

Với cùng dữ liệu và đúng ngữ nghĩa của ví dụ, hai truy vấn này phải cho cùng kết quả. Nếu truy vấn đầu trả về 12, truy vấn sau trả về 9, công cụ có lý do ghi lại cặp truy vấn để kiểm tra.

Trong `main.py`, `result_checking()` so sánh cả kiểu dữ liệu lẫn giá trị kết quả. Nhánh ghi lỗi logic hiện còn kiểm tra chuỗi `count` trong truy vấn biến đổi. Nếu một kết quả là `None`, nó ghi thông báo `None Check` thay vì ghi một cặp lỗi logic thông thường vào `bug.log`.

### 4.2. Truy vấn bị hạn chế thêm điều kiện

Nhóm **restricted queries** bổ sung ràng buộc vào mẫu đồ thị. Trong những trường hợp áp dụng phù hợp, ràng buộc mới làm tập kết quả nhỏ đi hoặc giữ nguyên.

```cypher
// Truy vấn gốc: không yêu cầu nút p phải có nhãn Person
MATCH (p)-[:ACTED_IN]->(m:Movie)
RETURN count(p)

// Truy vấn bị hạn chế thêm nhãn Person
MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
RETURN count(p)
```

Với ví dụ này, số đếm của truy vấn thứ hai phải **nhỏ hơn hoặc bằng** truy vấn thứ nhất. Nếu kết quả gốc là 12 mà kết quả bị hạn chế là 15, đó là dấu hiệu đáng kiểm tra.

`variant = 1` bật nhóm này. `restricted_result_checking()` hiện đánh dấu khi hai kết quả đều khác `None` và kết quả restricted lớn hơn kết quả gốc.

**Các ví dụ trên minh họa quan hệ so sánh, không chứng minh mọi phép biến đổi trong bộ công cụ đều đúng với mọi truy vấn.** Các chi tiết như `OPTIONAL MATCH`, `DISTINCT`, giá trị null, đường đi và `LIMIT` có thể làm điều kiện áp dụng phức tạp hơn. Cảnh báo cần được tái hiện và kiểm tra ngữ nghĩa.

## 5. Quy trình chạy từ đầu đến cuối

```text
Đọc graphgenie.ini
        ↓
Kết nối cơ sở dữ liệu có sẵn
        ↓
Quét nhãn, thuộc tính, quan hệ kết nối — nhánh Neo4j
        ↓
Sinh truy vấn Cypher gốc Q và thực thi Q
        ↓
Sinh các truy vấn tương đương Q1, Q2, ...
Sinh thêm truy vấn restricted nếu variant được bật
        ↓
Thực thi các truy vấn biến đổi
        ↓
So sánh kết quả và kiểm tra hiệu năng khi được bật
        ↓
Ghi log, ghi trường hợp nghi ngờ, rồi lặp với truy vấn mới
```

1. **Đọc cấu hình:** địa chỉ kết nối, thông tin đăng nhập, chiến lược sinh truy vấn, phép biến đổi và đường dẫn log.
2. **Chuẩn bị dữ liệu:** cơ sở dữ liệu phải có dữ liệu đồ thị từ trước. Chương trình chính không tự nạp bộ dữ liệu.
3. **Quét dữ liệu Neo4j:** lấy nhãn nút, kiểu quan hệ, thuộc tính và ma trận cho biết có kết nối giữa các cặp nhãn theo chiều hay không.
4. **Sinh truy vấn:** chọn mẫu đường đi, tên biến, nhãn, chiều cạnh, độ dài cạnh, điều kiện và biểu thức trả về.
5. **Biến đổi:** xây dựng nhiều cách viết liên quan với truy vấn gốc để có cơ sở so sánh.
6. **Thực thi và so sánh:** kiểm tra giá trị đếm; nếu bật kiểm tra hiệu năng, kiểm tra thêm chênh lệch thời gian ở nhóm tương đương.
7. **Lưu bằng chứng:** giữ truy vấn và kết quả trong log để người dùng có thể tái hiện.

Khi bật `multi_threading`, các truy vấn tương đương của một truy vấn gốc được chạy trong các luồng riêng. Công cụ đợi nhóm luồng này kết thúc rồi mới chuyển sang truy vấn gốc tiếp theo. Các truy vấn restricted vẫn được chạy tuần tự.

## 6. Mỗi file quan trọng làm nhiệm vụ gì?

| File hoặc thư mục | Vai trò trong dự án |
| --- | --- |
| `main.py` | Điều phối toàn bộ quy trình; chọn hệ quản trị, chạy truy vấn, so sánh kết quả, đo thời gian và ghi log. |
| `schema_scanner.py` | Quét dữ liệu Neo4j để lấy nhãn, thuộc tính và thông tin kết nối phục vụ bộ sinh truy vấn. |
| `query_generator.py` | Sinh truy vấn Cypher gốc, chủ yếu là mẫu đường đi đồ thị và biểu thức đếm. |
| `query_mutator.py` | Tạo các truy vấn tương đương và restricted từ truy vấn gốc bằng các quy tắc biến đổi. |
| `graphgenie.ini` | Cấu hình mà chương trình thực sự đọc khi chạy. |
| `graphgenie_guide.ini` | Bản cấu hình có chú thích tiếng Việt, giải thích cả tham số đang hoạt động và chưa áp dụng. |
| `requirements.txt` | Khai báo phụ thuộc Python; hiện bật `neo4j==6.3.0`, còn các dòng cho hệ khác đang bị comment. |
| `data/recommendations-50.dump` | File dump dữ liệu đi kèm; chương trình chính không tự import file này. |
| `artifacts/reproducing_bugs/` | Ví dụ, script và hướng dẫn tái hiện một số lỗi được lưu cùng dự án. |
| `tests/test_query_mutator.py` | Kiểm tra hành vi sinh truy vấn của bộ biến đổi; không phải bằng chứng rằng một hệ quản trị cụ thể có lỗi. |
| `logs/` | Nơi mã khởi tạo log chuyển các file log cũ vào khi đáp ứng điều kiện. |

Để đọc mã dễ hơn, bắt đầu từ khối `if __name__ == "__main__"` và hàm `Testing.testing()` trong `main.py`, sau đó đọc bộ sinh và bộ biến đổi.

## 7. Bộ sinh truy vấn hoạt động như thế nào?

`RandomCypherGenerator` ghép truy vấn theo cấu trúc:

```text
MATCH hoặc OPTIONAL MATCH
  + mẫu đường đi đồ thị
  + điều kiện WHERE
  + RETURN hoặc RETURN DISTINCT với count(...)
  + ORDER BY, SKIP, LIMIT được chọn ngẫu nhiên
```

Bộ sinh thay đổi hướng cạnh, tên biến, nhãn nút và kiểu quan hệ. Nó cũng có thể sinh cạnh có biểu thức độ dài biến đổi, hoặc đường đi chu trình dùng cùng một tên biến ở hai đầu.

Thông tin kết nối lấy từ Neo4j giúp chọn nhãn nút tiếp theo dựa trên nhãn trước đó và chiều cạnh. Đây là thông tin hỗ trợ sinh mẫu; nó không bảo đảm mọi truy vấn được tạo đều có kết quả hoặc đều được máy chủ chấp nhận.

`_node_num` là số vị trí nút ban đầu trong mẫu đường đi. Khi liên tiếp gặp lại các mẫu nhãn đã ghi nhận đủ nhiều lần, bộ sinh tăng số vị trí nút để thử những mẫu dài hơn. Nó không tăng theo một số truy vấn cố định.

Điểm cần nhớ: **tính ngẫu nhiên chủ yếu nằm ở cấu trúc truy vấn đồ thị**, còn phần `WHERE` hiện khá đơn giản. Bộ sinh luôn tạo `WHERE`, thường là kiểm tra một biến nút khác null kết hợp `AND True`, hoặc chỉ `WHERE True`.

## 8. Bộ biến đổi truy vấn làm gì?

Trong tài liệu dự án, **GQT — Graph Query Transformation** là biến đổi truy vấn đồ thị. Mã phân loại quy tắc thành ba nhóm để thống kê:

| Nhóm trong mã | Ý nghĩa và ví dụ |
| --- | --- |
| `Structure-GQT` | Biến đổi cấu trúc mẫu đồ thị, ví dụ tách đường đi hoặc mở một chu trình thành hai đầu kèm điều kiện bằng nhau. |
| `Property-GQT` | Biến đổi liên quan đến nhãn hoặc cách sử dụng biến/thuộc tính, ví dụ chuyển nhãn nút từ mẫu sang `WHERE`. |
| `Non-GQT` | Những biến đổi khác, ví dụ thêm điều kiện dư `AND True`, đổi tên biến hoặc đổi cách viết một phần truy vấn. |

`generate_equivalent_queries()` trước tiên áp dụng một tập quy tắc. Với Cypher trên hệ khác AgensGraph, nó tiếp tục chọn một số quy tắc để biến đổi lặp cho đến khi đạt mục tiêu `mutated_query_num`.

`generate_restricted_queries()` thử thêm nhãn nút, nhãn cạnh, hướng cạnh hoặc một nút mới. Một số quy tắc chỉ áp dụng được khi truy vấn gốc có dạng phù hợp.

`graph_pattern_mutation = 0` tắt các quy tắc có kiểm tra công tắc này, nhưng không tắt toàn bộ biến đổi. Những quy tắc như thêm `AND True` vẫn có thể chạy.

## 9. Dự án tìm những loại vấn đề nào?

### 9.1. Lỗi logic tiềm ẩn

Truy vấn chạy được nhưng kết quả không tuân theo quan hệ dự kiến: hai truy vấn tương đương cho số đếm khác nhau, hoặc truy vấn restricted cho số đếm lớn hơn truy vấn gốc.

Ví dụ minh họa: `base_result = 12`, `test_result = 9` cho một cặp được kỳ vọng tương đương. Điều cần điều tra là vì sao hai kết quả lệch nhau, bao gồm cả khả năng phép biến đổi hoặc bộ so sánh chưa phù hợp.

### 9.2. Vấn đề hiệu năng tiềm ẩn

Hai truy vấn tương đương có thể có thời gian rất khác nhau. Một cách viết mất 500 ms, cách còn lại mất 80 ms; tỷ lệ là `500 / 80 = 6.25`.

Trong mã hiện tại, cảnh báo hiệu năng cho nhóm tương đương chỉ xuất hiện khi đồng thời thỏa các điều kiện:

1. `perf_issue = 1`.
2. Thời gian truy vấn gốc lớn hơn `minimum_test_ms`.
3. Tỷ lệ giữa thời gian lớn hơn và nhỏ hơn vượt `threshold`.
4. Truy vấn tương đương chạy lâu hơn 50 ms và nhanh hơn truy vấn gốc.

Đây là tiêu chí tìm trường hợp đáng nghiên cứu, không phải kết luận rằng mọi chênh lệch thời gian đều là lỗi. Tải máy chủ, cache và việc chạy đồng thời đều có thể ảnh hưởng phép đo.

### 9.3. Ngoại lệ khi thực thi

Lỗi thực thi truy vấn được ghi vào `exception.log`, nếu không bị bộ lọc thông báo timeout loại bỏ. Một lỗi có thể đến từ cú pháp không phù hợp, quyền truy cập, phiên bản máy chủ hoặc lỗi nội bộ của hệ quản trị.

Để hiểu một ví dụ lỗi nội bộ được lưu trong dự án, có thể xem [hướng dẫn tái hiện trên Neo4j 5.4.0](artifacts/reproducing_bugs/neo4j-5.4.0/README.md). Đây là trường hợp gắn với phiên bản cụ thể, không chứng minh phiên bản bạn đang chạy còn lỗi đó.

## 10. Đọc các file log như thế nào?

| File mặc định | Nội dung cần tìm |
| --- | --- |
| `testing.log` | Truy vấn gốc, truy vấn tương đương/restricted, giá trị trả về, thời gian, thống kê và cảnh báo. |
| `bug.log` | Cặp truy vấn gốc và tương đương bị ghi nhận là nghi ngờ lỗi logic, kèm giá trị kết quả và thời điểm. |
| `exception.log` | Truy vấn gây ngoại lệ và thông tin lỗi; thông báo chứa `imeout` bị bỏ qua. |

**Theo mã hiện tại, cảnh báo hiệu năng và restricted được ghi vào `testing.log`; chúng không được ghi vào `bug.log` qua hàm `bug_log()`.** Điều này giúp bạn tránh chỉ đọc `bug.log` rồi bỏ sót các cảnh báo khác.

Một quy trình kiểm tra cảnh báo:

1. Tìm đoạn `Base Query` và truy vấn biến đổi tương ứng trong log.
2. Ghi lại phiên bản cơ sở dữ liệu, dữ liệu và cấu hình đang dùng.
3. Chạy lại từng truy vấn với dữ liệu không thay đổi để kiểm tra kết quả.
4. Với cảnh báo logic, kiểm tra phép biến đổi có giữ đúng quan hệ ngữ nghĩa hay không.
5. Với cảnh báo hiệu năng, chạy lặp và so sánh trong điều kiện tải tương tự; có thể xem thêm kế hoạch thực thi.
6. Rút gọn dữ liệu và truy vấn thành ví dụ nhỏ đủ tái hiện trước khi kết luận hoặc báo lỗi.

## 11. Bắt đầu dùng dự án theo thứ tự nào?

1. **Chuẩn bị Neo4j có dữ liệu:** nhánh Neo4j là hướng có bộ quét tự động trong repository. Máy chủ và dữ liệu cần có trước khi chạy chương trình.
2. **Chuẩn bị môi trường Python và cài phụ thuộc:** dùng môi trường ảo để quản lý các thư viện của dự án.
3. **Sửa `graphgenie.ini`:** điền địa chỉ, cổng, tài khoản, mật khẩu và các lựa chọn kiểm thử theo máy chủ thực tế.
4. **Chạy từ thư mục gốc dự án:** mã dùng đường dẫn tương đối để đọc cấu hình và ghi log.
5. **Quan sát log và dừng khi đủ dữ liệu:** vòng kiểm thử hiện chưa có điều kiện tự dừng theo giới hạn cấu hình.

Các lệnh cơ bản, nếu Python 3 và máy chủ Neo4j đã được chuẩn bị:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 main.py
```

Lệnh kích hoạt môi trường ở trên dành cho shell kiểu bash/zsh trên macOS/Linux. Cài thư viện Python không cài máy chủ Neo4j và không tự nạp file dump dữ liệu.

Đọc [README gốc](README.md) để tham khảo cách chuẩn bị máy chủ và dữ liệu. Hướng dẫn đó ghi môi trường tác giả từng kiểm thử là Python 3.8.10 và Ubuntu 20.04.2 LTS; đó không phải kết quả xác nhận tương thích cho mọi phiên bản hiện nay. Tài liệu này giải thích mã nguồn, không phải báo cáo đã chạy kiểm thử trên một máy chủ cụ thể.

## 12. Những điểm cần hiểu đúng trong phiên bản hiện tại

| Điểm trong cấu hình hoặc mã | Hành vi thực tế |
| --- | --- |
| `max_testing_query_num = 2000` | Được đọc nhưng chưa dùng làm điều kiện dừng; chương trình không tự dừng ở 2000 truy vấn. |
| `testing_times = 1` | Có vòng lặp ngoài, nhưng vòng `while True` bên trong không có điều kiện thoát bình thường. |
| `max_thread_num = 8` | Chưa được đọc để giới hạn luồng; không bảo đảm tối đa 8 luồng đồng thời. |
| `min_node_num`, `max_node_num` | Được đọc nhưng chưa giới hạn độ dài mẫu; bộ sinh dùng `_node_num` và tự tăng giá trị đó. |
| `predicate_rate`, `statistics` | Chưa điều khiển việc sinh `WHERE` hoặc bật/tắt thống kê như tên tham số có thể gợi ý. |
| `mutated_query_num` | Là mục tiêu số truy vấn tương đương ở nhánh có sinh lặp, không phải giới hạn cứng hay tổng tất cả truy vấn. |
| Kết quả được so sánh | Các nhánh thực thi chủ yếu lấy giá trị đầu tiên của hàng đầu tiên; không so sánh toàn bộ bảng trả về. |
| Đa luồng | Một số trạng thái, bộ đếm và việc ghi log được dùng chung, chưa có đồng bộ đầy đủ. |
| Gremlin | README ghi mã kiểm thử Gremlin chưa được phát hành; đổi `language` không đủ để hỗ trợ nó. |
| RedisGraph/AgensGraph | Có nhánh kết nối nhưng cần chuẩn bị thêm thư viện và thông tin nhãn; không có bộ quét tự động tương đương Neo4j trong luồng chính. |

Các điểm này phản ánh một bản công cụ nghiên cứu còn phần chưa hoàn thiện. Khi dùng để làm bài tập hoặc báo cáo, nên phân biệt **ý tưởng của phương pháp** với **mức độ hiện thực trong mã nguồn đang có**.

Giải thích từng cấu hình nằm trong [graphgenie_guide.ini](graphgenie_guide.ini).

## 13. Ý nghĩa học thuật và cách trình bày dự án

Điểm đáng chú ý của dự án là cách tạo tiêu chí kiểm tra khi không có sẵn đáp án chuẩn cho truy vấn ngẫu nhiên. Thay vì chỉ thay đổi điều kiện lọc, GraphGenie chú trọng biến đổi mẫu truy vấn đồ thị để tạo những truy vấn có quan hệ ngữ nghĩa với nhau.

Repository dẫn công trình “Detecting Logic Bugs in Graph Database Management Systems via Injective and Surjective Graph Query Transformation”, của Jiang và cộng sự, ICSE 2024. Thông tin trích dẫn đầy đủ được ghi trong [README.md](README.md); tài liệu này tập trung vào cách mã trong repository vận hành.

Nếu cần giải thích dự án trong một đoạn ngắn, có thể dùng:

> GraphGenie là công cụ kiểm thử tự động cho hệ quản trị cơ sở dữ liệu đồ thị. Công cụ sinh truy vấn Cypher, áp dụng các phép biến đổi để tạo truy vấn tương đương hoặc truy vấn có điều kiện chặt hơn, rồi so sánh kết quả và thời gian thực thi. Những cặp truy vấn vi phạm quan hệ dự kiến được ghi lại để điều tra lỗi logic hoặc vấn đề hiệu năng. Mã hiện tại có nhánh kết nối Neo4j, RedisGraph và AgensGraph, trong đó Neo4j có hỗ trợ quét dữ liệu tự động.

## 14. Từ vựng nhanh

| Thuật ngữ | Cách hiểu trong tài liệu này |
| --- | --- |
| Graph database | Cơ sở dữ liệu biểu diễn thực thể và quan hệ dưới dạng đồ thị. |
| Node / relationship | Nút / quan hệ nối các nút. |
| Label / relationship type | Nhãn phân loại nút / kiểu của quan hệ. |
| Graph pattern | Mẫu nút, cạnh, chiều và ràng buộc cần khớp trong truy vấn. |
| Base query | Truy vấn gốc do bộ sinh tạo ra. |
| Equivalent query | Truy vấn biến đổi được kỳ vọng cho kết quả bằng truy vấn gốc. |
| Restricted query | Truy vấn được thêm ràng buộc, có quan hệ kết quả dự kiến với truy vấn gốc. |
| Query mutation / GQT | Biến đổi cách biểu diễn hoặc cấu trúc của truy vấn. |
| Metamorphic testing | Kiểm thử bằng quan hệ giữa các lần chạy liên quan, thay vì đáp án tuyệt đối. |
| Test oracle | Tiêu chí dùng để đánh giá một kết quả có phù hợp kỳ vọng hay không. |
| Potential bug | Dấu hiệu lỗi cần được tái hiện và xác minh. |

Bạn có thể đọc nội dung tương ứng dưới dạng trang HTML tại [graphgenie_overview.html](graphgenie_overview.html).
