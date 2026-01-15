from django.db import models
import os
import uuid

class ContactModel(models.Model):
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField()
    subject = models.TextField(default='',null=True,blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.name} messages : {self.message}'
def get_file_path(instance,filename):
    ext = filename.split('.')[-1]
    
    filename = f"{uuid.uuid4().hex[:10]}.{ext}"
    return os.path.join('thumbanails/',filename)
class Thumbanails(models.Model):
    image = models.ImageField(upload_to=get_file_path,blank=True, null=True)
    name = models.CharField(null=True,max_length=250)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)