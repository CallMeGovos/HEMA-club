import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import requests
import bcrypt


def initialize_session_state():
    defaults = {
        'authentication_status': None,
        'name': None,
        'username': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Hàm gọi API từ Django backend
def get_dashboard_data():
    try:
        response = requests.get('http://localhost:8000/api/dashboard/')
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.RequestException:
        return None

# Hàm gọi API đăng ký
def register_user_to_backend(email, phone_number, username, name, address, major, password):
    try:
        response = requests.post('http://localhost:8000/api/register/', json={
            'email': email,
            'phone_number': phone_number,
            'username': username,
            'name': name,
            'address': address,
            'major': major,
            'password': password

        })
        if response.status_code == 201:
            return True, "Đăng ký thành công!"
        else:
            return False, response.json().get('error', 'Đăng ký thất bại')
    except requests.RequestException as e:
        return False, f"Lỗi kết nối: {str(e)}"

# Hàm gọi API đăng nhập
def login_user_to_backend(username, password):
    try:
        response = requests.post('http://localhost:8000/api/login/', json={
            'username': username,
            'password': password
        })
        if response.status_code == 200:
            return True, response.json().get('name', ''), username
        else:
            return False, response.json().get('error', 'Đăng nhập thất bại'), None
    except requests.RequestException as e:
        return False, f"Lỗi kết nối: {str(e)}", None

# Trang chủ (View)
def main_page():
    st.title("HEMA Club Dashboard")
    st.write("Chào mừng đến với hệ thống quản lý CLB HEMA")
    
    # Lấy dữ liệu từ backend
    data = get_dashboard_data()
    if data:
        st.subheader("Thông tin tổng quan")
        st.write(f"Tổng số thành viên: {data.get('total_members', 0)}")
        st.write(f"Số thiết bị: {data.get('total_equipments', 0)}")
        st.write(f"Số lịch tập sắp tới: {data.get('upcoming_sessions', 0)}")
    else:
        st.error("Không thể kết nối đến backend")

# Form đăng ký (View + Controller)
def register_page():
    st.title("Đăng ký tài khoản")
    with st.form("register_form"):
        username = st.text_input("Tên đăng nhập")
        email = st.text_input("Email")
        phone_number = st.text_input("Số điện thoại")
        name = st.text_input("Họ tên")
        address = st.text_input("Địa chỉ")
        major = st.text_input("Ngành học")
        password = st.text_input("Mật khẩu", type="password")
        password_confirm = st.text_input("Xác nhận mật khẩu", type="password")
        submit = st.form_submit_button("Đăng ký")

        if submit:
            if password != password_confirm:
                st.error("Mật khẩu và xác nhận mật khẩu không khớp")
            elif not all([username, email, name, password]):
                st.error("Vui lòng điền đầy đủ thông tin")
            else:
                success, message = register_user_to_backend(email, phone_number, address, major,username, name, password)
                if success:
                    st.success(message)
                    if st.button("Quay lại đăng nhập"):
                        st.session_state.page = "Đăng nhập"
                        st.rerun()
                else:
                    st.error(message)

# Giao diện chính (Controller)
def main():
    initialize_session_state()
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None

    # Sidebar điều hướng
    page = st.sidebar.selectbox("Chọn trang", ["Đăng nhập", "Đăng ký"])

    if page == "Đăng ký":
        register_page()
    else:
        if st.session_state["authentication_status"]:
            st.sidebar.write(f'Chào {st.session_state["name"]}')
            st.form_submit_button("Đăng xuất", on_click=lambda: [st.session_state.update(authentication_status=None, name=None, username=None), st.rerun()])
            main_page()
        else:
            st.title("Đăng nhập")
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập")
                password = st.text_input("Mật khẩu", type="password")
                submit = st.form_submit_button("Đăng nhập")

                if submit:
                    success, message, name = login_user_to_backend(username, password)
                    if success:
                        st.session_state["authentication_status"] = True
                        st.session_state["name"] = name
                        st.session_state["username"] = username
                        st.rerun()
                    else:
                        st.session_state["authentication_status"] = False
                        st.error(message)

if __name__ == "__main__":
    main()