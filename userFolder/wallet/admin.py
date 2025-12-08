from django.contrib import admin
from .models import *

class WalletModel(admin.ModelAdmin):
    list_display = ['user','balance','created_at','updated_at','is_active']
admin.site.register(Wallet,WalletModel)
class TransactionModel(admin.ModelAdmin):
    list_display = ['transaction_id','wallet','transaction_type','amount','description','status','related_order','timestamp']
admin.site.register(Transaction,TransactionModel)