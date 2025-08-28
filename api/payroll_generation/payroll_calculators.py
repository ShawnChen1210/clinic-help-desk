


class BasePayrollCalculator:
    """Base class for all payroll calculation strategies."""

    def __init__(self, user, user_profile, payment_detail, clinic_spreadsheet, start_date, end_date, site_settings,
                 viewset):
        self.user = user
        self.user_profile = user_profile
        self.payment_detail = payment_detail
        self.clinic_spreadsheet = clinic_spreadsheet
        self.start_date = start_date
        self.end_date = end_date
        self.site_settings = site_settings
        self.viewset = viewset  # Pass the viewset instance to access its helper methods

    def calculate_base_earnings(self):
        """This method must be implemented by each subclass."""
        raise NotImplementedError("Each calculator must implement calculate_base_earnings.")


class HourlyEmployeeCalculator(BasePayrollCalculator):
    def calculate_base_earnings(self):
        timesheet_sheet_id = self.clinic_spreadsheet.time_hour_sheet_id
        if not timesheet_sheet_id:
            raise ValueError(f'No timesheet configured for clinic: {self.clinic_spreadsheet.clinic.name}')

        daily_hours = self.viewset._get_user_daily_hours_from_sheet(
            timesheet_sheet_id, self.user, self.start_date, self.end_date
        )
        total_hours = sum(daily_hours.values())

        if total_hours == 0:
            # Check if revenue sharing/rent still needs to be processed
            has_rev_share, has_rent = self.viewset._has_revenue_sharing_or_rent_for_period(
                self.user_profile, self.start_date, self.end_date
            )
            if not (has_rev_share or has_rent):
                raise ValueError(f'No timesheet data for {self.user.username} and no other items to process.')

        # Calculate overtime and vacation pay
        overtime_vacation_result = self.viewset.calculate_overtime_and_vacation_pay(
            daily_hours=daily_hours,
            hourly_rate=self.payment_detail.hourly_wage,
            start_date=self.start_date,
            end_date=self.end_date,
            site_settings=self.site_settings,
            user=self.user,
            sheet_id=timesheet_sheet_id
        )

        regular_pay = overtime_vacation_result['regular_pay']
        overtime_pay = overtime_vacation_result['overtime_pay']
        vacation_pay = overtime_vacation_result['vacation_pay']
        total_earnings_before_tax = regular_pay + overtime_pay + vacation_pay

        period_days = (self.end_date - self.start_date).days + 1
        deductions_result = self.viewset.calculate_deductions(
            total_taxable_income=total_earnings_before_tax,
            period_days=period_days,
            user_profile=self.user_profile,
            site_settings=self.site_settings
        )

        return {
            'role_type': 'Hourly Employee',
            'total_hours': round(total_hours, 2),
            'hourly_wage': float(self.payment_detail.hourly_wage),
            'earnings': {
                'salary': float(regular_pay),
                'regular_pay': float(regular_pay),
                'overtime_pay': float(overtime_pay),
                'vacation_pay': float(vacation_pay),
            },
            'deductions': deductions_result['deductions'],
            'totals': {
                'total_earnings': float(total_earnings_before_tax),
                'total_deductions': deductions_result['total_deductions'],
                'net_payment': float(total_earnings_before_tax) - deductions_result['total_deductions'],
            },
            'breakdown': {
                'overtime_hours': overtime_vacation_result['overtime_hours'],
                'regular_hours': overtime_vacation_result['regular_hours'],
                'cpp_ytd_after': deductions_result['cpp_ytd_after'],
                'ei_ytd_after': deductions_result['ei_ytd_after'],
            }
        }


class HourlyContractorCalculator(BasePayrollCalculator):
    def calculate_base_earnings(self):
        timesheet_sheet_id = self.clinic_spreadsheet.time_hour_sheet_id
        if not timesheet_sheet_id:
            raise ValueError(f'No timesheet configured for clinic: {self.clinic_spreadsheet.clinic.name}')

        total_hours = self.viewset._get_user_hours_from_sheet(
            timesheet_sheet_id, self.user, self.start_date, self.end_date
        )

        if total_hours == 0:
            has_rev_share, has_rent = self.viewset._has_revenue_sharing_or_rent_for_period(
                self.user_profile, self.start_date, self.end_date
            )
            if not (has_rev_share or has_rent):
                raise ValueError(f'No timesheet data for {self.user.username} and no other items to process.')

        total_pay = float(self.payment_detail.hourly_wage) * total_hours

        return {
            'role_type': 'Hourly Contractor',
            'total_hours': total_hours,
            'hourly_wage': float(self.payment_detail.hourly_wage),
            'earnings': {'salary': total_pay, 'contractor_pay': total_pay, 'regular_pay': total_pay},
            'deductions': {},
            'totals': {'total_earnings': total_pay, 'total_deductions': 0.0, 'net_payment': total_pay},
        }


class CommissionBasedCalculator(BasePayrollCalculator):
    def _get_base_commission_data(self):
        compensation_sheet_id = self.clinic_spreadsheet.compensation_sales_sheet_id
        if not compensation_sheet_id:
            raise ValueError(f'No compensation sheet configured for clinic: {self.clinic_spreadsheet.clinic.name}')

        commission_data = self.viewset._get_commission_data_from_sheet(
            compensation_sheet_id, self.user, self.start_date, self.end_date
        )

        if not commission_data:
            has_rev_share, has_rent = self.viewset._has_revenue_sharing_or_rent_for_period(
                self.user_profile, self.start_date, self.end_date
            )
            if not (has_rev_share or has_rent):
                raise ValueError(f'No commission data for {self.user.username} and no other items to process.')
            return {'adjusted_total': 0.0, 'tax_gst': 0.0, 'invoice_data': []}, 0.0

        pos_fees = self.viewset._calculate_pos_fees_for_practitioner(
            commission_data['invoice_data'], self.clinic_spreadsheet
        )
        return commission_data, pos_fees

    def calculate_base_earnings(self):
        commission_data, pos_fees = self._get_base_commission_data()
        period_days = (self.end_date - self.start_date).days + 1

        return self.viewset._calculate_commission_payroll(
            user=self.user,
            user_profile=self.user_profile,
            commission_data=commission_data,
            pos_fees=pos_fees,
            site_settings=self.site_settings,
            start_date=self.start_date,
            end_date=self.end_date,
            period_days=period_days
        )