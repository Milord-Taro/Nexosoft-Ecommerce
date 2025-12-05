from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),  # enviamos todo a la app accounts
]

urlpatterns = [
    path("", include("accounts.urls")),
]

# 👇 Importante: estas líneas van FUERA de urlpatterns
handler404 = "accounts.views.custom_404"
handler500 = "accounts.views.custom_500"