from django.db import models
from django.contrib.auth.models import User
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    ytd_pay = models.FloatField(default=0.0)
    ytd_deduction = models.FloatField(default=0.0)
    cpp_contrib = models.FloatField(default=0.0)
    ei_contrib = models.FloatField(default=0.0)
    contrib_year = models.IntegerField(default=timezone.now().year)

    def reset_annual_contributions_if_needed(self):
        """Reset CPP and EI contributions if we're in a new year"""
        current_year = timezone.now().year
        if self.contrib_year < current_year:
            self.cpp_contrib = 0.0
            self.ei_contrib = 0.0
            self.contrib_year = current_year
            self.save()
            print(f"Reset annual contributions for {self.user.username} for year {current_year}")

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

class Student(PrimaryPaymentRole):
    pass

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
    TARGET_CHOICES = [
        ('specific_user', 'Specific User'),
        ('all_students', 'All Students'),
    ]

    target_type = models.CharField(
        max_length=20,
        choices=TARGET_CHOICES,
        default='specific_user'
    )

    target_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="revenue_sharing_targets",
        null=True,
        blank=True
    )
    sharing_rate = models.DecimalField(max_digits=8, decimal_places=2)

    def clean(self):


        if self.target_type == 'specific_user' and not self.target_user:
            raise ValidationError("target_user is required when target_type is 'specific_user'")

        if self.target_type == 'all_students' and self.target_user:
            raise ValidationError("target_user should be empty when target_type is 'all_students'")

    def get_target_users(self):
        """
        Returns a queryset of target users based on the target_type
        """
        if self.target_type == 'specific_user':
            return User.objects.filter(id=self.target_user.id) if self.target_user else User.objects.none()

        elif self.target_type == 'all_students':
            # Get all users with Student role # Import your Student model
            student_profiles = Student.objects.values_list('user_profile__user', flat=True)
            return User.objects.filter(id__in=student_profiles)

        return User.objects.none()

class HasRent(AdditionalPaymentRole):
    monthly_rent = models.DecimalField(max_digits=8, decimal_places=2)


