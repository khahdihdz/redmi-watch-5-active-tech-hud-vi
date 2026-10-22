# Kiểm thử trên thiết bị thật

Trạng thái hiện tại: **CHƯA THỰC HIỆN**.

Repo chỉ cho phép phát hành **stable** khi `tests/device_verification.json` có `"verified": true`. Đây là cổng bắt buộc, không phải gợi ý.

## Quy trình

1. Cài `tech-hud-vi.bin` theo hướng dẫn trong README (Notify for Xiaomi).
2. Chọn mặt đồng hồ trên máy.
3. Chụp ảnh màn hình thật ở ngoài trời và trong nhà.
4. Kiểm tra:
   - Giờ và phút khớp với điện thoại.
   - Thứ/ngày/tháng đúng, không mất dấu tiếng Việt.
   - Pin phần trăm khớp với cài đặt hệ thống.
   - Bước, nhịp tim, calo cập nhật khi vận động.
   - Nhiệt độ hiển thị sau khi đồng bộ thời tiết; thử cả giá trị âm nếu có thể.
   - Bốn dải `BƯỚC / TIM / CALO / NHIỆT ĐỘ` nằm gọn, không chồng lên nhau.
   - Không bị cắt chữ, không tràn panel, không nhấp nháy.
5. Theo dõi pin ít nhất 24 giờ.
6. Ghi kết quả vào `tests/device_verification.json`:

```json
{
  "verified": true,
  "device": "Redmi Watch 5 Active",
  "model": "M2351W1",
  "firmware": "phiên bản firmware thực tế",
  "date": "YYYY-MM-DD",
  "tester": "tên hoặc handle",
  "notes": "Mô tả kết quả, link ảnh chụp, lỗi còn lại."
}
```

7. Commit, chạy lại workflow, sau đó phát hành với `channel=stable` nếu mọi kiểm tra đạt.

## Nếu có lỗi

- Ghi rõ hiện tượng, ảnh chụp, firmware.
- Nếu đồng hồ reboot: xoá mặt tuỳ chỉnh, quay về mặt mặc định, báo lỗi. Không thử payload lạ.
- Không thử cài trên mẫu khác (Redmi Watch 5 / 5 Lite) — DeviceType khác.
