# Engine Unity

Bộ công cụ Việt hóa game Unity trên Switch (IL2CPP, UnityPy). Rút ra từ dự án
[UNLOGICAL](https://github.com/Foxiary/ul-vi-patch): những phần dùng lại được cho
game Unity khác được viết lại để nhận mọi đường dẫn qua tham số, còn các bản sửa
riêng của UNLOGICAL (`fix_*`) ở lại repo đó.

Cần Python 3 với UnityPy 1.25, pycryptodome, lz4, Pillow, openpyxl, NumPy,
fontTools — nút **Set up Python packages** trong app cài đủ.

## Quy trình

1. **Dump.** `switchfs.py exefs` và `switchfs.py romfs` đọc thẳng NSP bằng
   `prod.keys`. Giữ một bản dump gốc không bao giờ sửa, làm việc trên bản sao.
2. **Tìm chữ.** `unityls.py --summary` cho biết file nào chứa gì. Chữ thường nằm ở
   TextAsset (JSON, kịch bản), MonoBehaviour (TextMeshPro), hằng chuỗi IL2CPP
   (`il2cpp.py find`) và tranh vẽ sẵn chữ.
3. **Dịch.** `jsonsheet.py export` ra bảng ID | Source | Translation; dịch cột C;
   `jsonsheet.py apply` ghi lại. Từ chối dòng có Source đã lệch với file.
4. **Khung chữ.** `tmp.py list` tìm khung TextMeshPro theo chữ nó hiện;
   `tmp.py set` nới khung, bật ngắt dòng, cho tự co chữ trong một khoảng.
5. **Font.** `tmpfont.py info` / `font.py coverage` kiểm font có đủ dấu tiếng Việt
   không. Font TextMeshPro **động** thì `font.py replace` thay TTF nguồn; font
   **tĩnh** (glyph nướng sẵn vào atlas) thì `tmpfont.py add` nướng thêm glyph —
   chạy `tmpfont.py verify` với TTF gốc của font trước để chắc cách nướng khớp.
6. **Code.** `il2cpp.py patch` cho hằng chuỗi; `ips32.py` cho bản vá mã máy.
7. **Đóng gói.** `release.py` ra zip cho Ryujinx và Atmosphère.

Mọi lệnh ghi file đều **chạy thử** trước, phải thêm `--apply` (hay `--build`) mới
ghi; ghi đè lên chính file vào thì giữ bản `.bak`. Sau mỗi lần lưu, công cụ đọc
lại và kiểm mọi object khác vẫn giống từng byte.

Ví dụ UNLOGICAL — chỉ lấy lời thoại và tên người nói trong `ScenarioData`:

```
python tools/jsonsheet.py export Data/StreamingAssets/scenario/scenario01 scenario.xlsx ^
    --name ScenarioData --path "/(text|talkName)/\d+$"
```

Lựa chọn lưu dạng JSON nằm **trong** một chuỗi (như `selText` của UNLOGICAL):
thêm `--nested` khi `export`, ID nối các tầng bằng `#`.

## Giới hạn

- Chưa có công cụ chung cho tranh vẽ sẵn chữ; xem `docs/03-baked-art.md`.
- `tmpfont.py add` chỉ nướng vào chỗ trống của atlas có sẵn; atlas đầy thì phải
  dựng lại lớn hơn trong Unity Editor. Font nhiều atlas chưa hỗ trợ.
- `tmp.py set` không đổi được việc game tự ngắt dòng trong code (UNLOGICAL cắt
  tóm tắt chương ở 18 ký tự) — trường hợp đó cần bản vá `ips32.py`.
- NSP bản cập nhật (RomFS dạng BKTR) chưa đọc được.

## Tài liệu

`docs/` là ghi chú kỹ thuật từ UNLOGICAL (tiếng Anh): chữ nằm ở đâu, TextMeshPro
ngắt dòng ra sao, tranh vẽ sẵn chữ, các bẫy khi đóng gói lại bằng UnityPy, và
hằng chuỗi IL2CPP. Số liệu là của UNLOGICAL nhưng cơ chế là của Unity, áp dụng
được cho game khác. `tools/README.md` liệt kê từng công cụ.
