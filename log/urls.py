from django.urls import path
from . import views

urlpatterns = [
    path('sign_in', views.sign_in, name = "sign_in"),
    path('sign_up', views.sign_up, name = "sign_up"),
    path('sign_out', views.sign_out, name = "sign_out"),

    path('dashboard', views.dashboard, name = "dashboard"),

    path("export", views.export_csv_filter, name="export_csv_filter"),
    path("export/download", views.export_csv_download, name="export_csv_download"),

    path('summary', views.summary, name = "summary"),

    path('filter', views.transaction_filter_option, name = "filter"),
    path("transactions/page/<int:pn>/", views.transactions, name="transactions_page"),
    path("transactions/page/", views.transactions, {"pn": 1}, name="transactions_default"),
    path('transactions/save/', views.save_transactions, name="transactions_save"),

    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete')
]