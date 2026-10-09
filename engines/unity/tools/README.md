# Công cụ của engine Unity

Mỗi script tự mô tả đầy đủ trong docstring đầu file (`python tools/<tên>.py -h`).
Bảng dưới là bản tóm tắt.

| script | lệnh | việc |
|---|---|---|
| `switchfs.py` | `exefs`, `romfs`, `nso` | Đọc NSP bằng `prod.keys`: ExeFS + `main.flat`, RomFS của game/DLC, giải nén NSO |
| `unityls.py` | | Liệt kê object trong bundle / `.assets`, hoặc đếm theo loại (`--summary`) |
| `textasset.py` | `dump`, `import`, `replace` | Xuất TextAsset ra `.txt`, nạp lại, hoặc thay một thuật ngữ có kiểm cấu trúc JSON |
| `jsonsheet.py` | `export`, `apply` | Chuỗi trong TextAsset JSON ⇄ bảng XLSX `ID \| Source \| Translation`; `--nested` mở cả JSON lồng trong chuỗi |
| `tmp.py` | `list`, `set` | Khung chữ TextMeshPro: kích thước, vị trí, cỡ chữ, tự co, ngắt dòng, giãn chữ, lề |
| `font.py` | `list`, `extract`, `replace`, `coverage` | Font nhúng: xem, trích TTF, thay TTF, kiểm ký tự thiếu |
| `tmpfont.py` | `info`, `verify`, `add` | Font TextMeshPro tĩnh: nướng thêm glyph SDF vào atlas, không cần Unity Editor |
| `il2cpp.py` | `find`, `patch` | Hằng chuỗi trong `global-metadata.dat`, vá tại chỗ |
| `ips32.py` | | Bản vá mã máy IPS32 `<build id>.ips`, kiểm byte cũ với `main.flat` |
| `release.py` | | Zip cho Ryujinx và Atmosphère, có DLC, bỏ `.resS` |
| `unityio.py` | | Module dùng chung (nạp, lưu đúng packer, kiểm object không bị đụng) — không phải lệnh |

## Đã kiểm trên dữ liệu thật

Mỗi công cụ được chạy trên bản dump UNLOGICAL v1.0.2 và so với bản Việt hóa đã
phát hành:

- `switchfs.py exefs` ra đúng build id `669EA2FE…` và `main.flat` 82.207.152 B;
  `romfs` trên NSP DLC 1 ra 5 file giống hệt bản dump có sẵn.
- `ips32.py` dựng lại bản vá `.ips` đang phát hành, giống từng byte.
- `textasset.py import` nạp 18 TextAsset dịch vào bundle `json` gốc: 36/36 TextAsset
  giống bản phát hành, kích thước file bằng nhau.
- `jsonsheet.py`: xuất 9.502 chuỗi từ bundle `json`, điền bản dịch đã phát hành,
  ghi lại — mọi giá trị khớp bản phát hành; chỉ `DictionaryData` khác vì bản phát
  hành có đổi cấu trúc, việc nằm ngoài sheet. `ScenarioData` (66 MB JSON) xuất
  trong khoảng 20 giây.
- `il2cpp.py patch` cho `現在使用できません` đổi đúng 28 byte, trùng bản phát hành.
- `jsonsheet.py --nested` trên `ScenarioData`: 64.853 dòng (lời thoại, tên người
  nói, lựa chọn) xuất trong 7 giây, ghi lại 52.425 giá trị trong 10 giây; 528/529
  lựa chọn và 78.972/79.606 lời thoại khớp bản phát hành — phần chênh đều là chuỗi
  chỉ có dấu câu (`…………`), mặc định không xuất, cần `--all`.
- `tmp.py set` lặp lại bản sửa khung backlog của UNLOGICAL (cao 50 → 213, tự co
  28–39,5): component TMP và RectTransform giống bản phát hành **từng byte**. Trên
  `sharedassets17.assets` (không có type tree) đọc và ghi được nhờ `--nodes-from`.
- `tmpfont.py verify` với TTF gốc của `FOT-DNPShueiMGoStd-L SDF`: số đo của cả
  7.125 glyph khớp trong 1/64 px, sai số pixel trung bình 1,86/255. Với font sai
  (bản Bold, Arial) báo KHÔNG KHỚP. `add` nướng 102 chữ Việt từ Arial, không ô nào
  chồng nhau, đọc lại khớp; ảnh xem trước đúng đường chân chữ. **Chưa thử trong game.**
- `font.py replace` thay font điểm ảnh trong `ui_jp` (49 MB), font đọc lại giống
  từng byte; `coverage` báo font Nhật gốc thiếu 102/146 ký tự tiếng Việt.

## Quy ước

- Ghi file luôn là chạy thử trước; `--apply` / `--build` mới ghi.
- `--out` có thể trùng file vào; khi đó bản cũ được giữ thành `.bak`, `.bak2`…
- Bundle lưu bằng LZ4 (mặc định UnityPy là không nén: 4,1 MB thành 23,7 MB);
  `.assets` lưu không packer. Xem `docs/04-repacking.md`.
- File thiếu chuỗi phiên bản Unity cần `--unity-version` (UNLOGICAL: `2021.3.0f1`).
