from django.shortcuts import render, HttpResponse, redirect


# Create your views here.
def login(request):
    if request.method == "POST":
        return redirect("home")
    return render(request, "login.html")


def home(request):
    return render(request, "home.html")
