from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('rooms/', views.room_list_view, name='rooms'),
    path('guest-dashboard/', views.guest_dashboard_view, name='guest_dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('rooms/<int:room_id>/availability/', views.check_room_availability_view, name='check_room_availability'),
    path('payments/paypal/create-order/', views.create_paypal_order_view, name='paypal_create_order'),
    path('payments/paypal/capture-order/', views.capture_paypal_order_view, name='paypal_capture_order'),
    path('payments/paypal/cancel-order/', views.cancel_paypal_order_view, name='paypal_cancel_order'),
    path('book/<int:room_id>/', views.book_room_view, name='book_room'),
    path('my-bookings/', views.my_bookings_view, name='my_bookings'),
    path('edit-booking/<int:booking_id>/', views.edit_booking_view, name='edit_booking'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking_view, name='cancel_booking'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('update-status/<int:booking_id>/<str:new_status>/', views.update_status_view, name='update_status'),
    path('manage-rooms/', views.manage_rooms_view, name='manage_rooms'),
    path('manage-rooms/add/', views.add_room_view, name='add_room'),
    path('manage-rooms/edit/<int:room_id>/', views.edit_room_view, name='edit_room'),
    path('manage-rooms/toggle/<int:room_id>/', views.toggle_room_active_view, name='toggle_room_active'),
]
