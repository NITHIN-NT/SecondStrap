from django.db import models
from accounts.models import CustomUser
# Create your models here.

class AddressType(models.TextChoices):
    HOME = 'HOME', 'Home'
    WORK = 'WORK', 'Work/Office'
    OTHER = 'OTHER', 'Other'
class Address(models.Model):
    user = models.ForeignKey("accounts.CustomUser" , on_delete=models.CASCADE)
    full_name = models.CharField(max_length=250)
    address_line_1 = models.TextField()
    address_line_2 = models.TextField()
    city = models.CharField(max_length=250)
    state = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=10)
    phone_number = models.CharField(max_length=15) # Max length for international format
    country = models.CharField(max_length=250)
    is_default = models.BooleanField()
    address_type = models.CharField(
        max_length=50,
        choices=AddressType.choices,
        default=AddressType.HOME
    )

    class Meta:
        ordering = ['-is_default', 'full_name']
        db_table = 'user_addresses'

    def __str__(self):
        return f"{self.full_name}'s - Address in {self.city}"
    
    def get_full_address(self):
        parts = [
            self.full_name,
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.postal_code,
            self.state,
            self.country,
            self.address_type,
            self.phone_number,
        ]
        
        return ",".join(filter(None,parts))