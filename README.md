# Otome Translator (OTM)

Ứng dụng Electron để Việt hóa game otome trên Switch, với hai bộ công cụ (engine) chuyển qua lại ngay trên thanh bên trái:

| engine | dành cho | công cụ |
|---|---|---|
| **Otomate** | game Otomate / Idea Factory: container CRI `.cpk`, kịch bản `STCM2L`, cơ sở dữ liệu `.gbin`/`.gstr`, font bitmap `.ffu` | 34, từ [VE-ES](https://github.com/Foxiary/VE-ES) |
| **Unity** | game Unity IL2CPP: bundle và `.assets` (UnityPy), TextAsset JSON, khung chữ và font TextMeshPro (cả font tĩnh), hằng chuỗi IL2CPP, bản vá IPS32 | 22, rút từ [ul-vi-patch](https://github.com/Foxiary/ul-vi-patch) |

Mỗi engine có workspace, giá trị biểu mẫu và tài liệu riêng; đổi engine không làm mất gì của engine kia. Giao diện cung cấp biểu mẫu, chọn tệp, nhật ký trực tiếp và nút dừng cho từng thao tác dòng lệnh.

Ứng dụng không chứa dữ liệu game, font, bảng dịch hoặc khóa. Khi chọn một thư mục dự án, ứng dụng chép script và tài liệu của engine đang chọn còn thiếu vào đó. Tệp người dùng đã sửa được giữ nguyên.

## Tải về

Bản đóng gói nằm ở [Releases](https://github.com/Foxiary/Otome-Translator/releases). Các gói chưa được ký số, nên Windows SmartScreen hoặc macOS Gatekeeper có thể cảnh báo.

## Chạy từ mã nguồn

1. Cài Node.js và Python 3.
2. Clone kèm submodule engine: `git clone --recursive https://github.com/Foxiary/Otome-Translator.git`. Nếu đã clone rồi thì chạy `git submodule update --init`.
3. Trong thư mục repo, chạy `npm install` rồi `npm start`.
4. Trong ứng dụng, chọn **Python environment → Set up Python packages** để tạo môi trường riêng và cài thư viện cho cả hai engine (Pillow, fontTools, openpyxl, NumPy, UnityPy, pycryptodome, lz4). Bạn cũng có thể chọn một Python đã cài các thư viện này.
5. Chọn thư mục chứa dữ liệu dự án trong **Workspace**. Xem **Source documentation** để biết bố cục và quy trình dịch.

Nếu npm chặn bước cài Electron, chạy `npm approve-scripts electron` và `node node_modules/electron/install.js` một lần.

Đến bản 1.2.1 app có tên **VE-ES Desktop**. Lần đầu mở bản mới, app chép `settings.json` từ thư mục dữ liệu cũ (`%APPDATA%\ve-es-desktop` trên Windows) sang, nên workspace và môi trường Python cũ vẫn dùng được; workspace cũ trở thành workspace của engine Otomate.

## Đóng gói

- macOS: `npm run dist:mac`
- Windows x64: `npm run dist:win -- --x64`
- Linux: `npm run dist:linux`

## Engine

- `engines/otomate/` là submodule của [Foxiary/VE-ES](https://github.com/Foxiary/VE-ES), hiện ở commit `fc4fa68`.
- `engines/unity/` nằm ngay trong repo này. Xem `engines/unity/README.md`; mỗi công cụ đã được chạy trên dữ liệu UNLOGICAL thật và so với bản Việt hóa đã phát hành (`engines/unity/tools/README.md`).

Danh mục công cụ của từng engine nằm ở `src/catalog-otomate.js` và `src/catalog-unity.js`; `src/engines.js` khai báo engine, thư mục chép vào workspace, tài liệu và thư viện Python cần có.

Để lên bản VE-ES mới:

1. Ghi hash SHA-256 (sau khi đổi CRLF thành LF) của các file sắp bị thay vào `src/engine-update.json`. Workspace nào còn giữ đúng bản cũ đó sẽ được chép bản mới khi mở app.
2. `git -C engines/otomate pull origin master`, rồi commit con trỏ submodule mới.
3. Sửa `SOURCE_COMMIT` trong `src/main.js` thành commit đó.

## Thông báo cập nhật

Khi mở ứng dụng và mỗi ngày một lần, ứng dụng kiểm tra commit mới nhất của VE-ES (engine Otomate; engine Unity đi cùng bản app). Nếu khác `SOURCE_COMMIT`, ứng dụng hiển thị thông báo trong cửa sổ và, nếu hệ điều hành hỗ trợ, một thông báo desktop. Nút **Check updates** kiểm tra ngay. Ứng dụng không tự tải hay cài mã mới. Lỗi mạng hoặc giới hạn API không cản trở công việc.

## Cách hoạt động

Mỗi thao tác chạy script Python gốc với danh sách tham số, không qua shell. Các giá trị lặp như `--font` và `--sheet` dùng mỗi dòng một giá trị. Đường dẫn tương đối được tính từ workspace đã chọn. Nhật ký hiển thị đầu ra; **Stop** dừng tiến trình đang chạy.

Với engine Otomate, `build.py` dành riêng cho bố cục dự án Virche Evermore. Các công cụ khác nhận dữ liệu từ game Otomate khác như tài liệu nguồn mô tả; với `ffugen.py`, đổi game chỉ cần đổi `--template`. Biểu mẫu của `translate_glossary.py` ghi rõ các bản dịch mẫu có sẵn trong repo nguồn.
