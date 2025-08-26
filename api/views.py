from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from decimal import Decimal, ROUND_HALF_UP
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
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


# Create your views here.

@login_required(login_url='/registration/login_user/') #view for loading the user into the react app
def chd_app(request):
    csrf_token = get_token(request)
    return render(request, 'index.html', context={'csrf_token': csrf_token})

def home(request):
    return render(request, 'home.html')

@api_view(['GET'])
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

class AnalyticsViewSet(viewsets.ViewSet):
    column_pref_queryset = SheetColumnPreference.objects.all()
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    # DEFAULT GET FUNCTION FOR GETTING USER PREFERENCES
    def retrieve(self, request, pk=None):
        sheet_id = pk
        user = request.user

        try:
            preference = SheetColumnPreference.objects.get(user=user, sheet_id=sheet_id)
            serializer = SheetColumnPreferenceSerializer(preference)
            return Response(serializer.data)

        except SheetColumnPreference.DoesNotExist:
            # 4. If no preference is found, return a 404 error
            return Response(
                {'error': 'No preferences found for this sheet.'},
                status=status.HTTP_404_NOT_FOUND
            )

    # DEFAULT POST REQUEST FOR SETTING USER PREFERENCES
    def create(self, request, pk=None):
        sheet_id = pk
        user = request.user
        date_column = request.data.get('date_column')
        income_columns = request.data.get('income_columns')

        if not date_column or not income_columns:
            return Response(
                {'error': 'Both date_column and income_columns must be provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # This is the core logic. It finds a preference matching the user and sheet_id,
            # or creates a new one if it doesn't exist.
            preference, created = SheetColumnPreference.objects.update_or_create(
                user=user,
                sheet_id=sheet_id,
                defaults={
                    'date_column': date_column,
                    'income_columns': income_columns,
                }
            )

            status_text = "created" if created else "updated"
            return Response({'status': f'Preference {status_text} successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def income_summary(self, request, pk=None):
        try:
            sheet_data, sheet_headers = padded_google_sheets(pk, 'Sheet1')
            date_column = request.data.get('date_column')
            income_columns = request.data.get('income_columns')
            if not sheet_data:
                return Response({
                    'weekly': [],
                    'monthly': [],
                    'yearly': [],
                })

            df = pd.DataFrame(sheet_data, columns=sheet_headers)
            actual_columns = set(df.columns)

            # Check if the provided column names are valid
            if date_column not in actual_columns:
                return Response({'error': f"The date column '{date_column}' was not found in the sheet."}, status=400)

            for col in income_columns:
                if col not in actual_columns:
                    return Response({'error': f"The income column '{col}' was not found in the sheet."}, status=400)

            #data preparation
            try:
                df[date_column] = pd.to_datetime(df[date_column])
                for income_column in income_columns:
                    df[income_column] = pd.to_numeric(df[income_column])
            except Exception as e:
                return Response(
                    {'error': f"Failed to convert columns. Ensure data is in the correct format. Details: {e}"},
                    status=400)
            df.set_index(date_column, inplace=True)
            income_df = df[income_columns]

            #Resample and sum each income column for each time period
            weekly_subtotals = income_df.resample('W').sum()
            monthly_subtotals = income_df.resample('M').sum()
            yearly_subtotals = income_df.resample('Y').sum()

            #Sum the columns together to get a single total for each time period
            #axis=1 tells pandas to sum horizontally (across the columns)
            weekly_totals = weekly_subtotals.sum(axis=1).rename('Total Income')
            monthly_totals = monthly_subtotals.sum(axis=1).rename('Total Income')
            yearly_totals = yearly_subtotals.sum(axis=1).rename('Total Income')

            #formats total number to format for react charts
            def format_report(series, date_format):
                report_df = series.reset_index()
                report_df[date_column] = report_df[date_column].dt.strftime(date_format)
                return report_df.to_dict(orient='records')

            return Response({
                'weeklyReport': format_report(weekly_totals, '%Y-%m-%d'),
                'monthlyReport': format_report(monthly_totals, '%Y-%m'),
                'yearlyReport': format_report(yearly_totals, '%Y'),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['GET'])
    def get_sheet_headers(self, request, pk=None):
        try:
            sheet_data, sheet_headers = padded_google_sheets(pk, 'A1:Z2')
            return Response(
                {'columns': sheet_headers},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PayrollViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Only allow staff/superusers"""
        permission_classes = [IsAuthenticated]
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            self.permission_denied(self.request, message="Staff privileges required")
        return [permission() for permission in permission_classes]

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
        """Generate payroll for a specific user"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'You do not have permission to generate payroll'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            from decimal import Decimal
            from datetime import timedelta

            user = get_object_or_404(User, id=pk)
            user_profile = get_object_or_404(UserProfile, user=user)

            # Get site settings
            site_settings = SiteSettings.objects.first()
            if not site_settings:
                return Response(
                    {'error': 'Site settings not configured. Please configure tax rates and brackets first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parse request data
            start_date_str = request.data.get('startDate')
            end_date_str = request.data.get('endDate')
            clinic_id = request.data.get('clinic_id')

            if not all([start_date_str, end_date_str, clinic_id]):
                return Response(
                    {'error': 'Missing required fields: startDate, endDate, clinic_id'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            period_days = (end_date - start_date).days + 1

            # Get user's payment role
            if not hasattr(user_profile, 'payment_detail'):
                return Response(
                    {'error': 'User does not have a payment role configured'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            payment_detail = user_profile.payment_detail

            # Get the clinic and its timesheet sheet ID
            try:
                clinic = get_object_or_404(Clinic, id=clinic_id)
                clinic_spreadsheet = get_object_or_404(ClinicSpreadsheet, clinic=clinic)
                timesheet_sheet_id = clinic_spreadsheet.time_hour_sheet_id

                if not timesheet_sheet_id:
                    return Response(
                        {'error': f'No timesheet configured for clinic: {clinic.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                return Response(
                    {'error': f'Failed to get clinic timesheet configuration: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Handle different role types
            if isinstance(payment_detail, HourlyEmployee):
                # Get daily hours breakdown from timesheet
                daily_hours = self._get_user_daily_hours_from_sheet(
                    timesheet_sheet_id, user, start_date, end_date
                )

                total_hours = sum(daily_hours.values())

                if total_hours == 0:
                    # Check if user has revenue sharing or rent for this period
                    has_revenue_sharing, has_rent = self._has_revenue_sharing_or_rent_for_period(
                        user_profile, start_date, end_date
                    )

                    if not (has_revenue_sharing or has_rent):
                        return Response(
                            {
                                'error': f'No timesheet data found for {user.first_name} {user.last_name} in the specified period and no revenue sharing or rent to process'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Calculate overtime and vacation pay (works with zero hours)
                overtime_vacation_result = self.calculate_overtime_and_vacation_pay(
                    daily_hours=daily_hours,
                    hourly_rate=payment_detail.hourly_wage,
                    start_date=start_date,
                    end_date=end_date,
                    site_settings=site_settings,
                    user=user,
                    sheet_id=timesheet_sheet_id
                )

                regular_pay = overtime_vacation_result['regular_pay']
                overtime_pay = overtime_vacation_result['overtime_pay']
                vacation_pay = overtime_vacation_result['vacation_pay']
                total_earnings_before_tax = regular_pay + overtime_pay + vacation_pay

                # Debug logging
                print(f"=== PAYROLL DEBUG for {user.first_name} {user.last_name} ===")
                print(f"Total hours: {round(total_hours, 2)}")
                print(f"Regular hours: {overtime_vacation_result['regular_hours']}")
                print(f"Overtime hours: {overtime_vacation_result['overtime_hours']}")
                print(f"Regular pay: ${regular_pay}")
                print(f"Overtime pay: ${overtime_pay}")
                print(f"Vacation pay: ${vacation_pay}")
                print(f"Vacation rate from settings: {site_settings.vacation_pay_rate}%")
                print(f"Overtime rate from settings: {site_settings.overtime_pay_rate}x")
                print(f"Total before tax: ${total_earnings_before_tax}")
                print("=== END DEBUG ===")

                # Calculate deductions
                deductions_result = self.calculate_deductions(
                    total_taxable_income=total_earnings_before_tax,
                    period_days=period_days,
                    user_profile=user_profile,
                    site_settings=site_settings
                )

                # Prepare payroll data
                payroll_data = {
                    'user_id': user.id,
                    'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'pay_period_start': start_date_str,
                    'pay_period_end': end_date_str,
                    'role_type': 'Hourly Employee',
                    'total_hours': round(total_hours, 2),
                    'hourly_wage': float(payment_detail.hourly_wage),
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
                    'ytd_amounts': {
                        'earnings': deductions_result['projected_ytd_earnings'],
                        'deductions': deductions_result['projected_ytd_deductions'],
                    },
                    'breakdown': {
                        'overtime_hours': overtime_vacation_result['overtime_hours'],
                        'regular_hours': overtime_vacation_result['regular_hours'],
                        'cpp_ytd_after': deductions_result['cpp_ytd_after'],
                        'ei_ytd_after': deductions_result['ei_ytd_after'],
                    }
                }

            elif isinstance(payment_detail, HourlyContractor):
                total_hours = self._get_user_hours_from_sheet(timesheet_sheet_id, user, start_date, end_date)

                if total_hours == 0:
                    # Check if user has revenue sharing or rent for this period
                    has_revenue_sharing, has_rent = self._has_revenue_sharing_or_rent_for_period(
                        user_profile, start_date, end_date
                    )

                    if not (has_revenue_sharing or has_rent):
                        return Response(
                            {
                                'error': f'No timesheet data found for {user.first_name} {user.last_name} in the specified period and no revenue sharing or rent to process'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                total_pay = float(payment_detail.hourly_wage) * total_hours

                payroll_data = {
                    'user_id': user.id,
                    'user_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'pay_period_start': start_date_str,
                    'pay_period_end': end_date_str,
                    'role_type': 'Hourly Contractor',
                    'total_hours': total_hours,
                    'hourly_wage': float(payment_detail.hourly_wage),
                    'earnings': {
                        'salary': total_pay,
                        'contractor_pay': total_pay,
                        'regular_pay': total_pay,  # Add this for revenue sharing calculation
                        'overtime_pay': 0.0,
                    },
                    'deductions': {
                        'federal_tax': 0.0,
                        'provincial_tax': 0.0,
                        'cpp': 0.0,
                        'ei': 0.0,
                    },
                    'totals': {
                        'total_earnings': total_pay,
                        'total_deductions': 0.0,
                        'net_payment': total_pay,
                    },
                    'ytd_amounts': {
                        'earnings': float(user_profile.ytd_pay) + total_pay,
                        'deductions': float(user_profile.ytd_deduction),
                    },
                    'breakdown': {
                        'contractor_hours': total_hours,
                    }
                }

            elif isinstance(payment_detail, (CommissionEmployee, CommissionContractor)):
                # Commission-based payroll calculation
                compensation_sheet_id = clinic_spreadsheet.compensation_sales_sheet_id

                if not compensation_sheet_id:
                    return Response(
                        {'error': f'No compensation sales sheet configured for clinic: {clinic.name}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Get commission data from compensation sheet
                commission_data = self._get_commission_data_from_sheet(
                    compensation_sheet_id, user, start_date, end_date
                )

                if not commission_data:
                    # Check if user has revenue sharing or rent for this period
                    has_revenue_sharing, has_rent = self._has_revenue_sharing_or_rent_for_period(
                        user_profile, start_date, end_date
                    )

                    if not (has_revenue_sharing or has_rent):
                        return Response(
                            {
                                'error': f'No commission data found for {user.first_name} {user.last_name} in the specified period and no revenue sharing or rent to process'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Create zero-commission payroll structure
                    commission_data = {
                        'adjusted_total': 0.0,
                        'tax_gst': 0.0,
                        'invoice_data': []
                    }
                    pos_fees = 0.0
                else:
                    # Calculate POS fees using the matching algorithm
                    pos_fees = self._calculate_pos_fees_for_practitioner(
                        commission_data['invoice_data'], clinic_spreadsheet
                    )

                # Calculate commission payroll (handles zero commission case)
                payroll_data = self._calculate_commission_payroll(
                    user=user,
                    user_profile=user_profile,
                    commission_data=commission_data,
                    pos_fees=pos_fees,
                    site_settings=site_settings,
                    start_date=start_date,
                    end_date=end_date,
                    period_days=period_days
                )

                # Debug logging
                print(f"=== COMMISSION PAYROLL DEBUG for {user.first_name} {user.last_name} ===")
                print(f"Role type: {payroll_data['role_type']}")
                print(f"Commission rate: {payroll_data['commission_rate'] * 100:.1f}%")
                print(f"Gross income: ${payroll_data['earnings']['gross_income']}")
                print(f"Commission deduction (company keeps): ${payroll_data['deductions']['commission_deduction']}")
                print(f"Commission income (practitioner gets): ${payroll_data['earnings']['commission_earned']}")
                print(f"POS fees: ${pos_fees}")
                if 'vacation_pay' in payroll_data['earnings']:
                    print(f"Vacation pay: ${payroll_data['earnings']['vacation_pay']}")
                print(f"Net payment: ${payroll_data['totals']['net_payment']}")
                print("=== END DEBUG ===")

            elif isinstance(payment_detail, Student):
                # Students are not eligible for payroll
                return Response(
                    {'error': 'Students are not eligible for payroll generation'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            else:
                return Response(
                    {'error': 'Payroll calculation not implemented for this role type yet'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # ============ REVENUE SHARING AND RENT CALCULATIONS ============

            # Get base gross income for revenue sharing calculations
            if isinstance(payment_detail, (CommissionEmployee, CommissionContractor)):
                base_gross_income = Decimal(str(payroll_data['earnings']['gross_income']))
            elif isinstance(payment_detail, (HourlyEmployee, HourlyContractor)):
                # For hourly, use regular + overtime pay (before vacation pay)
                base_gross_income = (Decimal(str(payroll_data['earnings']['regular_pay'])) +
                                     Decimal(str(payroll_data['earnings'].get('overtime_pay', 0))))
            else:
                # Skip revenue sharing for other roles
                return Response(payroll_data, status=status.HTTP_200_OK)

            # 1. Calculate Rent Deduction
            rent_deduction, rent_description = self._calculate_rent_deduction(user_profile, start_date, end_date)

            # 2. Calculate Revenue Sharing Deductions (money going OUT)
            revenue_share_deduction, revenue_deduction_details = self._calculate_revenue_sharing_deductions(
                user, user_profile, base_gross_income
            )

            # 3. Calculate Revenue Sharing Income from specific users (money coming IN)
            revenue_share_income_users, revenue_income_user_details = self._calculate_revenue_sharing_income_from_user(
                user_profile, start_date, end_date, clinic_spreadsheet, site_settings
            )

            # 4. Calculate Revenue Sharing Income from students (money coming IN)
            revenue_share_income_students, revenue_income_student_details = self._calculate_revenue_sharing_income_from_students(
                user_profile, start_date, end_date, clinic_spreadsheet
            )

            total_revenue_share_income = revenue_share_income_users + revenue_share_income_students

            # Apply adjustments to payroll data based on role type
            if isinstance(payment_detail, CommissionContractor):
                # For contractors, adjust net payment directly (no tax implications)
                original_net_payment = Decimal(str(payroll_data['totals']['net_payment']))
                new_net_payment = original_net_payment - rent_deduction - revenue_share_deduction + total_revenue_share_income

                payroll_data['totals']['net_payment'] = float(new_net_payment)
                payroll_data['totals']['total_deductions'] = float(
                    Decimal(str(payroll_data['totals']['total_deductions'])) + rent_deduction + revenue_share_deduction
                )
                if total_revenue_share_income > 0:
                    payroll_data['totals']['total_earnings'] = float(
                        Decimal(str(payroll_data['totals']['total_earnings'])) + total_revenue_share_income
                    )
                    payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)

                # Add to deductions breakdown
                payroll_data['deductions']['rent'] = float(rent_deduction)
                payroll_data['deductions']['rent_description'] = rent_description
                payroll_data['deductions']['revenue_share_deduction'] = float(revenue_share_deduction)

            elif isinstance(payment_detail, CommissionEmployee):
                # For commission employees, treat as additional income/deductions
                original_total_earnings = Decimal(str(payroll_data['totals']['total_earnings']))
                original_total_deductions = Decimal(str(payroll_data['totals']['total_deductions']))

                # If there's revenue sharing income, recalculate taxes on the additional income
                if total_revenue_share_income > 0:
                    # Recalculate taxes on original income + revenue sharing income
                    new_taxable = original_total_earnings + total_revenue_share_income

                    # Calculate new deductions on the higher income
                    new_deductions_result = self.calculate_deductions(
                        total_taxable_income=float(new_taxable),
                        period_days=period_days,
                        user_profile=user_profile,
                        site_settings=site_settings
                    )

                    # Update payroll with new tax calculations
                    payroll_data['deductions']['federal_tax'] = new_deductions_result['deductions']['federal_tax']
                    payroll_data['deductions']['provincial_tax'] = new_deductions_result['deductions']['provincial_tax']
                    payroll_data['deductions']['cpp'] = new_deductions_result['deductions']['cpp']
                    payroll_data['deductions']['ei'] = new_deductions_result['deductions']['ei']

                    total_tax_deductions = Decimal(str(
                        new_deductions_result['deductions']['federal_tax'] +
                        new_deductions_result['deductions']['provincial_tax'] +
                        new_deductions_result['deductions']['cpp'] +
                        new_deductions_result['deductions']['ei']
                    ))

                    payroll_data['totals']['total_earnings'] = float(new_taxable)
                    payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)
                    payroll_data['breakdown']['cpp_ytd_after'] = new_deductions_result['cpp_ytd_after']
                    payroll_data['breakdown']['ei_ytd_after'] = new_deductions_result['ei_ytd_after']

                else:
                    total_tax_deductions = Decimal(str(
                        payroll_data['deductions']['federal_tax'] +
                        payroll_data['deductions']['provincial_tax'] +
                        payroll_data['deductions']['cpp'] +
                        payroll_data['deductions']['ei']
                    ))

                # Calculate final amounts
                new_total_deductions = original_total_deductions + rent_deduction + revenue_share_deduction
                new_net_payment = (Decimal(str(payroll_data['totals']['total_earnings'])) -
                                   new_total_deductions)

                payroll_data['totals']['net_payment'] = float(new_net_payment)
                payroll_data['totals']['total_deductions'] = float(new_total_deductions)
                payroll_data['deductions']['rent'] = float(rent_deduction)
                payroll_data['deductions']['rent_description'] = rent_description
                payroll_data['deductions']['revenue_share_deduction'] = float(revenue_share_deduction)

            elif isinstance(payment_detail, HourlyContractor):
                # Similar to commission contractor
                original_net_payment = Decimal(str(payroll_data['totals']['net_payment']))
                new_net_payment = original_net_payment - rent_deduction - revenue_share_deduction + total_revenue_share_income

                payroll_data['totals']['net_payment'] = float(new_net_payment)
                payroll_data['totals']['total_deductions'] = float(rent_deduction + revenue_share_deduction)
                if total_revenue_share_income > 0:
                    payroll_data['totals']['total_earnings'] = float(
                        Decimal(str(payroll_data['totals']['total_earnings'])) + total_revenue_share_income
                    )
                    payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)

                payroll_data['deductions']['rent'] = float(rent_deduction)
                payroll_data['deductions']['rent_description'] = rent_description
                payroll_data['deductions']['revenue_share_deduction'] = float(revenue_share_deduction)

            elif isinstance(payment_detail, HourlyEmployee):
                # For hourly employees, treat as additional income/deductions
                original_total_earnings = Decimal(str(payroll_data['totals']['total_earnings']))
                original_total_deductions = Decimal(str(payroll_data['totals']['total_deductions']))

                # If there's revenue sharing income, recalculate taxes on the additional income
                if total_revenue_share_income > 0:
                    # Recalculate taxes on original income + revenue sharing income
                    new_taxable = original_total_earnings + total_revenue_share_income

                    # Calculate new deductions on the higher income
                    new_deductions_result = self.calculate_deductions(
                        total_taxable_income=float(new_taxable),
                        period_days=period_days,
                        user_profile=user_profile,
                        site_settings=site_settings
                    )

                    # Update payroll with new tax calculations
                    payroll_data['deductions']['federal_tax'] = new_deductions_result['deductions']['federal_tax']
                    payroll_data['deductions']['provincial_tax'] = new_deductions_result['deductions']['provincial_tax']
                    payroll_data['deductions']['cpp'] = new_deductions_result['deductions']['cpp']
                    payroll_data['deductions']['ei'] = new_deductions_result['deductions']['ei']

                    payroll_data['totals']['total_earnings'] = float(new_taxable)
                    payroll_data['earnings']['revenue_share_income'] = float(total_revenue_share_income)
                    payroll_data['breakdown']['cpp_ytd_after'] = new_deductions_result['cpp_ytd_after']
                    payroll_data['breakdown']['ei_ytd_after'] = new_deductions_result['ei_ytd_after']

                # Calculate final amounts
                new_total_deductions = original_total_deductions + rent_deduction + revenue_share_deduction
                new_net_payment = (Decimal(str(payroll_data['totals']['total_earnings'])) -
                                   new_total_deductions)

                payroll_data['totals']['net_payment'] = float(new_net_payment)
                payroll_data['totals']['total_deductions'] = float(new_total_deductions)
                payroll_data['deductions']['rent'] = float(rent_deduction)
                payroll_data['deductions']['rent_description'] = rent_description
                payroll_data['deductions']['revenue_share_deduction'] = float(revenue_share_deduction)

            # Add breakdown details for debugging/transparency
            payroll_data['revenue_sharing_details'] = {
                'rent_deduction': float(rent_deduction),
                'revenue_share_deduction': float(revenue_share_deduction),
                'revenue_share_income_users': float(revenue_share_income_users),
                'revenue_share_income_students': float(revenue_share_income_students),
                'revenue_deduction_details': revenue_deduction_details,
                'revenue_income_user_details': revenue_income_user_details,
                'revenue_income_student_details': revenue_income_student_details,
            }

            # Debug logging
            print(f"=== REVENUE SHARING AND RENT DEBUG ===")
            print(f"Base gross income: ${base_gross_income}")
            print(f"Rent deduction: ${rent_deduction}")
            print(f"Revenue share deduction (OUT): ${revenue_share_deduction}")
            print(f"Revenue share income (IN): ${total_revenue_share_income}")
            print(f"Final net payment: ${payroll_data['totals']['net_payment']}")
            print("=== END DEBUG ===")

            # ============ REVENUE SHARING CONTRIBUTION DETAILS ============
            revenue_sharing_contributions = {
                'income_contributors': [],  # People who gave money to this user
                'deduction_recipients': []  # People this user gave money to
            }

            # Add income contributors (people who gave money to this user)
            if revenue_income_user_details:
                for detail in revenue_income_user_details:
                    revenue_sharing_contributions['income_contributors'].append({
                        'user_name': detail['from_user'],
                        'amount': detail['amount'],
                        'type': 'specific_user'
                    })

            if revenue_income_student_details:
                total_student_contribution = float(total_revenue_share_income - revenue_share_income_users)
                if total_student_contribution > 0:
                    revenue_sharing_contributions['income_contributors'].append({
                        'user_name': 'All Students Combined',
                        'amount': total_student_contribution,
                        'type': 'student_share',
                        'student_breakdown': revenue_income_student_details
                    })

            # Add deduction recipients (people this user gave money to)
            if revenue_deduction_details:
                for detail in revenue_deduction_details:
                    revenue_sharing_contributions['deduction_recipients'].append({
                        'user_name': detail['payee'],
                        'amount': detail['amount'],
                        'type': 'specific_user'
                    })

            # Add to payroll data
            payroll_data['revenue_sharing_contributions'] = revenue_sharing_contributions

            return Response(payroll_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to generate payroll: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
        """
        Fetch user hours from Google Sheet for the specified period (total hours)
        Used for contractors who don't need daily breakdown
        """
        try:
            sheet_data = read_google_sheets(sheet_id, "A:I")

            if not sheet_data or len(sheet_data) < 2:
                print("No data found in timesheet")
                return 0.0

            headers = sheet_data[0]
            data_rows = sheet_data[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            user_rows = df[df['Staff member'].str.strip() == user_full_name]

            if user_rows.empty:
                print(f"No timesheet entries found for user: {user_full_name}")
                return 0.0

            user_rows = user_rows.copy()
            user_rows['Date'] = pd.to_datetime(user_rows['Date'], errors='coerce')
            user_rows = user_rows.dropna(subset=['Date'])

            start_date_naive = start_date
            end_date_naive = end_date

            period_rows = user_rows[
                (user_rows['Date'].dt.date >= start_date_naive) &
                (user_rows['Date'].dt.date <= end_date_naive)
                ]

            if period_rows.empty:
                print(
                    f"No timesheet entries found for user {user_full_name} in period {start_date_naive} to {end_date_naive}")
                return 0.0

            total_minutes = 0.0
            for _, row in period_rows.iterrows():
                try:
                    minutes_value = row['Payable time (mins)']
                    if pd.isna(minutes_value) or minutes_value == '':
                        continue
                    total_minutes += float(minutes_value)
                except (ValueError, TypeError) as e:
                    print(f"Error converting minutes value '{minutes_value}' to float: {e}")
                    continue

            total_hours = total_minutes / 60.0
            print(
                f"Found {len(period_rows)} entries for {user_full_name}: {total_minutes} minutes = {total_hours:.2f} hours")

            return round(total_hours, 2)

        except Exception as e:
            print(f"Error fetching sheet data: {str(e)}")
            return 0.0

    def _get_user_daily_hours_from_sheet(self, sheet_id, user, start_date, end_date):
        """
        Fetch user hours from Google Sheet broken down by day
        Returns: dict with date as key and hours as value
        """
        try:
            sheet_data = read_google_sheets(sheet_id, "A:I")

            if not sheet_data or len(sheet_data) < 2:
                print("No data found in timesheet")
                return {}

            headers = sheet_data[0]
            data_rows = sheet_data[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            user_full_name = f"{user.first_name} {user.last_name}".strip()
            user_rows = df[df['Staff member'].str.strip() == user_full_name]

            if user_rows.empty:
                print(f"No timesheet entries found for user: {user_full_name}")
                return {}

            user_rows = user_rows.copy()
            user_rows['Date'] = pd.to_datetime(user_rows['Date'], errors='coerce')
            user_rows = user_rows.dropna(subset=['Date'])

            # Filter for the date range
            period_rows = user_rows[
                (user_rows['Date'].dt.date >= start_date) &
                (user_rows['Date'].dt.date <= end_date)
                ]

            if period_rows.empty:
                print(f"No timesheet entries found for user {user_full_name} in period {start_date} to {end_date}")
                return {}

            # Build daily hours dictionary
            daily_hours = {}
            for _, row in period_rows.iterrows():
                try:
                    date = row['Date'].date()
                    minutes_value = row['Payable time (mins)']

                    if pd.isna(minutes_value) or minutes_value == '':
                        continue

                    hours = float(minutes_value) / 60.0
                    daily_hours[date] = daily_hours.get(date, 0) + hours

                except (ValueError, TypeError) as e:
                    print(f"Error converting minutes value '{minutes_value}' to float: {e}")
                    continue

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
        """
        Extract commission data for a specific practitioner from compensation sheet
        Returns: dict with aggregated totals or None if no data found
        """
        try:
            sheet_data = read_google_sheets(compensation_sheet_id, "A:Z")

            if not sheet_data or len(sheet_data) < 2:
                print("No data found in compensation sheet")
                return None

            headers = sheet_data[0]
            data_rows = sheet_data[1:]
            df = pd.DataFrame(data_rows, columns=headers)

            # Normalize user name for matching
            user_full_name = f"{user.first_name} {user.last_name}".strip()

            # Filter for practitioner's rows
            practitioner_rows = []
            for _, row in df.iterrows():
                practitioner_name = self._normalize_practitioner_name(row.get('Practitioner', ''))
                if practitioner_name.lower() == user_full_name.lower():
                    practitioner_rows.append(row)

            if not practitioner_rows:
                print(f"No compensation data found for practitioner: {user_full_name}")
                return None

                # Convert to DataFrame and debug dates
            practitioner_df = pd.DataFrame(practitioner_rows)

            print(f"Found {len(practitioner_df)} total rows for {user_full_name}")

            # Parse dates and show what we found
            practitioner_df['Invoice Date'] = pd.to_datetime(practitioner_df['Invoice Date'], errors='coerce')

            print(f"Date range requested: {start_date} to {end_date}")
            print("Invoice dates found:")
            for date in practitioner_df['Invoice Date'].dropna():
                print(f"  - {date.date()}")

            # Filter by date range
            mask = (
                    (practitioner_df['Invoice Date'].dt.date >= start_date) &
                    (practitioner_df['Invoice Date'].dt.date <= end_date)
            )
            period_rows = practitioner_df[mask]

            print(f"Rows after date filtering: {len(period_rows)}")

            if period_rows.empty:
                print(f"No compensation data found for {user_full_name} in period {start_date} to {end_date}")
                return None

            # Aggregate the required columns
            try:
                adjusted_total = pd.to_numeric(period_rows['Adjusted Total'], errors='coerce').fillna(0).sum()
                tax_gst = pd.to_numeric(period_rows['Tax'], errors='coerce').fillna(0).sum()

                # Collect invoice and patient data for POS fee calculation
                invoice_data = []
                for _, row in period_rows.iterrows():
                    invoice_data.append({
                        'invoice_date': row['Invoice Date'].date() if pd.notna(row['Invoice Date']) else None,
                        'invoice_number': self._extract_base_invoice_number(row.get('Invoice #', '')),
                        'patient_name': str(row.get('Patient', '')).strip(),
                        'adjusted_total': pd.to_numeric(row.get('Adjusted Total', 0), errors='coerce') or 0
                    })

                return {
                    'adjusted_total': float(adjusted_total),
                    'tax_gst': float(tax_gst),
                    'invoice_data': invoice_data,
                    'period_start': start_date,
                    'period_end': end_date
                }

            except Exception as e:
                print(f"Error aggregating commission data: {str(e)}")
                return None

        except Exception as e:
            print(f"Error fetching commission data: {str(e)}")
            return None

    def _calculate_pos_fees_for_practitioner(self, invoice_data, clinic_spreadsheet):
        """
        Calculate total POS fees for a practitioner using the matching algorithm
        Returns: float (total POS fees)
        """
        try:
            if not invoice_data:
                return 0.0

            transaction_sheet_id = clinic_spreadsheet.transaction_report_sheet_id
            payment_sheet_id = clinic_spreadsheet.payment_transaction_sheet_id

            if not transaction_sheet_id or not payment_sheet_id:
                print("Missing required sheet IDs for POS fee calculation")
                return 0.0

            # Get transaction data
            transaction_data = read_google_sheets(transaction_sheet_id, "A:Z")
            if not transaction_data or len(transaction_data) < 2:
                return 0.0

            transaction_headers = transaction_data[0]
            transaction_df = pd.DataFrame(transaction_data[1:], columns=transaction_headers)

            # Get Jane payments data
            payment_data = read_google_sheets(payment_sheet_id, "A:Z")
            if not payment_data or len(payment_data) < 2:
                return 0.0

            payment_headers = payment_data[0]
            payment_df = pd.DataFrame(payment_data[1:], columns=payment_headers)

            total_pos_fees = 0.0

            for invoice_info in invoice_data:
                invoice_date = invoice_info['invoice_date']
                base_invoice_number = invoice_info['invoice_number']
                patient_name = invoice_info['patient_name']

                if not all([invoice_date, base_invoice_number, patient_name]):
                    continue

                # Step 1: Find matching transactions
                # Convert payment date to datetime for comparison
                transaction_df['Payment Date'] = pd.to_datetime(transaction_df['Payment Date'], errors='coerce')

                # Filter transactions by date, patient name, and Jane Payments method
                matching_transactions = transaction_df[
                    (transaction_df['Payment Date'].dt.date == invoice_date) &
                    (transaction_df['Payer'].str.contains(patient_name, case=False, na=False)) &
                    (transaction_df['Payment Method'].str.contains('Jane Payments', case=False, na=False))
                    ]

                # Also check if Applied To field contains our base invoice number
                def check_invoice_match(applied_to_str, base_number):
                    if pd.isna(applied_to_str):
                        return False
                    applied_invoices = str(applied_to_str).split(',')
                    for applied_invoice in applied_invoices:
                        applied_base = self._extract_base_invoice_number(applied_invoice.strip())
                        if applied_base == base_number:
                            return True
                    return False

                matching_transactions = matching_transactions[
                    matching_transactions['Applied To'].apply(lambda x: check_invoice_match(x, base_invoice_number))
                ]

                if matching_transactions.empty:
                    continue

                # Step 2: Match with Jane Payments to get fees
                for _, transaction in matching_transactions.iterrows():
                    transaction_amount = pd.to_numeric(transaction.get('Amount', 0), errors='coerce') or 0
                    transaction_date = transaction['Payment Date'].date()

                    # Find matching Jane Payments entry
                    payment_df['Date'] = pd.to_datetime(payment_df['Date'], errors='coerce')

                    matching_payments = payment_df[
                        (payment_df['Date'].dt.date == transaction_date) &
                        (payment_df['Customer'].str.contains(patient_name, case=False, na=False)) &
                        (pd.to_numeric(payment_df['Customer Charge'], errors='coerce').fillna(0).round(2) ==
                         round(float(transaction_amount), 2))
                        ]

                    # Sum up the Jane Payments fees for matching entries
                    for _, payment in matching_payments.iterrows():
                        jane_fee = pd.to_numeric(payment.get('Jane Payments Fee', 0), errors='coerce') or 0
                        total_pos_fees += float(jane_fee)
                        print(f"Found POS fee: ${jane_fee} for {patient_name} on {transaction_date}")

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

    def _create_payroll_record_for_user(self, target_user, period_start, period_end, clinic_spreadsheet, site_settings,
                                        payroll_type='AUTO'):
        """
        Create a PayrollRecords entry for any user based on their role type
        payroll_type: 'AUTO' for auto-generated, 'STU' for student revenue sharing
        """
        try:
            from django.utils import timezone
            import uuid

            # Check if record already exists
            existing_record = PayrollRecords.objects.filter(
                user=target_user,
                period_start=period_start,
                period_end=period_end
            ).first()

            if existing_record:
                print(
                    f"PayrollRecords already exists for {target_user.username} in period {period_start} to {period_end}")
                return existing_record

            target_user_profile = target_user.userprofile
            payment_detail = target_user_profile.payment_detail

            if not payment_detail:
                print(f"User {target_user.username} has no payment role configured")
                return None

            # Calculate period days
            period_days = (period_end - period_start).days + 1

            # Generate payroll based on their role type
            if isinstance(payment_detail, (CommissionEmployee, CommissionContractor)):
                # Commission calculation
                compensation_sheet_id = clinic_spreadsheet.compensation_sales_sheet_id
                if not compensation_sheet_id:
                    return None

                commission_data = self._get_commission_data_from_sheet(
                    compensation_sheet_id, target_user, period_start, period_end
                )

                if not commission_data:
                    return None

                pos_fees = self._calculate_pos_fees_for_practitioner(
                    commission_data['invoice_data'], clinic_spreadsheet
                )

                target_payroll_data = self._calculate_commission_payroll(
                    user=target_user,
                    user_profile=target_user_profile,
                    commission_data=commission_data,
                    pos_fees=pos_fees,
                    site_settings=site_settings,
                    start_date=period_start,
                    end_date=period_end,
                    period_days=period_days
                )

            elif isinstance(payment_detail, (HourlyEmployee, HourlyContractor)):
                # Hourly calculation
                timesheet_sheet_id = clinic_spreadsheet.time_hour_sheet_id
                if not timesheet_sheet_id:
                    return None

                if isinstance(payment_detail, HourlyEmployee):
                    daily_hours = self._get_user_daily_hours_from_sheet(
                        timesheet_sheet_id, target_user, period_start, period_end
                    )

                    overtime_vacation_result = self.calculate_overtime_and_vacation_pay(
                        daily_hours=daily_hours,
                        hourly_rate=payment_detail.hourly_wage,
                        start_date=period_start,
                        end_date=period_end,
                        site_settings=site_settings,
                        user=target_user,
                        sheet_id=timesheet_sheet_id
                    )

                    total_earnings_before_tax = (overtime_vacation_result['regular_pay'] +
                                                 overtime_vacation_result['overtime_pay'] +
                                                 overtime_vacation_result['vacation_pay'])

                    deductions_result = self.calculate_deductions(
                        total_taxable_income=float(total_earnings_before_tax),
                        period_days=period_days,
                        user_profile=target_user_profile,
                        site_settings=site_settings
                    )

                    target_payroll_data = {
                        'role_type': 'Hourly Employee',
                        'totals': {
                            'total_earnings': float(total_earnings_before_tax),
                            'total_deductions': deductions_result['total_deductions'],
                            'net_payment': float(total_earnings_before_tax) - deductions_result['total_deductions'],
                        },
                        'earnings': {
                            'regular_pay': float(overtime_vacation_result['regular_pay']),
                            'overtime_pay': float(overtime_vacation_result['overtime_pay']),
                            'vacation_pay': float(overtime_vacation_result['vacation_pay']),
                        },
                        'deductions': deductions_result['deductions']
                    }
                else:
                    # Contractor calculation
                    total_hours = self._get_user_hours_from_sheet(timesheet_sheet_id, target_user, period_start,
                                                                  period_end)
                    total_pay = float(payment_detail.hourly_wage) * total_hours

                    target_payroll_data = {
                        'role_type': 'Hourly Contractor',
                        'totals': {
                            'total_earnings': total_pay,
                            'total_deductions': 0.0,
                            'net_payment': total_pay,
                        },
                        'earnings': {'salary': total_pay},
                        'deductions': {}
                    }

            elif isinstance(payment_detail, Student):
                # Special handling for students - treat as 100% commission contractors
                compensation_sheet_id = clinic_spreadsheet.compensation_sales_sheet_id
                if not compensation_sheet_id:
                    return None

                commission_data = self._get_commission_data_from_sheet(
                    compensation_sheet_id, target_user, period_start, period_end
                )

                if not commission_data:
                    return None

                pos_fees = self._calculate_pos_fees_for_practitioner(
                    commission_data['invoice_data'], clinic_spreadsheet
                )

                # Students are treated as 100% commission contractors
                adjusted_total = Decimal(str(commission_data['adjusted_total']))
                tax_gst = Decimal(str(commission_data['tax_gst']))
                gross_income = adjusted_total + tax_gst
                pos_fees_decimal = Decimal(str(pos_fees))
                student_net = gross_income - pos_fees_decimal

                target_payroll_data = {
                    'role_type': 'Student',
                    'totals': {
                        'total_earnings': float(gross_income),
                        'total_deductions': float(pos_fees_decimal),
                        'net_payment': float(student_net),
                    },
                    'earnings': {
                        'adjusted_total': float(adjusted_total),
                        'tax_gst': float(tax_gst),
                        'gross_income': float(gross_income),
                    },
                    'deductions': {
                        'pos_fees': float(pos_fees_decimal),
                    }
                }
            else:
                print(f"Unsupported role type for payroll record creation: {type(payment_detail)}")
                return None

            # Create the PayrollRecords entry
            prefix = payroll_type if payroll_type != 'AUTO' else 'AUTO'
            payroll_number = f"{prefix}-{timezone.now().strftime('%Y%m%d')}-{target_user.id:04d}-{uuid.uuid4().hex[:6].upper()}"

            earnings = target_payroll_data.get('earnings', {})
            deductions = target_payroll_data.get('deductions', {})
            totals = target_payroll_data.get('totals', {})
            role_type = target_payroll_data.get('role_type', '')

            # Determine subtotal income based on role type
            if 'Commission' in role_type or role_type == 'Student':
                subtotal_income = float(earnings.get('adjusted_total', 0) or earnings.get('gross_income', 0))
            else:
                subtotal_income = float(earnings.get('regular_pay', 0) or earnings.get('salary', 0))

            record = PayrollRecords.objects.create(
                user=target_user,
                email=target_user.email,
                period_start=period_start,
                period_end=period_end,
                clinic=None,
                role_type=role_type,

                # Income fields
                subtotal_income=subtotal_income,
                hours_worked=float(target_payroll_data.get('total_hours', 0)),
                vacation_pay=float(earnings.get('vacation_pay', 0)),
                overtime_pay=float(earnings.get('overtime_pay', 0)),
                revenue_share_income=0.000,
                gst=float(earnings.get('tax_gst', 0)),
                total_income=float(totals.get('total_earnings', 0)),

                # Deduction fields
                commission_deduction=float(deductions.get('commission_deduction', 0)),
                pos_fees=float(deductions.get('pos_fees', 0) or earnings.get('pos_fees', 0)),
                provincial_income_tax=float(deductions.get('provincial_tax', 0)),
                federal_income_tax=float(deductions.get('federal_tax', 0)),
                cpp_contrib=float(deductions.get('cpp', 0)),
                ei_contrib=float(deductions.get('ei', 0)),
                rent=0.000,
                revenue_share_deduction=0.000,
                revenue_share_deduction_payee=0.000,
                total_deductions=float(totals.get('total_deductions', 0)),

                notes=f'{payroll_type}-generated payroll record',
                payroll_number=payroll_number,
            )

            print(f"Created PayrollRecords entry for {target_user.username}: {payroll_number}")
            return record

        except Exception as e:
            print(f"Error creating payroll record for {target_user.username}: {str(e)}")
            return None

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

            # Update YTD amounts
            try:
                user_profile = user.userprofile
                current_earnings = float(payroll_data.get('totals', {}).get('total_earnings', 0))
                current_deductions = float(payroll_data.get('totals', {}).get('total_deductions', 0))

                # Update YTD totals
                user_profile.ytd_pay += current_earnings
                user_profile.ytd_deduction += current_deductions

                # Update CPP and EI contributions if available in breakdown
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

            # Create PayrollRecords entry after successful email sending
            try:
                from django.utils import timezone
                import uuid

                # Generate unique payroll number
                payroll_number = f"PAY-{timezone.now().strftime('%Y%m%d')}-{user.id:04d}-{uuid.uuid4().hex[:6].upper()}"

                # Parse dates
                period_start = datetime.strptime(payroll_data.get('pay_period_start'), '%Y-%m-%d').date()
                period_end = datetime.strptime(payroll_data.get('pay_period_end'), '%Y-%m-%d').date()

                # Get data from payroll_data
                earnings = payroll_data.get('earnings', {})
                deductions = payroll_data.get('deductions', {})
                totals = payroll_data.get('totals', {})
                role_type = payroll_data.get('role_type', '')

                # Determine subtotal_income based on role type
                is_commission = 'Commission' in role_type
                if is_commission:
                    subtotal_income = float(earnings.get('gross_income', 0)) - float(earnings.get('tax_gst', 0))
                else:
                    subtotal_income = float(earnings.get('regular_pay', 0) or earnings.get('salary', 0))

                payroll_record = PayrollRecords.objects.create(
                    user=user,
                    email=user.email,
                    period_start=period_start,
                    period_end=period_end,
                    clinic=None,  # Could be added if you track clinic in payroll generation
                    role_type=role_type,

                    # Income fields
                    subtotal_income=subtotal_income,
                    hours_worked=float(payroll_data.get('total_hours', 0)),
                    vacation_pay=float(earnings.get('vacation_pay', 0)),
                    overtime_pay=float(earnings.get('overtime_pay', 0)),
                    revenue_share_income=float(earnings.get('revenue_share_income', 0)),
                    gst=float(earnings.get('tax_gst', 0)),
                    total_income=float(totals.get('total_earnings', 0)),

                    # Deduction fields
                    commission_deduction=float(deductions.get('commission_deduction', 0)),
                    pos_fees=float(deductions.get('pos_fees', 0) or earnings.get('pos_fees', 0)),
                    provincial_income_tax=float(deductions.get('provincial_tax', 0)),
                    federal_income_tax=float(deductions.get('federal_tax', 0)),
                    cpp_contrib=float(deductions.get('cpp', 0)),
                    ei_contrib=float(deductions.get('ei', 0)),
                    rent=float(deductions.get('rent', 0)),
                    revenue_share_deduction=float(deductions.get('revenue_share_deduction', 0)),
                    revenue_share_deduction_payee=None,  # Will be set below if applicable
                    total_deductions=float(totals.get('total_deductions', 0)),

                    # Additional fields
                    notes=payroll_data.get('notes', ''),
                    payroll_number=payroll_number,
                )

                print(f"PayrollRecords entry created: {payroll_number}")

                # ============ CREATE REVENUE SHARE CONTRIBUTION RECORDS ============
                revenue_contributions = payroll_data.get('revenue_sharing_contributions', {})

                # Create contribution records for revenue sharing income (money coming IN)
                if revenue_contributions.get('income_contributors'):
                    for contributor in revenue_contributions['income_contributors']:
                        # Find the contributing user (skip if it's "All Students Combined")
                        if contributor['user_name'] != 'All Students Combined':
                            try:
                                contributing_user = User.objects.get(username=contributor['user_name'])
                                RevenueShareContribution.objects.create(
                                    payroll_record=payroll_record,
                                    contributing_user=contributing_user,
                                    amount_contributed=float(contributor['amount']),
                                    contribution_type=contributor['type']
                                )
                                print(
                                    f"Created contribution record: {contributing_user.username} -> {user.username} (${contributor['amount']})")
                            except User.DoesNotExist:
                                print(f"Warning: Contributing user '{contributor['user_name']}' not found")
                        else:
                            # Handle student contributions - create records for each student
                            if contributor.get('student_breakdown'):
                                total_student_net = sum(float(s['net']) for s in contributor['student_breakdown'])
                                for student_detail in contributor['student_breakdown']:
                                    try:
                                        student_user = User.objects.get(username=student_detail['student'])
                                        # Calculate this student's share of the total student contribution
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
                                        print(
                                            f"Created student contribution record: {student_user.username} -> {user.username} (${student_share:.2f})")
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
                        print(f"Set revenue share deduction payee: {recipient_user.username}")
                    except User.DoesNotExist:
                        print(f"Warning: Deduction recipient '{recipient_name}' not found")

            except Exception as record_error:
                print(f"Error creating PayrollRecords entry: {str(record_error)}")
                # Log the error but don't fail the entire payroll process
                # The email was sent and YTD amounts were updated successfully

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


