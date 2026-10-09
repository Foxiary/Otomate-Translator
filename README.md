# Otomate Translator

Ứng dụng Electron cho bộ công cụ Việt hóa game Otomate / Idea Factory ([VE-ES](https://github.com/Foxiary/VE-ES)): container CRI `.cpk`, kịch bản `STCM2L`, cơ sở dữ liệu `.gbin`/`.gstr` và font bitmap `.ffu`. Giao diện cung cấp biểu mẫu, chọn tệp, nhật ký trực tiếp và nút dừng cho 34 thao tác dòng lệnh của bộ công cụ.

Ứng dụng không chứa dữ liệu game, font, bảng dịch hoặc khóa. Khi chọn một thư mục dự án, ứng dụng chép các script, `build.py`, `fonts.json` và tài liệu nguồn còn thiếu vào đó. Tệp người dùng đã sửa được giữ nguyên.

## Tải về

Bản đóng gói nằm ở [Releases](https://github.com/Foxiary/Otomate-Translator/releases). Các gói chưa được ký số, nên Windows SmartScreen hoặc macOS Gatekeeper có thể cảnh báo.

## Chạy từ mã nguồn

1. Cài Node.js và Python 3.
2. Clone kèm submodule engine: `git clone --recursive https://github.com/Foxiary/Otomate-Translator.git`. Nếu đã clone rồi thì chạy `git submodule update --init`.
3. Trong thư mục repo, chạy `npm install` rồi `npm start`.
4. Trong ứng dụng, chọn **Python environment → Set up Python packages** để tạo môi trường riêng và cài Pillow, fontTools, openpyxl, NumPy. Bạn cũng có thể chọn một Python đã cài các thư viện này.
5. Chọn thư mục chứa dữ liệu dự án trong **Workspace**. Xem **Source documentation** để biết bố cục và quy trình dịch.

Nếu npm chặn bước cài Electron, chạy `npm approve-scripts electron` và `node node_modules/electron/install.js` một lần.

## Đóng gói

- macOS: `npm run dist:mac`
- Windows x64: `npm run dist:win -- --x64`
- Linux: `npm run dist:linux`

## Engine

`engine/` là submodule của [Foxiary/VE-ES](https://github.com/Foxiary/VE-ES), hiện ở commit `5791cbd`. Bản này có viền tối `--stroke`, và dấu câu tiếng Nhật (`？！。「」…`) được vẽ bằng glyph Latin của font nguồn (tắt bằng `--no-normalize-punctuation`).

Để lên bản engine mới:

1. Ghi hash SHA-256 (sau khi đổi CRLF thành LF) của các file sắp bị thay vào `src/engine-update.json`. Workspace nào còn giữ đúng bản cũ đó sẽ được chép bản mới khi mở app.
2. `git -C engine pull origin master`, rồi commit con trỏ `engine` mới.
3. Sửa `SOURCE_COMMIT` trong `src/main.js` thành commit engine mới.

## Thông báo cập nhật

Khi mở ứng dụng và mỗi ngày một lần, ứng dụng kiểm tra commit mới nhất của VE-ES. Nếu khác `SOURCE_COMMIT`, ứng dụng hiển thị thông báo trong cửa sổ và, nếu hệ điều hành hỗ trợ, một thông báo desktop. Nút **Check updates** kiểm tra ngay. Ứng dụng không tự tải hay cài mã mới. Lỗi mạng hoặc giới hạn API không cản trở công việc.

## Cách hoạt động

Mỗi thao tác chạy script Python gốc với danh sách tham số, không qua shell. Các giá trị lặp như `--font` và `--sheet` dùng mỗi dòng một giá trị. Đường dẫn tương đối được tính từ workspace đã chọn. Nhật ký hiển thị đầu ra; **Stop** dừng tiến trình đang chạy.

`build.py` dành riêng cho bố cục dự án Virche Evermore. Các công cụ khác nhận dữ liệu từ game Otomate khác như tài liệu nguồn mô tả; với `ffugen.py`, đổi game chỉ cần đổi `--template`. Biểu mẫu của `translate_glossary.py` ghi rõ các bản dịch mẫu có sẵn trong repo nguồn.
