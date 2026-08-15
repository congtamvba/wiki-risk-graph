# Tổng kết 6 bước xây dựng Wiki Risk Graph

## 1. Mục tiêu

Project xây dựng một Wiki Risk Graph phục vụ đào tạo theo luồng:

```text
CSV
  -> Kiểm tra dữ liệu
  -> Chuẩn hóa
  -> entities.csv + relations.csv
  -> Wiki Markdown
  -> Obsidian Graph View
  -> Neo4j
```

Mô hình graph MVP:

```text
KiemSoat -MITIGATES-> RuiRo -OBSERVED_AS-> SuKienRuiRo
```

Toàn bộ dữ liệu seed hiện tại có `data_origin=SYNTHETIC`. Trạng thái `VERIFIED` chỉ có ý nghĩa trong phạm vi bài lab, không được dùng cho kết luận nghiệp vụ hoặc kiểm toán.

## 2. Bước 1 - Kiểm tra dữ liệu nguồn

### File đã tạo

- `scripts/inspect_data.py`

### Dữ liệu đã kiểm tra

| File | Số dòng | Khóa chính |
| --- | ---: | --- |
| `data/risk_profiles_seed.csv` | 12 | `id` |
| `data/controls_seed.csv` | 10 | `id` |
| `data/risk_events_seed.csv` | 12 | `id` |
| `data/relationships_seed.csv` | 22 | Không có cột `id` |

### Kết quả

- Không có giá trị null hoặc rỗng trong bốn file.
- Không có dòng trùng.
- Không có khóa chính trùng trong ba file entity.
- Không có khóa tham chiếu bị thiếu.
- `risk_events_seed.csv.risk_id` tham chiếu hợp lệ tới `risk_profiles_seed.csv.id`.
- Có 10 quan hệ `MITIGATES` và 12 quan hệ `OBSERVED_AS`.
- Xác định được ba loại node: `RuiRo`, `KiemSoat`, `SuKienRuiRo`.

### Dữ liệu chưa có

- `owner_unit_id` chỉ là mã tham chiếu; chưa có master data Đơn vị.
- `owner_role_id` chỉ là mã tham chiếu; chưa có master data Vai trò.
- Chưa có dữ liệu `VanBan`, `DieuKhoan`, `QuyTrinh` và `BangChung` cho MVP này.
- Không suy luận hoặc tự đặt tên Đơn vị, Vai trò từ các mã tham chiếu.

### Lệnh chạy

```powershell
python scripts/inspect_data.py
```

## 3. Bước 2 - Chuẩn hóa dữ liệu

### File đã tạo

- `scripts/build_entities.py`
- `outputs/entities.csv`
- `outputs/relations.csv`

### Kết quả entity

| Type | Số lượng |
| --- | ---: |
| `RuiRo` | 12 |
| `KiemSoat` | 10 |
| `SuKienRuiRo` | 12 |
| **Tổng** | **34** |

`entities.csv` có 34 ID duy nhất, không có ID rỗng hoặc trùng. Schema chung giữ các cột tối thiểu:

```text
id, type, name, description, source_file, data_origin, verification_status
```

Các thuộc tính nghiệp vụ gốc cũng được giữ lại, gồm thông tin phân loại rủi ro, nguyên nhân, tác động, mức độ, mã owner, loại và tần suất kiểm soát, ngày sự kiện, severity và tổn thất.

Nguồn sự kiện không có cột `name`, vì vậy script dùng nguyên văn `description` nguồn làm `name`; không sinh thêm nội dung.

### Kết quả relation

| Relationship type | Số lượng |
| --- | ---: |
| `MITIGATES` | 10 |
| `OBSERVED_AS` | 12 |
| **Tổng** | **22** |

- `relations.csv` giữ nguyên 22 bản ghi từ nguồn.
- Không có orphan reference.
- Không tự sinh quan hệ.
- Không thay đổi `verification_status`.

### Lệnh chạy

```powershell
python scripts/build_entities.py
```

## 4. Bước 3 - Sinh Wiki Markdown

### File đã tạo

- `scripts/build_wiki.py`
- `wiki/Home.md`
- `wiki/risks/*.md`
- `wiki/controls/*.md`
- `wiki/events/*.md`

### Kết quả

| Nhóm trang | Số lượng |
| --- | ---: |
| Trang rủi ro | 12 |
| Trang kiểm soát | 10 |
| Trang sự kiện | 12 |
| Trang Home | 1 |
| **Tổng trang Markdown** | **35** |

- Tổng số Obsidian wikilink: 78.
- Mỗi entity có YAML frontmatter gồm `id`, `type`, `verification_status`, `data_origin`.
- Tên file được xử lý an toàn cho Windows và Obsidian.
- Wikilink sử dụng đường dẫn theo thư mục để tránh nhầm trang.
- Mỗi relation được hiển thị ở hai đầu cùng `relationship_type`, `evidence_quote` và `verification_status`.
- Không có quan hệ nào được tạo ngoài `relations.csv`.

Ví dụ đường đi:

```text
Đối soát tự động giao dịch và sổ cái
  -MITIGATES->
Giao dịch chuyển tiền bị hạch toán sai
  -OBSERVED_AS->
Sai lệch trạng thái giao dịch được phát hiện khi đối soát cuối ngày
```

### Lệnh chạy

```powershell
python scripts/build_wiki.py
```

## 5. Bước 4 - Kiểm thử Wiki

### File đã tạo

- `scripts/validate_wiki.py`
- `outputs/wiki_validation_report.md`

### Kết quả kiểm thử

| Tiêu chí | Kết quả |
| --- | ---: |
| Tổng file Markdown | 35 |
| Tổng wikilink | 78 |
| Wikilink bị hỏng | 0 |
| Entity trùng ID | 0 |
| Trang có ID ngoài `entities.csv` | 0 |
| ID trùng giữa các trang | 0 |
| Entity chưa có trang Wiki | 0 |
| Relation tham chiếu entity không tồn tại | 0 |
| `RuiRo` không có `SuKienRuiRo` | 0 |
| Trang không liên kết với trang khác | 0 |
| `RuiRo` không có `KiemSoat` | 2 |

### Phân loại lỗi

- Lỗi chương trình sinh Wiki: **0**.
- Thiếu hụt dữ liệu: **2** rủi ro chưa có kiểm soát:
  - `RR-011`: Nhà cung cấp công nghệ không đáp ứng cam kết.
  - `RR-012`: Xung đột lợi ích trong mua sắm.
- Hai rủi ro trên vẫn có sự kiện `OBSERVED_AS`, nên không phải node đứng một mình.
- Không bổ sung quan hệ giả để che thiếu hụt dữ liệu.

Validator chủ động trả exit code `1` khi còn lỗi hoặc thiếu hụt dữ liệu. Báo cáo vẫn được tạo thành công.

### Lệnh chạy

```powershell
python scripts/validate_wiki.py
```

## 6. Bước 5 - Quan sát bằng Obsidian

### Kết quả chuẩn bị

- Đã cài Obsidian phiên bản `1.13.7`.
- Vault đã sẵn sàng tại `C:\RAG\wiki-risk-graph\wiki`.
- `Home.md` liên kết tới toàn bộ 34 trang entity.
- Kiểm tra tự động xác nhận 78 wikilink đều có trang đích.

### Cách quan sát

1. Mở Obsidian.
2. Chọn **Open folder as vault**.
3. Chọn thư mục `C:\RAG\wiki-risk-graph\wiki`.
4. Mở `Home.md`.
5. Mở **Graph View**.
6. Có thể lọc `-file:Home` để loại node Home và nhìn rõ các cụm nghiệp vụ.

### Kết quả graph cần quan sát

- `RR-001` đến `RR-010`: mỗi rủi ro có một kiểm soát và một sự kiện.
- `RR-011` và `RR-012`: mỗi rủi ro có một sự kiện nhưng chưa có kiểm soát.
- Mỗi kiểm soát hiện giảm thiểu đúng một rủi ro.
- Không có entity đứng một mình.

Graph View là bước quan sát trực quan trong ứng dụng Obsidian; dữ liệu và liên kết đã được kiểm tra tự động ở bước 4.

## 7. Bước 6 - Nạp Neo4j

### File đã tạo

- `cypher/schema.cypher`
- `cypher/demo_queries.cypher`
- `scripts/load_neo4j.py`
- `README.md`

### Thiết kế

- Constraint duy nhất theo `id` cho `RuiRo`, `KiemSoat`, `SuKienRuiRo`.
- Node và relation được nạp bằng `MERGE` để chạy lại không tạo duplicate.
- ID và properties được truyền bằng parameterized Cypher.
- Label và relationship type chỉ được lấy từ whitelist ba node type và hai relationship type đã biết.
- Mật khẩu không được hard-code; loader đọc các biến `NEO4J_*` từ `.env`.

### Kết quả nạp thực tế

| Thành phần Neo4j | Số lượng |
| --- | ---: |
| Node `RuiRo` | 12 |
| Node `KiemSoat` | 10 |
| Node `SuKienRuiRo` | 12 |
| Edge `MITIGATES` | 10 |
| Edge `OBSERVED_AS` | 12 |
| Đường `KiemSoat -> RuiRo -> SuKienRuiRo` | 10 |

- Tổng cộng 34 node và 22 relation đã được nạp thành công.
- Chạy loader lần hai vẫn giữ nguyên 34 node và 22 relation, xác nhận không tạo duplicate.
- Rủi ro không có kiểm soát trong Neo4j: `RR-011`, `RR-012`.
- Relation chưa `VERIFIED`: 0.
- Với `risk_id=RR-001`, query trả về kiểm soát `KS-001` và sự kiện `SK-001`.
- Cả sáu demo query A-F đã được Neo4j chấp nhận khi chạy `EXPLAIN`.

### Demo query đã chuẩn bị

1. Xem toàn bộ graph.
2. Tìm kiểm soát giảm thiểu một rủi ro.
3. Tìm sự kiện của một rủi ro.
4. Tìm đường `KiemSoat -> RuiRo -> SuKienRuiRo`.
5. Tìm rủi ro không có kiểm soát.
6. Tìm relation chưa `VERIFIED`.

### Lệnh nạp

```powershell
python scripts/load_neo4j.py
```

## 8. Kết luận chung

Luồng kỹ thuật của MVP đã hoàn thành từ CSV tới Wiki Markdown, Obsidian và Neo4j:

```text
4 CSV nguồn
  -> 34 entity + 22 relation
  -> 35 trang Wiki + 78 wikilink
  -> 34 node + 22 edge trong Neo4j
```

Không phát hiện lỗi chương trình trong quá trình sinh và kiểm thử Wiki. Không có khóa tham chiếu thiếu, link hỏng, node trùng hoặc edge trùng sau khi nạp lại Neo4j.

Thiếu hụt dữ liệu còn lại được công khai, không che giấu:

- `RR-011` chưa có quan hệ `MITIGATES` từ một `KiemSoat`.
- `RR-012` chưa có quan hệ `MITIGATES` từ một `KiemSoat`.
- Chưa có master data Đơn vị và Vai trò cho `owner_unit_id`, `owner_role_id`.
- Chưa có dữ liệu `VanBan`, `DieuKhoan`, `QuyTrinh` cho phần Graph RAG mở rộng.

Không tự bịa dữ liệu hoặc quan hệ để lấp các khoảng trống trên.