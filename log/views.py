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
from django.http import HttpResponse, HttpResponseRedirect
import yfinance as yf
import requests
from django.core.mail import EmailMessage
from io import StringIO
import io
from django.core.mail import send_mail
from urllib.parse import urlencode
from django.urls import reverse



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
    tickers = {
        "VN-Index": "^VNINDEX.VN",
        "S&P 500": "^GSPC",
        "Dow Jones": "^DJI",
        "Vàng": "GC=F",
        "Dầu Brent": "BZ=F"
    }

    data = {}
    for name, code in tickers.items():
        try:
            ticker = yf.Ticker(code)
            hist = ticker.history(period="5d")  # 5 ngày gần nhất
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            change = round((last - prev) / prev * 100, 2)
            data[name] = {"price": round(last, 2), "change": change}
        except Exception:
            data[name] = {"price": None, "change": None}

    # --- Lấy tin tức đầu tư ---
    news_api = "https://newsapi.org/v2/everything"
    params = {
        "q":"tesla",
        "sortBy":"publishedAt",
        "language": "en",
        "apiKey": "5609d1642d77413e8073dc7247b79575",
        "pageSize": 5
    }
    
    news_list = []

    try:
        res = requests.get(news_api, params=params)
        res.raise_for_status()  # Kiểm tra lỗi HTTP
        news_data = res.json() 
        print(res.json())
        print("\n")
        news = news_data.get("articles", [])
        for n in news:
            news_list.append({
                "title": n.get("title"),
                "url": n.get("url"),
                "source": n.get("source", {}).get("name"),
                "description": n.get("description", ""),
                "publishedAt": n.get("publishedAt")
            })
    except Exception as e:
        print("Lỗi khi lấy tin:", e)
        news_list = []

    print(f"News list is {news_list}\n")
    return render(request, "dashboard.html", {
        "market_data": data,
        "news_list": news_list,
    })


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
    return render(request, "category_confirm_delete.html", {"category": category})


@login_required
def save_transactions(request):
    if request.method == "POST":
        type = request.POST.get("type")
        category = request.POST.get("category")
        amount = request.POST.get("amounts")
        note = request.POST.get("note", "").strip()

        # Xử lý ngày giờ
        date_input = request.POST.get("date")
        time_input = request.POST.get("time")
        ampm = request.POST.get("ampm")

        now = datetime.now()

        if date_input:
            try:
                date_val = datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError:
                # fallback ngày hiện tại nếu người dùng nhập sai
                date_val = now.date()
        else:
            date_val = now.date()

        # Giờ
        if time_input:
            try:
                h_str, m_str = time_input.split(":")[:2]
                h = int(h_str)
                m = int(m_str)
            except Exception:
                h, m = now.hour, now.minute

            # Nếu input là 24h (13..23) => bỏ qua AM/PM
            # Nếu input là 0..12 và có AM/PM => mới áp dụng quy tắc 12h
            if 0 <= h <= 12 and ampm in ("AM", "PM"):
                if ampm == "PM" and h != 12:
                    h += 12           # 1..11 PM -> +12
                elif ampm == "AM" and h == 12:
                    h = 0             # 12 AM -> 00

            # Chuẩn hoá lại phạm vi giờ/phút an toàn
            h = min(max(h, 0), 23)
            m = min(max(m, 0), 59)

            time_val = f"{h:02d}:{m:02d}:00"     # lưu dạng HH:MM:SS cho MySQL TIME
        else:
            time_val = now.strftime("%H:%M:00")

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

        cursor.execute(
            "INSERT INTO transactions (type, amount, date, time, note, category) VALUES (%s, %s, %s, %s, %s, %s)",
            (type, amount, date_val, time_val, note, category)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return redirect("transactions_default")


@login_required
def transactions(request, pn=None):
    # pn có thể dùng từ path /transactions/page/<pn>/ hoặc GET ?pn=
    pn = pn or int(request.GET.get("pn", 1))
    field = None
    option = None
    
    # đọc filter
    if request.GET.get("filter") == "true":
        field = request.GET.get("field")
        option = request.GET.get("option")
    categories = Category.objects.all()

    # Lấy dữ liệu ban đầu
    transactions = get_transactions("all", "")

    # ✅ gọi filter nếu có param
    if field and option:
        transactions = transacton_filter(request.GET, transactions)

    page_list, page = paging_obj(transactions, pn)
    return render(request, f"transactions.html", {
        "page_list": page_list,
        "page_obj": page,
        'categories': categories
    })


def filter_by_type(transactions, option):
    """Lọc giao dịch theo loại thu/chi"""
    return [t for t in transactions if t["type"] == option]


def filter_by_amount(transactions, request):
    min_val = request.get("min")
    max_val = request.get("max")

    min_val = float(min_val) if min_val else 0
    max_val = float(max_val) if max_val else float("inf")

    return [
        t for t in transactions
        if min_val <= float(t["amount"]) <= max_val
    ]


def filter_by_date(transactions, option):
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)

    if option == "today":
        return [t for t in transactions if t["date"] == today]

    if option == "yesterday":
        return [t for t in transactions if t["date"] == yesterday]

    if option == "last7":
        start = today - timedelta(days=7)
        return [t for t in transactions if start <= t["date"] <= today]

    if option == "last30":
        start = today - timedelta(days=30)
        return [t for t in transactions if start <= t["date"] <= today]

    if option == "this_month":
        return [t for t in transactions
                if t["date"].year == today.year and t["date"].month == today.month]

    if option == "last_month":
        last_month = today.month - 1 or 12
        year = today.year if today.month > 1 else today.year - 1
        return [t for t in transactions
                if t["date"].year == year and t["date"].month == last_month]

    return transactions


def filter_by_category(transactions, option):
    opt = (option or "").strip().lower()
    return [t for t in transactions if (t.get("category") or "").strip().lower() == opt]


def filter_by_time(transactions, option):
    def get_hour(t):
        return t["time"].hour if hasattr(t["time"], "hour") else int(str(t["time"])[:2])

    if option == "all_day":
        return transactions

    if option == "morning":
        # 06:00 → 11:59
        return [t for t in transactions if 6 <= get_hour(t) <= 11]

    if option == "afternoon":
        # 12:00 → 17:59
        return [t for t in transactions if 12 <= get_hour(t) <= 17]

    if option == "evening":
        # 18:00 → 21:59
        return [t for t in transactions if 18 <= get_hour(t) <= 21]

    if option == "night":
        # 22:00 → 05:59 (qua ngày kế tiếp)
        return [t for t in transactions if get_hour(t) >= 22 or get_hour(t) <= 5]

    return transactions


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
    field = None
    options = []
    categories = None
    selected_option = None

    if request.method == "POST":
        field = request.POST.get("field") or request.GET.get("field")
        stage = request.POST.get("stage")

        # BƯỚC 1: Người dùng chọn field → hiển thị options của field
        if stage == "select_field":
            if field == "type":
                options = ["thu", "chi"]
            elif field == "amount":
                options = ["min,max", "min", "max"]
            elif field == "date":
                options = ["today", "yesterday", "last7", "last30", "this_month", "last_month"]
            elif field == "category":
                # lấy danh mục của user, hiển thị như options
                categories = Category.objects.filter(user=request.user).order_by("name")
            elif field == "time":
                options = ["all_day", "morning", "afternoon", "evening", "night"]
            elif field == "note":
                options = ["has_note", "no_note", "food", "shopping", "bills", "entertainment", "other"]

            return render(request, "filter.html", {
                "field": field,
                "options": options,         # ⬅️ dùng "options" (không phải "option")
                "categories": categories
            })

        # BƯỚC 2: Người dùng chọn option
        if stage == "choose_option":
            selected_option = request.POST.get("option", "")

            # Nếu field = amount → cần hỏi thêm min/max tùy option
            if field == "amount":
                return render(request, "filter.html", {
                    "field": field,
                    "options": ["min,max", "min", "max"],
                    "selected_option": selected_option,  # để template biết hiển thị input nào
                })

            # Field khác amount → lọc ngay (redirect về trang giao dịch kèm query)
            url = reverse("transactions_page", kwargs={"pn": 1})
            return HttpResponseRedirect(
                f"{url}?filter=true&field={field}&option={selected_option}"
            )

        # BƯỚC 3: Submit min/max cho amount → redirect về trang giao dịch
        if stage == "filter":
            selected_option = request.POST.get("selected_option") or request.POST.get("option") or ""
            min_val = request.POST.get("min", "")
            max_val = request.POST.get("max", "")

            qs = {"filter": "true", "field": "amount", "option": selected_option}
            if min_val:
                qs["min"] = min_val
            if max_val:
                qs["max"] = max_val

            url = reverse("transactions_page", kwargs={"pn": 1})
            return HttpResponseRedirect(f"{url}?{urlencode(qs)}")

    # Lần đầu mở form
    return render(request, "filter.html")


def transacton_filter(request, transactions):
    field = request.get("field")
    option = request.get("option")

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
        case "category":  # fix:2025-11-01 — thêm xử lý category
            return filter_by_category(transactions, option)
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
        password="",
        port=3307,
        database="btl_web",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    query = "SELECT type, amount, date, time, note, category FROM transactions"
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

@login_required
def summary(request):
    
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



    
