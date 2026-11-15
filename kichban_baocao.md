# Kịch bản báo cáo: Kiểm chứng lỗi trong bài báo GraphGenie (Neo4j và TinkerPop)

> **Thông điệp duy nhất người nghe cần nhớ:**
> *"Nhóm không tin vào bài báo, nhóm chạy lại từng lỗi. Lỗi là có thật, Neo4j đã sửa, và trên TinkerPop phương pháp này
> vẫn tìm ra lỗi mới, kể cả lỗi của chính GraphGenie."*

Mọi phần bên dưới đều phục vụ câu này. Khi bị hỏi vặn, hãy quay về nó.

---

## 0. Tổng quan: 5 slide, khoảng 8 phút

Bộ slide: **`Slide_KiemChung_LoiGraphGenie.pptx`** (dựng trên template UIT, theo cấu trúc `BaoCao_KiemChung_TomTat.docx`; lời nói của từng slide có trong phần *Notes*).

| Slide | Tiêu đề (câu kết luận) | Mục trong bản tóm tắt | Demo | Thời lượng | Người trình bày |
|---|---|---|---|---|---|
| 1 | Cùng một câu hỏi, Neo4j trả về 43 và 491 | 1. Câu hỏi | – | 1 phút | [ ] |
| 2 | Không cần đáp án vẫn bắt được lỗi, kiểm chứng bằng một lệnh | 2. Cách thực hiện + 3. Cách chạy | – | 1,5 phút | [ ] |
| 3 | 8/8 lỗi Neo4j tái hiện được, bản hiện tại đã sửa 7/8 | 4. Kết quả Neo4j | **Demo 1** | 2 phút | [ ] |
| 4 | TinkerPop: 3 lỗi thật, nhưng 67/68 cảnh báo là giả | 5. Kết quả TinkerPop | **Demo 2** | 2 phút | [ ] |
| 5 | Lỗi có thật, đã được sửa, và cảnh báo phải được kiểm chứng | 6. Phân loại + 7. Hạn chế + 8. Kết luận | – | 1,5 phút | [ ] |
| | **Tổng** | | | **~8 phút** + hỏi đáp | |

Chỉ cần đọc 5 tiêu đề là nắm được toàn bộ bài. Những gì không có trên slide (lỗi hiệu năng chi tiết, RedisGraph/AgensGraph)
nằm trong phần **Hỏi đáp** (mục 3).

Tài liệu đi kèm: `BaoCao_KiemChung_TomTat.docx` (3 trang, phát cho người nghe) và `BaoCao_KiemChung_LoiGraphGenie.docx` (bản đầy đủ).

---

## 1. Chuẩn bị trước buổi báo cáo (làm trước ít nhất 30 phút)

### 1.1. Bật server

```bash
# Neo4j phiên bản lỗi (Docker)
docker start neo4j-5-1-0            # cổng 17687, recommendations

# TinkerPop
docker start gremlin                # cổng 8182

# Neo4j hiện tại: mở Neo4j Desktop → Start instance GraphGenieLab (cổng 7687)
```

Nếu `docker start neo4j-5-1-0` báo *"Neo4j is already running"* (lần trước bị tắt đột ngột), tạo lại container trên cùng volume:

```bash
docker rm -f neo4j-5-1-0 && docker run -d --name neo4j-5-1-0 -p 17687:7687 \
  -v neo4j-5-1-0-data:/data -e NEO4J_AUTH=neo4j/12344321 neo4j:5.1.0-community
```

### 1.2. Chạy thử toàn bộ demo một lần

Chạy đúng các lệnh demo ở slide 3 và slide 4 (mục 2), xác nhận ra kết quả như kịch bản.
Lần chạy đầu của mỗi server chậm hơn (biên dịch truy vấn), nên chạy thử còn giúp "làm nóng" server.

### 1.3. Mở sẵn trên màn hình

- [ ] Terminal đã `cd` vào thư mục project, đã `source .venv/bin/activate`, chữ đủ to (≥ 18pt).
- [ ] `bug_cases/neo4j/logic_bugs.json` mở trong editor (để chỉ vào trường `paper_result`).
- [ ] Bản PDF bài báo, mở sẵn trang có **Listing 6** (trang 7) và **Bảng 3** (trang 6).
- [ ] `Slide_KiemChung_LoiGraphGenie.pptx` ở chế độ Presenter View (thấy được Notes).
- [ ] File tóm tắt 3 trang (để mở khi bị hỏi về phân loại hoặc chi tiết).

### 1.4. Phương án dự phòng nếu demo hỏng

Không sửa lỗi trước mặt người nghe. Chuyển ngay sang kết quả đã lưu:

```bash
ls bug_cases/results/      # mỗi lần chạy đều có file JSON kèm thời điểm và phiên bản
```

Nói: *"Mỗi lần chạy đều được lưu lại. Đây là kết quả lúc [giờ] ngày 10/11, cùng câu truy vấn, cùng server."*
Nên chụp sẵn ảnh màn hình output của Demo 1 và Demo 2; slide 3 và 4 đã có sẵn kết quả dạng bảng làm bằng chứng nếu demo hỏng.

---

## 2. Kịch bản từng slide

Ký hiệu: 🗣️ lời nói · 🖥️ trên slide · ⌨️ lệnh demo · 🎯 điểm nhấn · ➡️ câu chuyển sang slide sau

### Slide 1. "Cùng một câu hỏi, Neo4j trả về 43 và 491" (1 phút)

🖥️ Hai câu truy vấn Q, Q' với hai con số 43 (đỏ) và 491 (xanh); dòng ghi chú; ba câu hỏi đánh số.

🗣️ *"Hai câu truy vấn này hỏi cùng một điều: đếm những người vừa đạo diễn vừa đóng trong cùng một bộ phim. Câu trên viết điều kiện
'đạo diễn' ngay trong mẫu, câu dưới viết trong WHERE. Cùng câu hỏi, cùng dữ liệu, nhưng Neo4j trả 43 và 491.
Ít nhất một con số là sai, và hệ quản trị không hề báo lỗi."*

🎯 Dừng 2 giây cho người nghe tự nhận ra vấn đề.

🗣️ Chỉ vào ba câu hỏi: *"Nhóm không muốn chỉ đọc lại bài báo, nên tự kiểm chứng ba câu hỏi này bằng thực nghiệm.
Cuối bài nhóm sẽ trả lời đúng ba câu này."*

➡️ *"Làm sao biết có lỗi khi không biết đáp án đúng?"*

### Slide 2. "Không cần đáp án vẫn bắt được lỗi, kiểm chứng bằng một lệnh" (1,5 phút)

🖥️ Sơ đồ Q → Q' → "≠ ?"; bảng 3 tiêu chí; thẻ "Bộ case và môi trường"; hai lệnh chạy; bốn nhãn kết luận.

🗣️ Nguyên lý (chỉ vào sơ đồ): *"Khó nhất của lỗi logic là không biết đáp án đúng. GraphGenie hỏi một câu theo hai cách cùng ý nghĩa, Q và Q'.
Nếu hai cách cho kết quả khác nhau thì chắc chắn hệ quản trị sai, vì sự thật chỉ có một. Giống như hỏi 'lớp có bao nhiêu bạn nữ'
và 'lớp có bao nhiêu bạn không phải nam'."*

🗣️ Bảng tiêu chí (10 giây): *"Lỗi logic là kết quả khác nhau, lỗi nội bộ là server báo lỗi, lỗi hiệu năng là chênh hơn 5 lần, đúng ngưỡng của bài báo."*

🗣️ Bộ case và môi trường: *"Nhóm gom lỗi Neo4j của bài báo thành file JSON, mỗi case có câu gốc, câu biến đổi và nguồn; TinkerPop thì nhóm tự tìm
và đối chiếu với Neo4j. Phiên bản cũ chạy bằng Docker, phiên bản hiện tại là GraphGenieLab của nhóm. Script tự kiểm tra dataset,
giới hạn thời gian, đo nhiều lần và đối chiếu với Neo4j để tránh kết luận sai."*

🗣️ Chỉ vào lệnh và các nhãn: *"Mỗi server chỉ cần một lệnh; mỗi case nhận một trong bốn kết luận này."*

➡️ *"Nói thì dễ, giờ nhóm chạy thật."*

### Slide 3. "8/8 lỗi Neo4j tái hiện được, bản hiện tại đã sửa 7/8" (2 phút)

🖥️ Ma trận 7 dòng (đỏ: có lỗi, xanh: không lỗi, vàng: chưa kết luận); hai con số lớn 8/8 và 7/8; lệnh chạy; dòng "Phát hiện thêm".

⌨️ **Demo 1, bước 1:** chạy trên Neo4j 5.1.0, phiên bản issue báo lỗi:

```bash
python bug_cases/run_bug_cases.py bug_cases/neo4j/logic_bugs.json --uri bolt://127.0.0.1:17687
```

```
Server: 5.1.0 (community) @ bolt://127.0.0.1:17687
NEO4J-L1   neo4j#12991    BUG REPRODUCED  kết quả khác nhau: 43 ≠ 491  (khớp số liệu bài báo)
NEO4J-L2   neo4j#12996    BUG REPRODUCED  kết quả khác nhau: None ≠ 100004
```

🗣️ *"Đây là Neo4j 5.1.0. 43 và 491, **trùng khớp từng con số** với Listing 6 trong bài báo."* (mở PDF trang 7, chỉ vào `Result: 43` và `Result: 491`)

🎯 Khoảnh khắc thuyết phục nhất: con số trên terminal và con số trong bài báo nằm cạnh nhau.

⌨️ **Demo 1, bước 2:** cùng lệnh, chỉ đổi sang GraphGenieLab (Neo4j 2026.09 của nhóm):

```bash
python bug_cases/run_bug_cases.py bug_cases/neo4j/logic_bugs.json --uri bolt://127.0.0.1:7687
```

🗣️ *"Cùng câu truy vấn, cùng dữ liệu, chỉ khác phiên bản: bây giờ cả hai câu đều trả 491. Vậy 491 là đáp án đúng, Neo4j cũ bỏ sót hơn 90% kết quả.
Nhà phát triển Neo4j xác nhận trên GitHub: 'fixed in 5.2'."*

🗣️ Quay lại slide, đọc theo cột: *"Cột đầu toàn đỏ: **8 trên 8 case** tái hiện được lỗi trên đúng phiên bản bị báo. Cột cuối gần như toàn xanh:
Neo4j hiện tại đã sửa **7 trên 8**. Một ví dụ nữa: lỗi I1 chỉ đổi tên biến `n` thành `a` mà Neo4j 4.4.12 báo lỗi.
Tên biến không thể thay đổi ý nghĩa truy vấn, nên lỗi chắc chắn nằm ở hệ quản trị."*

🗣️ Chỉ vào dòng "Phát hiện thêm": *"Điều bài báo không nói: L2 và I2 **vẫn còn trên 5.4.0** dù issue đã đóng từ tháng 1/2023.
Không thể tin trạng thái 'closed' trên GitHub; phải chạy thử mới biết."*

➡️ *"Neo4j đã rõ. Còn TinkerPop, nơi bài báo không công bố một câu truy vấn nào?"*

### Slide 4. "TinkerPop: 3 lỗi thật, nhưng 67/68 cảnh báo là giả" (2 phút)

🖥️ Bảng 4 dòng (logic / nội bộ / hiệu năng / báo động giả) có cột Neo4j đối chiếu; con số lớn 67/68; thẻ "emit() gắn nhầm chỗ"; thẻ "Báo động giả".

🗣️ Bối cảnh (20 giây): *"TinkerPop dùng Gremlin, GraphGenie sinh Cypher nên phải qua plugin dịch. Bài báo chỉ ghi '6 lỗi Gremlin chưa xác nhận'.
Nhóm tự chạy GraphGenie, được 68 cảnh báo lỗi logic. Câu hỏi là: cảnh báo nào là thật?"*

⌨️ **Demo 2:** chạy với Neo4j làm đáp án đối chiếu:

```bash
python bug_cases/run_bug_cases.py bug_cases/tinkerpop/logic_bugs.json bug_cases/tinkerpop/false_positives.json \
    --reference-uri bolt://127.0.0.1:7687
```

```
TP-L1   BUG REPRODUCED  kết quả khác nhau: 265517 ≠ 531034  [đối chiếu: base=265517, mutated=265517]
TP-F1   FALSE POSITIVE  kết quả khác nhau: 0 ≠ 1 (hệ đối chiếu cũng trả 0 / 1)
```

🗣️ **Lỗi thật** (chỉ vào thẻ trái): *"Chỉ viết ngược chiều đường đi User → Movie → Genre mà TinkerPop đếm **gấp đôi**, 531 nghìn thay vì 265 nghìn;
Neo4j trả 265 nghìn cho cả hai. Nhóm tìm ra vì sao: trong câu Gremlin do plugin dịch, lệnh `emit` dành cho đoạn đường thứ hai lại đứng ngay sau đoạn thứ nhất,
nên bị gắn nhầm và mỗi đường đi bị đếm hai lần. Gremlin viết tay cho kết quả đúng, nên lỗi nằm ở bộ dịch."*

🗣️ **Báo động giả** (chỉ vào con số 67/68 rồi thẻ phải), nói chậm: *"Còn 67 trên 68 cảnh báo thì sao? Chúng đều có dạng: count(g) ra 0 nhưng count(*) ra 1.
Neo4j cũng trả 0 và 1, **cả hai đều đúng**: OPTIONAL MATCH không khớp vẫn trả một dòng null. Lỗi nằm ở chính GraphGenie, ở luật biến đổi
count(x) thành count(*). Nếu không đối chiếu, nhóm đã báo cáo nhầm 67 lỗi."*

🎯 Đóng góp riêng của nhóm. Nhìn vào người nghe: *"Kiểm thử tự động mà không kiểm chứng thì 98% cảnh báo là sai."*

🗣️ Lướt hai dòng còn lại của bảng (10 giây): *"Lỗi nội bộ ClassCastException và lỗi hiệu năng chênh hơn 2000 lần cũng đều nằm ở bộ dịch."*

➡️ *"Vậy ba câu hỏi ban đầu có câu trả lời."*

### Slide 5. "Lỗi có thật, đã được sửa, và cảnh báo phải được kiểm chứng" (1,5 phút)

🖥️ Ba câu trả lời đánh số; bảng phân loại (nguyên nhân gốc × loại lỗi); thẻ "Hạn chế".

🗣️ Đọc lần lượt ba câu trả lời: *"Một: lỗi có thật, 8/8 case tái hiện được, khớp số liệu bài báo. Hai: Neo4j hiện tại đã sửa 7/8.
Ba: TinkerPop có 3 lỗi thật của bộ dịch, và 67/68 cảnh báo là giả."*

🗣️ Bảng phân loại (20 giây): *"Giống bài báo, nhóm phân loại theo loại lỗi và nguyên nhân gốc. Lỗi Neo4j đến từ toán tử Expand(Into), cách đếm và planner;
lỗi TinkerPop đến từ bộ dịch. Dòng cuối là lỗi của chính GraphGenie: luật count(*) sinh báo động giả. Lỗi logic của TinkerPop được tìm ra
nhờ luật đảo chiều mẫu đồ thị, đúng luận điểm chính của bài báo."*

🗣️ Hạn chế, chủ động nói trước khi bị hỏi: *"P1 chưa đo được vì cả hai câu vượt giới hạn bộ nhớ; lỗi TinkerPop chưa được nhà phát triển xác nhận;
dữ liệu TinkerPop chỉ giữ một nhãn mỗi đỉnh nên nhóm chỉ so sánh hai câu trên cùng một hệ."*

🗣️ Câu chốt (học thuộc): *"Nhóm không tin vào bài báo, nhóm chạy lại. Phương pháp của GraphGenie hiệu quả thật, nhưng cảnh báo tự động
phải được kiểm chứng. Toàn bộ kết quả hôm nay chạy lại được bằng một lệnh trên máy của nhóm. Xin cảm ơn."*

---

## 3. Hỏi đáp dự kiến

Nguyên tắc trả lời: **trả lời thẳng trong một câu → đưa bằng chứng → dừng lại.** Không giải thích dài nếu không được hỏi tiếp.

**H1. Làm sao biết kết quả nào là đúng?**
→ Không cần biết. Hai câu tương đương mà khác kết quả thì chắc chắn có ít nhất một câu sai. Khi cần biết đáp án đúng,
nhóm dùng Neo4j bản mới làm đối chiếu: ví dụ #12991, bản mới trả 491 cho cả hai câu.

**H2. Lỗi đã được sửa rồi thì kiểm chứng để làm gì?**
→ Ba lý do. (1) Chứng minh số liệu bài báo là thật và tái lập được, đây là chuẩn mực của nghiên cứu. (2) Phát hiện điều bài báo không nói:
#12996 và #12988 vẫn còn trên 5.4.0 dù issue đã đóng. (3) Trên TinkerPop, lỗi tìm được **vẫn còn ở thời điểm hiện tại**.

**H3. Lỗi TinkerPop là lỗi của plugin chứ đâu phải của TinkerPop?**
→ Đúng, và nhóm nói rõ điều đó. Nhóm chứng minh bằng cách viết tay câu Gremlin tương đương thì kết quả đúng.
Bài báo cũng xếp 6 lỗi Gremlin vào nhóm "chưa xác nhận" chính vì plugin có thể dịch sai (chú thích 10). Người dùng truy vấn TinkerPop bằng Cypher sẽ nhận kết quả sai, nên đây vẫn là lỗi thực tế.

**H4. 67/68 cảnh báo là giả, vậy GraphGenie có đáng tin không?**
→ Trên Neo4j, luật gây báo động giả này không được bật, và tác giả rút gọn, kiểm tra từng trường hợp trước khi báo cáo lỗi (mục 6.1 của bài báo).
Trên TinkerPop luật này được bật nên sinh báo động giả. Nhóm chỉ ra đúng luật gây lỗi và cách sửa: không áp dụng count(*) cho OPTIONAL MATCH.
Đây là đóng góp cải tiến của nhóm.

**H5. Bài báo báo cáo 19 lỗi, sao nhóm chỉ kiểm 8?**
→ Bộ case trong báo cáo tập trung vào Neo4j theo phạm vi đồ án. Ngoài ra nhóm đã tái hiện thêm các lỗi RedisGraph và AgensGraph
(`paper_bugs/results/reproduce_results.json`): tái hiện được **cả 6 lỗi** (5 lỗi RedisGraph, 1 lỗi AgensGraph) trên phiên bản cũ. Hai phát hiện đáng chú ý:
- **FalkorDB** (hệ kế thừa RedisGraph) **vẫn còn** lỗi #2744: đếm 50 thay vì 90.
- **AgensGraph** bản mới nhất v2.14.1 **vẫn còn** lỗi #609, dù issue đã đóng năm 2025.

**H6. Thời gian đo trên TinkerPop gồm cả mạng, có chính xác không?**
→ Độ trễ mạng cục bộ chỉ vài mili-giây, còn chênh lệch là 9,6 giây so với 4 mili-giây (hơn 2000 lần), nên không ảnh hưởng kết luận.
Nhóm còn đo 3 lần lấy trung vị.

**H7. Tại sao P1 không kết luận được, sao không chạy lâu hơn?**
→ Trên GraphGenieLab cả hai câu vượt giới hạn bộ nhớ giao dịch 716,8 MiB chỉ sau 2 giây, nên chạy lâu hơn cũng không có kết quả.
Muốn đo phải tăng bộ nhớ của DBMS. Điều quan trọng: câu bọc CALL vốn chạy 5,7 giây trên bản cũ nay cũng nặng như câu gốc,
tức là khoảng chênh lệch đã không còn.

**H8. Dữ liệu TinkerPop khác Neo4j thì so sánh có công bằng không?**
→ Nhóm chỉ kết luận dựa trên so sánh **hai câu trên cùng một hệ**. Khi đối chiếu với Neo4j, chỉ dùng các case không phụ thuộc
vào khác biệt nhãn (Genre, User, Movie giống hệt nhau ở hai hệ). Số nút và cạnh khớp tuyệt đối: 28.863 và 166.261.

**H9. Làm sao người khác kiểm tra lại kết quả của nhóm?**
→ Một lệnh. Mỗi case trong file JSON ghi nguồn (Listing nào trong bài báo, issue nào trên GitHub), và mỗi lần chạy lưu kết quả kèm phiên bản và thời điểm.
Có thể demo lại ngay tại chỗ.

**H10. GraphGenie khác gì các công cụ trước như GDBMeter hay Grand?**
→ GDBMeter chỉ biến đổi điều kiện lọc (WHERE); Grand so sánh nhiều hệ với nhau nên dễ báo động giả khi các hệ có ngữ nghĩa khác nhau.
GraphGenie biến đổi chính mẫu đồ thị. Lỗi TP-L1 của nhóm là ví dụ: nó chỉ lộ ra khi đảo chiều mẫu đồ thị.

---

## 4. Mẹo trình bày để thuyết phục

1. **Số liệu trước, giải thích sau.** Mở bằng "43 và 491" chứ không mở bằng "Kiểm thử biến hình là…".
2. **Cho thấy, đừng chỉ kể.** Demo trực tiếp, đặt kết quả terminal cạnh trang bài báo.
3. **Một ví dụ cho mỗi ý.** Không đọc hết 8 case; đọc cột màu rồi chọn 1–2 case ấn tượng nhất (L1: khớp bài báo, I1: chỉ đổi tên biến).
4. **Thí nghiệm có đối chứng.** Luôn nói rõ "cùng câu, cùng dữ liệu, chỉ khác phiên bản" hoặc "Neo4j cũng trả như vậy".
5. **Nói hạn chế trước khi bị hỏi.** Người nghe tin phần còn lại hơn.
6. **Nhấn mạnh đóng góp riêng của nhóm**, những điều bài báo không có:
   - phát hiện báo động giả (67/68 cảnh báo), chỉ ra luật gây lỗi và cách sửa;
   - tìm ra nguyên nhân lỗi TinkerPop tới mức câu Gremlin;
   - phát hiện lỗi vẫn còn sau khi issue đóng, và artifact ghi nhầm số issue;
   - bộ case JSON + script chạy lại bằng một lệnh.
7. **Kết thúc bằng câu mở đầu.** Quay lại 3 câu hỏi; người nghe ra về với đúng thông điệp ở đầu file này.

---

## 5. Bảng số liệu để tra nhanh khi bị hỏi

| Mục | Số liệu |
|---|---|
| Dataset recommendations | 28.863 nút, 166.261 cạnh (giống Neo4j và TinkerPop) |
| #12991 trên 5.1.0 | 43 so với 491 (khớp Listing 6) |
| #12996 trên 5.1.0 và 5.4.0 | rỗng so với 100004 |
| #12973 trên 4.4.12 | ≥ 120 giây so với 5,7 giây (≥ 21 lần); bài báo: 4.642 giây so với 6 giây (776 lần) |
| #13034 trên 5.4.0 | 0,47 giây so với 118 giây (254 lần); bài báo: khoảng 2000 lần |
| TP-L1 | 265.517 so với 531.034 (gấp đôi) |
| TP-P1 / TP-P2 | 2.284 lần / 6.214 lần |
| Log GraphGenie TinkerPop | 68 cặp nghi lỗi (67 báo động giả), 316 lỗi nội bộ (cùng một lỗi), 36 cảnh báo hiệu năng |
| GraphGenieLab | Neo4j 2026.09 enterprise, 3 database: neo4j, pole, cybersecurity; giới hạn bộ nhớ giao dịch 716,8 MiB |
| RedisGraph / AgensGraph (ngoài bộ case) | 6/6 lỗi tái hiện (RedisGraph 5, AgensGraph 1); FalkorDB còn #2744 (50 so với 90); AgensGraph v2.14.1 còn #609 |
