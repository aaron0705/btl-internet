from django.db import models
# Create your models here.
from django.contrib.auth.models import User

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)  
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)   # đổi amounts -> amount
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()} - {self.amount}"


class Category(models.Model):
    TYPE_CHOICES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    color = models.CharField(max_length=7, default='#cccccc')  # HEX màu, VD: #ff0000
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')  # mỗi user không trùng tên category
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"