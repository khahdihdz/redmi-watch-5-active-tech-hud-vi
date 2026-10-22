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

## 3.1. Ràng buộc ảnh của compiler Gen2 (DeviceType 3651)

Kiểm chứng bằng cách giải mã assembly `XiaomiWatch.Common` nhúng trong `compile.exe` (chỉ để hiểu định dạng, không phân phối lại):

- `SetupImageList` gọi `BitmapList.Split('|')` rồi `s.Split(':')[1]` cho mọi widget `Shape="31"`. Vì vậy **mỗi entry của image list bắt buộc có tiền tố `(giá_trị):`**, nếu thiếu compiler ném `Index was outside the bounds of the array`.
- `RedmiWatch5ActiveCompressor` giới hạn **256 màu RGBA** cho mỗi ảnh; vượt quá sẽ báo `Colors count is more than 256 pcs`.
- Bộ nén tạo buffer đầu ra bằng đúng kích thước dữ liệu đã pad `(width + 1) × height`. Với ảnh nhỏ hơn 256 byte sau pad, nhánh `StartingSmallData` ghi thêm header và làm tràn buffer (`Destination array was not long enough`). Vì vậy mọi bitmap được pad thêm hàng trong suốt cho tới khi `(width + 1) × height ≥ 256`.
- Widget số dùng ảnh index 0–9; ảnh thứ 11 là dấu trừ cho giá trị âm (ví dụ nhiệt độ), đúng quy ước của Mi Create. Preview v1.1.2 render dấu trừ trong ô riêng cho `-5`, `-10`, `-20`.

Các ràng buộc này được cài đặt trong `scripts/common.py` (`fit_compiler_limits`) và `scripts/generate_assets.py`, rồi kiểm tra lại bằng `scripts/validate_assets.py` trước khi biên dịch.

## 4. Tiếng Việt

- Định dạng `.fprj` không hỗ trợ nhúng font/text động; mọi widget là ảnh hoặc digit bitmap.
- Từ v1.1.0, nhãn, số liệu và phần chữ trong preview dùng **Lora** (serif, OFL); riêng `HH:MM` dùng **DSEG7 Classic Bold** (bảy đoạn, OFL).
- Lora có đủ `ă â đ ê ô ơ ư` và các dấu thanh; DSEG7 chỉ có chữ số nên dấu `:` được vẽ bằng hình học. `validate_assets.py` kiểm tra cmap của cả hai font bằng `fontTools`.
- Lora là font tỉ lệ, nên mỗi bộ số 0–9 dùng **một cỡ chữ chung**; nếu fit từng glyph riêng, số `1` sẽ cao hơn `0`/`8`.
- DSEG7 là font bảy đoạn: ink của `1`/`4` ngắn hơn `0`/`8`. Vì vậy `render_glyph()` căn **đáy** chung cho bộ `digit_time` thay vì căn giữa từng glyph; test `test_seven_segment_digits_share_one_baseline` bảo vệ quy tắc này.
- Be Vietnam Pro và Orbitron không còn được dùng để render kể từ v1.1.0.
- Preview và fprj dùng cùng một bộ bitmap, nên không có sai lệch giữa ảnh xem trước và mặt đồng hồ.
- Màn hình có bán kính bo góc **82 px**. `validate_assets.py` kiểm tra bốn góc của mọi panel, icon, widget và nhãn nằm trong hình chữ nhật bo góc; preview cũng được mask theo đúng bán kính này.
- Panel/nhãn trạng thái và bitmap kết nối đã được bỏ từ v1.0.3; vòng MỤC TIÊU, giá trị phần trăm và source `1021` đã được bỏ từ v1.1.1. Bốn panel dữ liệu được đặt quanh đồng hồ trung tâm từ v1.1.3; v1.1.2 căn thẳng hàng nội dung và hỗ trợ nhiệt độ âm.
- Từ v1.1.4, ảnh preview nội bộ đưa cho compiler là **background tĩnh**, không phải ảnh tổng hợp có số/chữ. Preview tổng hợp của v1.1.3 làm đồng hồ reboot khi mở danh sách chọn mặt; background đã được xác nhận an toàn trên thiết bị. Ảnh xem trước phát hành `design/preview.png` vẫn là ảnh tổng hợp đầy đủ.
- Từ v1.0.4, `draw_text()` vẽ từng ký tự bằng anchor `ls` trên một baseline chung (lấy từ cap height của `H`). Trước đó anchor `lt` căn theo đỉnh từng glyph nên chữ có dấu tiếng Việt bị tụt xuống so với chữ không dấu.

## 5. Dữ liệu

Source list cho `redmi_watch_5_active` trong `Mi-Create/src/data/sources.json` có:

- `0811/0911/1000911` giờ
- `1011/1111/1211` phút
- `1812` ngày, `1012` tháng, `2012` thứ
- `0841` pin
- `0821` bước
- `0822` nhịp tim, `0823` calo
- `2031` nhiệt độ

`1021` (% mục tiêu bước) và `1023` (% mục tiêu calo) vẫn có trong allowlist nghiên cứu nhưng không còn widget nào sử dụng. **Không có** source quãng đường, vì vậy dự án không hiển thị KM.

## 6. Cài đặt

- README của `xag/watch-faces/redmi-watch-5-active` mô tả quy trình Notify for Xiaomi: log Mi Fitness → import → Custom watch face (.bin).
- Ghi chú rõ: Mi Fitness không cài file ngoài catalogue; Gadgetbridge hiện không cài được; iPhone không hỗ trợ.
- Dự án chỉ lặp lại quy trình đã được ghi nhận cho đúng mẫu, không mở rộng cho mẫu khác.

## 7. Bảo mật

- Không dùng payload OOB read/DoS từ nghiên cứu; chỉ dùng mô tả định dạng.
- Không flash firmware, không root, không mở bootloader.
- CI: quyền đọc mặc định, chỉ job release có quyền ghi; action bên thứ ba pin SHA; compiler pin SHA-256; không chạy compiler trên PR từ fork.
