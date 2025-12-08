from django.db import models
from django.conf import settings
from decimal import Decimal
from userFolder.order.models import OrderMain

class TransactionType(models.TextChoices):
    CREDIT = 'CR', 'Credit' 
    DEBIT = 'DB', 'Debit'   

class TransactionStatus(models.TextChoices):
    PENDING = 'PD', 'Pending'
    COMPLETED = 'CP', 'Completed'
    FAILED = 'FL', 'Failed'
    REFUNDED = 'RF', 'Refunded'
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='wallet')
    balance = models.DecimalField(max_digits=10,decimal_places=2,default=Decimal(0.00),verbose_name='Current Balance')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"Wallet for {self.user.first_name} | Balance: {self.balance}"
    
    
class Transaction(models.Model):
    wallet = models.ForeignKey(Wallet,on_delete=models.CASCADE,related_name='transactions',verbose_name='Wallet')
    transaction_id = models.CharField(max_length=100,unique=True,verbose_name='Transaction ID')
    transaction_type = models.CharField(max_length=2,choices=TransactionType.choices,verbose_name='Type')
    amount = models.DecimalField(max_digits=10,decimal_places=2,verbose_name='Amount')
    description = models.CharField(max_length=255,blank=True,null=True)
    status = models.CharField(max_length=2,choices=TransactionStatus.choices,default=TransactionStatus.PENDING)
    related_order = models.ForeignKey(OrderMain,on_delete=models.SET_NULL,null=True,blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"

    def __str__(self):
        return f"{self.transaction_type} {self.amount} for {self.wallet.user.first_name}"