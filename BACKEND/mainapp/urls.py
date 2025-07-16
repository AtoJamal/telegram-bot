# mainapp/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Template Views
    path('templates/', views.get_templates, name='get_templates'),
    path('templates/<str:template_id>/', views.get_template_by_id, name='get_template_by_id'),

    # Order Views
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/<str:order_id>/', views.get_order_by_id, name='get_order_by_id'),
    path('orders/<str:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<str:order_id>/upload-payment-screenshot/', views.upload_payment_screenshot, name='upload_payment_screenshot'),
    path('orders/<str:order_id>/approve-payment/', views.approve_payment, name='approve_payment'),
    path('orders/<str:order_id>/assign-designer/', views.assign_order_to_designer, name='assign_order_to_designer'),
    path('orders/<str:order_id>/complete/', views.complete_order, name='complete_order'),

    # Admin Views
    path('admin/orders/pending-verification/', views.get_pending_orders, name='get_pending_orders'),
    path('admin/orders/approved/', views.get_approved_orders, name='get_approved_orders'),
    path('admin/orders/status/<str:status_name>/', views.get_orders_by_status, name='get_orders_by_status'),

    # Candidate Views
    path('candidates/create/', views.create_candidate, name='create_candidate'),
    path('candidates/telegram/<str:telegram_user_id>/', views.get_candidate_by_telegram_id, name='get_candidate_by_telegram_id'),
    path('candidates/<str:candidate_uid>/profile/', views.get_complete_candidate_profile, name='get_complete_candidate_profile'),

    # Subcollection Views (for a specific candidate)
    path('candidates/work-experience/add/', views.add_work_experience, name='add_work_experience'),
    path('candidates/education/add/', views.add_education, name='add_education'),
    path('candidates/skills/add/', views.add_skill, name='add_skill'),

    path('designers/available/', views.get_available_designers, name='get_available_designers'),
    path('designers/<str:designer_id>/', views.get_designer_by_id, name='get_designer_by_id'),

    # Delivery Views
    path('delivery/orders/ready/', views.get_orders_ready_for_delivery, name='get_orders_ready_for_delivery'),
    path('delivery/orders/<str:order_id>/mark-delivered/', views.mark_order_delivered, name='mark_order_delivered'),

    # Telegram Bot Helper Views
    path('telegram/webhook/', views.telegram_webhook, name='telegram_webhook'),

    # Health Check View
    path('health/', views.health_check, name='health_check'),
]