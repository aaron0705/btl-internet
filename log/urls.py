from django.urls import path
from . import views

urlpatterns = [
    path('sign_in', views.sign_in, name = "sign_in"),
    path('sign_up', views.sign_up, name = "sign_up"),
    path('sign_out', views.sign_out, name = "sign_out"),
    path('dashboard', views.dashboard, name = "dashboard"),
    path('categories', views.categories, name = "categories"),
    path('transactions', views.transactions, name = "transactions"),
    path('export_csv', views.export_csv, name = "export_csv"),
    path('summary', views.summary, name = "summary")
]