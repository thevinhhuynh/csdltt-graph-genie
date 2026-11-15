#!/usr/bin/env bash
# Thu thập bằng chứng cho hai lỗi vẫn còn trên Neo4j 5.4.0 dù báo cáo lỗi đã đóng:
#   L2 = neo4j#12996 (lỗi logic: count + SKIP)   I2 = neo4j#12988 (lỗi nội bộ: OPTIONAL + DISTINCT + shortestPath)
# Truy vấn chạy bằng cypher-shell (công cụ chính thức của Neo4j), không qua chương trình của nhóm.
# Chạy từ thư mục gốc project: bash bug_cases/evidence/collect_evidence_L2_I2.sh
set -u
cd "$(dirname "$0")"

STAMP=$(date +%Y%m%d-%H%M%S)
LOG="evidence_L2_I2_${STAMP}.log"
PASS=12344321
CONTAINER=neo4j-5-4-0
DESKTOP_SHELL="$HOME/Library/Application Support/neo4j-desktop/Application/Data/dbmss/dbms-a32c8b3e-9103-4e10-aa5d-1a09d00dc458/bin/cypher-shell"

L2_Q="MATCH (a)-[b:RATED]->(c) RETURN count(a) SKIP 1"
L2_Q2="MATCH (a)-[b:RATED]->(c) RETURN count(b) SKIP 1"
I2_Q="OPTIONAL MATCH p=shortestPath((a:User)-[:IN_GENRE*]-(c:Genre)) RETURN DISTINCT p"
VERSION_Q="CALL dbms.components() YIELD name, versions, edition RETURN name, versions[0] AS version, edition"
DATA_Q="MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() RETURN nodes, count(r) AS relationships"

line() { printf '%s\n' "------------------------------------------------------------------------"; }
now() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

# chạy một câu trong container bằng cypher-shell của chính phiên bản đó
in_container() {
  echo "\$ cypher-shell \"$1\""
  echo "[thời điểm UTC: $(now)]"
  docker exec "$CONTAINER" cypher-shell -u neo4j -p "$PASS" --format plain "$1" 2>&1
  echo "[mã thoát: $?]"
  echo
}

# chạy một câu trên GraphGenieLab (Neo4j Desktop) bằng cypher-shell đi kèm instance đó
on_desktop() {
  echo "\$ cypher-shell \"$1\""
  echo "[thời điểm UTC: $(now)]"
  "$DESKTOP_SHELL" -a bolt://127.0.0.1:7687 -u neo4j -p "$PASS" --format plain "$1" 2>&1
  echo "[mã thoát: $?]"
  echo
}

{
  echo "BẰNG CHỨNG: L2 (neo4j#12996) VÀ I2 (neo4j#12988) VẪN CÒN TRÊN NEO4J 5.4.0"
  echo "Tạo lúc (UTC): $(now)    Máy: $(uname -sm)"
  line

  echo "1. PHIÊN BẢN ĐANG KIỂM TRA"
  echo
  echo "Container: $CONTAINER"
  echo "Docker image: $(docker inspect "$CONTAINER" --format '{{.Config.Image}}')"
  echo "Mã băm image (digest): $(docker image inspect "$(docker inspect "$CONTAINER" --format '{{.Config.Image}}')" --format '{{index .RepoDigests 0}}')"
  echo "Ngày build image: $(docker image inspect "$(docker inspect "$CONTAINER" --format '{{.Config.Image}}')" --format '{{.Created}}')"
  echo
  in_container "$VERSION_Q"
  echo "Bộ dữ liệu (recommendations-50: kỳ vọng 28863 nút, 166261 cạnh):"
  in_container "$DATA_Q"
  line

  echo "2. L2 – neo4j#12996 (lỗi logic)"
  echo "Hai câu chỉ khác biến được đếm (a hay b). count() không nhóm chỉ trả 1 dòng; SKIP 1 bỏ dòng đó,"
  echo "nên CẢ HAI câu phải trả về rỗng. Nếu một câu trả rỗng còn câu kia trả số => lỗi."
  echo
  in_container "$L2_Q"
  in_container "$L2_Q2"
  line

  echo "3. I2 – neo4j#12988 (lỗi nội bộ)"
  echo "Truy vấn hợp lệ; nếu máy chủ trả Neo.DatabaseError.Statement.ExecutionFailed => lỗi."
  echo
  START=$(date -u +"%Y-%m-%dT%H:%M:%S")
  in_container "$I2_Q"
  echo "Log của chính máy chủ Neo4j 5.4.0 ghi nhận lỗi (docker logs, từ $START UTC):"
  docker logs --since "$START" "$CONTAINER" 2>&1 | grep -E "ERROR|ExecutionFailed" | cut -c1-400
  echo
  line

  echo "4. ĐỐI CHỨNG: CÙNG CÁC CÂU TRÊN NEO4J HIỆN TẠI (GraphGenieLab, Neo4j Desktop)"
  echo
  on_desktop "$VERSION_Q"
  on_desktop "$L2_Q"
  on_desktop "$L2_Q2"
  on_desktop "$I2_Q"
  line

  echo "5. TRẠNG THÁI BÁO CÁO LỖI TRÊN GITHUB (lấy trực tiếp từ api.github.com)"
  echo
  for n in 12996 12988; do
    curl -s "https://api.github.com/repos/neo4j/neo4j/issues/$n" | python3 -c '
import sys, json
d = json.load(sys.stdin)
if "number" not in d:
    print("  không lấy được:", d.get("message"))
else:
    print("  #{}  \"{}\"  trạng thái={}  mở={}  đóng={}".format(d["number"], d["title"], d["state"], d["created_at"][:10], (d.get("closed_at") or "")[:10]))
    print("     {}".format(d["html_url"]))'
  done
  echo
  echo "Image Neo4j 5.4.0 ở mục 1 được build ngày 2023-02-09, SAU ngày đóng của cả hai báo cáo lỗi (01/2023),"
  echo "nhưng hai lỗi vẫn tái hiện ở mục 2 và 3; còn ở mục 4, Neo4j hiện tại cho kết quả đúng."
  echo "=> Đóng báo cáo lỗi không có nghĩa bản 5.4.0 đã chứa bản sửa; bản sửa chỉ có trong các phiên bản sau."
  line
} > "$LOG"

shasum -a 256 "$LOG" > "$LOG.sha256"
echo "Đã ghi: bug_cases/evidence/$LOG"
echo "Mã băm SHA-256: $(cut -d' ' -f1 "$LOG.sha256")  (lưu trong $LOG.sha256)"
