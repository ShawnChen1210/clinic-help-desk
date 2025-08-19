from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages

#imports for email stuff
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .forms import *
from .models import *
from .tokens import *
import re
# Create your views here.

def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
                # Redirect to a success page.
            else:
                form = LoginForm()
        else:
            form = LoginForm()
    return render(request, 'login.html', {"form": LoginForm})

def activate_email(request, user, to_email):
    mail_subject = 'Activate your account'
    message = render_to_string('template_activate_account.html', {
        'user': user.username,
        'domain': get_current_site(request).domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f'Hey {user}, please check your email at {to_email} for an activation link to finish the registration process!')
    else:
        messages.error(request, 'An error occurred. Please check your email and try again.')

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True #now the user is allowed to log in now that its is_active is true
        user.save()
        messages.success(request, 'Thank you for your email confirmation. Now you can login your account.')
        return redirect('login_user')
    else:
        messages.error(request, 'Activation link is invalid!')

    return redirect('home')

def register_user(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.is_active = False #the user cannot log in if is_active is false
            user.save()
            UserProfile.objects.create(user=user)
            activate_email(request, user, form.cleaned_data['email'])

            login(request, user)
            return redirect('home')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {"form": RegistrationForm})

def members(request):
    if request.user.is_staff: #extra security to make sure only staff can access
        if request.method == 'POST':
            action = request.POST.get('action')
            user_id = request.POST.get('user_id')

            if action == 'verify_user':
                user = User.objects.get(pk=user_id)
                if user.userprofile.is_verified:
                    user.userprofile.is_verified = False
                    user.userprofile.save()
                else:
                    user.userprofile.is_verified = True
                    user.userprofile.save()

            if action == 'make_staff':
                user = User.objects.get(pk=user_id)
                if user.is_staff:
                    user.is_staff = False
                    user.save()
                else:
                    user.is_staff = True
                    user.save()

        users = User.objects.select_related('userprofile').exclude(pk=request.user.pk).all()
        return render(request, 'members.html', {"users": users})
    else:
        return redirect('home')


@login_required
def profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Helper function to get role details (moved outside to reuse)
    def get_role_details(role):
        """Extract role-specific details into a standardized format"""
        if not role:
            return {}

        details = {
            'type': role.__class__.__name__,
            'payroll_dates': getattr(role, 'payroll_dates', []),
        }

        # Map role types to their details
        if hasattr(role, 'hourly_wage'):
            details['hourly_wage'] = role.hourly_wage
            details['employment_type'] = 'Employee' if 'Employee' in role.__class__.__name__ else 'Contractor'
        elif hasattr(role, 'commission_rate'):
            details['commission_rate'] = role.commission_rate
            details['employment_type'] = 'Employee' if 'Employee' in role.__class__.__name__ else 'Contractor'

        return details

    # Helper function to get context data (moved outside to reuse)
    def get_context_data():
        # Get payment role information for display with specific details
        primary_role = getattr(profile, 'payment_detail', None)
        primary_role_details = get_role_details(primary_role)

        # Get additional payment roles with their specific details
        additional_roles = []
        for role in profile.additional_roles.all():
            role_data = {
                'id': role.id,
                'type': role.polymorphic_ctype.name,
                'description': role.description,
            }

            # Add specific details based on role type
            if isinstance(role, ProfitSharing):
                role_data['sharing_rate'] = role.sharing_rate
                role_data['type_display'] = 'Profit Sharing'
            elif isinstance(role, RevenueSharing):
                role_data['sharing_rate'] = role.sharing_rate
                role_data['target_user'] = role.target_user
                role_data['type_display'] = 'Revenue Sharing'
            elif isinstance(role, HasRent):
                role_data['monthly_rent'] = role.monthly_rent
                role_data['type_display'] = 'Rent'

            additional_roles.append(role_data)

        return {
            'profile': profile,
            'primary_role': primary_role,
            'primary_role_details': primary_role_details,
            'additional_roles': additional_roles,
        }

    if request.method == 'POST':
        try:
            # Input validation and sanitization
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()

            # Validate username (alphanumeric + underscores only)
            if not re.match(r'^[a-zA-Z0-9_]{3,150}$', username):
                messages.error(request,
                               'Username must be 3-150 characters and contain only letters, numbers, and underscores.')
                return render(request, 'profile.html', get_context_data())

            # Validate names (letters, spaces, hyphens only)
            if first_name and not re.match(r'^[a-zA-Z\s\-]{1,30}$', first_name):
                messages.error(request, 'First name can only contain letters, spaces, and hyphens (max 30 chars).')
                return render(request, 'profile.html', get_context_data())

            if last_name and not re.match(r'^[a-zA-Z\s\-]{1,30}$', last_name):
                messages.error(request, 'Last name can only contain letters, spaces, and hyphens (max 30 chars).')
                return render(request, 'profile.html', get_context_data())

            # Check if username already exists (excluding current user)
            if User.objects.exclude(pk=request.user.pk).filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'profile.html', get_context_data())

            # Process payroll dates with limits
            billing_dates = request.POST.getlist('billing_dates')

            # Limit number of payroll dates
            if len(billing_dates) > 10:
                messages.error(request, 'Maximum 10 payroll dates allowed.')
                return render(request, 'profile.html', get_context_data())

            valid_billing_dates = []
            allowed_strings = ['end of month']

            for date_str in billing_dates:
                date_str = date_str.strip()
                if not date_str:
                    continue

                # Limit string length
                if len(date_str) > 20:
                    messages.error(request, 'Payroll date entries must be 20 characters or less.')
                    return render(request, 'profile.html', get_context_data())

                # Check if it's the allowed special string
                if date_str.lower() == 'end of month':
                    valid_billing_dates.append(date_str.lower())
                else:
                    # Validate it's a number between 1-28
                    try:
                        day = int(date_str)
                        if 1 <= day <= 28:
                            valid_billing_dates.append(str(day))
                        else:
                            messages.error(request, f'Day {day} must be between 1 and 28.')
                            return render(request, 'profile.html', get_context_data())
                    except ValueError:
                        messages.error(request,
                                       f'Invalid entry. Use numbers 1-28 or "end of month".')
                        return render(request, 'profile.html', get_context_data())

            # Update user fields
            request.user.username = username
            request.user.first_name = first_name
            request.user.last_name = last_name

            # Update profile fields - note: changed from billing_dates to payroll_dates
            # If you want to update the primary payment role's payroll_dates:
            if hasattr(profile, 'payment_detail') and profile.payment_detail:
                profile.payment_detail.payroll_dates = valid_billing_dates
                profile.payment_detail.save()

            # Save changes
            request.user.save()
            profile.save()

            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')

        except IntegrityError:
            messages.error(request, 'Username already exists. Please choose a different username.')
            return render(request, 'profile.html', get_context_data())
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
            return render(request, 'profile.html', get_context_data())
        except Exception as e:
            messages.error(request, 'An unexpected error occurred. Please try again.')
            return render(request, 'profile.html', get_context_data())

    # GET request - return the context data
    return render(request, 'profile.html', get_context_data())