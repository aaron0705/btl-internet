from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import pymysql
from datetime import datetime


# Create your views here.\
# Kết nối database
conn = pymysql.connect(
    host="localhost",
    user="django",
    password="matkhau123",
    port=3306,
    database="btl_web",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

# 2. Tạo cursor
cursor = conn.cursor()

# đăng ký
def sign_up(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            return render(request, "signup.html", {"error": "Mật khẩu không trùng khớp"})

        # Kiểm tra user đã tồn tại chưa
        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Tài khoản đã tồn tại"})

        # Tạo user mới
        new_user = User.objects.create_user(username=username, password=password1)
        login(request, new_user)  # đăng nhập ngay sau khi đăng ký
        return redirect("sign_in")

    return render(request, "signup.html")

# đăng nhập
def sign_in(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Đúng tài khoản -> tạo và lưu trong bảng
            login(request, user)
            return redirect("dashboard")  # chuyển hướng sau khi đăng nhập trở về trang chính
        else:
            # Sai thông tin -> lại chuyển về trang đăng nhập
            return render(request, "signin.html", {"error": "Sai tài khoản hoặc mật khẩu"})
        
    return render(request, "signin.html")

# đăng xuất
def sign_out(request):
    logout(request)
    return redirect("sign_in")

def dashboard(request):
    return render(request, "dashboard.html")

def categories(request):
    return 

def transactions(request):
    if request.method == "POST":
        type = request.POST.get("type")
        amounts = request.POST.get("amounts")
        now = datetime.now()
        date = now.date()
        time = now.time()
        note = request.POST.get("note")

        cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s, %s)", (type, amounts, date, time, note))
        return redirect("transactions")

    cmd = "SELECT * FROM transactions"
    cursor.execute(cmd + ";")
    transactions = cursor.fetchall()
    return render(request, "transactions.html", {"transactions" : transactions})

def export_csv(request):
    return

def summary(request):
    return
