from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Category, Transaction
from .forms import CategoryForm
from django.core.paginator import Paginator 
import csv
from django.http import HttpResponse

# Đăng ký
def sign_up(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            return render(request, "signup.html", {"error": "Mật khẩu không trùng khớp"})

        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Tài khoản đã tồn tại"})

        new_user = User.objects.create_user(username=username, password=password1)
        login(request, new_user)  # đăng nhập ngay sau khi đăng ký
        return redirect("sign_in")

    return render(request, "signup.html")


# Đăng nhập
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


# Đăng xuất
def sign_out(request):
    logout(request)
    return redirect("sign_in")


# Dashboard
@login_required
def dashboard(request):
    return render(request, "dashboard.html")



@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'categories/category_list.html', {'categories': categories})


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
    return render(request, "categories/category_form.html", {"form": form})


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
    return render(request, "categories/category_form.html", {"form": form})


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        category.delete()
        return redirect("category_list")
    return render(request, "categories/category_confirm_delete.html", {"category": category})

@login_required
def transactions(request):
    if request.method == "POST":
        Transaction.objects.create(
            user=request.user,
            type=request.POST.get("type"),
            amount=request.POST.get("amount"),  # đổi từ amounts -> amount
            note=request.POST.get("note"),
        )
        return redirect("transactions")

    transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-time')

    paginator = Paginator(transactions, 10)  # mỗi trang 10 giao dịch
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "transactions.html", {
        "transactions": page_obj.object_list,
        "page_obj": page_obj
    })

@login_required
def export_csv_page(request):
    """Hiển thị form chọn kiểu lọc trước khi xuất CSV"""
    return render(request, "export_csv.html")

# Xuất CSV
@login_required
def export_csv(request):
    filter_type = request.GET.get("filter_type", "all")
    value = request.GET.get("value", "")

    print(">>> DEBUG:", filter_type, value)  # Kiểm tra xem có nhận được không

    transactions = Transaction.objects.filter(user=request.user)

    if filter_type == "day" and value:
        transactions = transactions.filter(date=value)
    elif filter_type == "month" and value:
        year, month = value.split("-")
        transactions = transactions.filter(date__year=year, date__month=month)
    elif filter_type == "year" and value:
        transactions = transactions.filter(date__year=value)

    transactions = transactions.order_by('-date', '-time')

    response = HttpResponse(content_type='text/csv')
    filename = f"transactions_{filter_type}_{value or 'all'}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Ngày', 'Giờ', 'Loại', 'Danh mục', 'Số tiền', 'Ghi chú'])

    for t in transactions:
        writer.writerow([
            t.date.strftime('%Y-%m-%d'),
            t.time.strftime('%H:%M:%S'),
            t.get_type_display(),
            t.category.name if t.category else 'Chưa phân loại',
            f"{t.amount:.2f}",
            t.note
        ])
    return response


# Tổng kết
@login_required
def summary(request):
    return HttpResponse("Chưa triển khai")