import random
import string
from django.db import models
from django.conf import settings


def generate_referral_code():
    """Generate a unique 8-character alphanumeric referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class Referral(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='referrals')
    referral_code = models.CharField(max_length=10, default=generate_referral_code, unique=True,editable=False,db_index=True)
    used_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Referral'
    
    def __str__(self):
        return f"{self.user.first_name} - {self.referral_code}"
    
    def save(self, *args, **kwargs):
        # Ensure unique referral code
        if not self.pk:
            while Referral.objects.filter(referral_code=self.referral_code).exists():
                self.referral_code = generate_referral_code()
        super().save(*args, **kwargs)


class ReferralUsage(models.Model):
    class Status(models.TextChoices):
        REWARDED = 'Rewarded', 'Rewarded'
        ACTIVE = 'Active', 'Active'
        PENDING = 'Pending', 'Pending'
        
    referrer = models.ForeignKey(Referral, on_delete=models.CASCADE,related_name='usages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='referral_usages')
    referral_reward = models.PositiveIntegerField()
    is_reward_credited = models.BooleanField(default=False)
    status = models.CharField(max_length=50,choices=Status.choices,default=Status.PENDING,)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Referral Usage'
        unique_together = [['receiver', 'referrer']]
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.receiver.first_name} used {self.referrer.referral_code}"