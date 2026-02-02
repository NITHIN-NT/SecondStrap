from django.db import models
from accounts.models import CustomUser
from django.core.validators import RegexValidator
# Create your models here.

class AddressType(models.TextChoices):
    HOME = 'HOME', 'Home'
    WORK = 'WORK', 'Work/Office'
    OTHER = 'OTHER', 'Other'
class Address(models.Model):
    phone_validator = RegexValidator(
        regex=r'^[6-9]\d{9}$',
        message="Enter a valid 10-digit Indian phone number.",
        code="invalid_phone"
    )
    name_validator_regex = RegexValidator(
        regex=r'^[A-Za-z\s]+$',
        message="Name must contain only letters",
        code='invalid_name'
    )
    postal_code_validator = RegexValidator(
        regex=r'^[0-9]{6}$',
        message="Enter a valid 6-digit postal code.",
        code="invalid_postal_code"
    )
    address_line_validator = RegexValidator(
        regex=r"^[A-Za-z0-9\s,./#\-()]+$",
        message="Enter a valid address line (only letters, numbers and , . / # - ( ) allowed).",
        code="invalid_address_line"
    )
    user = models.ForeignKey("accounts.CustomUser" , on_delete=models.CASCADE)
    full_name = models.CharField(max_length=250,validators=[name_validator_regex])
    address_line_1 = models.TextField(validators=[address_line_validator])
    address_line_2 = models.TextField(blank=True, null=True,validators=[address_line_validator])
    city = models.CharField(max_length=250,validators=[name_validator_regex])
    state = models.CharField(max_length=250,validators=[name_validator_regex])
    postal_code = models.CharField(max_length=10,validators=[postal_code_validator])
    phone_number = models.CharField(max_length=15,validators=[phone_validator]) # Max length for international format
    country = models.CharField(max_length=250,validators=[name_validator_regex])
    is_default = models.BooleanField()
    address_type = models.CharField(
        max_length=50,
        choices=AddressType.choices,
        default=AddressType.HOME,
        blank=True,
        null=True
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