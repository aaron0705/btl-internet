from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
import pymysql
from datetime import datetime, timedelta
import re


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

        cursor.execute("INSERT INTO transactions VALUES (%s, %s, %s, %s, %s)", (type, amounts, date, time, note))
        return redirect("transactions")

    cmd = "SELECT * FROM transactions"
    cursor.execute(cmd + ";")
    transactions = cursor.fetchall()
    return render(request, "transactions.html", {"transactions" : transactions})

def transaction_filer_option(request):
    if request.method == "POST":
        field = request.POST.get("field")

        options = []
        match field:
            case "type":
                options = ['thu', 'chi']
            case "amount":
                options = ["min, max", "min", "max"]
            case "date":
                options = [
                    "today",        # Hôm nay
                    "yesterday",    # Hôm qua
                    "last7",        # 7 ngày qua
                    "last30",       # 30 ngày qua
                    "this_month",   # Tháng này
                    "last_month"    # Tháng trước
                ]
            case "time":
                options = [
                    "all_day",    # Cả ngày
                    "morning",    # Buổi sáng
                    "afternoon",  # Buổi chiều
                    "evening",    # Buổi tối
                    "night"       # Ban đêm
                ]
            case "note":
                options = [
                    ("food", "Ăn uống"),
                    ("shopping", "Mua sắm"),
                    ("bills", "Hóa đơn"),
                    ("entertainment", "Giải trí"),
                    ("other", "Khác"),
                    ("has_note", "Có ghi chú"),
                    ("no_note", "Không có ghi chú")
                ]
        # Trả về trang filter.html rồi hiện lên các option dạng lựa chọn rồi chọn l
    return render(request, "filter.html", {"option" : options})

def transacton_filter(request):
    cursor.execute("SELECT * FROM transactions;")
    transactions = cursor.fetchall()
    match_transaction = []
    if request.method == "POST":
        field = request.POST.get("field")
        option = request.POST.get("option")
    
        for transaction in transactions:
            match field:
                case "type":
                    match option:
                        case 'thu':
                            if transaction['type'] == 'thu':
                                match_transaction.append(transaction)
                        case 'chi':
                            if transaction['type'] == 'chi':
                                match_transaction.append(transaction)
                    
                case "amount":
                    match option:
                        case 'min, max':
                            min = request.POST.get("min")
                            max = request.POST.get("max")
                        case 'min':
                            min = request.POST.get("min")
                            max = float('inf')
                        case 'max':
                            min = 0
                            max = request.POST.get("max")
                    if int(transaction['amount']) > min and transaction['amount'] <= max:
                        match_transaction.append(transaction)

                case "date":
                    # --- Lấy ngày hiện tại và hôm qua ---
                    today_date = datetime.today().date()
                    yesterday_date = today_date - timedelta(days=1)

                    today_str = today_date.strftime("%Y-%m-%d")
                    yesterday_str = yesterday_date.strftime("%Y-%m-%d")

                    # --- Sinh regex pattern ---
                    patterns = {
                        "today": rf"^{today_str}$",
                        "yesterday": rf"^{yesterday_str}$",
                        # last7: từ (today - 6 ngày) -> today
                        "last7": rf"^{(today_date - timedelta(days=6)).strftime('%Y-%m-%d')}|.*{today_str}$",
                        # last30: từ (today - 29 ngày) -> today
                        "last30": r"^\d{4}-\d{2}-\d{2}$",  # regex chỉ kiểm tra định dạng, khoảng ngày lọc thêm bằng logic
                        # this_month: tất cả ngày trong tháng hiện tại
                        "this_month": rf"^{today_date.strftime('%Y-%m')}-\d{{2}}$",
                        # last_month: tất cả ngày trong tháng trước
                        "last_month": rf"^{(today_date - timedelta(days=today_date.day)).strftime('%Y-%m')}-\d{{2}}$",
                    }
                    for key, pattern in patterns.items():
                        if re.match(pattern, transaction['date']):
                            match_transaction.append(transaction)
                        
                case "time":
                    patterns = {
                        # all_day: bất kỳ giờ phút hợp lệ
                        "all_day": r"^(?:[01]\d|2[0-3]):[0-5]\d$",

                        # morning: 06:00 – 11:59
                        "morning": r"^(0[6-9]|1[0-1]):[0-5]\d$",

                        # afternoon: 12:00 – 17:59
                        "afternoon": r"^(1[2-7]):[0-5]\d$",

                        # evening: 18:00 – 23:59
                        "evening": r"^(1[8-9]|2[0-3]):[0-5]\d$",

                        # night: 00:00 – 05:59
                        "night": r"^(0[0-5]):[0-5]\d$",
                    }
                    for key, pattern in patterns.items():
                        if re.match(pattern, transaction['date']):
                            match_transaction.append(transaction)
                case "note":
                    patterns = {
                        # Có ghi chú (bất kỳ ký tự nào, không chỉ khoảng trắng)
                        "has_note": r"^.+$",

                        # Không có ghi chú (chuỗi rỗng hoặc chỉ toàn khoảng trắng)
                        "no_note": r"^\s*$",

                        # Food: chứa từ khóa liên quan ăn uống
                        "food": r".*(ăn|cơm|phở|nhà hàng|quán|food).*",

                        # Shopping: chứa từ khóa liên quan mua sắm
                        "shopping": r".*(mua|shop|quần áo|giày dép|shopping).*",

                        # Bills: chứa từ khóa hóa đơn
                        "bills": r".*(hóa\s*đơn|điện|nước|internet|bill).*",

                        # Entertainment: chứa từ khóa giải trí
                        "entertainment": r".*(xem phim|karaoke|game|giải\s*trí).*",

                        # Other: có note nhưng không match nhóm nào ở trên
                        # (regex không thể tự phân biệt -> cần kiểm tra bằng logic Python)
                        "other": None  
                    }
                    for key, pattern in patterns.items():
                        if key != "other" and pattern and re.search(pattern, transaction['note'].lower()):
                            match_transaction.append(transaction)
                            break
                    else:
                        # Nếu không khớp nhóm nào nhưng note vẫn có nội dung => other
                        if transaction['note'].strip():
                            match_transaction.append(transaction)
    return render(request, "transaction.html", {"transactions" : match_transaction})

def export_csv(request):
    return render(request, "export.html")

def summary(request):
    return render(request, "summary.html")
