# Sơ đồ Use Case - Ứng dụng Optimus Prime (Web)

## Diễn viên (Actor)
- **Người dùng (User)**: Người sử dụng ứng dụng web để đăng nhập, chat, quản lý profile, cấp dưới, sự kiện, và trang bị.

## Use Case
1. **Đăng nhập**
   - **Mô tả**: Người dùng nhập `account` hoặc `email` và `password` để truy cập.
   - **Điều kiện tiên quyết**: Người dùng chưa đăng nhập.
   - **Luồng chính**:
     1. Người dùng nhập `account`/`email` và `password` trong sidebar.
     2. Hệ thống gọi API `/login` để xác thực.
     3. Nếu thành công, hệ thống tải lịch sử chat (`/history/<account>/<chatbot>`), profile (`/getProfile/<account>`), và danh sách cấp dưới (`/getSubordinates/<account>`).
   - **Luồng phụ**:
     - Nếu thông tin đăng nhập sai, hiển thị lỗi "Invalid account/email or password".
     - Nếu tài khoản bị xóa, hiển thị thông tin người xóa từ `deleted_profiles`.
   - **Kết quả**: Người dùng truy cập giao diện chính (tab Chat, Profile, Subordinates, Events, Gears).
   - **API**: `/login`

2. **Đăng xuất**
   - **Mô tả**: Người dùng thoát khỏi phiên làm việc.
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập.
   - **Luồng chính**:
     1. Người dùng nhấn nút "Đăng xuất" trong sidebar.
     2. Hệ thống xóa `session_state` (username, messages, profile).
     3. Hệ thống chuyển về giao diện đăng nhập.
   - **Kết quả**: Người dùng trở về trạng thái chưa đăng nhập.

3. **Gửi tin nhắn đến chatbot**
   - **Mô tả**: Người dùng gửi tin nhắn và nhận phản hồi từ chatbot.
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập, chọn chatbot từ danh sách (`/getChatbotList`).
   - **Luồng chính**:
     1. Người dùng chọn chatbot trong tab Chat.
     2. Người dùng nhập tin nhắn và nhấn "Gửi".
     3. Hệ thống gọi API `/chat` với `account`, `chatbotName`, `message`.
     4. Hệ thống hiển thị tin nhắn người dùng (căn phải, nền xanh) và phản hồi bot (căn trái, nền xám).
   - **Luồng phụ**:
     - Nếu API `/chat` lỗi (ví dụ: "Không thể kết nối đến chatbot"), hiển thị thông báo lỗi.
     - Nếu tin nhắn trống, yêu cầu nhập lại.
   - **Kết quả**: Tin nhắn và phản hồi hiển thị trong tab Chat.
   - **API**: `/chat`, `/getChatbotList`

4. **Gửi tin nhắn đến callbot**
   - **Mô tả**: Người dùng gửi tin nhắn và nhận phản hồi từ callbot.
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập, chọn callbot từ danh sách (`/getCallbotList`).
   - **Luồng chính**:
     1. Người dùng chọn callbot trong tab Chat.
     2. Người dùng nhập tin nhắn và nhấn "Gửi".
     3. Hệ thống gọi API `/call` với `account`, `callbotName`, `message`.
     4. Hệ thống hiển thị tin nhắn và phản hồi (tương tự chatbot).
   - **Luồng phụ**:
     - Nếu API `/call` lỗi, hiển thị thông báo lỗi.
     - Nếu tin nhắn trống, yêu cầu nhập lại.
   - **Kết quả**: Tin nhắn và phản hồi hiển thị trong tab Chat.
   - **API**: `/call`, `/getCallbotList`

5. **Xem lịch sử chat/call**
   - **Mô tả**: Người dùng xem lịch sử tin nhắn với chatbot/callbot.
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập, chọn chatbot/callbot.
   - **Luồng chính**:
     1. Hệ thống gọi API `/history/<account>/<chatbot>` hoặc `/history/<account>/<callbot>`.
     2. Hệ thống hiển thị lịch sử trong tab Chat (người dùng căn phải, bot căn trái).
   - **Luồng phụ**:
     - Nếu API `/history` lỗi hoặc bảng không tồn tại, hiển thị danh sách rỗng.
   - **Kết quả**: Lịch sử chat/call hiển thị đầy đủ.
   - **API**: `/history/<account>/<chatbot>`

6. **Xem profile**
   - **Mô tả**: Người dùng xem thông tin cá nhân (name, age, email, hierarchy, position, title).
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập.
   - **Luồng chính**:
     1. Người dùng mở tab Profile.
     2. Hệ thống gọi API `/getProfile/<account>`.
     3. Hệ thống hiển thị thông tin (name + house, age, email, hierarchy, title).
   - **Luồng phụ**:
     - Nếu API `/getProfile` lỗi, hiển thị thông báo "User information not found".
   - **Kết quả**: Thông tin profile hiển thị trong tab Profile.
   - **API**: `/getProfile/<account>`

7. **Cập nhật profile**
   - **Mô tả**: Người dùng chỉnh sửa thông tin cá nhân (name, house, birth_year, email, hierarchy, position, legion, company, platoon).
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập.
   - **Luồng chính**:
     1. Người dùng mở form chỉnh sửa trong tab Profile.
     2. Người dùng nhập thông tin và gửi.
     3. Hệ thống gọi API để cập nhật `user_information` (chưa có endpoint, cần thêm).
     4. Hệ thống làm mới tab Profile.
   - **Luồng phụ**:
     - Nếu dữ liệu không hợp lệ (ví dụ: position không đúng), hiển thị lỗi.
   - **Kết quả**: Profile được cập nhật.
   - **API**: (Cần thêm `/updateProfile`)

8. **Lên lịch huấn luyện**
   - **Mô tả**: Người dùng yêu cầu lên lịch huấn luyện qua tin nhắn chatbot.
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập, gửi tin nhắn chứa "schedule".
   - **Luồng chính**:
     1. Người dùng gửi tin nhắn với từ khóa "schedule" (ví dụ: "Schedule training on Monday").
     2. Hệ thống gọi API `/chat`, trích xuất `content`, `time_start`, `time_end` bằng LLM.
     3. Hệ thống lưu sự kiện vào `timetable_events` qua `scheduler_agent`.
     4. Hệ thống trả về xác nhận (không lưu vào lịch sử chat).
   - **Luồng phụ**:
     - Nếu trích xuất thất bại, hiển thị lỗi "Could not extract training info".
   - **Kết quả**: Sự kiện huấn luyện được lưu.
   - **API**: `/chat` (với `scheduler_agent`)

9. **Quản lý cấp dưới**
   - **Mô tả**: Người dùng xem và quản lý cấp dưới (thay đổi position, xóa profile).
   - **Điều kiện tiên quyết**: Người dùng đã đăng nhập, có quyền (theo `position_tree`).
   - **Luồng chính**:
     1. Người dùng mở tab Subordinates.
     2. Hệ thống gọi API `/getSubordinates/<account>` để lấy danh sách cấp dưới.
     3. Người dùng chọn cấp dưới, thực hiện:
        - **Thay đổi position**: Gửi API `/changePosition/<account>` với `subordinateName`, `subordinateEmail`, `newPosition`.
        - **Xóa profile**: Gửi API `/deleteProfile` với `accountRequest`, `accountToDelete`.
     4. Hệ thống làm mới danh sách cấp dưới.
   - **Luồng phụ**:
     - Nếu không có quyền, hiển thị lỗi "No permission" hoặc "Target is not your subordinate".
     - Nếu thông tin cấp dưới sai, hiển thị lỗi.
   - **Kết quả**: Danh sách cấp dưới, position, hoặc profile được cập nhật.
   - **API**: `/getSubordinates/<account>`, `/changePosition/<account>`, `/deleteProfile`

10. **Quản lý trang bị**
    - **Mô tả**: Người dùng xem và đồng bộ trang bị (thêm/xóa).
    - **Điều kiện tiên quyết**: Người dùng đã đăng nhập.
    - **Luồng chính**:
      1. Người dùng mở tab Gears.
      2. Hệ thống gọi API `/getGears/<account>` để lấy danh sách trang bị.
      3. Người dùng thêm/xóa trang bị qua form:
         - Thêm: Gửi API `/syncGear` với `action="add"`, `gear_type`, `gear_quantity`, `horse_name` (nếu là HORSE).
         - Xóa: Gửi API `/syncGear` với `action="delete"`, `gear_type`, `imageResId`.
      4. Hệ thống làm mới danh sách trang bị.
    - **Luồng phụ**:
      - Nếu dữ liệu không hợp lệ (ví dụ: `gear_type` sai), hiển thị lỗi.
    - **Kết quả**: Danh sách trang bị được cập nhật.
    - **API**: `/getGears/<account>`, `/syncGear`

## Mô tả sơ đồ
- **Diễn viên**: Người dùng (User) nằm ở bên trái.
- **Use case**: 10 hình oval (Đăng nhập, Đăng xuất, Gửi tin nhắn đến chatbot, Gửi tin nhắn đến callbot, Xem lịch sử chat/call, Xem profile, Cập nhật profile, Lên lịch huấn luyện, Quản lý cấp dưới, Quản lý trang bị) nằm ở bên phải.
- **Mối quan hệ**:
  - Người dùng tương tác trực tiếp với tất cả use case.
  - **Include**:
    - "Đăng nhập" bao gồm "Xem lịch sử chat/call", "Xem profile", "Quản lý cấp dưới", "Quản lý trang bị" (tải dữ liệu khi đăng nhập).
    - "Gửi tin nhắn đến chatbot/callbot" bao gồm "Xem lịch sử chat/call" (cập nhật lịch sử).
    - "Lên lịch huấn luyện" bao gồm "Gửi tin nhắn đến chatbot" (xử lý qua `/chat`).
  - **Extend**:
    - "Cập nhật profile" mở rộng từ "Xem profile".
    - "Quản lý cấp dưới" mở rộng từ "Xem profile" (xem cấp dưới dựa trên position).
    - "Quản lý trang bị" mở rộng từ "Xem profile" (trang bị liên quan đến account).
- **Ghi chú**:
  - API `/chat`, `/call`, `/history`, `/getProfile`, `/getSubordinates`, `/changePosition`, `/deleteProfile`, `/getGears`, `/syncGear` hỗ trợ các use case.
  - Lỗi "Không thể kết nối đến chatbot" được xử lý trong "Gửi tin nhắn đến chatbot/callbot" bằng thông báo lỗi.
  - Giao diện chat (tương tự `RecyclerView`) hiển thị tin nhắn động trong tab Chat.
  - Tab Profile hiển thị thông tin từ `user_information`, tab Subordinates hiển thị cấp dưới, tab Gears hiển thị trang bị.