# HEMA-club

### Sitemap

🏠 **Trang chủ (Dashboard)**
- 🔐 Đăng nhập / Đăng ký (streamlit-authenticator)
- 🧑‍💼 Quản lý hồ sơ  
  - Xem / Sửa thông tin  
  - Vai trò: Thành viên / Admin
- ⚔️ Quản lý CLB HEMA  
  - Danh sách thành viên  
  - Thêm / Xoá / Cập nhật
- 📅 Thời gian biểu  
  - Tạo lịch tập hợp  
  - Xem lịch theo ngày / tuần
- 🛡️ Quản lý thiết bị  
  - Thêm / Xoá trang bị  
  - Giao thiết bị cho thành viên
- 🤖 Giao tiếp với AI Agent  
  - Chat  
  - Lên lịch tập  
  - Nhận tư vấn

#### Trang Đăng nhập
![Login Screen](images/login.png)

#### Trang Đăng ký
![Register Screen](images/register.png)

#### Cấu trúc dự án
Hema-club/
├── app.py
├── back_End.py
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── chatbot.html
│   └── callbot.html
├── Database.db