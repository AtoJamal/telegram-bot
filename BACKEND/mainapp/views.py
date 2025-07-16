from django.shortcuts import render

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import uuid
from .models import *
from .serializers import *


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API results"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# Template Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_templates(request):
    """Get paginated templates for Telegram bot"""
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        offset = (page - 1) * page_size
        
        templates = Template.get_active_templates(limit=page_size, offset=offset)
        serializer = TemplateSerializer(templates, many=True)
        
        return Response({
            'templates': serializer.data,
            'page': page,
            'page_size': page_size,
            'has_next': len(templates) == page_size
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_template_by_id(request, template_id):
    """Get specific template by ID"""
    try:
        template = Template.get_by_id(template_id)
        if not template:
            return Response({'error': 'Template not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TemplateSerializer(template)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Order Views
@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    """Create new order from Telegram bot"""
    try:
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            order = Order(**serializer.validated_data)
            order.save()
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_order_by_id(request, order_id):
    """Get order by ID"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def update_order_status(request, order_id):
    """Update order status"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        if new_status:
            order.update_status(new_status, notes)
            return Response(OrderSerializer(order).data)
        
        return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def upload_payment_screenshot(request, order_id):
    """Upload payment screenshot for order"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        screenshot_url = request.data.get('screenshot_url')
        if not screenshot_url:
            return Response({'error': 'Screenshot URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.paymentScreenshotUrl = screenshot_url
        order.update_status('pending_verification')
        
        return Response(OrderSerializer(order).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def approve_payment(request, order_id):
    """Approve payment for order (Admin only)"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        order.approve_payment()
        return Response(OrderSerializer(order).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def assign_order_to_designer(request, order_id):
    """Assign order to designer"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        designer_id = request.data.get('designer_id')
        if not designer_id:
            return Response({'error': 'Designer ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.assign_to_designer(designer_id)
        
        # Update designer's assigned orders
        designer = Designer.get_by_user_id(designer_id)
        if designer:
            designer.assign_order(order_id)
        
        return Response(OrderSerializer(order).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def complete_order(request, order_id):
    """Mark order as completed with CV URL"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        cv_url = request.data.get('cv_url')
        if not cv_url:
            return Response({'error': 'CV URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        order.mark_completed(cv_url)
        
        # Update designer's assigned orders
        if order.designerId:
            designer = Designer.get_by_user_id(order.designerId)
            if designer:
                designer.complete_order(order_id)
        
        return Response(OrderSerializer(order).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Admin Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_pending_orders(request):
    """Get orders pending verification"""
    try:
        orders = Order.get_pending_verification()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_approved_orders(request):
    """Get approved orders ready for assignment"""
    try:
        orders = Order.get_approved_orders()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_orders_by_status(request, status_name):
    """Get orders by status"""
    try:
        orders = Order.get_by_status(status_name)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Candidate Views
@api_view(['POST'])
@permission_classes([AllowAny])
def create_candidate(request):
    """Create new candidate"""
    try:
        serializer = CandidateSerializer(data=request.data)
        if serializer.is_valid():
            candidate = Candidate(**serializer.validated_data)
            candidate.uid = str(uuid.uuid4())  # Generate UID if not provided
            candidate.save()
            return Response(CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_candidate_by_telegram_id(request, telegram_user_id):
    """Get candidate by Telegram user ID"""
    try:
        candidate = Candidate.get_by_telegram_user_id(telegram_user_id)
        if not candidate:
            return Response({'error': 'Candidate not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CandidateSerializer(candidate)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_complete_candidate_profile(request, candidate_uid):
    """Get complete candidate profile with all subcollections"""
    try:
        manager = CandidateManager(candidate_uid)
        profile = manager.get_complete_profile()
        
        if not profile:
            return Response({'error': 'Candidate not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(profile)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Subcollection Views
@api_view(['POST'])
@permission_classes([AllowAny])
def add_work_experience(request):
    """Add work experience to candidate"""
    try:
        serializer = WorkExperienceSerializer(data=request.data)
        if serializer.is_valid():
            work_exp = WorkExperience(**serializer.validated_data)
            work_exp.save()
            return Response(WorkExperienceSerializer(work_exp).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_education(request):
    """Add education to candidate"""
    try:
        serializer = EducationSerializer(data=request.data)
        if serializer.is_valid():
            education = Education(**serializer.validated_data)
            education.save()
            return Response(EducationSerializer(education).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def add_skill(request):
    """Add skill to candidate"""
    try:
        serializer = SkillSerializer(data=request.data)
        if serializer.is_valid():
            skill = Skill(**serializer.validated_data)
            skill.save()
            return Response(SkillSerializer(skill).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Designer Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_designers(request):
    """Get available designers"""
    try:
        designers = Designer.get_available_designers()
        serializer = DesignerSerializer(designers, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_designer_by_id(request, designer_id):
    """Get designer by ID"""
    try:
        designer = Designer.get_by_user_id(designer_id)
        if not designer:
            return Response({'error': 'Designer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DesignerSerializer(designer)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Delivery Views
@api_view(['GET'])
@permission_classes([AllowAny])
def get_orders_ready_for_delivery(request):
    """Get orders ready for delivery (for cron job)"""
    try:
        orders = Order.get_completed_orders_for_delivery()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([AllowAny])
def mark_order_delivered(request, order_id):
    """Mark order as delivered"""
    try:
        order = Order.get_by_id(order_id)
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        order.mark_delivered()
        return Response(OrderSerializer(order).data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Telegram Bot Helper Views
@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """Handle Telegram webhook for bot interactions"""
    try:
        # This will be implemented based on your Telegram bot logic
        # For now, just return success
        return Response({'status': 'success'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Health Check View
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({'status': 'healthy', 'message': 'API is running'})
