from django.shortcuts import get_object_or_404
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from registration.models import *
from ..services.google_sheets import *
import pandas as pd
from django.utils import timezone
from datetime import datetime, timedelta
from ..models import *
from .payroll_calculators import *
import traceback

class PayrollViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only allow staff/superusers"""
        permission_classes = [IsAuthenticated]
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            self.permission_denied(self.request, message="Staff privileges required")
        return [permission() for permission in permission_classes]

    def _get_payroll_calculator(self, user, user_profile, payment_detail, clinic_spreadsheet, start_date, end_date,
                                site_settings) -> BasePayrollCalculator:
        """
        ## NEW METHOD ##
        Factory method to get the correct payroll calculator strategy.
        """

        # Mapping from model class to calculator class
        calculator_map = {
            HourlyEmployee: HourlyEmployeeCalculator,
            HourlyContractor: HourlyContractorCalculator,
            CommissionEmployee: CommissionBasedCalculator,
            CommissionContractor: CommissionBasedCalculator,
        }

        CalculatorClass = calculator_map.get(payment_detail.__class__)

        if not CalculatorClass:
            if isinstance(payment_detail, Student):
                raise TypeError('Students are not eligible for payroll generation.')
            raise TypeError(f"Payroll calculation not implemented for role: {payment_detail.__class__.__name__}")

        return CalculatorClass(user, user_profile, payment_detail, clinic_spreadsheet, start_date, end_date,
                               site_settings, viewset=self)

    @action(detail=True, methods=['get'])
    def get_user(self, request, pk=None):
        """Get user details for payroll generation"""
        try:
            user = get_object_or_404(User, id=pk)
            user_profile = get_object_or_404(UserProfile, user=user)

            # Get payment role details
            payment_detail = getattr(user_profile, 'payment_detail', None)
            primary_role = None
            payment_frequency = 'semi-monthly'  # default

            if payment_detail:
                primary_role = payment_detail.polymorphic_ctype.name
                payment_frequency = getattr(payment_detail, 'payment_frequency', 'semi-monthly')

            user_data = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'primaryRole': primary_role,
                'payment_frequency': payment_frequency,  # Changed from payroll_dates
                'ytd_pay': user_profile.ytd_pay,
                'ytd_deduction': user_profile.ytd_deduction,
                'cpp_contrib': user_profile.cpp_contrib,
                'ei_contrib': user_profile.ei_contrib,
            }

            return Response(user_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to get user details: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def generate_payroll(self, request, pk=None):
        """Generate payroll for a specific user using a strategy pattern."""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'You do not have permission to generate payroll'},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            user = get_object_or_404(User, id=pk)
            user_profile = get_object_or_404(UserProfile, user=user)
            user_profile.reset_annual_contributions_if_needed()
            site_settings = SiteSettings.objects.first()
            if not site_settings:
                return Response({'error': 'Site settings not configured.'}, status=status.HTTP_400_BAD_REQUEST)
            start_date = datetime.strptime(request.data['startDate'], '%Y-%m-%d').date()
            end_date = datetime.strptime(request.data['endDate'], '%Y-%m-%d').date()
            period_days = (end_date - start_date).days + 1
            clinic = get_object_or_404(Clinic, id=request.data['clinic_id'])
            clinic_spreadsheet = get_object_or_404(ClinicSpreadsheet, clinic=clinic)
            payment_detail = getattr(user_profile, 'payment_detail', None)
            if not payment_detail:
                return Response({'error': 'User does not have a payment role configured.'},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                calculator = self._get_payroll_calculator(user, user_profile, payment_detail, clinic_spreadsheet,
                                                          start_date, end_date, site_settings)
                payroll_data = calculator.calculate_base_earnings()
            except (ValueError, TypeError) as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            earnings = payroll_data.get('earnings', {})
            is_commission = 'Commission' in payroll_data.get('role_type', '')
            base_gross_income = Decimal(str(earnings.get('gross_income', 0))) if is_commission else \
                (Decimal(str(earnings.get('regular_pay', 0))) + Decimal(str(earnings.get('overtime_pay', 0))))
            rent_deduction, rent_description = self._calculate_rent_deduction(user_profile, start_date, end_date)
            rev_share_deduction, rev_deduction_details = self._calculate_revenue_sharing_deductions(user, user_profile,
                                                                                                    base_gross_income)
            rev_share_income_users, rev_income_user_details = self._calculate_revenue_sharing_income_from_user(
                user_profile, start_date, end_date, clinic_spreadsheet, site_settings)
            rev_share_income_students, rev_income_student_details = self._calculate_revenue_sharing_income_from_students(
                user_profile, start_date, end_date, clinic_spreadsheet)
            total_revenue_share_income = rev_share_income_users + rev_share_income_students
            payroll_data = self._apply_final_adjustments(payroll_data, payment_detail, period_days, user_profile,
                                                         site_settings, rent_deduction, rev_share_deduction,
                                                         total_revenue_share_income)
            payroll_data['deductions']['rent_description'] = rent_description
            payroll_data['revenue_sharing_details'] = {
                'rent_deduction': float(rent_deduction), 'revenue_share_deduction': float(rev_share_deduction),
                'revenue_share_income_users': float(rev_share_income_users),
                'revenue_share_income_students': float(rev_share_income_students),
                'revenue_deduction_details': rev_deduction_details,
                'revenue_income_user_details': rev_income_user_details,
                'revenue_income_student_details': rev_income_student_details,
            }
            revenue_sharing_contributions = {'income_contributors': [], 'deduction_recipients': []}
            if rev_income_user_details:
                for detail in rev_income_user_details:
                    revenue_sharing_contributions['income_contributors'].append(
                        {'user_name': detail['from_user'], 'amount': detail['amount'], 'type': 'specific_user'})
            if rev_income_student_details:
                total_student_contribution = float(total_revenue_share_income - rev_share_income_users)
                if total_student_contribution > 0:
                    revenue_sharing_contributions['income_contributors'].append(
                        {'user_name': 'All Students Combined', 'amount': total_student_contribution,
                         'type': 'student_share', 'student_breakdown': rev_income_student_details})
            if rev_deduction_details:
                for detail in rev_deduction_details:
                    revenue_sharing_contributions['deduction_recipients'].append(
                        {'user_name': detail['payee'], 'amount': detail['amount'], 'type': 'specific_user'})
            payroll_data['revenue_sharing_contributions'] = revenue_sharing_contributions
            return Response(payroll_data, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response({'error': f'Failed to generate payroll: {str(e)}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _has_revenue_sharing_or_rent_for_period(self, user_profile, period_start, period_end):
        """
        Check if user has any revenue sharing roles or rent that would apply for this period
        Returns: (has_revenue_sharing, has_rent)
        """
        try:
            # Check for revenue sharing roles
            has_revenue_sharing = RevenueSharing.objects.filter(
                user_profile=user_profile
            ).exists()

            # Check for rent roles and if period contains month end
            rent_roles = user_profile.additional_roles.filter(polymorphic_ctype__model='hasrent')
            has_rent = False

            if rent_roles.exists():
                # Check if period contains end of any month
                current_date = period_start
                while current_date <= period_end:
                    # Check if this date is the last day of the month
                    next_day = current_date + timedelta(days=1)
                    if next_day.month != current_date.month:  # Month changed, so current_date is month end
                        has_rent = True
                        break
                    current_date += timedelta(days=1)

            return has_revenue_sharing, has_rent

        except Exception as e:
            print(f"Error checking revenue sharing/rent eligibility: {str(e)}")
            return False, False


    def calculate_overtime_and_vacation_pay(self, daily_hours, hourly_rate, start_date, end_date, site_settings, user,
                                            sheet_id):
        """
        Calculate overtime and vacation pay for hourly employees
        Uses week-by-week overtime calculation with backward-looking partial weeks
        """
        hourly_rate = Decimal(str(hourly_rate))
        overtime_multiplier = Decimal(str(site_settings.overtime_pay_rate))
        vacation_rate = Decimal(str(site_settings.vacation_pay_rate)) / 100

        regular_hours = Decimal('0')
        overtime_hours = Decimal('0')

        # Get all calendar weeks that intersect with the pay period
        weeks_to_process = self._get_calendar_weeks_in_period(start_date, end_date)

        for week_info in weeks_to_process:
            week_start = week_info['week_start']
            week_end = week_info['week_end']
            is_partial_start = week_info['is_partial_start']
            is_partial_end = week_info['is_partial_end']

            # Get hours for this week
            if is_partial_start:
                # Look backward to get full week hours
                full_week_hours = self._get_full_week_hours(
                    daily_hours, week_start, week_end, start_date, end_date, user, sheet_id
                )
                week_hours_in_period = Decimal('0')
                for check_date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
                    if week_start <= check_date <= week_end:
                        week_hours_in_period += Decimal(str(daily_hours.get(check_date, 0)))

            elif is_partial_end:
                # Don't look forward - treat as regular hours to avoid double-counting
                full_week_hours = Decimal('0')
                week_hours_in_period = Decimal('0')
                for check_date in [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]:
                    if week_start <= check_date <= week_end:
                        week_hours_in_period += Decimal(str(daily_hours.get(check_date, 0)))
                        full_week_hours += week_hours_in_period  # Same as period hours
            else:
                # Full week within period
                full_week_hours = Decimal('0')
                week_hours_in_period = Decimal('0')
                for day_offset in range(7):
                    check_date = week_start + timedelta(days=day_offset)
                    hours = Decimal(str(daily_hours.get(check_date, 0)))
                    full_week_hours += hours
                    week_hours_in_period += hours

            # Apply overtime logic
            if full_week_hours > Decimal('40'):
                # Week has overtime
                total_overtime_hours = full_week_hours - Decimal('40')

                if is_partial_start:
                    # Allocate all overtime hours to this payroll (no proportional split)
                    period_overtime_hours = total_overtime_hours
                    period_regular_hours = week_hours_in_period - period_overtime_hours
                    # Ensure we don't have negative regular hours
                    if period_regular_hours < 0:
                        period_regular_hours = Decimal('0')
                        period_overtime_hours = week_hours_in_period
                else:
                    # Full week or partial end week
                    period_overtime_hours = max(Decimal('0'), week_hours_in_period - Decimal('40'))
                    period_regular_hours = min(week_hours_in_period, Decimal('40'))
            else:
                # No overtime this week
                period_overtime_hours = Decimal('0')
                period_regular_hours = week_hours_in_period

            regular_hours += period_regular_hours
            overtime_hours += period_overtime_hours

        # Calculate pay amounts
        regular_pay = regular_hours * hourly_rate
        overtime_pay = overtime_hours * hourly_rate * overtime_multiplier
        total_pay_before_vacation = regular_pay + overtime_pay
        vacation_pay = total_pay_before_vacation * vacation_rate

        return {
            'regular_hours': round(float(regular_hours), 2),  # Round in backend
            'overtime_hours': round(float(overtime_hours), 2),  # Round in backend
            'regular_pay': regular_pay,
            'overtime_pay': overtime_pay,
            'vacation_pay': vacation_pay,
        }

    def calculate_deductions(self, total_taxable_income, period_days, user_profile, site_settings):
        """
        Calculate all deductions: federal tax, provincial tax, CPP, and EI
        """
        total_taxable_income = Decimal(str(total_taxable_income))
        period_days = Decimal(str(period_days))

        # Annualize income for tax calculation
        daily_income = total_taxable_income / period_days
        annual_income = daily_income * Decimal('365')

        # Calculate tax brackets
        federal_tax_annual = self._calculate_tax_brackets(
            annual_income, site_settings.federal_tax_brackets
        )
        provincial_tax_annual = self._calculate_tax_brackets(
            annual_income, site_settings.provincial_tax_brackets
        )

        # Pro-rate taxes back to period
        federal_tax_period = (federal_tax_annual * period_days / Decimal('365')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        provincial_tax_period = (provincial_tax_annual * period_days / Decimal('365')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Calculate CPP
        cpp_exemption_annual = Decimal(str(site_settings.cpp_exemption))
        cpp_exemption_period = (cpp_exemption_annual * period_days / Decimal('365')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        cpp_taxable_income = max(Decimal('0'), total_taxable_income - cpp_exemption_period)
        cpp_deduction_calculated = (cpp_taxable_income * Decimal(str(site_settings.cpp)) / 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Apply CPP cap
        cpp_cap = Decimal(str(site_settings.cpp_cap))
        current_cpp_ytd = Decimal(str(user_profile.cpp_contrib))
        cpp_remaining_room = max(Decimal('0'), cpp_cap - current_cpp_ytd)
        cpp_deduction_final = min(cpp_deduction_calculated, cpp_remaining_room)

        # Calculate EI
        ei_deduction_calculated = (total_taxable_income * Decimal(str(site_settings.ei_ee)) / 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Apply EI cap
        ei_cap = Decimal(str(site_settings.ei_cap))
        current_ei_ytd = Decimal(str(user_profile.ei_contrib))
        ei_remaining_room = max(Decimal('0'), ei_cap - current_ei_ytd)
        ei_deduction_final = min(ei_deduction_calculated, ei_remaining_room)

        # Calculate totals
        total_deductions = float(
            federal_tax_period + provincial_tax_period + cpp_deduction_final + ei_deduction_final
        )

        return {
            'deductions': {
                'federal_tax': float(federal_tax_period),
                'provincial_tax': float(provincial_tax_period),
                'cpp': float(cpp_deduction_final),
                'ei': float(ei_deduction_final),
            },
            'total_deductions': total_deductions,
            'projected_ytd_earnings': float(Decimal(str(user_profile.ytd_pay)) + total_taxable_income),
            'projected_ytd_deductions': float(
                Decimal(str(user_profile.ytd_deduction)) + Decimal(str(total_deductions))),
            'cpp_ytd_after': float(current_cpp_ytd + cpp_deduction_final),
            'ei_ytd_after': float(current_ei_ytd + ei_deduction_final),
        }

    def _calculate_tax_brackets(self, annual_income, tax_brackets):
        """
        Calculate progressive tax brackets
        """
        if not tax_brackets:
            return Decimal('0')

        annual_income = Decimal(str(annual_income))
        total_tax = Decimal('0')

        for bracket in tax_brackets:
            tax_rate = Decimal(str(bracket['tax_rate'])) / 100
            min_income = Decimal(str(bracket['min_income']))
            max_income = Decimal(str(bracket['max_income']))

            if annual_income <= min_income:
                break

            taxable_in_bracket = min(annual_income, max_income) - min_income
            if taxable_in_bracket > 0:
                total_tax += taxable_in_bracket * tax_rate

        return total_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _get_calendar_weeks_in_period(self, start_date, end_date):
        """
        Get all calendar weeks that intersect with the pay period
        Returns list of week info with partial week flags
        """
        weeks = []
        current_date = start_date

        while current_date <= end_date:
            # Find the start of this week (Monday)
            week_start = current_date - timedelta(days=current_date.weekday())
            week_end = week_start + timedelta(days=6)

            # Determine if this week is partial
            is_partial_start = week_start < start_date
            is_partial_end = week_end > end_date

            weeks.append({
                'week_start': week_start,
                'week_end': week_end,
                'is_partial_start': is_partial_start,
                'is_partial_end': is_partial_end,
            })

            # Move to next week
            current_date = week_end + timedelta(days=1)
            if current_date > end_date:
                break

        return weeks

    def _get_full_week_hours(self, daily_hours, week_start, week_end, period_start, period_end, user, sheet_id):
        """
        Get total hours for a full calendar week, including days outside the pay period
        For partial weeks at the start, this fetches additional timesheet data
        """
        total_hours = Decimal('0')

        # Add hours from within the pay period (already have this data)
        for check_date in [period_start + timedelta(days=x) for x in range((period_end - period_start).days + 1)]:
            if week_start <= check_date <= week_end:
                total_hours += Decimal(str(daily_hours.get(check_date, 0)))

        # For dates outside the period but within the week, fetch additional data
        dates_to_fetch = []
        for day_offset in range(7):
            check_date = week_start + timedelta(days=day_offset)
            if check_date < period_start or check_date > period_end:
                dates_to_fetch.append(check_date)

        if dates_to_fetch:
            # Fetch hours for dates outside the pay period
            additional_hours = self._get_hours_for_specific_dates(sheet_id, user, dates_to_fetch)
            for date, hours in additional_hours.items():
                total_hours += Decimal(str(hours))

        return total_hours

    def _get_hours_for_specific_dates(self, sheet_id, user, dates_list):
        """
        Fetch user hours from Google Sheet for specific dates
        Returns: dict with date as key and hours as value
        """
        try:
            if not dates_list:
                return {}

            sheet_data = read_google_sheets(sheet_id, "A:I")

            if not sheet_data or len(sheet_data) < 2:
                return {date: 0 for date in dates_list}

            headers = sheet_data[0]
            data_rows = sheet_data[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            user_rows = df[df['Staff member'].str.strip() == user_full_name]

            if user_rows.empty:
                return {date: 0 for date in dates_list}

            user_rows = user_rows.copy()
            user_rows['Date'] = pd.to_datetime(user_rows['Date'], errors='coerce')
            user_rows = user_rows.dropna(subset=['Date'])

            # Filter for the specific dates
            target_dates = [pd.Timestamp(date) for date in dates_list]
            filtered_rows = user_rows[user_rows['Date'].isin(target_dates)]

            # Build hours dictionary
            hours_dict = {date: 0.0 for date in dates_list}  # Initialize with 0

            for _, row in filtered_rows.iterrows():
                try:
                    date = row['Date'].date()
                    minutes_value = row['Payable time (mins)']

                    if pd.isna(minutes_value) or minutes_value == '':
                        continue

                    hours = float(minutes_value) / 60.0
                    hours_dict[date] = hours_dict.get(date, 0.0) + hours

                except (ValueError, TypeError) as e:
                    print(f"Error converting minutes value '{minutes_value}' to float: {e}")
                    continue

            return hours_dict

        except Exception as e:
            print(f"Error fetching specific dates data: {str(e)}")
            return {date: 0 for date in dates_list}

    def _get_user_hours_from_sheet(self, sheet_id, user, start_date, end_date):
        # UPDATED: Switched to the efficient date range query.
        """
        Fetch total user hours from Google Sheet for the specified period.
        """
        try:
            df = read_sheet_by_date_range(
                sheet_id=sheet_id,
                date_column_name="Date",
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                print(f"No timesheet entries found for period {start_date} to {end_date}")
                return 0.0

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            user_rows = df[df['Staff member'].str.strip() == user_full_name]

            if user_rows.empty:
                print(f"No timesheet entries found for user: {user_full_name} in the period.")
                return 0.0

            total_minutes = pd.to_numeric(user_rows['Payable time (mins)'], errors='coerce').fillna(0).sum()
            total_hours = total_minutes / 60.0
            print(f"Found {len(user_rows)} entries for {user_full_name}: {total_hours:.2f} hours")
            return round(total_hours, 2)
        except Exception as e:
            print(f"Error fetching sheet data: {str(e)}")
            return 0.0

    def _get_user_daily_hours_from_sheet(self, sheet_id, user, start_date, end_date):
        # UPDATED: Switched to the efficient date range query.
        """
        Fetch user hours from Google Sheet broken down by day.
        """
        try:
            df = read_sheet_by_date_range(
                sheet_id=sheet_id,
                date_column_name="Date",
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                return {}

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            user_rows = df[df['Staff member'].str.strip() == user_full_name].copy()

            if user_rows.empty:
                return {}

            user_rows['DateOnly'] = pd.to_datetime(user_rows['Date']).dt.date
            user_rows['PayableMinutes'] = pd.to_numeric(user_rows['Payable time (mins)'], errors='coerce').fillna(0)

            daily_minutes = user_rows.groupby('DateOnly')['PayableMinutes'].sum()
            daily_hours = (daily_minutes / 60.0).round(2).to_dict()

            print(f"Found daily hours for {user_full_name}: {daily_hours}")
            return daily_hours
        except Exception as e:
            print(f"Error fetching sheet data: {str(e)}")
            return {}

    def _normalize_practitioner_name(self, name):
        """
        Normalize practitioner name by removing content in parentheses
        Example: "Amanda Seminiano (Registered Massage Therapist)" -> "Amanda Seminiano"
        """
        import re
        if not name:
            return ""
        # Remove anything in parentheses and normalize whitespace
        normalized = re.sub(r'\([^)]*\)', '', str(name))
        # Replace multiple spaces with single space and strip
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _extract_base_invoice_number(self, invoice_str):
        """
        Extract base invoice number, ignoring suffixes
        Example: "18269-C01" -> "18269"
        """
        if not invoice_str:
            return ""
        # Split on first dash and take the first part
        return str(invoice_str).split('-')[0]

    def _get_commission_data_from_sheet(self, compensation_sheet_id, user, start_date, end_date):
        # UPDATED: Switched to the efficient date range query.
        """
        Extract commission data for a specific practitioner from compensation sheet.
        """
        try:
            df = read_sheet_by_date_range(
                sheet_id=compensation_sheet_id,
                date_column_name="Invoice Date",
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                print(f"No compensation data found for period {start_date} to {end_date}")
                return None

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            period_rows = df[df['Practitioner'].apply(
                lambda x: self._normalize_practitioner_name(x).lower() == user_full_name.lower()
            )]

            if period_rows.empty:
                print(f"No compensation data found for {user_full_name} in period.")
                return None

            adjusted_total = pd.to_numeric(period_rows['Adjusted Total'], errors='coerce').fillna(0).sum()
            tax_gst = pd.to_numeric(period_rows['Tax'], errors='coerce').fillna(0).sum()

            invoice_data = []
            for _, row in period_rows.iterrows():
                invoice_data.append({
                    'invoice_date': pd.to_datetime(row['Invoice Date']).date() if pd.notna(
                        row['Invoice Date']) else None,
                    'invoice_number': self._extract_base_invoice_number(row.get('Invoice #', '')),
                    'patient_name': str(row.get('Patient', '')).strip(),
                    'adjusted_total': pd.to_numeric(row.get('Adjusted Total', 0), errors='coerce') or 0
                })

            return {
                'adjusted_total': float(adjusted_total),
                'tax_gst': float(tax_gst),
                'invoice_data': invoice_data
            }
        except Exception as e:
            print(f"Error fetching commission data: {str(e)}")
            return None

    def _calculate_pos_fees_for_practitioner(self, invoice_data, clinic_spreadsheet):
        # UPDATED: Massively optimized to make only two API calls instead of reading sheets in a loop.
        """
        Calculate total POS fees for a practitioner using the matching algorithm.
        """
        try:
            if not invoice_data:
                return 0.0

            transaction_sheet_id = clinic_spreadsheet.transaction_report_sheet_id
            payment_sheet_id = clinic_spreadsheet.payment_transaction_sheet_id

            if not all([transaction_sheet_id, payment_sheet_id]):
                print("Missing required sheet IDs for POS fee calculation")
                return 0.0

            # Find the date range needed for the query
            invoice_dates = {item['invoice_date'] for item in invoice_data if item['invoice_date']}
            if not invoice_dates:
                return 0.0
            min_date, max_date = min(invoice_dates), max(invoice_dates)

            # Make one efficient call for each sheet to get all potentially relevant data
            transaction_df = read_sheet_by_date_range(transaction_sheet_id, "Payment Date", min_date, max_date)
            payment_df = read_sheet_by_date_range(payment_sheet_id, "Date", min_date, max_date)

            if transaction_df.empty or payment_df.empty:
                return 0.0

            total_pos_fees = 0.0
            for invoice_info in invoice_data:
                # ... (the inner loop logic for matching remains the same but now operates on pre-fetched DataFrames)
                invoice_date = invoice_info['invoice_date']
                base_invoice_number = invoice_info['invoice_number']
                patient_name = invoice_info['patient_name']

                if not all([invoice_date, base_invoice_number, patient_name]):
                    continue

                matching_transactions = transaction_df[
                    (pd.to_datetime(transaction_df['Payment Date']).dt.date == invoice_date) &
                    (transaction_df['Payer'].str.contains(patient_name, case=False, na=False)) &
                    (transaction_df['Payment Method'].str.contains('Jane Payments', case=False, na=False)) &
                    (transaction_df['Applied To'].str.contains(base_invoice_number, na=False))
                    ]

                if matching_transactions.empty:
                    continue

                for _, transaction in matching_transactions.iterrows():
                    transaction_amount = pd.to_numeric(transaction.get('Amount', 0), errors='coerce') or 0

                    matching_payments = payment_df[
                        (pd.to_datetime(payment_df['Date']).dt.date == invoice_date) &
                        (payment_df['Customer'].str.contains(patient_name, case=False, na=False)) &
                        (pd.to_numeric(payment_df['Customer Charge'], errors='coerce').fillna(0).round(2) == round(
                            float(transaction_amount), 2))
                        ]

                    for _, payment in matching_payments.iterrows():
                        jane_fee = pd.to_numeric(payment.get('Jane Payments Fee', 0), errors='coerce') or 0
                        total_pos_fees += float(jane_fee)

            print(f"Total calculated POS fees: ${total_pos_fees}")
            return total_pos_fees
        except Exception as e:
            print(f"Error calculating POS fees: {str(e)}")
            return 0.0

    def _calculate_vacation_pay_only(self, gross_income, site_settings):
        """
        Calculate vacation pay only (no overtime for commission employees)
        """
        try:
            gross_income = Decimal(str(gross_income))
            vacation_rate = Decimal(str(site_settings.vacation_pay_rate)) / 100
            vacation_pay = gross_income * vacation_rate
            return float(vacation_pay)
        except Exception as e:
            print(f"Error calculating vacation pay: {str(e)}")
            return 0.0

    def _calculate_commission_payroll(self, user, user_profile, commission_data, pos_fees, site_settings, start_date,
                                      end_date, period_days):
        """
        Calculate payroll for commission-based roles
        """
        try:
            payment_detail = user_profile.payment_detail

            # Base calculations
            adjusted_total = Decimal(str(commission_data['adjusted_total']))
            tax_gst = Decimal(str(commission_data['tax_gst']))
            pos_fees_decimal = Decimal(str(pos_fees))

            gross_income = adjusted_total + tax_gst

            # Calculate commission properly
            # Note: commission_rate is already stored as a decimal (e.g., 0.79 = 79%)
            commission_rate_decimal = Decimal(str(payment_detail.commission_rate))  # Already a decimal
            commission_income = gross_income * commission_rate_decimal  # What practitioner keeps
            commission_deduction = gross_income * (Decimal('1') - commission_rate_decimal)  # What company keeps

            if isinstance(payment_detail, CommissionContractor):
                # Contractor: Simple calculation, no tax deductions
                net_payment = commission_income - pos_fees_decimal  # Practitioner gets their commission minus POS fees

                payroll_data = {
                    'user_id': user.id,
                    'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'pay_period_start': start_date.strftime('%Y-%m-%d'),
                    'pay_period_end': end_date.strftime('%Y-%m-%d'),
                    'role_type': 'Commission Contractor',
                    'commission_rate': float(payment_detail.commission_rate),
                    'earnings': {
                        'gross_income': float(gross_income),
                        'adjusted_total': float(adjusted_total),
                        'tax_gst': float(tax_gst),
                        'commission_earned': float(commission_income),
                        'pos_fees': float(pos_fees_decimal),
                        'salary': float(net_payment),  # For template compatibility
                    },
                    'deductions': {
                        'federal_tax': 0.0,
                        'provincial_tax': 0.0,
                        'cpp': 0.0,
                        'ei': 0.0,
                        'commission_deduction': float(commission_deduction),  # Fixed: This is what company keeps
                        'pos_fees': float(pos_fees_decimal),
                    },
                    'totals': {
                        'total_earnings': float(gross_income),
                        'total_deductions': float(commission_deduction + pos_fees_decimal),
                        'net_payment': float(net_payment),
                    },
                    'ytd_amounts': {
                        'earnings': float(user_profile.ytd_pay) + float(net_payment),
                        'deductions': float(user_profile.ytd_deduction),
                    },
                    'breakdown': {
                        'commission_rate': float(payment_detail.commission_rate),
                        'gross_before_fees': float(gross_income),
                        'commission_income': float(commission_income),
                        'commission_deduction': float(commission_deduction),
                    }
                }

            elif isinstance(payment_detail, CommissionEmployee):
                # Employee: Add vacation pay and calculate tax deductions
                vacation_pay = self._calculate_vacation_pay_only(float(commission_income), site_settings)
                vacation_pay_decimal = Decimal(str(vacation_pay))

                # Total taxable income is commission income + vacation pay - pos fees
                total_before_tax_deductions = commission_income + vacation_pay_decimal - pos_fees_decimal

                # Calculate tax deductions on the taxable amount
                deductions_result = self.calculate_deductions(
                    total_taxable_income=float(total_before_tax_deductions),
                    period_days=period_days,
                    user_profile=user_profile,
                    site_settings=site_settings
                )

                net_payment = total_before_tax_deductions - Decimal(str(deductions_result['total_deductions']))

                payroll_data = {
                    'user_id': user.id,
                    'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'pay_period_start': start_date.strftime('%Y-%m-%d'),
                    'pay_period_end': end_date.strftime('%Y-%m-%d'),
                    'role_type': 'Commission Employee',
                    'commission_rate': float(payment_detail.commission_rate),
                    'earnings': {
                        'gross_income': float(gross_income),
                        'adjusted_total': float(adjusted_total),
                        'tax_gst': float(tax_gst),
                        'commission_earned': float(commission_income),
                        'vacation_pay': vacation_pay,
                        'pos_fees': float(pos_fees_decimal),
                        'salary': float(total_before_tax_deductions),  # For template compatibility
                    },
                    'deductions': {
                        'federal_tax': deductions_result['deductions']['federal_tax'],
                        'provincial_tax': deductions_result['deductions']['provincial_tax'],
                        'cpp': deductions_result['deductions']['cpp'],
                        'ei': deductions_result['deductions']['ei'],
                        'commission_deduction': float(commission_deduction),  # Fixed: This is what company keeps
                        'pos_fees': float(pos_fees_decimal),
                    },
                    'totals': {
                        'total_earnings': float(gross_income + vacation_pay_decimal),
                        'total_deductions': float(commission_deduction + pos_fees_decimal) + deductions_result[
                            'total_deductions'],
                        'net_payment': float(net_payment),
                    },
                    'ytd_amounts': {
                        'earnings': deductions_result['projected_ytd_earnings'],
                        'deductions': deductions_result['projected_ytd_deductions'],
                    },
                    'breakdown': {
                        'commission_rate': float(payment_detail.commission_rate),
                        'gross_before_fees': float(gross_income),
                        'vacation_pay': vacation_pay,
                        'cpp_ytd_after': deductions_result['cpp_ytd_after'],
                        'ei_ytd_after': deductions_result['ei_ytd_after'],
                        'commission_income': float(commission_income),
                        'commission_deduction': float(commission_deduction),
                    }
                }

            else:
                raise ValueError(f"Unsupported commission role type: {type(payment_detail)}")

            return payroll_data

        except Exception as e:
            print(f"Error calculating commission payroll: {str(e)}")
            raise e

    def _calculate_rent_deduction(self, user_profile, period_start, period_end):
        """
        Calculate rent deduction if period contains end of month and user has rent role
        Returns: (rent_amount, rent_description)
        """
        try:
            # Check if user has HasRent additional role
            rent_roles = user_profile.additional_roles.filter(polymorphic_ctype__model='hasrent')
            if not rent_roles.exists():
                return Decimal('0'), ''

            # Check if period contains end of any month
            current_date = period_start
            contains_month_end = False

            while current_date <= period_end:
                # Check if this date is the last day of the month
                next_day = current_date + timedelta(days=1)
                if next_day.month != current_date.month:  # Month changed, so current_date is month end
                    contains_month_end = True
                    break
                current_date += timedelta(days=1)

            if contains_month_end:
                rent_role = rent_roles.first()
                print(rent_role.description)
                return Decimal(str(rent_role.monthly_rent)), rent_role.description

            return Decimal('0'), ''

        except Exception as e:
            print(f"Error calculating rent deduction: {str(e)}")
            return Decimal('0'), ''

    def _calculate_revenue_sharing_deductions(self, user, user_profile, gross_income):
        """
        Calculate revenue sharing deductions (money going OUT to others who target this user)
        """
        try:

            # Find all RevenueSharing roles that target this specific user
            revenue_sharing_deductions = RevenueSharing.objects.filter(
                target_type='specific_user',
                target_user=user
            )

            total_deduction = Decimal('0')
            deduction_details = []

            for sharing_role in revenue_sharing_deductions:
                sharing_rate = Decimal(str(sharing_role.sharing_rate))
                deduction_amount = gross_income * sharing_rate
                total_deduction += deduction_amount

                deduction_details.append({
                    'payee': sharing_role.user_profile.user.username,
                    'rate': float(sharing_rate),
                    'amount': float(deduction_amount)
                })

                print(f"Revenue sharing deduction: ${deduction_amount} to {sharing_role.user_profile.user.username}")

            return total_deduction, deduction_details

        except Exception as e:
            print(f"Error calculating revenue sharing deductions: {str(e)}")
            return Decimal('0'), []

    def _ensure_payroll_record_exists(self, target_user, period_start, period_end, clinic_spreadsheet, site_settings):
        """
        Ensure a payroll record exists for the target user in the specified period.
        If not, generate one automatically using the consolidated helper.
        """
        try:
            # Check if record already exists first
            existing_record = PayrollRecords.objects.filter(
                user=target_user,
                period_start=period_start,
                period_end=period_end
            ).first()

            if existing_record:
                return existing_record

            # Use the consolidated helper method
            return self._create_payroll_record_for_user(
                target_user, period_start, period_end, clinic_spreadsheet, site_settings, payroll_type='AUTO'
            )

        except Exception as e:
            print(f"Error ensuring payroll record exists for {target_user.username}: {str(e)}")
            return None

    def _calculate_revenue_sharing_income_from_user(self, user_profile, period_start, period_end, clinic_spreadsheet,
                                                    site_settings):
        """
        Calculate revenue sharing income from specific users (money coming IN)
        """
        try:
            # Query RevenueSharing directly instead of filtering additional_roles
            user_revenue_roles = RevenueSharing.objects.filter(
                user_profile=user_profile,
                target_type='specific_user'
            )

            total_income = Decimal('0')
            income_details = []

            for revenue_role in user_revenue_roles:
                if revenue_role.target_user:
                    # Ensure payroll record exists for target user
                    payroll_record = self._ensure_payroll_record_exists(
                        revenue_role.target_user, period_start, period_end, clinic_spreadsheet, site_settings
                    )

                    if payroll_record:
                        # Calculate revenue sharing based on their gross income
                        sharing_rate = Decimal(str(revenue_role.sharing_rate))

                        # Get gross income from the record
                        if 'Commission' in payroll_record.role_type:
                            gross_income = Decimal(str(payroll_record.subtotal_income + payroll_record.gst))
                        else:
                            gross_income = Decimal(str(payroll_record.subtotal_income))

                        income_amount = gross_income * sharing_rate
                        total_income += income_amount

                        # Update the target user's record with revenue share deduction
                        payroll_record.revenue_share_deduction = float(income_amount)
                        payroll_record.total_deductions = float(
                            Decimal(str(payroll_record.total_deductions)) + income_amount)
                        payroll_record.save()

                        income_details.append({
                            'from_user': revenue_role.target_user.username,
                            'gross_income': float(gross_income),
                            'rate': float(sharing_rate),
                            'amount': float(income_amount)
                        })

                        print(
                            f"Revenue sharing income: ${income_amount} from {revenue_role.target_user.username} (${gross_income} * {sharing_rate})")

            return total_income, income_details

        except Exception as e:
            print(f"Error calculating revenue sharing income from users: {str(e)}")
            return Decimal('0'), []

    def _create_payroll_record(self, user, payroll_data, period_start, period_end, clinic=None,
                               payroll_type='PAY', notes=''):
        """
        Consolidated function to create or update PayrollRecords entries.
        Finds a record based on user, period_start, and period_end.
        """
        try:
            import uuid

            # Extract data from payroll_data
            earnings = payroll_data.get('earnings', {})
            deductions = payroll_data.get('deductions', {})
            totals = payroll_data.get('totals', {})
            role_type = payroll_data.get('role_type', '')

            # Calculate net payment and employer contributions
            net_payment = float(totals.get('net_payment', 0))
            cpp_er = float(deductions.get('cpp', 0))
            ei_er = float(deductions.get('ei', 0)) * 1.4 if 'Employee' in role_type else 0.0

            # Determine subtotal_income based on role type
            is_commission = 'Commission' in role_type or role_type == 'Student'
            if is_commission:
                subtotal_income = float(earnings.get('adjusted_total', 0) or earnings.get('gross_income', 0))
                if earnings.get('tax_gst'):
                    subtotal_income = float(earnings.get('gross_income', 0)) - float(earnings.get('tax_gst', 0))
            else:
                subtotal_income = float(earnings.get('regular_pay', 0) or earnings.get('salary', 0))

            # Prepare the data for the record
            record_data = {
                'email': user.email,
                'clinic': clinic,
                'role_type': role_type,
                'subtotal_income': subtotal_income,
                'hours_worked': float(payroll_data.get('total_hours', 0)),
                'vacation_pay': float(earnings.get('vacation_pay', 0)),
                'overtime_pay': float(earnings.get('overtime_pay', 0)),
                'revenue_share_income': float(earnings.get('revenue_share_income', 0)),
                'gst': float(earnings.get('tax_gst', 0)),
                'total_income': float(totals.get('total_earnings', 0)),
                'commission_deduction': float(deductions.get('commission_deduction', 0)),
                'pos_fees': float(deductions.get('pos_fees', 0) or earnings.get('pos_fees', 0)),
                'provincial_income_tax': float(deductions.get('provincial_tax', 0)),
                'federal_income_tax': float(deductions.get('federal_tax', 0)),
                'cpp_contrib': float(deductions.get('cpp', 0)),
                'cpp_er': cpp_er,
                'ei_contrib': float(deductions.get('ei', 0)),
                'ei_er': ei_er,
                'rent': float(deductions.get('rent', 0)),
                'revenue_share_deduction': float(deductions.get('revenue_share_deduction', 0)),
                'total_deductions': float(totals.get('total_deductions', 0)),
                'net_payment': net_payment,
                'notes': notes,
            }

            # Use update_or_create to find a match or create a new record
            record, created = PayrollRecords.objects.update_or_create(
                user=user,
                period_start=period_start,
                period_end=period_end,
                defaults=record_data
            )

            # If a new record is created, assign it a unique payroll number
            if created:
                payroll_number = f"{payroll_type}-{timezone.now().strftime('%Y%m%d')}-{user.id:04d}-{uuid.uuid4().hex[:6].upper()}"
                record.payroll_number = payroll_number
                record.save()
                print(f"Created new PayrollRecords entry: {payroll_number} for {user.username}")
            else:
                print(f"Updated existing PayrollRecords entry: {record.payroll_number} for {user.username}")

            return record

        except Exception as e:
            print(f"Error creating or updating PayrollRecords entry for {user.username}: {str(e)}")
            return None

    def _create_revenue_share_contributions(self, payroll_record, payroll_data):
        """Helper to create revenue share contribution records"""
        try:
            revenue_contributions = payroll_data.get('revenue_sharing_contributions', {})

            # Create contribution records for revenue sharing income
            if revenue_contributions.get('income_contributors'):
                for contributor in revenue_contributions['income_contributors']:
                    if contributor['user_name'] != 'All Students Combined':
                        try:
                            contributing_user = User.objects.get(username=contributor['user_name'])
                            RevenueShareContribution.objects.create(
                                payroll_record=payroll_record,
                                contributing_user=contributing_user,
                                amount_contributed=float(contributor['amount']),
                                contribution_type=contributor['type']
                            )
                        except User.DoesNotExist:
                            print(f"Warning: Contributing user '{contributor['user_name']}' not found")
                    else:
                        # Handle student contributions
                        if contributor.get('student_breakdown'):
                            total_student_net = sum(float(s['net']) for s in contributor['student_breakdown'])
                            for student_detail in contributor['student_breakdown']:
                                try:
                                    student_user = User.objects.get(username=student_detail['student'])
                                    if total_student_net > 0:
                                        student_share = float(contributor['amount']) * (
                                                float(student_detail['net']) / total_student_net)
                                    else:
                                        student_share = 0.0

                                    RevenueShareContribution.objects.create(
                                        payroll_record=payroll_record,
                                        contributing_user=student_user,
                                        amount_contributed=student_share,
                                        contribution_type='student_share'
                                    )
                                except User.DoesNotExist:
                                    print(f"Warning: Student user '{student_detail['student']}' not found")

            # Set revenue_share_deduction_payee if there's only one recipient
            if revenue_contributions.get('deduction_recipients') and len(
                    revenue_contributions['deduction_recipients']) == 1:
                recipient_name = revenue_contributions['deduction_recipients'][0]['user_name']
                try:
                    recipient_user = User.objects.get(username=recipient_name)
                    payroll_record.revenue_share_deduction_payee = recipient_user
                    payroll_record.save()
                except User.DoesNotExist:
                    print(f"Warning: Deduction recipient '{recipient_name}' not found")

        except Exception as e:
            print(f"Error creating revenue share contributions: {str(e)}")

    def _calculate_revenue_sharing_income_from_students(self, user_profile, period_start, period_end,
                                                        clinic_spreadsheet):
        """
        Calculate revenue sharing income from all students (money coming IN from student activities)
        """
        try:
            # Check if user has revenue sharing targeting all students
            # Query RevenueSharing directly instead of filtering additional_roles
            student_revenue_roles = RevenueSharing.objects.filter(
                user_profile=user_profile,
                target_type='all_students'
            )

            if not student_revenue_roles.exists():
                return Decimal('0'), []

            # Get all users with Student primary role
            student_user_profiles = UserProfile.objects.filter(
                payment_detail__polymorphic_ctype__model='student'
            ).select_related('user')

            if not student_user_profiles.exists():
                return Decimal('0'), []

            total_student_net = Decimal('0')
            student_details = []

            # Calculate net income for each student as if they were commission contractors with 100% rate
            for student_profile in student_user_profiles:
                student_user = student_profile.user

                try:
                    # Get commission data for this student
                    compensation_sheet_id = clinic_spreadsheet.compensation_sales_sheet_id
                    if not compensation_sheet_id:
                        continue

                    commission_data = self._get_commission_data_from_sheet(
                        compensation_sheet_id, student_user, period_start, period_end
                    )

                    if not commission_data:
                        continue

                    # Calculate POS fees
                    pos_fees = self._calculate_pos_fees_for_practitioner(
                        commission_data['invoice_data'], clinic_spreadsheet
                    )

                    # Calculate as if 100% commission rate (students keep 100%, clinic gets 0%)
                    adjusted_total = Decimal(str(commission_data['adjusted_total']))
                    tax_gst = Decimal(str(commission_data['tax_gst']))
                    gross_income = adjusted_total + tax_gst
                    pos_fees_decimal = Decimal(str(pos_fees))

                    # Student net = gross_income - pos_fees (no commission deduction since rate is 100%)
                    student_net = gross_income - pos_fees_decimal
                    total_student_net += student_net

                    student_details.append({
                        'student': student_user.username,
                        'gross_income': float(gross_income),
                        'pos_fees': float(pos_fees_decimal),
                        'net': float(student_net)
                    })

                    print(
                        f"Student calculation: {student_user.username} - Gross: ${gross_income}, POS: ${pos_fees_decimal}, Net: ${student_net}")

                    site_settings = SiteSettings.objects.first()
                    if not site_settings:
                        return Response(
                            {'error': 'Site settings not configured. Please configure tax rates and brackets first.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # Create PayrollRecords entry for the student
                    self._create_payroll_record_for_user(
                        student_user, period_start, period_end, clinic_spreadsheet, site_settings, payroll_type='STU'
                    )

                except Exception as student_error:
                    print(f"Error calculating for student {student_user.username}: {str(student_error)}")
                    continue

            # Apply revenue sharing rate to total student net
            total_revenue_income = Decimal('0')
            for revenue_role in student_revenue_roles:
                sharing_rate = Decimal(str(revenue_role.sharing_rate))
                revenue_income = total_student_net * sharing_rate
                total_revenue_income += revenue_income

                print(f"Revenue sharing from students: ${total_student_net} * {sharing_rate} = ${revenue_income}")

            return total_revenue_income, student_details

        except Exception as e:
            print(f"Error calculating revenue sharing income from students: {str(e)}")
            return Decimal('0'), []

    def _create_payroll_record_for_user(self, target_user, period_start, period_end, clinic_spreadsheet,
                                        site_settings, payroll_type='AUTO'):
        """
        ## UPDATED METHOD ##
        Create a PayrollRecords entry for any user based on their role type using the calculator pattern.
        """
        try:
            # Check if record already exists to avoid duplicate auto-generation
            if PayrollRecords.objects.filter(user=target_user, period_start=period_start,
                                             period_end=period_end).exists():
                return PayrollRecords.objects.get(user=target_user, period_start=period_start, period_end=period_end)

            target_user_profile = target_user.userprofile
            payment_detail = target_user_profile.payment_detail
            if not payment_detail:
                return None

            # Generate payroll data using the appropriate calculator
            target_payroll_data = None
            if isinstance(payment_detail, Student):
                # Handle student calculation for revenue sharing purposes (as 100% commission contractor)
                # ... (this specific logic can be built into a StudentCalculator if needed)
                pass  # Placeholder for student-specific auto-generation if different from commission

            # Use the main calculator logic
            calculator = self._get_payroll_calculator(target_user, target_user_profile, payment_detail,
                                                      clinic_spreadsheet, period_start, period_end, site_settings)
            target_payroll_data = calculator.calculate_base_earnings()

            if not target_payroll_data:
                return None

            # Use consolidated function to create/update the record in the database
            return self._create_payroll_record(
                user=target_user,
                payroll_data=target_payroll_data,
                period_start=period_start,
                period_end=period_end,
                clinic=clinic_spreadsheet.clinic,
                payroll_type=payroll_type,
                notes=f'{payroll_type}-generated payroll record'
            )

        except Exception as e:
            traceback.print_exc()
            print(f"Error creating payroll record for {target_user.username}: {str(e)}")
            return None

    def _apply_final_adjustments(self, payroll_data, payment_detail, period_days, user_profile, site_settings,
                                 rent_deduction, revenue_share_deduction, total_revenue_share_income):
        """
        ## NEW HELPER METHOD ##
        Applies final adjustments for rent and revenue sharing to the calculated payroll data.
        This contains the logic that was previously duplicated inside the large if/elif block.
        """
        is_employee = isinstance(payment_detail, (HourlyEmployee, CommissionEmployee))

        if is_employee:
            original_total_earnings = Decimal(str(payroll_data['totals']['total_earnings']))
            original_total_deductions = Decimal(str(payroll_data['totals']['total_deductions']))

            # If there's revenue sharing income, recalculate taxes on the new, higher total
            if total_revenue_share_income > 0:
                new_taxable_income = original_total_earnings + total_revenue_share_income
                new_deductions_result = self.calculate_deductions(
                    total_taxable_income=float(new_taxable_income),
                    period_days=period_days,
                    user_profile=user_profile,
                    site_settings=site_settings
                )

                # Update payroll with new tax calculations
                payroll_data['deductions'].update(new_deductions_result['deductions'])
                payroll_data['totals']['total_earnings'] = float(new_taxable_income)
                payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)
                payroll_data['breakdown']['cpp_ytd_after'] = new_deductions_result['cpp_ytd_after']
                payroll_data['breakdown']['ei_ytd_after'] = new_deductions_result['ei_ytd_after']

            # Apply final rent and revenue share deductions
            final_total_deductions = Decimal(
                str(payroll_data['totals']['total_deductions'])) + rent_deduction + revenue_share_deduction
            final_net_payment = Decimal(str(payroll_data['totals']['total_earnings'])) - final_total_deductions

            payroll_data['totals']['total_deductions'] = float(final_total_deductions)
            payroll_data['totals']['net_payment'] = float(final_net_payment)

        else:  # Contractor logic
            original_net_payment = Decimal(str(payroll_data['totals']['net_payment']))
            new_net_payment = original_net_payment - rent_deduction - revenue_share_deduction + total_revenue_share_income

            payroll_data['totals']['net_payment'] = float(new_net_payment)
            payroll_data['totals']['total_deductions'] = float(
                Decimal(str(payroll_data['totals']['total_deductions'])) + rent_deduction + revenue_share_deduction)

            if total_revenue_share_income > 0:
                payroll_data['totals']['total_earnings'] = float(
                    Decimal(str(payroll_data['totals']['total_earnings'])) + total_revenue_share_income)
                payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)

        # Add deductions to breakdown for display
        payroll_data['deductions']['rent'] = float(rent_deduction)
        payroll_data['deductions']['revenue_share_deduction'] = float(revenue_share_deduction)

        return payroll_data

    @action(detail=True, methods=['post'])
    def send_payroll(self, request, pk=None):
        """Send payroll email and update YTD amounts"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'You do not have permission to send payroll'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = get_object_or_404(User, id=pk)
            payroll_data = request.data

            # Get clinic_id from request data
            clinic_id = request.data.get('clinic_id')
            clinic = None
            if clinic_id:
                clinic = get_object_or_404(Clinic, id=clinic_id)

            # Update YTD amounts
            try:
                user_profile = user.userprofile
                current_earnings = float(payroll_data.get('totals', {}).get('total_earnings', 0))
                current_deductions = float(payroll_data.get('totals', {}).get('total_deductions', 0))

                user_profile.ytd_pay += current_earnings
                user_profile.ytd_deduction += current_deductions

                breakdown = payroll_data.get('breakdown', {})
                if 'cpp_ytd_after' in breakdown:
                    user_profile.cpp_contrib = float(breakdown['cpp_ytd_after'])
                if 'ei_ytd_after' in breakdown:
                    user_profile.ei_contrib = float(breakdown['ei_ytd_after'])

                user_profile.save()
            except Exception as e:
                return Response(
                    {'error': f'Failed to update YTD amounts: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Send email
            try:
                self._send_payroll_email(user, payroll_data)
            except Exception as e:
                print(f"Email sending failed: {str(e)}")

            # Create PayrollRecords entry using consolidated function
            try:
                period_start = datetime.strptime(payroll_data.get('pay_period_start'), '%Y-%m-%d').date()
                period_end = datetime.strptime(payroll_data.get('pay_period_end'), '%Y-%m-%d').date()

                payroll_record = self._create_payroll_record(
                    user=user,
                    payroll_data=payroll_data,
                    period_start=period_start,
                    period_end=period_end,
                    clinic=clinic,
                    payroll_type='PAY',
                    notes=payroll_data.get('notes', '')
                )

                if not payroll_record:
                    print("Warning: Failed to create PayrollRecords entry")

                # Handle revenue sharing contributions and deduction payee
                if payroll_record:
                    self._create_revenue_share_contributions(payroll_record, payroll_data)

            except Exception as record_error:
                print(f"Error creating PayrollRecords entry: {str(record_error)}")

            return Response({
                'message': 'Payroll sent successfully',
                'user_id': user.id,
                'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'net_payment': payroll_data.get('totals', {}).get('net_payment', 0),
                'new_ytd_earnings': user_profile.ytd_pay,
                'new_ytd_deductions': user_profile.ytd_deduction,
                'sent_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to send payroll: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _send_payroll_email(self, user, payroll_data):
        """Send payroll email to user using Django template with commission support"""
        try:
            if not user.email:
                raise ValueError(f"User {user.username} does not have an email address configured")

            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.conf import settings

            subject = f"Payslip for Pay Period Ending {payroll_data.get('pay_period_end', '')}"

            # Format currency values
            def format_currency(amount):
                return f"{float(amount or 0):.2f}"

            # Get earnings data
            earnings = payroll_data.get('earnings', {})
            breakdown = payroll_data.get('breakdown', {})
            deductions = payroll_data.get('deductions', {})

            # Determine if this is commission-based payroll
            is_commission = 'Commission' in payroll_data.get('role_type', '')

            # Prepare context for template
            context = {
                'user': user,
                'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'pay_period_start': payroll_data.get('pay_period_start', ''),
                'pay_period_end': payroll_data.get('pay_period_end', ''),
                'role_type': payroll_data.get('role_type', ''),

                # Common fields
                'salary_amount': format_currency(earnings.get('salary', 0)),
                'total_earnings': format_currency(payroll_data.get('totals', {}).get('total_earnings', 0)),
                'total_deductions': format_currency(payroll_data.get('totals', {}).get('total_deductions', 0)),
                'net_payment': format_currency(payroll_data.get('totals', {}).get('net_payment', 0)),
                'ytd_earnings': format_currency(payroll_data.get('ytd_amounts', {}).get('earnings', 0)),
                'ytd_deductions': format_currency(payroll_data.get('ytd_amounts', {}).get('deductions', 0)),
                'notes': payroll_data.get('notes', ''),
                'company_name': 'Alternative Therapy On the Go Inc.',
                'company_address': '23 - 7330 122nd Street, Surrey, BC V3W 1B4',
                'rent': format_currency(deductions.get('rent', 0)),
                'rent_description': deductions.get('rent_description', ''),
                'revenue_share_income': format_currency(earnings.get('revenue_share_income', 0)),
                'revenue_sharing_contributions': payroll_data.get('revenue_sharing_contributions', {
                    'income_contributors': [],
                    'deduction_recipients': []
                }),
                'revenue_share_deduction': format_currency(deductions.get('revenue_share_deduction', 0)),
            }

            if is_commission:
                # Commission-specific context
                context.update({
                    'commission_rate': f"{float(payroll_data.get('commission_rate', 0)) * 100:.1f}%",
                    # Convert to percentage
                    'gross_income': format_currency(earnings.get('gross_income', 0)),
                    'adjusted_total': format_currency(earnings.get('adjusted_total', 0)),
                    'tax_gst': format_currency(earnings.get('tax_gst', 0)),
                    'commission_deduction': format_currency(deductions.get('commission_deduction', 0)),
                    'commission_earned': format_currency(earnings.get('commission_earned', 0)),
                    'pos_fees': format_currency(earnings.get('pos_fees', 0)),
                    'vacation_pay': format_currency(earnings.get('vacation_pay', 0)) if earnings.get('vacation_pay',
                                                                                                     0) > 0 else "0.00",

                    # Tax deductions (for commission employees)
                    'federal_tax': format_currency(deductions.get('federal_tax', 0)),
                    'provincial_tax': format_currency(deductions.get('provincial_tax', 0)),
                    'cpp': format_currency(deductions.get('cpp', 0)),
                    'ei': format_currency(deductions.get('ei', 0)),

                    # YTD Contributions for checking caps
                    'cpp_ytd_before': format_currency(
                        (breakdown.get('cpp_ytd_after', 0) or 0) - (deductions.get('cpp', 0) or 0)),
                    'cpp_ytd_after': format_currency(breakdown.get('cpp_ytd_after', 0)),
                    'ei_ytd_before': format_currency(
                        (breakdown.get('ei_ytd_after', 0) or 0) - (deductions.get('ei', 0) or 0)),
                    'ei_ytd_after': format_currency(breakdown.get('ei_ytd_after', 0)),
                })
            else:
                # Hourly-based context
                context.update({
                    'total_hours': payroll_data.get('total_hours', 0),
                    'hourly_wage': format_currency(payroll_data.get('hourly_wage', 0)),

                    # Earnings breakdown for hourly employees
                    'earnings': {
                        'regular_pay': format_currency(earnings.get('regular_pay', 0)),
                        'overtime_pay': format_currency(earnings.get('overtime_pay', 0)),
                        'vacation_pay': format_currency(earnings.get('vacation_pay', 0)),
                    },

                    # Hours breakdown for hourly employees
                    'breakdown': {
                        'regular_hours': breakdown.get('regular_hours', 0),
                        'overtime_hours': breakdown.get('overtime_hours', 0),
                    },

                    # Tax deductions for hourly employees
                    'federal_tax': format_currency(deductions.get('federal_tax', 0)),
                    'provincial_tax': format_currency(deductions.get('provincial_tax', 0)),
                    'cpp': format_currency(deductions.get('cpp', 0)),
                    'ei': format_currency(deductions.get('ei', 0)),

                    # YTD Contributions for checking caps (hourly employees)
                    'cpp_ytd_before': format_currency(
                        (breakdown.get('cpp_ytd_after', 0) or 0) - (deductions.get('cpp', 0) or 0)),
                    'cpp_ytd_after': format_currency(breakdown.get('cpp_ytd_after', 0)),
                    'ei_ytd_before': format_currency(
                        (breakdown.get('ei_ytd_after', 0) or 0) - (deductions.get('ei', 0) or 0)),
                    'ei_ytd_after': format_currency(breakdown.get('ei_ytd_after', 0)),
                })

            # Render HTML template
            html_content = render_to_string('payroll_email.html', context)

            # Send HTML-only email
            send_mail(
                subject=subject,
                message='',  # Empty plain text message
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[user.email],
                fail_silently=False,
                html_message=html_content,  # HTML version only
            )

            print(f"Payroll email sent to {user.email}")

        except Exception as e:
            print(f"Error sending payroll email: {str(e)}")
            raise e

