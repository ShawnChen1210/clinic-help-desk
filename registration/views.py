from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages

#imports for email stuff
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage

from .forms import *
from .models import UserProfile
from .tokens import *
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
