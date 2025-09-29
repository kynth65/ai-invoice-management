from django.urls import path
from . import frontend_views

urlpatterns = [
    # Authentication
    path('login/', frontend_views.login_view, name='login'),
    path('logout/', frontend_views.logout_view, name='logout'),

    # Main dashboard (home page)
    path('', frontend_views.home_view, name='home'),

    # Invoice management
    path('upload/', frontend_views.upload_view, name='upload_invoice'),
    path('invoices/', frontend_views.invoice_list_view, name='invoice_list'),
    path('invoice/<int:pk>/', frontend_views.invoice_detail_view, name='invoice_detail'),

    # Analytics
    path('analytics/', frontend_views.analytics_view, name='analytics'),

    # AJAX endpoints
    path('ajax/upload/', frontend_views.QuickUploadView.as_view(), name='ajax_upload'),
]