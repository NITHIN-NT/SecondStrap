from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import get_adapter
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        logger.info(f"--- pre_social_login started for {sociallogin.account.provider} ---")
        # This is called when the user is about to be logged in.
        # sociallogin.user is not yet created.
        if sociallogin.is_existing:
            logger.info("Social account already exists, continuing.")
            return

        # check if a user with this email already exists
        email = sociallogin.account.extra_data.get('email')
        logger.info(f"Social login extra_data: {sociallogin.account.extra_data}")
        if not email:
            logger.error("No email provided by social provider")
            return

        try:
            User = get_user_model()
            user = User.objects.get(email=email)
            logger.info(f"Found existing user with email {email}, connecting social account.")
            sociallogin.connect(request, user)
            return
        except User.DoesNotExist:
            logger.info(f"No user found with email {email}, will proceed with new user creation.")
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
        user.email = email
        user.first_name = sociallogin.account.extra_data.get('given_name', '')
        user.last_name = sociallogin.account.extra_data.get('family_name', '')
        user.is_active = True
        user.is_verified = True
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



