from django.db import models
from django.contrib.auth.models import User
from polymorphic.models import PolymorphicModel


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user)

class PrimaryPaymentRole(PolymorphicModel):
    # This ensures each user can only have ONE primary payment role
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name="payment_detail")
    payroll_dates = models.JSONField(default=list)

    def __str__(self):
        return f"{self.user_profile.user.username} - {self.polymorphic_ctype.name}"

    def get_payroll_dates(self):
        """
        Get payroll dates, ensuring we always have at least 'end of month' as default
        """
        dates = self.payroll_dates
        if not dates:
            return ['end of month']
        return dates

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

