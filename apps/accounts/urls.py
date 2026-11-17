from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profil/", views.profile_view, name="profile"),
    path("password/ubah/", auth_views.PasswordChangeView.as_view(
        template_name="accounts/password_change.html",
        success_url="/password/ubah/selesai/",
    ), name="password_change"),
    path("password/ubah/selesai/", auth_views.PasswordChangeDoneView.as_view(
        template_name="accounts/password_change_done.html",
    ), name="password_change_done"),
    path("password/reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/password/reset/terkirim/",
    ), name="password_reset"),
    path("password/reset/terkirim/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/password/reset/selesai/",
    ), name="password_reset_confirm"),
    path("password/reset/selesai/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),
    path("app/pengguna/", views.UserListView.as_view(), name="user_list"),
    path("app/pengguna/baru/", views.UserCreateView.as_view(), name="user_create"),
    path("app/pengguna/<int:pk>/ubah/", views.UserUpdateView.as_view(), name="user_update"),
]
