from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import get_adapter
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    print("--- CUSTOM SOCIAL ADAPTER SAVE_USER IS RUNNING ---")
    '''
        This Adapter is used to auto Active the Google authenticated users 
        Saving their Data to the database .
    '''
    def is_open_for_signup(self, request, sociallogin):
        return False

    def pre_social_login(self, request, sociallogin):
        # This is called when the user is about to be logged in.
        # sociallogin.user is not yet created.
        if sociallogin.is_existing:
            return

        # check if a user with this email already exists
        try:
            User = get_user_model()
            user = User.objects.get(email=sociallogin.account.extra_data['email'])
            sociallogin.connect(request, user)
            return
        except User.DoesNotExist:
            pass

        # you can check for more things here, like if the user's email is verified
        if 'email' not in sociallogin.account.extra_data:
            # this will prevent the user from signing up
            # and you can redirect them to a page that explains why
            # or just render a template with a message.
            # for now, we'll just prevent the signup
            return

        # create a new user
        user = get_adapter().new_user(request)
        user.email = sociallogin.account.extra_data['email']
        user.first_name = sociallogin.account.extra_data.get('given_name', '')
        user.last_name = sociallogin.account.extra_data.get('family_name', '')
        user.is_active = True
        sociallogin.user = user
        user.save()

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        extra_data = sociallogin.account.extra_data
        logger.info(f"Social login extra_data: {extra_data}")

        user.first_name = extra_data.get('given_name', '')
        user.last_name = extra_data.get('family_name', '')
        user.profile = extra_data.get('picture', '')

        phone_numbers = extra_data.get('phoneNumbers', [])
        if phone_numbers:
            user.phone = phone_numbers[0].get('value')

        user.is_active = True

        user.save()
        return user



