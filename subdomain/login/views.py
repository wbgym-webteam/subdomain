from django.shortcuts import render, redirect

# Create your views here.


def login(request):
    if request.method == "POST":
        return redirect("home")
    return render(request, "login.html")
