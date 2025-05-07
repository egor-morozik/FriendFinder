from django.shortcuts import render
from django.http import HttpResponse

def profile_list(request):
    return HttpResponse("All profiles...")

def profile_detail(request, pk):
    return HttpResponse(f"Profile ID {pk}")

def like_create(request):
    return HttpResponse("Creat like")

def like_detail(request, pk):
    return HttpResponse(f"Like ID {pk}")