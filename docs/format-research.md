# Nghiên cứu định dạng & quyết định kỹ thuật

Tài liệu này ghi lại bằng chứng dùng để chọn compiler, định dạng và quy trình cài. Không có kết luận nào dựa trên phần mở rộng file.

## 1. Thiết bị và độ phân giải

- `ooflet/Mi-Create`, `src/data/devices.json`:
  ```json
  "redmi_watch_5_active": {"string": "Redmi Watch 5 Active", "width": 320, "height": 385, "radius": 82}
  ```
- `m0tral/MiWatchLuaWatchfaces`, thư mục `_NonLuaModels/RedmiWatch5_Active/Dash/` và `DOTs/` chứa project `.fprj` thật với `DeviceType="3651"` và toạ độ nằm trong 320×385.

Kết luận: dùng `DeviceType="3651"`, canvas `320×385`.

## 2. Định dạng đầu ra

- File mẫu `xag/watch-faces/redmi-watch-5-active/two-skies/two-skies-pop.bin`:
  - magic `5A A5 34 12`
  - version `0x00010000`
  - bảng resource 16 byte/bản ghi bắt đầu tại `0x100` (mẫu có 64 bản ghi), offset trỏ tới vùng dữ liệu trong file.
  - tên mặt đồng hồ nằm trong header (`Two Skies Pop`).
- `Byterialab/xiaomi-smart-watch-research` công bố cùng magic và cấu trúc resource table `[type][flags][offset][size]`, đồng thời cho thấy firmware không kiểm tra offset.

Kết luận: `.bin` là định dạng Gen2 thật. Phần mở rộng `.bin`/`.face` chỉ là quy ước; dự án xuất `.bin` sau khi xác minh magic và bảng resource. Không đổi đuôi PNG thành BIN.

## 3. Compiler

- `EasyFace` yêu cầu cài `EasyFace_setup.msi` trên Windows và thay file cho dòng máy mới; không có compiler chạy native trên Linux.
- `Mi-Create` đóng gói `src/compiler/compile.exe` (PE32, .NET Framework 4.7.2, ImageMagick). Mã nguồn Mi Create **không** chứa compiler; README ghi rõ compiler là bên thứ ba, không Open Source.
- `Mi-Create/src/utils/project.py` gọi:
  ```text
  compile.exe -b <project.fprj> <output-dir> <Name>.face 1461256429
  ```
  và có nhánh dùng `wine` khi chạy trên Linux.
- `Mi-Create/src/utils/exporter.py` xác nhận `.fprj` là định dạng đầu vào của compiler, không phải `wfDef.json` (GMF compile chưa được triển khai).

Kết luận:

- Dùng đúng compiler Mi Create, pin commit `586a917d…` và SHA-256 `bf0f7230…`.
- Chạy trên runner `windows-2022` để tránh phụ thuộc Wine và native ImageMagick.
- Không phân phối lại `compile.exe`.
- Nếu compiler không khả dụng, pipeline chỉ phát hành preview + source và ghi rõ **không có file cài đặt**.

## 4. Tiếng Việt

- Định dạng `.fprj` không hỗ trợ nhúng font/text động; mọi widget là ảnh hoặc digit bitmap.
- Vì vậy toàn bộ nhãn được rasterize bằng **Be Vietnam Pro** (có đủ `ă â đ ê ô ơ ư` và các dấu thanh). Kiểm tra bằng `fontTools` cmap trong `validate_assets.py`.
- Font **Orbitron** chỉ dùng cho chữ số; font này không có glyph tiếng Việt và không được dùng cho nhãn.
- Preview và fprj dùng cùng một bộ bitmap, nên không có sai lệch giữa ảnh xem trước và mặt đồng hồ.

## 5. Dữ liệu

Source list cho `redmi_watch_5_active` trong `Mi-Create/src/data/sources.json` có:

- `0811/0911/1000911` giờ
- `1011/1111/1211` phút
- `1812` ngày, `1012` tháng, `2012` thứ
- `0841` pin, `2041` Bluetooth
- `0821` bước, `1021` % mục tiêu bước
- `0822` nhịp tim, `0823` calo
- `2031` nhiệt độ

**Không có** source quãng đường. Vì vậy dự án không hiển thị KM.

## 6. Cài đặt

- README của `xag/watch-faces/redmi-watch-5-active` mô tả quy trình Notify for Xiaomi: log Mi Fitness → import → Custom watch face (.bin).
- Ghi chú rõ: Mi Fitness không cài file ngoài catalogue; Gadgetbridge hiện không cài được; iPhone không hỗ trợ.
- Dự án chỉ lặp lại quy trình đã được ghi nhận cho đúng mẫu, không mở rộng cho mẫu khác.

## 7. Bảo mật

- Không dùng payload OOB read/DoS từ nghiên cứu; chỉ dùng mô tả định dạng.
- Không flash firmware, không root, không mở bootloader.
- CI: quyền đọc mặc định, chỉ job release có quyền ghi; action bên thứ ba pin SHA; compiler pin SHA-256; không chạy compiler trên PR từ fork.
