from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(PrimaryPaymentRole)
admin.site.register(RevenueSharing)
admin.site.register(AdditionalPaymentRole)