from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from registration.models import *
import traceback
from django.db import transaction
import re
from api.serializers import *
from .services.google_sheets import *
import pandas as pd
import tempfile
from django.middleware.csrf import get_token
from django.utils import timezone
from datetime import datetime, timedelta
import uuid
from .models import *
from collections import defaultdict
from rest_framework.permissions import AllowAny

# Create your views here.

@login_required(login_url='/registration/login_user/') #view for loading the user into the react app
def chd_app(request):
    csrf_token = get_token(request)
    return render(request, 'index.html', context={'csrf_token': csrf_token})

def home(request):
    return render(request, 'home.html')

@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf(request):
    """
    A simple view to get the CSRF token.
    """
    token = get_token(request)
    return Response({'csrfToken': token})

@api_view(['GET'])
def user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class SiteSettingsViewSet(viewsets.ModelViewSet):
    """
    Simple ViewSet for site settings management.
    Only staff/superusers can access.
    """
    queryset = SiteSettings.objects.all()
    serializer_class = SiteSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only allow staff/superusers"""
        permission_classes = [IsAuthenticated]
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            self.permission_denied(self.request, message="Staff privileges required")
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        """Create or update settings (only allow one instance)"""
        existing = SiteSettings.objects.first()
        if existing:
            # Update existing instead of creating new
            serializer = self.get_serializer(existing, data=request.data)
        else:
            serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClinicViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _check_staff_permission(self, user):
        """Helper method to check if user has staff permissions"""
        return user.is_staff or user.is_superuser

    def _delete_clinic_sheets(self, clinic):
        """Delete the 5 Google Sheets for a clinic"""
        try:
            spreadsheets = clinic.spreadsheets

            sheet_ids = [
                spreadsheets.compensation_sales_sheet_id,
                spreadsheets.daily_transaction_sheet_id,
                spreadsheets.transaction_report_sheet_id,
                spreadsheets.payment_transaction_sheet_id,
                spreadsheets.time_hour_sheet_id  # Added 5th sheet
            ]

            deleted_count = 0
            for sheet_id in sheet_ids:
                if sheet_id:
                    if delete_google_sheet(sheet_id):
                        print(f"Successfully deleted Google Sheet: {sheet_id}")
                        deleted_count += 1
                    else:
                        print(f"Failed to delete Google Sheet: {sheet_id}")

            print(f"Successfully deleted {deleted_count} out of {len([id for id in sheet_ids if id])} sheets")
            return deleted_count

        except ClinicSpreadsheet.DoesNotExist:
            print("No spreadsheets found for clinic")
            return 0
        except Exception as e:
            print(f"Error deleting sheets: {e}")
            return 0

    def _create_clinic_sheets(self, clinic):
        """Create the 5 Google Sheets for a clinic"""
        try:
            # Define sheet titles
            sheet_titles = {
                'compensation_sales': f"{clinic.name} - Compensation + Sales Report",
                'daily_transaction': f"{clinic.name} - Daily Transaction Report",
                'transaction_report': f"{clinic.name} - Transaction Report",
                'payment_transaction': f"{clinic.name} - Payment Transaction Report",
                'time_hour': f"{clinic.name} - Hours Report"  # Added 5th sheet
            }

            # Create each sheet and collect IDs
            sheet_ids = {}
            for sheet_type, title in sheet_titles.items():
                sheet_id = create_new_google_sheet(title)
                if sheet_id:
                    sheet_ids[f"{sheet_type}_sheet_id"] = sheet_id
                    print(f"Created {sheet_type} sheet: {sheet_id}")
                else:
                    print(f"Failed to create {sheet_type} sheet")
                    # If any sheet fails, we might want to clean up or handle differently

            # Create or update ClinicSpreadsheet record
            spreadsheet_data = {
                'compensation_sales_sheet_id': sheet_ids.get('compensation_sales_sheet_id'),
                'daily_transaction_sheet_id': sheet_ids.get('daily_transaction_sheet_id'),
                'transaction_report_sheet_id': sheet_ids.get('transaction_report_sheet_id'),
                'payment_transaction_sheet_id': sheet_ids.get('payment_transaction_sheet_id'),
                'time_hour_sheet_id': sheet_ids.get('time_hour_sheet_id')  # Added 5th sheet
            }

            clinic_spreadsheet, created = ClinicSpreadsheet.objects.get_or_create(
                clinic=clinic,
                defaults=spreadsheet_data
            )

            if not created:
                # Update existing record
                for field, value in spreadsheet_data.items():
                    if value:  # Only update if we got a valid sheet ID
                        setattr(clinic_spreadsheet, field, value)
                clinic_spreadsheet.save()

            return clinic_spreadsheet

        except Exception as e:
            print(f"Error creating sheets for clinic {clinic.name}: {e}")
            return None

    def list(self, request):
        """List all clinics"""
        try:
            clinics = Clinic.objects.all().order_by('name')
            clinics_data = []

            for clinic in clinics:
                # Get or check if spreadsheets exist
                try:
                    spreadsheets = clinic.spreadsheets
                    has_sheets = spreadsheets.has_sheets
                except ClinicSpreadsheet.DoesNotExist:
                    has_sheets = False

                clinics_data.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'created_at': clinic.created_at,
                    'updated_at': clinic.updated_at,
                    'has_sheets': has_sheets
                })

            return Response(clinics_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch clinics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Get a specific clinic"""
        try:
            clinic = Clinic.objects.get(pk=pk)

            # Get or create spreadsheets
            spreadsheets, created = ClinicSpreadsheet.objects.get_or_create(clinic=clinic)

            response_data = {
                'id': clinic.id,
                'name': clinic.name,
                'compensation_sales_sheet_id': spreadsheets.compensation_sales_sheet_id,
                'daily_transaction_sheet_id': spreadsheets.daily_transaction_sheet_id,
                'transaction_report_sheet_id': spreadsheets.transaction_report_sheet_id,
                'payment_transaction_sheet_id': spreadsheets.payment_transaction_sheet_id,
                'time_hour_sheet_id': spreadsheets.time_hour_sheet_id,  # Added 5th sheet
                'created_at': clinic.created_at,
                'updated_at': clinic.updated_at
            }
            return Response(response_data)
        except Clinic.DoesNotExist:
            return Response(
                {'error': 'Clinic not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to fetch clinic: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """Create a new clinic with automatic sheet creation"""
        if not self._check_staff_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            clinic_name = request.data.get('name', '').strip()

            if not clinic_name:
                return Response(
                    {'error': 'Clinic name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create the clinic
            clinic = Clinic.objects.create(name=clinic_name)

            # Automatically create Google Sheets
            clinic_spreadsheet = self._create_clinic_sheets(clinic)

            response_data = {
                'id': clinic.id,
                'name': clinic.name,
                'created_at': clinic.created_at,
                'updated_at': clinic.updated_at,
                'has_sheets': clinic_spreadsheet is not None and clinic_spreadsheet.has_sheets
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):
                return Response(
                    {'error': 'A clinic with this name already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {'error': f'Failed to create clinic: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, pk=None):
        """Delete a clinic and its Google Sheets"""
        if not self._check_staff_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            clinic = Clinic.objects.get(pk=pk)
            clinic_name = clinic.name

            # Delete Google Sheets first
            deleted_sheets_count = self._delete_clinic_sheets(clinic)

            # Then delete database records (CASCADE will delete ClinicSpreadsheet)
            clinic.delete()

            return Response({
                'success': True,
                'message': f'Clinic "{clinic_name}" deleted successfully',
                'deleted_sheets': deleted_sheets_count
            })

        except Clinic.DoesNotExist:
            return Response(
                {'error': 'Clinic not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete clinic: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for dashboard-related endpoints
    """

    @action(detail=True, methods=['get'])
    def income_report(self, request, pk=None):
        """Generate income report aggregated by weekly/monthly periods"""
        try:
            # Get clinic and spreadsheet
            clinic = get_object_or_404(Clinic, id=pk)
            clinic_spreadsheet = get_object_or_404(ClinicSpreadsheet, clinic=clinic)

            if not clinic_spreadsheet.daily_transaction_sheet_id:
                return Response(
                    {'error': 'No daily transaction sheet configured for this clinic'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get date range (1 year from current date)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)

            print(f"Date range: {start_date} to {end_date}")  # Debug

            # Read transaction data from Google Sheet
            sheet_data = read_google_sheets(clinic_spreadsheet.daily_transaction_sheet_id, "A:D")

            if not sheet_data or len(sheet_data) < 2:
                print("No sheet data found")  # Debug
                return Response({
                    'weeklyReport': [],
                    'monthlyReport': []
                })

            print(f"Sheet data rows: {len(sheet_data)}")  # Debug

            # Convert to DataFrame
            headers = sheet_data[0]
            data_rows = sheet_data[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            print(f"DataFrame columns: {df.columns.tolist()}")  # Debug
            print(f"DataFrame shape before cleaning: {df.shape}")  # Debug

            # Clean and filter data
            # Handle different possible date formats
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce', infer_datetime_format=True)
            df['Total'] = pd.to_numeric(df['Total'], errors='coerce').fillna(0)

            print(f"DataFrame shape after date conversion: {df.shape}")  # Debug
            print(f"Date parsing errors: {df['Date'].isna().sum()}")  # Debug

            # Filter out invalid dates first
            df = df[df['Date'].notna()]
            print(f"DataFrame shape after removing invalid dates: {df.shape}")  # Debug

            # Filter out processing fees (more flexible matching)
            if 'Payment Method' in df.columns:
                before_filter = len(df)
                df = df[~df['Payment Method'].str.contains('Processing Fees', case=False, na=False)]
                print(f"Filtered out {before_filter - len(df)} processing fee rows")  # Debug
            else:
                print("Warning: 'Payment Method' column not found")  # Debug

            # Filter by date range
            before_date_filter = len(df)
            df = df[
                (df['Date'].dt.date >= start_date) &
                (df['Date'].dt.date <= end_date)
                ]
            print(f"DataFrame shape after date range filter: {df.shape}")  # Debug
            print(f"Filtered out {before_date_filter - len(df)} rows outside date range")  # Debug

            if len(df) == 0:
                print("No transaction data after filtering")  # Debug
                return Response({
                    'weeklyReport': [],
                    'monthlyReport': [],
                    'debug': {
                        'total_rows_from_sheet': len(data_rows),
                        'date_range': f"{start_date} to {end_date}",
                        'message': 'No transaction data found in date range after filtering'
                    }
                })

            # Get payroll data for the same period
            payroll_records = PayrollRecords.objects.filter(
                clinic=clinic,
                period_start__gte=start_date,
                period_start__lte=end_date
            ).values('period_start', 'net_payment', 'ei_er', 'cpp_er')

            print(f"Found {len(payroll_records)} payroll records")  # Debug

            # Aggregate payroll by period_start date - total cost to clinic
            payroll_by_date = defaultdict(Decimal)
            for record in payroll_records:
                date = record['period_start']
                # Total clinic cost = net_payment + employer EI + employer CPP
                clinic_cost = (
                    Decimal(str(record['net_payment'])) +
                    Decimal(str(record['ei_er'])) +
                    Decimal(str(record['cpp_er']))
                )
                payroll_by_date[date] += clinic_cost
                print(f"Payroll for {date}: net={record['net_payment']}, ei_er={record['ei_er']}, cpp_er={record['cpp_er']}, total={clinic_cost}")  # Debug

            # Generate weekly report
            weekly_report = []
            current_date = start_date
            weeks_processed = 0
            while current_date <= end_date and weeks_processed < 100:  # Safety limit
                # Calculate week boundaries (Monday to Sunday)
                week_start = current_date - timedelta(days=current_date.weekday())
                week_end = week_start + timedelta(days=6)

                if week_end > end_date:
                    week_end = end_date

                # Get transaction income for this week
                week_transactions = df[
                    (df['Date'].dt.date >= week_start) &
                    (df['Date'].dt.date <= week_end)
                    ]
                transaction_income = float(week_transactions['Total'].sum())

                # Get payroll expenses for this week
                payroll_expense = 0
                for check_date in [week_start + timedelta(days=x) for x in range((week_end - week_start).days + 1)]:
                    if check_date in payroll_by_date:
                        payroll_expense += float(payroll_by_date[check_date])

                # Calculate net income
                net_income = transaction_income - payroll_expense

                # Only add weeks that have some data (income or expenses)
                if transaction_income != 0 or payroll_expense != 0:
                    weekly_report.append({
                        'Date': week_start.strftime('%Y-%m-%d'),
                        'Net Income': net_income,
                        'Transaction Income': transaction_income,
                        'Payroll Expense': payroll_expense
                    })

                # Move to next week
                current_date = week_end + timedelta(days=1)
                weeks_processed += 1

            print(f"Generated {len(weekly_report)} weekly records")  # Debug

            # Generate monthly report
            monthly_report = []
            df['YearMonth'] = df['Date'].dt.to_period('M')
            monthly_transactions = df.groupby('YearMonth')['Total'].sum()

            print(f"Monthly transaction totals: {dict(monthly_transactions)}")  # Debug

            # Get all months in the range
            current_month = start_date.replace(day=1)
            end_month = end_date.replace(day=1)
            months_processed = 0

            while current_month <= end_month and months_processed < 24:  # Safety limit
                period = pd.Period(current_month, freq='M')

                # Get transaction income for this month
                transaction_income = float(monthly_transactions.get(period, 0))

                # Get payroll expenses for this month
                month_end = (current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                if month_end > end_date:
                    month_end = end_date

                payroll_expense = 0
                for check_date in [current_month + timedelta(days=x) for x in
                                   range((month_end - current_month).days + 1)]:
                    if check_date in payroll_by_date:
                        payroll_expense += float(payroll_by_date[check_date])

                # Calculate net income
                net_income = transaction_income - payroll_expense

                # Only add months that have some data (income or expenses)
                if transaction_income != 0 or payroll_expense != 0:
                    monthly_report.append({
                        'Date': current_month.strftime('%Y-%m'),
                        'Net Income': net_income,
                        'Transaction Income': transaction_income,
                        'Payroll Expense': payroll_expense
                    })

                # Move to next month
                if current_month.month == 12:
                    current_month = current_month.replace(year=current_month.year + 1, month=1)
                else:
                    current_month = current_month.replace(month=current_month.month + 1)

                months_processed += 1

            print(f"Generated {len(monthly_report)} monthly records")  # Debug

            return Response({
                'weeklyReport': weekly_report,
                'monthlyReport': monthly_report,
                'debug': {
                    'transaction_rows_processed': len(df),
                    'payroll_records_found': len(payroll_records),
                    'date_range': f"{start_date} to {end_date}",
                    'weekly_periods': len(weekly_report),
                    'monthly_periods': len(monthly_report)
                }
            })

        except Exception as e:
            print(f"Error in income_report: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()  # Debug
            return Response(
                {'error': f'Failed to generate income report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class MemberViewSet(viewsets.ViewSet):
    """ViewSet for managing members and their roles"""
    permission_classes = [IsAuthenticated]

    def _check_staff_permission(self, user):
        """Helper method to check if user has staff permissions"""
        return user.is_staff or user.is_superuser

    @action(detail=False, methods=['get'], url_path='current-user')
    def current_user(self, request):
        """Get current user info including staff status"""
        try:
            profile = UserProfile.objects.get(user=request.user)
            is_verified = profile.is_verified
        except UserProfile.DoesNotExist:
            is_verified = False

        user_data = {
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
            'is_verified': is_verified,
        }
        print(str(user_data))
        return Response(user_data)

    def list(self, request):
        """List all users with their roles (staff/superuser only)"""
        if not self._check_staff_permission(request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        users_data = []
        users = User.objects.all().order_by('username')

        for user in users:
            # Get user profile
            try:
                profile = UserProfile.objects.get(user=user)
                is_verified = profile.is_verified
            except UserProfile.DoesNotExist:
                is_verified = False
                profile = None

            # Get primary role and its data
            primary_role = None
            primary_role_data = {}
            payment_frequency = 'semi-monthly'  # default

            if profile:
                try:
                    primary_payment_role = profile.payment_detail
                    if primary_payment_role:
                        primary_role = primary_payment_role.polymorphic_ctype.model
                        payment_frequency = getattr(primary_payment_role, 'payment_frequency', 'semi-monthly')

                        # Get the actual role data based on type
                        if hasattr(primary_payment_role, 'hourly_wage'):
                            primary_role_data['hourly_wage'] = float(primary_payment_role.hourly_wage)
                        elif hasattr(primary_payment_role, 'commission_rate'):
                            primary_role_data['commission_rate'] = float(primary_payment_role.commission_rate)
                        # Student role has no additional data
                except AttributeError:
                    primary_role = None

            # Get additional roles and their data
            additional_roles = []
            additional_role_data = {}
            if profile:
                try:
                    for role in profile.additional_roles.all():
                        role_type = role.polymorphic_ctype.model
                        additional_roles.append(role_type)

                        # Get the specific role data
                        if role_type == 'profitsharing':
                            additional_role_data['profitsharing'] = {
                                'sharing_rate': float(role.sharing_rate),
                                'description': role.description
                            }
                        elif role_type == 'revenuesharing':
                            additional_role_data['revenuesharing'] = {
                                'sharing_rate': float(role.sharing_rate),
                                'description': role.description,
                                'target_type': getattr(role, 'target_type', 'specific_user'),  # Add this line
                                'target_user': role.target_user.username if role.target_user else ''
                            }
                        elif role_type == 'hasrent':
                            additional_role_data['hasrent'] = {
                                'monthly_rent': float(role.monthly_rent),
                                'description': role.description
                            }
                except Exception as e:
                    print(f"Error getting additional roles for {user.username}: {e}")
                    additional_roles = []

            user_data = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'is_verified': is_verified,
                'is_staff': user.is_staff,
                'primaryRole': primary_role,
                'primaryRoleData': primary_role_data,
                'payment_frequency': payment_frequency,
                'additionalRoles': additional_roles,
                'additionalRoleData': additional_role_data,
            }
            users_data.append(user_data)

        return Response(users_data)

    @action(detail=True, methods=['post'], url_path='update-roles')
    def update_roles(self, request, pk=None):
        """Update user roles and verification status (staff/superuser only)"""
        print(f"=== Starting update_roles for user {pk} ===")
        print(f"Request data: {request.data}")

        if not self._check_staff_permission(request.user):
            print("Permission denied")
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            print("Step 1: Finding user")
            user = User.objects.get(pk=pk)
            print(f"Found user: {user.username}")

            print("Step 2: Getting or creating profile")
            profile, created = UserProfile.objects.get_or_create(user=user)
            print(f"Profile - Created: {created}, ID: {profile.id}")

            data = request.data
            primary_role = data.get('primary_role', '')
            additional_roles = data.get('additional_roles', [])
            is_verified = data.get('is_verified', False)
            is_staff = data.get('is_staff', False)
            payment_frequency = data.get('payment_frequency', 'semi-monthly')
            primary_role_values = data.get('primaryRoleValues', {})
            additional_role_values = data.get('additionalRoleValues', {})

            print(f"Primary role: {primary_role}")
            print(f"Additional roles: {additional_roles}")
            print(f"Is verified: {is_verified}")
            print(f"Is staff: {is_staff}")
            print(f"Payment frequency: {payment_frequency}")

            with transaction.atomic():
                print("Step 3: Updating verification status")
                profile.is_verified = is_verified
                profile.save()
                print("Verification status updated")

                # Update user's staff status
                print("Step 3.5: Updating staff status")
                user.is_staff = is_staff
                user.save()
                print(f"Staff status updated to: {is_staff}")

                # Store the payment_frequency (either from request or existing)
                existing_payment_frequency = payment_frequency
                print("Step 4: Handling primary role deletion")
                if hasattr(profile, 'payment_detail') and profile.payment_detail:
                    print(f"Deleting existing primary role: {profile.payment_detail}")
                    try:
                        old_role = profile.payment_detail
                        # Only preserve existing frequency if no new frequency was provided
                        if not payment_frequency or payment_frequency == 'semi-monthly':
                            existing_payment_frequency = getattr(old_role, 'payment_frequency', 'semi-monthly')
                            print(f"Preserved existing payment frequency: {existing_payment_frequency}")
                        old_role.delete()
                        print("Successfully deleted existing primary role")
                        profile.refresh_from_db()
                    except Exception as e:
                        print(f"Error deleting primary role: {e}")
                        print(f"Traceback: {traceback.format_exc()}")

                print("Step 5: Handling additional roles deletion")
                # Delete existing additional roles
                try:
                    existing_additional = profile.additional_roles.all()
                    print(f"Found {existing_additional.count()} existing additional roles")

                    for role in existing_additional:
                        print(f"Deleting: {role}")
                        role.delete()

                    print("Successfully deleted all existing additional roles")
                    profile.refresh_from_db()
                except Exception as e:
                    print(f"Error deleting additional roles: {e}")
                    print(f"Traceback: {traceback.format_exc()}")

                print("Step 6: Creating new primary role")
                # Create new primary role if specified
                if primary_role:
                    print(f"Creating new primary role: {primary_role}")

                    try:
                        role_classes = {
                            'hourlyemployee': HourlyEmployee,
                            'hourlycontractor': HourlyContractor,
                            'commissionemployee': CommissionEmployee,
                            'commissioncontractor': CommissionContractor,
                            'student': Student,  # Add this line
                        }
                        print("Role classes imported successfully")
                    except NameError as e:
                        print(f"NameError importing role classes: {e}")
                        return Response(
                            {'error': f'Role class import error: {e}'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )

                    if primary_role in role_classes:
                        role_class = role_classes[primary_role]
                        print(f"Using role class: {role_class}")

                        try:
                            if primary_role in ['hourlyemployee', 'hourlycontractor']:
                                wage = primary_role_values.get('hourly_wage', 0.00)
                                print(
                                    f"Creating hourly role with wage: {wage}, frequency: {existing_payment_frequency}")
                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    hourly_wage=wage,
                                    payment_frequency=existing_payment_frequency,
                                )
                            elif primary_role in ['commissionemployee', 'commissioncontractor']:
                                rate = primary_role_values.get('commission_rate', 0.00)
                                print(
                                    f"Creating commission role with rate: {rate}, frequency: {existing_payment_frequency}")
                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    commission_rate=rate,
                                    payment_frequency=existing_payment_frequency,
                                )
                            elif primary_role == 'student':
                                print(f"Creating student role with frequency: {existing_payment_frequency}")
                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    payment_frequency=existing_payment_frequency,
                                )
                            print(f"Successfully created primary role: {role_instance}")
                            profile.refresh_from_db()
                        except Exception as e:
                            print(f"Error creating primary role: {e}")
                            print(f"Traceback: {traceback.format_exc()}")
                            return Response(
                                {'error': f'Failed to create primary role: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )

                # Step 7: Creating new additional roles
                print("Step 7: Creating new additional roles")
                try:
                    additional_role_classes = {
                        'profitsharing': ProfitSharing,
                        'revenuesharing': RevenueSharing,
                        'hasrent': HasRent,
                    }
                    print("Additional role classes imported successfully")
                except NameError as e:
                    print(f"NameError importing additional role classes: {e}")
                    return Response(
                        {'error': f'Additional role class import error: {e}'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                # Check for duplicates in the request (application-level constraint)
                if len(additional_roles) != len(set(additional_roles)):
                    return Response(
                        {'error': 'Cannot assign multiple roles of the same type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Create additional roles
                for role_type in additional_roles:
                    print(f"Processing additional role: {role_type}")
                    if role_type in additional_role_classes:
                        role_class = additional_role_classes[role_type]
                        role_data = additional_role_values.get(role_type, {})
                        print(f"Role data for {role_type}: {role_data}")

                        try:
                            if role_type == 'profitsharing':
                                description = role_data.get('description', f"Profit sharing for {user.username}")
                                sharing_rate = role_data.get('sharing_rate', 0.00)
                                print(f"Creating ProfitSharing: desc='{description}', rate={sharing_rate}")

                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    description=description,
                                    sharing_rate=sharing_rate
                                )

                            elif role_type == 'revenuesharing':
                                target_type = role_data.get('target_type', 'specific_user')
                                target_user = None
                                target_username = role_data.get('target_user', '')

                                print(f"Revenue sharing target_type: {target_type}")
                                print(f"Target username: '{target_username}'")

                                # Validate target_type and target_user relationship
                                if target_type == 'specific_user':
                                    if not target_username or target_username.strip() == '' or target_username == 'null':
                                        return Response(
                                            {'error': 'Target user is required when target type is "specific_user"'},
                                            status=status.HTTP_400_BAD_REQUEST
                                        )
                                    try:
                                        target_user = User.objects.get(username=target_username.strip())
                                        print(f"Found target user: {target_user.username}")
                                    except User.DoesNotExist:
                                        print(f"Target user not found: {target_username}")
                                        return Response(
                                            {'error': f'Target user "{target_username}" not found'},
                                            status=status.HTTP_400_BAD_REQUEST
                                        )
                                elif target_type == 'all_students':
                                    if target_username and target_username.strip() != '' and target_username != 'null':
                                        return Response(
                                            {'error': 'Target user should be empty when target type is "all_students"'},
                                            status=status.HTTP_400_BAD_REQUEST
                                        )
                                    target_user = None
                                    print("Revenue sharing will target all students")

                                description = role_data.get('description', f"Revenue sharing for {user.username}")
                                sharing_rate = role_data.get('sharing_rate', 0.00)
                                print(
                                    f"Creating RevenueSharing: desc='{description}', rate={sharing_rate}, target_type={target_type}, target={target_user}")

                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    description=description,
                                    target_type=target_type,  # Add this line
                                    target_user=target_user,
                                    sharing_rate=sharing_rate
                                )

                            elif role_type == 'hasrent':
                                description = role_data.get('description', f"Rent payment for {user.username}")
                                monthly_rent = role_data.get('monthly_rent', 0.00)
                                print(f"Creating HasRent: desc='{description}', rent={monthly_rent}")

                                role_instance = role_class.objects.create(
                                    user_profile=profile,
                                    description=description,
                                    monthly_rent=monthly_rent
                                )

                            print(f"Successfully created {role_type}: {role_instance}")

                        except Exception as e:
                            print(f"Error creating {role_type}: {e}")
                            print(f"Traceback: {traceback.format_exc()}")
                            return Response(
                                {'error': f'Failed to create {role_type} role: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR
                            )
                    else:
                        print(f"Unknown role type: {role_type}")

            print("=== Update completed successfully ===")
            return Response({
                'success': True,
                'message': 'User roles updated successfully'
            })

        except User.DoesNotExist:
            print(f"User not found: {pk}")
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Unexpected error in update_roles: {str(e)}")
            print(f"Exception type: {type(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Failed to update user roles: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SpreadsheetViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def _has_access(self, user):
        """
        Simplified permission check - only staff and superusers have access
        """
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    def _get_clinic_spreadsheet_by_sheet_id(self, sheet_id):
        """
        Find the ClinicSpreadsheet that owns this sheet_id
        Returns the ClinicSpreadsheet object if found, None otherwise
        """
        try:
            # Check all five possible sheet ID fields
            clinic_spreadsheet = ClinicSpreadsheet.objects.filter(
                models.Q(compensation_sales_sheet_id=sheet_id) |
                models.Q(daily_transaction_sheet_id=sheet_id) |
                models.Q(transaction_report_sheet_id=sheet_id) |
                models.Q(payment_transaction_sheet_id=sheet_id) |
                models.Q(time_hour_sheet_id=sheet_id)  # Added 5th sheet
            ).first()

            return clinic_spreadsheet
        except Exception as e:
            print(f"Error finding clinic spreadsheet: {e}")
            return None

    def _get_sheet_info(self, clinic_spreadsheet, sheet_id):
        """
        Get sheet information based on which field matches the sheet_id
        """
        if clinic_spreadsheet.compensation_sales_sheet_id == sheet_id:
            return {
                'name': f"{clinic_spreadsheet.clinic.name} - Compensation + Sales Report",
                'type': 'compensation_sales'
            }
        elif clinic_spreadsheet.daily_transaction_sheet_id == sheet_id:
            return {
                'name': f"{clinic_spreadsheet.clinic.name} - Daily Transaction Report",
                'type': 'daily_transaction'
            }
        elif clinic_spreadsheet.transaction_report_sheet_id == sheet_id:
            return {
                'name': f"{clinic_spreadsheet.clinic.name} - Transaction Report",
                'type': 'transaction_report'
            }
        elif clinic_spreadsheet.payment_transaction_sheet_id == sheet_id:
            return {
                'name': f"{clinic_spreadsheet.clinic.name} - Payment Transaction Report",
                'type': 'payment_transaction'
            }
        elif clinic_spreadsheet.time_hour_sheet_id == sheet_id:  # Added 5th sheet
            return {
                'name': f"{clinic_spreadsheet.clinic.name} - Hours Report",
                'type': 'time_hour'
            }
        return {'name': 'Unknown Sheet', 'type': 'unknown'}

    def _clean_csv_file(self, file_path):
        """
        General CSV cleaning function that handles:
        - Extra header lines (like Jane Payments)
        - Empty lines
        - Malformed first lines
        - Encoding issues
        Returns cleaned dataframe
        """
        try:
            # First, try reading normally with UTF-8
            df = pd.read_csv(file_path, encoding='utf-8').fillna('')
            if not df.empty and len(df.columns) > 3:  # Reasonable number of columns
                return df
        except UnicodeDecodeError:
            # Try with latin1 encoding
            try:
                df = pd.read_csv(file_path, encoding='latin1').fillna('')
                if not df.empty and len(df.columns) > 3:
                    return df
            except:
                pass
        except:
            pass

        # If normal reading failed, try cleaning the file
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
                lines = f.readlines()

        # Remove empty lines and find the best header line
        non_empty_lines = [line.strip() for line in lines if line.strip()]

        if not non_empty_lines:
            raise ValueError("File appears to be empty")

        # Look for a line that looks like CSV headers (has commas and reasonable length)
        header_line_index = 0
        for i, line in enumerate(non_empty_lines):
            if ',' in line and len(line.split(',')) >= 3:  # At least 3 columns
                header_line_index = i
                break

        # Use the cleaned lines from header onwards
        cleaned_lines = non_empty_lines[header_line_index:]

        # Write to temp file and read as dataframe
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8',
                                         newline='') as temp_file:
            temp_file.write('\n'.join(cleaned_lines))
            cleaned_path = temp_file.name

        try:
            df = pd.read_csv(cleaned_path, encoding='utf-8').fillna('')
            return df
        except UnicodeDecodeError:
            df = pd.read_csv(cleaned_path, encoding='latin1').fillna('')
            return df
        finally:
            if os.path.exists(cleaned_path):
                os.remove(cleaned_path)

    def _detect_csv_type(self, df):
        """
        Simplified CSV type detection based on key headers
        """
        headers = [col.strip().lower() for col in df.columns]
        header_set = set(headers)

        # Define key headers for each type (only the most distinctive ones)
        type_signatures = {
            'daily_transaction': {'date', 'payment method', 'total', 'number of transactions'},
            'transaction_report': {'payment date', 'patient_guid', 'applied to'},
            'payment_transaction': {'payment type', 'customer charge', 'jane payments fee'},
            'compensation_sales_compensation': {'commission rate', 'adjustments owed to staff member', 'practitioner'},
            'compensation_sales_sales': {'location', 'staff member', 'payer', 'collected', 'balance'},
            'time_hour': {'staff member', 'start time', 'end time', 'payable time'}  # Added hours report detection
        }

        # Check for exact or close matches
        for type_name, required_headers in type_signatures.items():
            if required_headers.issubset(header_set):
                if type_name.startswith('compensation_sales'):
                    return 'compensation_sales', type_name.split('_')[-1]
                else:
                    return type_name, None

        return None, None

    def _get_target_sheet_id(self, clinic_id, sheet_type):
        """
        Get the sheet ID for the detected type
        """
        try:
            clinic = Clinic.objects.get(pk=clinic_id)
            clinic_spreadsheet, _ = ClinicSpreadsheet.objects.get_or_create(clinic=clinic)

            field_map = {
                'compensation_sales': clinic_spreadsheet.compensation_sales_sheet_id,
                'daily_transaction': clinic_spreadsheet.daily_transaction_sheet_id,
                'transaction_report': clinic_spreadsheet.transaction_report_sheet_id,
                'payment_transaction': clinic_spreadsheet.payment_transaction_sheet_id,
                'time_hour': clinic_spreadsheet.time_hour_sheet_id,  # Added 5th sheet
            }

            return field_map.get(sheet_type)
        except:
            return None

    def _sort_dataframe_by_type(self, df, sheet_type):
        """
        Sort dataframe based on sheet type requirements
        """
        try:
            if sheet_type == 'payment_transaction':
                # Sort by Payment column (integer) from biggest to smallest
                if 'Payment' in df.columns:
                    # Convert to numeric, treating non-numeric as 0
                    df['_payment_sort'] = pd.to_numeric(df['Payment'], errors='coerce').fillna(0)
                    df = df.sort_values('_payment_sort', ascending=False).drop('_payment_sort', axis=1)

            elif sheet_type == 'daily_transaction':
                # Sort by Date column from most recent to oldest
                # Format: "August 02 2025, 11:00 AM"
                if 'Date' in df.columns:
                    df['_date_sort'] = pd.to_datetime(df['Date'], errors='coerce')
                    df = df.sort_values('_date_sort', ascending=False, na_position='last').drop('_date_sort', axis=1)

            elif sheet_type == 'transaction_report':
                # Sort by Payment Date column from most recent to oldest
                # Format: "07-21-2025"
                if 'Payment Date' in df.columns:
                    df['_date_sort'] = pd.to_datetime(df['Payment Date'], format='%m-%d-%Y', errors='coerce')
                    df = df.sort_values('_date_sort', ascending=False, na_position='last').drop('_date_sort', axis=1)

            elif sheet_type == 'time_hour':  # Added hours report sorting
                # Sort by Date column from most recent to oldest
                if 'Date' in df.columns:
                    df['_date_sort'] = pd.to_datetime(df['Date'], errors='coerce')
                    df = df.sort_values('_date_sort', ascending=False, na_position='last').drop('_date_sort', axis=1)

            elif sheet_type == 'compensation_sales':
                # Keep existing merge column sorting logic
                merge_column = self.detect_merge_column(df)
                if merge_column:
                    df['_sort_key'] = df[merge_column].apply(self.extract_sort_key)
                    df = df.sort_values('_sort_key').drop('_sort_key', axis=1)

            # Clean any NaN values that might have been introduced during sorting
            return df.fillna('')

        except Exception as e:
            print(f"Error sorting dataframe: {e}")
            # Return cleaned dataframe if sorting fails
            return df.fillna('')

    def _upload_to_sheet(self, sheet_id, df, require_merge_column=False, sheet_type=None):
        """
        Upload dataframe to Google Sheet, handling merge column logic, sorting, and duplicate prevention
        """
        clinic_spreadsheet = self._get_clinic_spreadsheet_by_sheet_id(sheet_id)
        existing_data, existing_headers = padded_google_sheets(sheet_id, 'A1:Z5')
        is_first_upload = not existing_data and not existing_headers

        if require_merge_column:
            # This is compensation_sales type - use existing merge logic
            merge_column = self.detect_merge_column(df)
            if not merge_column:
                raise ValueError('This sheet type requires a column with format #####-P## or #####-C##')

            if is_first_upload:
                # Store merge column and sort data
                clinic_spreadsheet.merge_column = merge_column
                clinic_spreadsheet.save()
                # Sort the dataframe
                df = self._sort_dataframe_by_type(df, sheet_type)
            else:
                # For subsequent uploads, merge logic will be handled elsewhere
                # Don't sort here as merge_dataframes_by_key handles its own sorting
                pass
        else:
            # For non-merge based sheet types, handle duplicates with existing data
            if not is_first_upload:
                # Merge with existing data and remove duplicates
                df = self._merge_with_existing_data(sheet_id, df, sheet_type)
            else:
                # First upload - just remove duplicates within the new data and sort
                df = self._remove_duplicate_rows(df, sheet_type)
                df = self._sort_dataframe_by_type(df, sheet_type)

        # Ensure data is clean before uploading
        df = df.fillna('').replace([float('inf'), float('-inf')], '')

        # Upload data
        data_to_upload = [df.columns.tolist()] + df.values.tolist()
        write_google_sheets(sheet_id, 'Sheet1', data_to_upload)

        return 'first_upload' if is_first_upload else 'data_updated'

    def detect_merge_column(self, df):
        """
        Detects column with format #####-P## or #####-C##
        Returns column name if found, None otherwise
        """
        pattern = r'^\d{5}-[PC]\d{2}$'

        for col in df.columns:
            # Check if any non-null values in this column match the pattern
            sample_values = df[col].dropna().astype(str).head(10)  # Check first 10 non-null values
            if any(re.match(pattern, str(val)) for val in sample_values):
                return col
        return None

    def extract_sort_key(self, value):
        """
        Extracts the 5-digit number from format #####-P## or #####-C##
        Returns integer for sorting, or float('inf') if invalid format
        """
        if pd.isna(value):
            return float('inf')

        pattern = r'^(\d{5})-[PC]\d{2}$'
        match = re.match(pattern, str(value))
        if match:
            return int(match.group(1))
        return float('inf')

    def merge_dataframes_by_key(self, existing_df, new_df, existing_merge_col, new_merge_col):
        """
        Merge dataframes with the following logic:
        1. If a key exists in both, update the existing row with new data ONLY if data is different
        2. If a key only exists in new_df, add it as a new row
        3. Keep all existing rows, even if not in new_df
        4. Skip identical rows (same key + same data in overlapping columns)
        5. Sort final result by the key column
        """
        try:
            if existing_df.empty:
                # If no existing data, rename merge column and return sorted new data
                new_df_copy = new_df.copy().fillna('')
                if new_merge_col != existing_merge_col:
                    new_df_copy = new_df_copy.rename(columns={new_merge_col: existing_merge_col})

                new_df_copy['_sort_key'] = new_df_copy[existing_merge_col].apply(self.extract_sort_key)
                result = new_df_copy.sort_values('_sort_key').drop('_sort_key', axis=1)
                return result.fillna('')

            # Clean data - replace NaN with empty strings and create copies
            existing_df = existing_df.copy().fillna('')
            new_df = new_df.copy().fillna('')

            # Rename new merge column to match existing if different
            if new_merge_col != existing_merge_col and new_merge_col in new_df.columns:
                new_df = new_df.rename(columns={new_merge_col: existing_merge_col})

            # Create a combined column set
            all_columns = list(existing_df.columns)
            for col in new_df.columns:
                if col not in all_columns:
                    all_columns.append(col)

            # Convert dataframes to dictionaries for easier manipulation
            existing_dict = {}
            for _, row in existing_df.iterrows():
                key = str(row[existing_merge_col]).strip()
                if key and key != 'nan' and key != '':  # Skip empty, nan, or blank keys
                    existing_dict[key] = row.to_dict()

            new_dict = {}
            for _, row in new_df.iterrows():
                key = str(row[existing_merge_col]).strip()
                if key and key != 'nan' and key != '':  # Skip empty, nan, or blank keys
                    new_dict[key] = row.to_dict()

            # Process all keys (existing and new)
            all_keys = set(existing_dict.keys()) | set(new_dict.keys())
            result_data = []

            for key in all_keys:
                merged_row = {}

                # Initialize with empty values for all columns
                for col in all_columns:
                    merged_row[col] = ''

                # Start with existing data if available
                if key in existing_dict:
                    for col, val in existing_dict[key].items():
                        merged_row[col] = str(val) if val is not None else ''

                # Check if we need to update with new data
                if key in new_dict:
                    new_row_data = new_dict[key]
                    has_changes = False

                    # Check if this is truly new data or identical to existing
                    if key in existing_dict:
                        # Compare overlapping columns to see if anything actually changed
                        existing_row_data = existing_dict[key]

                        for col, new_val in new_row_data.items():
                            new_val_str = str(new_val) if new_val is not None else ''
                            existing_val_str = str(existing_row_data.get(col, '')) if existing_row_data.get(
                                col) is not None else ''

                            # Only consider it a change if:
                            # 1. New value is not empty AND different from existing, OR
                            # 2. Existing value is empty and new value is not empty
                            if new_val_str != '' and new_val_str != existing_val_str:
                                has_changes = True
                                break
                            elif existing_val_str == '' and new_val_str != '':
                                has_changes = True
                                break

                        # If no changes detected, skip updating this row
                        if not has_changes:
                            print(f"Skipping identical row for key: {key}")
                            # Just add the existing row as-is
                            result_data.append(merged_row)
                            continue

                    # Update/add with new data (only if there are actual changes or it's a completely new key)
                    for col, val in new_row_data.items():
                        val_str = str(val) if val is not None else ''
                        # Update if new value is not empty, or if existing value is empty
                        if val_str != '' or merged_row.get(col, '') == '':
                            merged_row[col] = val_str

                    print(f"Updated/added row for key: {key}")

                result_data.append(merged_row)

            # Remove any completely empty rows (all values are empty strings)
            result_data = [row for row in result_data if any(val.strip() for val in row.values())]

            # Create result dataframe
            result_df = pd.DataFrame(result_data, columns=all_columns).fillna('')

            # Sort by merge column
            result_df['_sort_key'] = result_df[existing_merge_col].apply(self.extract_sort_key)
            result_df = result_df.sort_values('_sort_key').drop('_sort_key', axis=1)

            return result_df.fillna('')

        except Exception as e:
            print(f"Error in merge_dataframes_by_key: {str(e)}")
            raise e

    # DEFAULT GET: for retrieving a whole spreadsheet from google sheets for display in the frontend
    def retrieve(self, request, pk=None):
        sheet_id = pk
        user = request.user

        # Simplified permission check
        if not self._has_access(user):
            return Response(
                {'error': f'No permission for user {user.username}'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find the clinic spreadsheet that owns this sheet
        clinic_spreadsheet = self._get_clinic_spreadsheet_by_sheet_id(sheet_id)
        if not clinic_spreadsheet:
            return Response(
                {'error': f'Sheet with ID {sheet_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        sheet_info = self._get_sheet_info(clinic_spreadsheet, sheet_id)

        try:
            # Fetch fresh data from Google Sheets
            sheet_data, sheet_header = padded_google_sheets(sheet_id, 'Sheet1')

            return Response({
                'success': True,
                'sheet_data': sheet_data,
                'sheet_header': sheet_header,
                'sheet_name': sheet_info['name'],
                'sheet_type': sheet_info['type'],
                'clinic_name': clinic_spreadsheet.clinic.name,
                'clinic_id': clinic_spreadsheet.clinic.id,
                'sheet_date': clinic_spreadsheet.created_at,
                'sheet_id': sheet_id,
                'merge_column': getattr(clinic_spreadsheet, 'merge_column', None)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch sheet data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # For checking if the user is allowed access to the spreadsheet before uploading
    @action(detail=True, methods=['GET'])
    def check_perms(self, request, pk=None):
        if self._has_access(request.user):
            return Response(
                {'success': True},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'success': False, 'error': 'No permission to access this sheet'},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=False, methods=['POST'])
    def detect_and_upload(self, request):
        """
        Upload CSV, detect type, and upload to appropriate sheet
        """
        if not self._has_access(request.user):
            return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)

        clinic_id = request.data.get('clinic_id')
        uploaded_file = request.FILES.get('file')

        if not clinic_id or not uploaded_file:
            return Response({'error': 'clinic_id and file are required'}, status=status.HTTP_400_BAD_REQUEST)

        temp_file_path = None
        try:
            # Save uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # Clean and read CSV using general cleaning method
            df = self._clean_csv_file(temp_file_path)

            # Detect type
            sheet_type, subtype = self._detect_csv_type(df)
            if not sheet_type:
                return Response({
                    'error': 'Could not detect CSV type from headers',
                    'detected_headers': df.columns.tolist()
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get target sheet
            target_sheet_id = self._get_target_sheet_id(clinic_id, sheet_type)
            if not target_sheet_id:
                return Response({
                    'error': f'No {sheet_type} sheet configured for this clinic'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if compensation_sales needs merge handling
            if sheet_type == 'compensation_sales':
                clinic_spreadsheet = self._get_clinic_spreadsheet_by_sheet_id(target_sheet_id)
                existing_data, _ = padded_google_sheets(target_sheet_id, 'A1:Z5')

                if existing_data:  # Not first upload, need merge preview
                    merge_column = self.detect_merge_column(df)
                    if not merge_column:
                        return Response({
                            'error': 'Compensation/Sales data requires merge column format #####-P## or #####-C##'
                        }, status=status.HTTP_400_BAD_REQUEST)

                    # Store for merge process
                    request.session.update({
                        'temp_file_path': temp_file_path,
                        'uploaded_merge_column': merge_column,
                        'stored_merge_column': clinic_spreadsheet.merge_column,
                        'target_sheet_id': target_sheet_id
                    })

                    return Response({
                        'success': True,
                        'action': 'merge_required',
                        'sheet_type': sheet_type,
                        'target_sheet_id': target_sheet_id,
                        'headers': df.columns.tolist(),
                        'preview_data': df.head(5).fillna('').to_dict(orient='records'),
                    })

            # Direct upload for other types or first upload
            action = self._upload_to_sheet(
                target_sheet_id,
                df,
                require_merge_column=(sheet_type == 'compensation_sales'),
                sheet_type=sheet_type
            )

            return Response({
                'success': True,
                'action': action,
                'sheet_type': sheet_type,
                'target_sheet_id': target_sheet_id,
                'message': f'Successfully uploaded {sheet_type} data'
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up temp file if not stored in session
            if temp_file_path and 'temp_file_path' not in request.session:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

    @action(detail=False, methods=['POST'])
    def cleanup_temp_files(self, request):
        """
        Clean up temporary files from session
        """
        try:
            session_files = ['merged_data_path', 'temp_file_path']
            for file_key in session_files:
                file_path = request.session.get(file_key)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

            # Clear all session data
            session_keys = ['merged_data_path', 'temp_file_path', 'uploaded_merge_column',
                            'stored_merge_column', 'target_sheet_id']
            for key in session_keys:
                request.session.pop(key, None)

            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def upload_csv(self, request, pk=None):
        sheet_id = pk

        # Simplified permission check
        if not self._has_access(request.user):
            return Response(
                {'error': 'No permission to upload to this sheet'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find the clinic spreadsheet
        clinic_spreadsheet = self._get_clinic_spreadsheet_by_sheet_id(sheet_id)
        if not clinic_spreadsheet:
            return Response(
                {'error': 'Sheet not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'no file provided'}, status=status.HTTP_400_BAD_REQUEST)

        temp_file_path = ''
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            # Use general CSV cleaning method
            uploaded_df = self._clean_csv_file(temp_file_path)

            # Get existing sheet data
            sheet_data, sheet_headers = padded_google_sheets(pk, 'A1:Z5')

            # FIRST UPLOAD CASE
            if not sheet_data and not sheet_headers:
                # Detect merge column in the uploaded file
                merge_column = self.detect_merge_column(uploaded_df)

                if not merge_column:
                    return Response({
                        'error': 'No column with required format (#####-P## or #####-C##) found'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Store merge column in ClinicSpreadsheet model
                clinic_spreadsheet.merge_column = merge_column
                clinic_spreadsheet.save()

                # Sort by the merge column before uploading (compensation/sales data)
                uploaded_df = self._sort_dataframe_by_type(uploaded_df, 'compensation_sales')

                # Ensure data is clean before uploading
                uploaded_df = uploaded_df.fillna('').replace([float('inf'), float('-inf')], '')

                data_to_upload = [uploaded_df.columns.tolist()] + uploaded_df.values.tolist()
                write_google_sheets(pk, 'Sheet1', data_to_upload)

                return Response({
                    'status': 'first_upload_complete',
                    'merge_column': merge_column
                }, status=status.HTTP_200_OK)

            # SUBSEQUENT UPLOADS
            else:
                # Get stored merge column
                stored_merge_column = getattr(clinic_spreadsheet, 'merge_column', None)

                if not stored_merge_column:
                    return Response({
                        'error': 'No merge column stored for this sheet'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Detect merge column in uploaded file
                uploaded_merge_column = self.detect_merge_column(uploaded_df)

                if not uploaded_merge_column:
                    return Response({
                        'error': 'No column with required format found in uploaded file'
                    }, status=status.HTTP_400_BAD_REQUEST)

                request.session['temp_file_path'] = temp_file_path
                request.session['uploaded_merge_column'] = uploaded_merge_column
                request.session['stored_merge_column'] = stored_merge_column

                return Response({
                    'success': True,
                    'headers': uploaded_df.columns.tolist(),
                    'body': uploaded_df.head(5).fillna('').to_dict(orient='records'),
                    'sheet_data': sheet_data,
                    'sheet_headers': sheet_headers,
                    'uploaded_merge_column': uploaded_merge_column,
                    'stored_merge_column': stored_merge_column,
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def merge_sheets(self, request, pk=None):
        # Simplified permission check
        if not self._has_access(request.user):
            return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Use target_sheet_id from session (set by detect_and_upload) or fallback to URL
            sheet_id = request.session.get('target_sheet_id', pk)

            # Get session data
            session_data = {
                'uploaded_merge_column': request.session.get('uploaded_merge_column'),
                'stored_merge_column': request.session.get('stored_merge_column'),
                'temp_file_path': request.session.get('temp_file_path')
            }

            if not all(session_data.values()):
                return Response({'error': 'Missing merge data'}, status=status.HTTP_400_BAD_REQUEST)

            if not os.path.exists(session_data['temp_file_path']):
                return Response({'error': 'Upload file not found'}, status=status.HTTP_400_BAD_REQUEST)

            # Get existing data and merge
            existing_data, existing_headers = padded_google_sheets(sheet_id, 'Sheet1')
            existing_df = pd.DataFrame(existing_data, columns=existing_headers).fillna('') if existing_data else pd.DataFrame()

            # Use general CSV cleaning method
            uploaded_df = self._clean_csv_file(session_data['temp_file_path'])

            merged_df = self.merge_dataframes_by_key(
                existing_df, uploaded_df,
                session_data['stored_merge_column'],
                session_data['uploaded_merge_column']
            )

            # merge_dataframes_by_key already handles sorting for compensation_sales
            # Ensure data is clean for storage
            merged_df = merged_df.fillna('').replace([float('inf'), float('-inf')], '')

            # Store merged data with robust encoding
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w+', encoding='utf-8',
                                             newline='') as temp_file:
                merged_df.fillna('').replace([float('inf'), float('-inf')], '').to_csv(temp_file, index=False,
                                                                                       encoding='utf-8')
                request.session['merged_data_path'] = temp_file.name

            return Response({
                'success': True,
                'merged_headers': merged_df.columns.tolist(),
                'merged_data': merged_df.fillna('').to_dict(orient='records'),
                'merge_strategy': 'Key-based merge with update/insert logic'
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def confirm_merge_sheets(self, request, pk=None):
        # Simplified permission check
        if not self._has_access(request.user):
            return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)

        # Use target_sheet_id from session or fallback to URL
        sheet_id = request.session.get('target_sheet_id', pk)
        merged_data_path = request.session.get('merged_data_path')

        if not merged_data_path or not os.path.exists(merged_data_path):
            return Response({'error': 'No merge data found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Read merged data with encoding fallback
            try:
                merged_df = pd.read_csv(merged_data_path, encoding='utf-8').fillna('')
            except UnicodeDecodeError:
                # Fallback to latin1 if utf-8 fails
                merged_df = pd.read_csv(merged_data_path, encoding='latin1').fillna('')

            # Clean any remaining problematic characters thoroughly
            merged_df = merged_df.fillna('').replace([float('inf'), float('-inf'), 'inf', '-inf'], '')

            # Ensure all data is string type to avoid upload issues
            for col in merged_df.columns:
                merged_df[col] = merged_df[col].astype(str).replace('nan', '')

            write_df_to_sheets(sheet_id, 'Sheet1', merged_df)

            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up all session data
            session_keys = ['merged_data_path', 'temp_file_path', 'uploaded_merge_column',
                            'stored_merge_column', 'target_sheet_id']
            for key in session_keys:
                file_path = request.session.get(key)
                if key.endswith('_path') and file_path and os.path.exists(file_path):
                    os.remove(file_path)
                request.session.pop(key, None)

    @action(detail=True, methods=['POST'])
    def delete_session_storage(self, request, pk=None):
        try:
            session_files = ['merged_data_path', 'temp_file_path']
            for file_key in session_files:
                file_path = request.session.get(file_key)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

            # Clean up all session data
            session_keys = ['merged_data_path', 'temp_file_path', 'uploaded_merge_column',
                            'stored_merge_column', 'target_sheet_id']
            for key in session_keys:
                request.session.pop(key, None)

            return Response({'success': True})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _remove_duplicate_rows(self, df, sheet_type):
        """
        Remove completely duplicate rows from dataframe.
        For different sheet types, we may want different duplicate detection logic.
        """
        try:
            if df.empty:
                return df

            # Convert all columns to string to ensure consistent comparison
            df_str = df.astype(str).fillna('')

            # For most sheet types, remove rows that are completely identical
            if sheet_type in ['daily_transaction', 'transaction_report', 'payment_transaction', 'time_hour']:
                # Remove completely duplicate rows
                original_count = len(df_str)
                df_deduped = df_str.drop_duplicates(keep='first')
                removed_count = original_count - len(df_deduped)

                if removed_count > 0:
                    print(f"Removed {removed_count} duplicate rows from {sheet_type} data")

                return df_deduped

            # For compensation_sales, duplicates should be handled by merge logic
            elif sheet_type == 'compensation_sales':
                return df

            else:
                # Default: remove complete duplicates
                return df_str.drop_duplicates(keep='first')

        except Exception as e:
            print(f"Error removing duplicates: {e}")
            return df

    def _merge_with_existing_data(self, sheet_id, new_df, sheet_type):
        """
        For non-merge based sheet types, combine new data with existing data
        and remove duplicates intelligently.
        """
        try:
            # Get existing data
            existing_data, existing_headers = padded_google_sheets(sheet_id, 'Sheet1')

            if not existing_data or not existing_headers:
                # No existing data, just remove duplicates from new data
                return self._remove_duplicate_rows(new_df, sheet_type)

            # Create existing dataframe
            existing_df = pd.DataFrame(existing_data, columns=existing_headers).fillna('')

            # Combine dataframes
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)

            # Remove duplicates
            deduplicated_df = self._remove_duplicate_rows(combined_df, sheet_type)

            # Sort the final result
            sorted_df = self._sort_dataframe_by_type(deduplicated_df, sheet_type)

            return sorted_df

        except Exception as e:
            print(f"Error merging with existing data: {e}")
            # If merge fails, just return the new data with duplicates removed
            return self._remove_duplicate_rows(new_df, sheet_type)


