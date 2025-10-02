from django.db import models
# Create your models here.
from django.contrib.auth.models import User


class Category(models.Model):
    TYPE_CHOICES = [
        ('income', 'Thu nhập'),
        ('expense', 'Chi tiêu'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    color = models.CharField(max_length=7, default="#291717")  # HEX màu, VD: #ff0000
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')  # mỗi user không trùng tên category
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"