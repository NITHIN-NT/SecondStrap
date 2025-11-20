from django.utils.crypto import get_random_string
import string

def generate_alphabetical_code(length=4):
    '''
        This is used to gnerate A-Z OTP
    '''
    allowed_chars = string.ascii_uppercase

    code = get_random_string(length=length, allowed_chars=allowed_chars)

    return code