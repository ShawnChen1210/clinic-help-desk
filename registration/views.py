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
from .models import UserProfile
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
                return render(request, 'profile.html', {'profile': profile})

            # Validate names (letters, spaces, hyphens only)
            if first_name and not re.match(r'^[a-zA-Z\s\-]{1,30}$', first_name):
                messages.error(request, 'First name can only contain letters, spaces, and hyphens (max 30 chars).')
                return render(request, 'profile.html', {'profile': profile})

            if last_name and not re.match(r'^[a-zA-Z\s\-]{1,30}$', last_name):
                messages.error(request, 'Last name can only contain letters, spaces, and hyphens (max 30 chars).')
                return render(request, 'profile.html', {'profile': profile})

            # Check if username already exists (excluding current user)
            if User.objects.exclude(pk=request.user.pk).filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a different username.')
                return render(request, 'profile.html', {'profile': profile})

            # Process payroll dates with limits
            billing_dates = request.POST.getlist('billing_dates')

            # Limit number of payroll dates
            if len(billing_dates) > 10:
                messages.error(request, 'Maximum 10 payroll dates allowed.')
                return render(request, 'profile.html', {'profile': profile})

            valid_billing_dates = []
            allowed_strings = ['end of month']

            for date_str in billing_dates:
                date_str = date_str.strip()
                if not date_str:
                    continue

                # Limit string length
                if len(date_str) > 20:
                    messages.error(request, 'Payroll date entries must be 20 characters or less.')
                    return render(request, 'profile.html', {'profile': profile})

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
                            return render(request, 'profile.html', {'profile': profile})
                    except ValueError:
                        messages.error(request,
                                       f'Invalid entry: {escape(date_str)}. Use numbers 1-28 or "end of month".')
                        return render(request, 'profile.html', {'profile': profile})

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
        except ValidationError as e:
            messages.error(request, f'Validation error: {str(e)}')
        except Exception as e:
            messages.error(request, 'An unexpected error occurred. Please try again.')

    # Get payment role information for display
    primary_role = None
    additional_roles = []

    try:
        # Get primary payment role
        primary_role = profile.payment_detail
    except:
        primary_role = None

    # Get additional payment roles
    additional_roles = profile.additional_roles.all()

    context = {
        'profile': profile,
        'primary_role': primary_role,
        'additional_roles': additional_roles,
    }

    return render(request, 'profile.html', context)