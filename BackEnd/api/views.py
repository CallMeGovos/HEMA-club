# api/views.py
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User, Equipment, TrainingSession
import bcrypt
import datetime

class RegisterView(APIView):
    def post(self, request):
        try:
            data = request.data
            email = data.get('email')
            phone_number = data.get('phone_number')
            username = data.get('username')
            name = data.get('name')
            address = data.get('address', '')
            major = data.get('major', '')
            password = data.get('password')

            # Kiểm tra các trường bắt buộc
            if not all([email, phone_number, username, name, password]):
                return Response({'error': 'Vui lòng điền đầy đủ thông tin'}, status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra email và username đã tồn tại
            if User.objects.filter(email=email).exists():
                return Response({'error': 'Email đã được sử dụng'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(username=username).exists():
                return Response({'error': 'Tên đăng nhập đã được sử dụng'}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(phone_number=phone_number).exists():
                return Response({'error': 'Số điện thoại đã được sử dụng'}, status=status.HTTP_400_BAD_REQUEST)

            # Mã hóa mật khẩu
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Tạo người dùng mới
            user = User(
                email=email,
                phone_number=phone_number,
                username=username,
                name=name,
                address=address,
                major=major,
                password=hashed_password
            )
            user.save()

            return Response({'message': 'Đăng ký thành công'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'Lỗi: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    def post(self, request):
        try:
            username = request.data.get('username')
            password = request.data.get('password')

            if not all([username, password]):
                return Response({'error': 'Vui lòng cung cấp tên đăng nhập và mật khẩu'}, status=status.HTTP_400_BAD_REQUEST)

            # Tìm người dùng
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return Response({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'}, status=status.HTTP_401_UNAUTHORIZED)

            # Kiểm tra mật khẩu
            if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                return Response({'message': 'Đăng nhập thành công', 'name': user.name}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Tên đăng nhập hoặc mật khẩu không đúng'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': f'Lỗi: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardView(APIView):
    def get(self, request):
        try:
            total_members = User.objects.count()
            total_equipments = Equipment.objects.count()
            upcoming_sessions = TrainingSession.objects.filter(date__gte=datetime.datetime.now()).count()

            return Response({
                'total_members': total_members,
                'total_equipments': total_equipments,
                'upcoming_sessions': upcoming_sessions
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Lỗi: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)