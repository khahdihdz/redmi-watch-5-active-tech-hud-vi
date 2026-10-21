# Changelog

Mọi thay đổi đáng chú ý được ghi ở đây. Định dạng theo [Semantic Versioning](https://semver.org/lang/vi/).

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
