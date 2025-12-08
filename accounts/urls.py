from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.register_view, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path("perfil/", views.perfil_view, name="perfil"),
    path("recuperar-clave/", views.recuperar_clave_view, name="recuperar_clave"),



    path("demo-404/", views.demo_404, name="demo_404"),
    path("demo-500/", views.demo_error_500, name="demo_500"),


]
