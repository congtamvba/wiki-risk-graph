# Wiki Risk Graph

MVP đào tạo biểu diễn chuỗi quan hệ:

```text
KiemSoat -MITIGATES-> RuiRo -OBSERVED_AS-> SuKienRuiRo
```

Dữ liệu seed hiện tại là dữ liệu mô phỏng (`data_origin=SYNTHETIC`). Không dùng dữ liệu này cho kết luận nghiệp vụ hoặc kiểm toán.

## Chuẩn bị môi trường

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Tạo `.env` ở thư mục gốc, không commit mật khẩu:

```dotenv
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

## Thứ tự chạy project

1. Kiểm tra dữ liệu nguồn:

   ```powershell
   python scripts/inspect_data.py
   ```

2. Chuẩn hóa CSV:

   ```powershell
   python scripts/build_entities.py
   ```

3. Sinh Wiki Markdown:

   ```powershell
   python scripts/build_wiki.py
   ```

4. Kiểm thử Wiki:

   ```powershell
   python scripts/validate_wiki.py
   ```

   Báo cáo được ghi tại `outputs/wiki_validation_report.md`. Bộ seed hiện tại có hai rủi ro chưa có kiểm soát (`RR-011`, `RR-012`), vì vậy validator chủ động trả exit code `1`; đây là thiếu dữ liệu, không phải lỗi sinh Wiki.

5. Quan sát bằng Obsidian: chọn **Open folder as vault**, mở thư mục `wiki/`, mở `Home.md`, sau đó mở **Graph View**.

6. Nạp Neo4j: mở Neo4j Desktop và khởi động DBMS trước, sau đó chạy:

   ```powershell
   python scripts/load_neo4j.py
   ```

   Script đọc `outputs/entities.csv` và `outputs/relations.csv`, tạo schema từ `cypher/schema.cypher`, rồi dùng `MERGE` để có thể chạy lại mà không tạo duplicate.

7. Chạy các truy vấn mẫu trong `cypher/demo_queries.cypher`. Với query B và C, đặt parameter `risk_id`, ví dụ `RR-001`, trong Neo4j Browser hoặc Workspace.

## Dữ liệu chưa có

`owner_unit_id` và `owner_role_id` chỉ là mã tham chiếu; project chưa có master data Đơn vị và Vai trò. Không suy luận tên từ các mã này. Dữ liệu hiện tại cũng chưa có `VanBan`, `DieuKhoan` hoặc `QuyTrinh`.