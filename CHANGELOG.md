# Changelog

Mọi thay đổi đáng chú ý được ghi ở đây. Định dạng theo [Semantic Versioning](https://semver.org/lang/vi/).

## [v1.0.2] — 2026-10-21

### Thay đổi

- Dùng **Be Vietnam Pro** cho cả chữ số thời gian và số liệu, thay cho Orbitron.
- Chọn một cỡ chữ chung cho cả bộ 0–9 để các chữ số cao bằng nhau; sửa lỗi số `1` cao vượt các số `0`, `8`.
- Giữ nguyên bố cục tối giản, tên thứ đầy đủ và các sửa lỗi tràn nội dung của v1.0.1.

### Giới hạn

- Vẫn là **pre-release** vì chưa kiểm thử trên Redmi Watch 5 Active thật.

## [v1.0.1] — 2026-10-21

### Sửa lỗi hiển thị

- Bỏ vạch trang trí chạy ngang qua nhãn **MỤC TIÊU**; nhãn nằm gọn dưới vòng tiến độ.
- Bỏ vòng vạch chia bị lệch tâm 6 px quanh vòng mục tiêu.
- Căn lại giá trị phần trăm trong vòng mục tiêu và bỏ dấu `%` thừa.
- Mở rộng vùng số để không tràn/không cắt: bước 6 chữ số, calo 5 chữ số, nhiệt độ 3 chữ số (hỗ trợ `-10`).
- Dịch nhãn trạng thái sang **ĐÃ KẾT NỐI** / **MẤT KẾT NỐI**.
- Hiển thị `0` thay vì ô trống khi số bước, calo, nhịp tim hoặc mục tiêu bằng 0.

### Tinh gọn nội dung

- Bỏ footer tên thiết bị, dòng `HUD-CORE`, nhãn `PIN`, đơn vị `BPM`/`KCAL` và chấm trạng thái trùng với panel.
- Tên thứ đầy đủ: **CHỦ NHẬT, THỨ HAI, THỨ BA, THỨ TƯ, THỨ NĂM, THỨ SÁU, THỨ BẢY**.
- Ngày hiển thị dạng `21/10`, bỏ chữ **THÁNG**.
- Giữ đơn vị `°C` cạnh giá trị nhiệt độ.

### Giới hạn

- Vẫn là **pre-release** vì chưa kiểm thử trên Redmi Watch 5 Active thật.

## [v1.0.0] — 2026-10-21

### Thêm mới

- Giao diện Tech HUD VI cho Redmi Watch 5 Active (DeviceType `3651`, 320×385).
- Đồng hồ số lớn, khung HUD góc vát, đường mạch, panel thông số, vòng mục tiêu.
- Nhãn tiếng Việt có dấu được rasterize bằng Be Vietnam Pro; kiểm tra glyph tự động.
- Bốn panel dữ liệu thật: BƯỚC (`0821`), TIM (`0822`), CALO (`0823`), NHIỆT ĐỘ (`2031`).
- Vòng MỤC TIÊU 21 mức từ source `1021`.
- Panel TRẠNG THÁI từ source `2041`.
- Script sinh asset, kiểm tra thiết bị, kiểm tra asset/fprj, build compiler thật, xác minh binary, đóng gói release.
- GitHub Actions: build source, build binary trên Windows, artifact, checksum, release theo tag.
- Pin compiler commit + SHA-256; action bên thứ ba pin SHA.

### Giới hạn

- Chưa kiểm thử trên thiết bị thật → phát hành pre-release.
- Không có KM vì không có source quãng đường được tài liệu hoá.
- Không có AOD.

## Quy ước

- `v1.0.1`: sửa lỗi.
- `v1.1.0`: thêm tính năng.
- `v2.0.0`: thay đổi lớn.
- Không ghi đè tag/release đã tồn tại.
