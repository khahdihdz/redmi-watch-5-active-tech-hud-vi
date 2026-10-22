# Changelog

Mọi thay đổi đáng chú ý được ghi ở đây. Định dạng theo [Semantic Versioning](https://semver.org/lang/vi/).

## [v1.1.0] — 2026-10-22

### Thay đổi

- Thiết kế lại theo phong cách **steampunk / brass**: nền da/gunmetal, khung đồng hồ brass, bánh răng, đinh tán, ống dẫn và panel viền đồng.
- Đồng hồ `HH:MM` dùng **DSEG7 Classic Bold** bảy đoạn màu amber; các số 1/4 được căn đáy chung với 0/8 thay vì căn giữa.
- Nhãn và số liệu dùng **Lora** serif (OFL) thay Be Vietnam Pro; validator vẫn kiểm tra đủ glyph tiếng Việt.
- Giữ bốn panel dữ liệu, vòng **MỤC TIÊU** căn giữa và vùng an toàn bo góc **82 px**.
- Thêm giấy phép Lora/DSEG7, cập nhật validator, test baseline bảy đoạn và tài liệu font.

### Giới hạn

- Vẫn là **pre-release** vì chưa kiểm thử trên Redmi Watch 5 Active thật.

## [v1.0.4] — 2026-10-22

### Sửa lỗi

- Sửa lỗi chữ trên cùng một dòng bị nhô lên/thụt xuống: mọi ký tự giờ dùng chung **baseline** thay vì căn theo đỉnh của từng glyph.
- Dấu tiếng Việt (Ứ, Ư, Ớ, Ệ, Ộ…) mở rộng phía trên dòng; thân chữ thẳng hàng với chữ không dấu.
- Dời chữ thứ xuống trong khung 110×26 để dấu không bị cắt; làm lại nhãn trên nền và toàn bộ ảnh thứ.
- Thêm test hồi quy kiểm tra baseline của chữ có dấu.

### Giới hạn

- Vẫn là **pre-release** vì chưa kiểm thử trên Redmi Watch 5 Active thật.

## [v1.0.3] — 2026-10-22

### Thay đổi

- Bỏ panel, nhãn **TRẠNG THÁI**, widget kết nối và toàn bộ bitmap `conn_*`; không còn dùng source `2041`.
- Căn giữa vòng **MỤC TIÊU** và nhãn dưới vòng; khoảng trống hai bên được giữ sạch, không đặt nội dung sát góc.
- Dời brand, thứ, pin và ngày vào vùng an toàn; bỏ các khung góc L bị che bởi bo góc; thu gọn thước tick hai bên.
- Thêm kiểm tra tự động: panel, icon, widget và nhãn phải nằm trong hình chữ nhật bo góc bán kính **82 px**.
- Preview được mask theo đúng bo góc và hiển thị chú thích ảnh minh họa.

### Giới hạn

- Vẫn là **pre-release** vì chưa kiểm thử trên Redmi Watch 5 Active thật.

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
