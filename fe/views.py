from django.shortcuts import render

def index_view(request):
    return render(request, 'fe/index.html')