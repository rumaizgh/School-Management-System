from django.shortcuts import render

def login_view(request):
    """Renders the Web Admin Login Page."""
    return render(request, 'web_admin/login.html')

def dashboard_view(request):
    """Renders the Single-Page Web Admin Dashboard."""
    return render(request, 'web_admin/dashboard.html')
