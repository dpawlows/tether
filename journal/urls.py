from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('new/', views.new_journal, name='new_journal'),
    path('open/', views.open_journal, name='open_journal'),
    path('journal/<uuid:pk>/', views.journal_view, name='journal_view'),
    path('journal/<uuid:pk>/add/', views.add_entry, name='add_entry'),
    path('journal/<uuid:pk>/meta/', views.save_meta, name='save_meta'),
    path('journal/<uuid:pk>/map/', views.save_map, name='save_map'),
    path('journal/<uuid:pk>/delete/', views.delete_journal, name='delete_journal'),
    path('journal/<uuid:pk>/entry/<int:entry_pk>/edit/', views.edit_entry, name='edit_entry'),
]
