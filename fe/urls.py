from django.urls import path
from . import views

app_name = 'fe'

urlpatterns = [

    path('', views.index_view, name='index'),

]
