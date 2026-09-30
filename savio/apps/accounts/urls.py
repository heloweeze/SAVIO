from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.SavioLoginView.as_view(), name="login"),
    path("logout/", views.SavioLogoutView.as_view(), name="logout"),
    path("profil/", views.profile, name="profile"),
    path("profil/mot-de-passe/", views.password_change, name="password_change"),
]
