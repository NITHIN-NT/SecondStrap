from django.contrib import messages
from django.shortcuts import redirect

def custom_inactive_account_view(request):
    '''
    This view handel the inacitve google authenticated users
    '''   

    messages.error(request, 'Your account is inactive. Please contact support or check your email to verify.')

    return redirect('/')