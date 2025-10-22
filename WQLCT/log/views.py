from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import pymysql
from datetime import datetime, timedelta, date
import re
from .models import Category
from .forms import CategoryForm
from django.core.paginator import Paginator 
import json
import csv
from django.http import HttpResponse
from django.core.mail import EmailMessage
from io import StringIO
import io
from django.core.mail import send_mail


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
        login(request, new_user)  
        # đăng nhập ngay sau khi đăng ký
        return redirect("sign_in")

    return render(request, "signup.html")


# đăng nhập
def sign_in(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "signin.html", {"error": "Sai tài khoản hoặc mật khẩu"})
        
    return render(request, "signin.html")


# đăng xuất
@login_required
def sign_out(request):
    logout(request)
    return redirect("sign_in")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            return redirect("category_list")
    else:
        form = CategoryForm()
    return render(request, "category_form.html", {"form": form})


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    return render(request, "category_form.html", {"form": form})


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.delete()
        return redirect("category_list")
    return render(request, "categories/category_confirm_delete.html", {"category": category})


@login_required
def transactions(request):
    filter_flag = request.GET.get("filter", "false") == "true"
    pn = int(request.GET.get("pn", 1))
    if request.method == "POST":
        type = request.POST.get("type")
        amounts = request.POST.get("amounts")
        now = datetime.now()
        date = now.date()
        time = now.strftime("%H:%M")
        note = request.POST.get("note")

        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="",
            port=3307,
            database="btl_web",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        # ✅ fix:2025-10-05 — Thêm tên cột rõ ràng + commit DB
        cursor.execute(
            "INSERT INTO transactions (type, amount, date, time, note) VALUES (%s, %s, %s, %s, %s)",
            (type, amounts, date, time, note)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("transactions")

    # ✅ fix:2025-10-05 — Đọc dữ liệu rồi đóng kết nối
    transactions = []
    transactions = get_transactions("all", "")

    if filter_flag:
        transactions = transacton_filter(request, transactions)

    page_list, page = paging_obj(transactions, pn)
    return render(request, "transactions.html", {
        "page_list": page_list,
        "page_obj": page
    })


def filter_by_type(transactions, option):
    """Lọc giao dịch theo loại thu/chi"""
    return [t for t in transactions if t["type"] == option]


def filter_by_amount(transactions, request):
    """Lọc giao dịch theo số tiền (min, max)"""
    min_val = float(request.POST.get("min", 0))
    max_val = float(request.POST.get("max", float("inf")))
    return [
        t for t in transactions
        if min_val <= float(t["amount"]) <= max_val
    ]


def filter_by_date(transactions, option):
    """Lọc giao dịch theo ngày (hôm nay, hôm qua, tuần này,...)"""
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")
    yesterday_str = yesterday.strftime("%Y-%m-%d")

    patterns = {
        "today": rf"^{today_str}$",
        "yesterday": rf"^{yesterday_str}$",
        "last7": rf"^{(today - timedelta(days=6)).strftime('%Y-%m-%d')}|.*{today_str}$",
        "last30": r"^\d{4}-\d{2}-\d{2}$",
        "this_month": rf"^{today.strftime('%Y-%m')}-\d{{2}}$",
        "last_month": rf"^{(today - timedelta(days=today.day)).strftime('%Y-%m')}-\d{{2}}$",
    }

    pattern = patterns.get(option)
    if not pattern:
        return transactions
    return [t for t in transactions if re.search(pattern, t["date"])]


def filter_by_time(transactions, option):
    """Lọc giao dịch theo khung giờ"""
    patterns = {
        "all_day": r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        "morning": r"^(0[6-9]|1[0-1]):[0-5]\d$",
        "afternoon": r"^(1[2-7]):[0-5]\d$",
        "evening": r"^(1[8-9]|2[0-3]):[0-5]\d$",
        "night": r"^(0[0-5]):[0-5]\d$",
    }
    pattern = patterns.get(option)
    if not pattern:
        return transactions
    return [t for t in transactions if re.match(pattern, t["time"])]


def filter_by_note(transactions, option):
    """Lọc giao dịch theo nội dung ghi chú"""
    patterns = {
        "has_note": r"^.+$",
        "no_note": r"^\s*$",
        "food": r".*(ăn|cơm|phở|nhà hàng|quán|food).*",
        "shopping": r".*(mua|shop|quần áo|giày dép|shopping).*",
        "bills": r".*(hóa\s*đơn|điện|nước|internet|bill).*",
        "entertainment": r".*(xem phim|karaoke|game|giải\s*trí).*",
        "other": None
    }

    pattern = patterns.get(option)
    result = []
    for t in transactions:
        note = t["note"].lower().strip() if t["note"] else ""
        if pattern and re.search(pattern, note):
            result.append(t)
        elif option == "other" and note and not any(
            re.search(p, note) for k, p in patterns.items() if k not in ["other", "no_note"]
        ):
            result.append(t)
    return result

@login_required
def transaction_filter_option(request):  
    # ✅ fix:2025-10-05 — đổi tên đúng (filer → filter)
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
                    "today", "yesterday", "last7", "last30", "this_month", "last_month"
                ]
            case "time":
                options = [
                    "all_day", "morning", "afternoon", "evening", "night"
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

    # ✅ fix:2025-10-05 — đổi key trả về cho đúng
    return render(request, "filter.html", {"options": options})


@login_required
def transacton_filter(request, transactions):
    """Hàm tổng điều hướng đến các bộ lọc con"""
    if request.method != "POST":
        return transactions

    field = request.POST.get("field")
    option = request.POST.get("option")

    match field:
        case "type":
            return filter_by_type(transactions, option)
        case "amount":
            return filter_by_amount(transactions, request)
        case "date":
            return filter_by_date(transactions, option)
        case "time":
            return filter_by_time(transactions, option)
        case "note":
            return filter_by_note(transactions, option)
        case _:
            return transactions


# ✅ fix:2025-10-05 — Giữ nguyên logic phân trang
def paging_obj(obj, pn):
    paginator = Paginator(obj, 10)
    page_obj = paginator.get_page(pn)
    return [page_obj.object_list, page_obj]


# --- Hàm chung để lấy danh sách giao dịch từ CSDL ---
def get_transactions(filter_type="all", value=""):
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="222004",
        port=3306,
        database="btl_web",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    query = "SELECT type, amount, date, time, note FROM transactions"
    params = ()

    query_map = {
        "day": "DATE(date) = %s",
        "month": "DATE_FORMAT(date, '%Y-%m') = %s",
        "year": "YEAR(date) = %s"
    }

    if filter_type in query_map and value:
        query += f" WHERE {query_map[filter_type]}"
        params = (value,)

    query += " ORDER BY date;"
    cursor.execute(query, params)
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()
    return transactions

@login_required
# --- Hàm 1: Hiển thị form lọc và kết quả ---
def export_csv_filter(request):
    filter_type = request.GET.get("filter_type", "all")
    value = request.GET.get("value", "")
    transactions = get_transactions(filter_type, value)

    return render(request, "export_csv.html", {"transactions" : transactions})

@login_required
def export_csv_download(request):
    filter_type = request.POST.get("filter_type", "all")
    value = request.POST.get("value", "")
    export_method = request.POST.get("export_method", "download")
    email_to = request.POST.get("email_to", "")

    transactions = get_transactions(filter_type, value)

    # --- Tạo file CSV trong bộ nhớ ---
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Loại', 'Số tiền', 'Ngày', 'Giờ', 'Ghi chú'])

    for t in transactions:
        date_str = t["date"].strftime("%Y-%m-%d") if isinstance(t["date"], (datetime, date)) else str(t["date"])
        time_str = t["time"].strftime("%H:%M:%S") if hasattr(t["time"], "strftime") else str(t["time"])
        writer.writerow([
            t["type"],
            f"{float(t['amount']):.2f}",
            date_str,
            time_str,
            t["note"] or ""
        ])

    csv_data = buffer.getvalue()
    buffer.close()

    # --- Nếu chọn tải về ---
    if export_method == "download":
        response = HttpResponse(csv_data, content_type='text/csv')
        filename = f"transactions_{filter_type}_{value or 'all'}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # --- Nếu chọn gửi qua email ---
    elif export_method == "email" and email_to:
        email = EmailMessage(
            subject="Dữ liệu CSV bạn yêu cầu",
            body="Dưới đây là file CSV chứa dữ liệu giao dịch bạn đã yêu cầu.",
            to=[email_to],
        )
        email.attach(f"transactions_{filter_type}_{value or 'all'}.csv", csv_data, "text/csv")
        email.send()

        return HttpResponse("<h3>✅ File CSV đã được gửi tới email của bạn!</h3>")

    else:
        return HttpResponse("<h3>⚠️ Vui lòng nhập email hợp lệ.</h3>")
    
def test_email(request):
    send_mail(
        "Test",
        "Hello from Django!",
        "youremail@gmail.com",
        ["your_other_mail@gmail.com"]
    )
    return HttpResponse("Email sent successfully!")
    

@login_required
def summary(request):
    
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="222004",
        port=3306,
        database="btl_web",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # Lấy tùy chọn người dùng chọn tổng kết
    summary_option = request.GET.get("option", "month")  # mặc định là theo tháng

    # Xác định câu truy vấn MySQL phù hợp
    query = ""
    params = ()

    # Lấy ngày hiện tại
    now = datetime.now()

    # ---- Các truy vấn tổng hợp ----
    match summary_option:
        case "month":
            query = """
                SELECT MONTH(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) = %s
                GROUP BY MONTH(date)
                ORDER BY MONTH(date);
            """
            params = (now.year,)

        case "quarter":
            query = """
                SELECT QUARTER(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) = %s
                GROUP BY QUARTER(date)
                ORDER BY QUARTER(date);
            """
            params = (now.year,)

        case "year":
            query = """
                SELECT YEAR(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                GROUP BY YEAR(date)
                ORDER BY YEAR(date);
            """

        case "2year":
            start_year = now.year - 1
            query = """
                SELECT YEAR(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) >= %s
                GROUP BY YEAR(date)
                ORDER BY YEAR(date);
            """
            params = (start_year,)

        case "5year":
            start_year = now.year - 4
            query = """
                SELECT YEAR(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) >= %s
                GROUP BY YEAR(date)
                ORDER BY YEAR(date);
            """
            params = (start_year,)

        case "10year":
            start_year = now.year - 9
            query = """
                SELECT YEAR(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) >= %s
                GROUP BY YEAR(date)
                ORDER BY YEAR(date);
            """
            params = (start_year,)

        case _:
            query = """
                SELECT MONTH(date) AS period,
                       SUM(CASE WHEN type='thu' THEN amount ELSE 0 END) AS total_income,
                       SUM(CASE WHEN type='chi' THEN amount ELSE 0 END) AS total_expense
                FROM transactions
                WHERE YEAR(date) = %s
                GROUP BY MONTH(date)
                ORDER BY MONTH(date);
            """
            params = (now.year,)

    # Thực thi truy vấn
    cursor.execute(query, params)
    result = cursor.fetchall()

    # ---- Logic bổ sung bằng Python ----
    total_income = sum(r['total_income'] for r in result)
    total_expense = sum(r['total_expense'] for r in result)
    total_expense_and_income = total_expense + total_income
    net_balance = total_income - total_expense

    # fix:2025-10-10 - chuẩn bị dữ liệu để hiển thị biểu đồ
    labels = [str(r['period']) for r in result]
    income_data = [float(r['total_income']) for r in result]
    expense_data = [float(r['total_expense']) for r in result]

    # fix:2025-10-10 - truyền sang template ở dạng JSON để Chart.js đọc được
    context = {
        "labels": json.dumps(labels),
        "income_data": json.dumps(income_data),
        "expense_data": json.dumps(expense_data),
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
    }

    cursor.close()
    conn.close()
    return render(request, "summary.html", context)

    