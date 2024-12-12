from django.db import models

# Create your models here.

from django.db import models
from django.utils import timezone


class LoginCode(models.Model):
    # Unique identifier for the login code
    code = models.CharField(max_length=20, unique=True)  # The actual login code
    created_at = models.DateTimeField(auto_now_add=True)  # When the code was created
    is_used = models.BooleanField(
        default=False
    )  # Flag to indicate if the code has been used
    usage_limit = models.IntegerField(default=1)  # Number of times the code can be used
    start_time = models.DateTimeField(null=True, blank=True)  # Start time for usage
    expiration_time = models.DateTimeField(
        null=True, blank=True
    )  # Expiration time for usage
    access_to = models.CharField(max_length=200)

    def is_valid(self):
        """
        Check if the login code is valid based on its usage limit and time constraints.
        """
        if self.is_used:
            return False  # Code has already been used

        if self.usage_limit == 0:
            return True  # Code can be used indefinitely

        if self.usage_limit > 1:
            return True  # Code can be used multiple times

        if self.start_time and self.expiration_time:
            now = timezone.now()
            return (
                self.start_time <= now <= self.expiration_time
            )  # Check if current time is within the range

        return False  # Default to invalid if no conditions are met

    def use_code(self):
        """
        Mark the code as used and decrease the usage limit if applicable.
        """
        if self.is_valid():
            self.is_used = True
            if self.usage_limit > 1:
                self.usage_limit -= 1
            self.save()
            return True  # Successfully used the code
        return False  # Code cannot be used

    def __str__(self):
        return f"LoginCode(code={self.code}, is_used={self.is_used}), access_to{self.access_to}"


class AdminUser(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=200)

    def __str__(self):
        return self.username
