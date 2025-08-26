from django.db import models
from django.contrib.auth.models import User

class Clinic(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ClinicSpreadsheet(models.Model):
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name='spreadsheets')

    # The sheet IDs
    compensation_sales_sheet_id = models.CharField(max_length=255, null=True, blank=True)
    daily_transaction_sheet_id = models.CharField(max_length=255, null=True, blank=True)
    transaction_report_sheet_id = models.CharField(max_length=255, null=True, blank=True)
    payment_transaction_sheet_id = models.CharField(max_length=255, null=True, blank=True)
    time_hour_sheet_id = models.CharField(max_length=255, null=True, blank=True)

    # For the compensation_sales_sheet merge
    merge_column = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Clinic Sheets"

    def __str__(self):
        return f"{self.clinic} - Sheets"

    @classmethod
    def get_sheets(cls):
        """Get or create the singleton clinic sheets instance"""
        sheets, created = cls.objects.get_or_create(id=1)
        return sheets

    @property
    def has_sheets(self):
        """Check if any sheets are created"""
        return any([
            self.compensation_sales_sheet_id,
            self.daily_transaction_sheet_id,
            self.transaction_report_sheet_id,
            self.payment_transaction_sheet_id,
            self.time_hour_sheet_id,
        ])

# A new model to store a user's column preferences for a specific sheet. (for analytics)
class SheetColumnPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sheet_id = models.CharField(max_length=255)
    date_column = models.CharField(max_length=255)
    income_columns = models.JSONField()

    class Meta:
        unique_together = ('user', 'sheet_id')

    def __str__(self):
        return f"{self.user.username}'s preference for {self.sheet_id}"

class SiteSettings(models.Model):
    federal_tax_brackets = models.JSONField(default=list, help_text="Federal income tax brackets")
    provincial_tax_brackets = models.JSONField(default=list, help_text="Provincial income tax brackets")
    cpp = models.DecimalField(max_digits=8, decimal_places=3)
    cpp_exemption = models.DecimalField(max_digits=8, decimal_places=3)
    cpp_cap = models.DecimalField(max_digits=8, decimal_places=3)
    ei_ee = models.DecimalField(max_digits=8, decimal_places=3)
    ei_er = models.DecimalField(max_digits=8, decimal_places=3)
    ei_cap = models.DecimalField(max_digits=8, decimal_places=3)
    vacation_pay_rate = models.DecimalField(max_digits=8, decimal_places=3)
    overtime_pay_rate = models.DecimalField(max_digits=8, decimal_places=3)

class PayrollRecords(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    period_start = models.DateField()
    period_end = models.DateField()
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, null=True, blank=True)
    role_type = models.CharField(max_length=50)

    # Income
    subtotal_income = models.DecimalField(max_digits=8, decimal_places=3)
    hours_worked = models.DecimalField(max_digits=8, decimal_places=3)
    vacation_pay = models.DecimalField(max_digits=8, decimal_places=3)
    overtime_pay = models.DecimalField(max_digits=8, decimal_places=3)
    revenue_share_income = models.DecimalField(max_digits=8, decimal_places=3)
    gst = models.DecimalField(max_digits=8, decimal_places=3)
    total_income = models.DecimalField(max_digits=8, decimal_places=3)

    # Deductions
    commission_deduction = models.DecimalField(max_digits=8, decimal_places=3)
    pos_fees = models.DecimalField(max_digits=8, decimal_places=3)
    provincial_income_tax = models.DecimalField(max_digits=8, decimal_places=3)
    federal_income_tax = models.DecimalField(max_digits=8, decimal_places=3)
    cpp_contrib = models.DecimalField(max_digits=8, decimal_places=3)
    ei_contrib = models.DecimalField(max_digits=8, decimal_places=3)
    rent = models.DecimalField(max_digits=10, decimal_places=3)
    revenue_share_deduction = models.DecimalField(max_digits=8, decimal_places=3)
    revenue_share_deduction_payee = models.DecimalField(max_digits=8, decimal_places=3)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=3)

    notes = models.TextField(blank=True)
    payroll_number = models.CharField(max_length=50, unique=True)