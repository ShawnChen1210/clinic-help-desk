from django.db import models
from django.contrib.auth.models import User
from polymorphic.models import PolymorphicModel


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    ytd_pay = models.FloatField(default=0.0)
    ytd_deduction = models.FloatField(default=0.0)
    cpp_contrib = models.FloatField(default=0.0)
    ei_contrib = models.FloatField(default=0.0)

    def __str__(self):
        return str(self.user)

class PrimaryPaymentRole(PolymorphicModel):
    FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('semi-monthly', 'Semi-monthly'),
        ('monthly', 'Monthly'),
    ]

    # This ensures each user can only have ONE primary payment role
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="payment_detail")
    payment_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default='semi-monthly'
    )

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.polymorphic_ctype.name}"

class HourlyEmployee(PrimaryPaymentRole):
    hourly_wage = models.DecimalField(max_digits=8, decimal_places=2)

    def calculate_pay(self, hours_worked):
        return self.hourly_wage * hours_worked

class HourlyContractor(PrimaryPaymentRole):
    hourly_wage = models.DecimalField(max_digits=8, decimal_places=2)

    def calculate_pay(self, hours_worked):
        return self.hourly_wage * hours_worked

class CommissionEmployee(PrimaryPaymentRole):
    commission_rate = models.DecimalField(max_digits=8, decimal_places=2)

    def calculate_pay(self, income):
        return income * self.commission_rate

class CommissionContractor(PrimaryPaymentRole):
    commission_rate = models.DecimalField(max_digits=8, decimal_places=2)

    def calculate_pay(self, income):
        return income * self.commission_rate


class AdditionalPaymentRole(PolymorphicModel):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="additional_roles"
    )
    description = models.CharField(max_length=255)

class ProfitSharing(AdditionalPaymentRole):
    sharing_rate = models.DecimalField(max_digits=8, decimal_places=2)

class RevenueSharing(AdditionalPaymentRole):
    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="revenue_sharing_targets",
        null=True,
        blank=True
    )
    sharing_rate = models.DecimalField(max_digits=8, decimal_places=2)

class HasRent(AdditionalPaymentRole):
    monthly_rent = models.DecimalField(max_digits=8, decimal_places=2)

