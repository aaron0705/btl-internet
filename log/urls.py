from django.urls import path
from . import views

urlpatterns = [
    path('sign_in', views.sign_in, name = "sign_in"),
    path('sign_up', views.sign_up, name = "sign_up"),
    path('sign_out', views.sign_out, name = "sign_out"),
    path('dashboard', views.dashboard, name = "dashboard"),
    path('export_csv', views.export_csv, name = "export_csv"),
    path('summary', views.summary, name = "summary"),
    path("transactions/", views.transactions, name="transactions"),
    path('transactions/filter_option', views.transaction_filter_option, name = "filter_option"),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete')
]