from django.db import models

class ContactModel(models.Model):
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField()
    subject = models.TextField(default='',null=True,blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.name} messages : {self.message}'