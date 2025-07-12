from django.contrib.auth.tokens import PasswordResetTokenGenerator

#custom token generator for account activation
class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            # Create a hash value by combining:
            # - user.pk: The user's primary key (ID) converted to string
            # - timestamp: When the token was created (converted to string)
            # - user.is_active: The user's activation status (True/False converted to string)
            #
            # By including user.is_active, the token becomes invalid once the user
            # is activated (is_active changes from False to True)
            str(user.pk) + str(timestamp) + str(user.is_active)
        )

account_activation_token = AccountActivationTokenGenerator()