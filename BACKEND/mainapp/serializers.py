from rest_framework import serializers
from django.utils import timezone
from typing import Dict, Any
import re

class BaseFirestoreSerializer(serializers.Serializer):
    """Base serializer for Firestore models"""
    
    def create(self, validated_data):
        """Create method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create method")
    
    def update(self, instance, validated_data):
        """Update method to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement update method")


class UserSerializer(BaseFirestoreSerializer):
    """Serializer for User model"""
    
    uid = serializers.CharField(read_only=True)
    email = serializers.EmailField()
    firstName = serializers.CharField(max_length=50)
    middleName = serializers.CharField(max_length=50, allow_blank=True, required=False)
    lastName = serializers.CharField(max_length=50)
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=['candidate', 'admin', 'designer']),
        default=['candidate']
    )
    isActive = serializers.BooleanField(default=True)
    createdAt = serializers.DateTimeField(read_only=True)
    lastLoginAt = serializers.DateTimeField(read_only=True, allow_null=True)
    
    def validate_email(self, value):
        """Validate email format"""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise serializers.ValidationError("Invalid email format")
        return value


class AdminSerializer(BaseFirestoreSerializer):
    """Serializer for Admin model"""
    
    user_id = serializers.CharField()
    adminLevel = serializers.ChoiceField(
        choices=['superAdmin', 'contentAdmin', 'paymentAdmin'],
        default='contentAdmin'
    )


class DesignerSerializer(BaseFirestoreSerializer):
    """Serializer for Designer model"""
    
    user_id = serializers.CharField()
    specialization = serializers.ListField(
        child=serializers.CharField(max_length=100),
        default=list
    )
    isAvailable = serializers.BooleanField(default=True)
    assignedOrders = serializers.ListField(
        child=serializers.CharField(),
        default=list,
        read_only=True
    )
    lastAssignedOrderAt = serializers.DateTimeField(read_only=True, allow_null=True)
    portfolioUrl = serializers.URLField(allow_blank=True, required=False)


class TemplateSerializer(BaseFirestoreSerializer):
    """Serializer for Template model"""
    
    id = serializers.CharField(read_only=True)
    canvaLink = serializers.URLField()
    thumbnailUrl = serializers.URLField()
    isActive = serializers.BooleanField(default=True)
    
    def validate_canvaLink(self, value):
        """Validate Canva link format"""
        if not value.startswith('https://www.canva.com/'):
            raise serializers.ValidationError("Invalid Canva link format")
        return value


class OrderSerializer(BaseFirestoreSerializer):
    """Serializer for Order model"""
    
    id = serializers.CharField(read_only=True)
    candidateId = serializers.CharField()
    designerId = serializers.CharField(allow_blank=True, required=False)
    templateId = serializers.CharField()
    deliveryDate = serializers.DateTimeField(read_only=True, allow_null=True)
    finalCvUrl = serializers.URLField(allow_blank=True, required=False)
    paymentScreenshotUrl = serializers.URLField(allow_blank=True, required=False)
    orderedAt = serializers.DateTimeField(read_only=True)
    paymentVerified = serializers.BooleanField(default=False)
    status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('awaitingPayment', 'Awaiting Payment'),
            ('pendingVerification', 'Pending Verification'),
            ('approved', 'Approved'),
            ('assigned', 'Assigned'),
            ('inProgress', 'In Progress'),
            ('awaiting_review', 'Awaiting Review'),
            ('completed', 'Completed'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )
    notes = serializers.CharField(allow_blank=True, required=False)
    lastStatusUpdate = serializers.DateTimeField(read_only=True)
    telegramUserId = serializers.CharField()


class CandidateSerializer(BaseFirestoreSerializer):
    """Serializer for Candidate model"""
    
    uid = serializers.CharField(read_only=True)
    firstName = serializers.CharField(max_length=50)
    middleName = serializers.CharField(max_length=50, allow_blank=True, required=False)
    lastName = serializers.CharField(max_length=50)
    phoneNumber = serializers.CharField(max_length=20)
    emailAddress = serializers.EmailField()
    linkedinProfile = serializers.URLField(allow_blank=True, required=False)
    city = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)
    profileUrl = serializers.URLField(allow_blank=True, required=False)
    availability = serializers.CharField(max_length=100, allow_blank=True, required=False)
    lastUpdatedAt = serializers.DateTimeField(read_only=True)
    telegramUserId = serializers.CharField()
    
    def validate_phoneNumber(self, value):
        """Validate phone number format"""
        if not re.match(r'^\+?[1-9]\d{1,14}$', value):
            raise serializers.ValidationError("Invalid phone number format")
        return value


class CareerObjectiveSerializer(BaseFirestoreSerializer):
    """Serializer for CareerObjective model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    summaryText = serializers.CharField(max_length=500)


class WorkExperienceSerializer(BaseFirestoreSerializer):
    """Serializer for WorkExperience model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    jobTitle = serializers.CharField(max_length=100)
    companyName = serializers.CharField(max_length=100)
    location = serializers.CharField(max_length=100)
    startDate = serializers.DateField()
    endDate = serializers.DateField(allow_null=True, required=False)
    description = serializers.CharField(max_length=1000)
    
    def validate(self, data):
        """Validate date ranges"""
        if data.get('endDate') and data.get('startDate'):
            if data['endDate'] < data['startDate']:
                raise serializers.ValidationError("End date must be after start date")
        return data


class EducationSerializer(BaseFirestoreSerializer):
    """Serializer for Education model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    degreeName = serializers.CharField(max_length=100)
    institutionName = serializers.CharField(max_length=100)
    startDate = serializers.DateField()
    endDate = serializers.DateField(allow_null=True, required=False)
    gpa = serializers.CharField(max_length=20, allow_blank=True, required=False)
    achievementsHonors = serializers.CharField(max_length=500, allow_blank=True, required=False)
    
    def validate(self, data):
        """Validate date ranges"""
        if data.get('endDate') and data.get('startDate'):
            if data['endDate'] < data['startDate']:
                raise serializers.ValidationError("End date must be after start date")
        return data


class SkillSerializer(BaseFirestoreSerializer):
    """Serializer for Skill model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    skillName = serializers.CharField(max_length=100)
    category = serializers.CharField(max_length=50, allow_blank=True, required=False)
    proficiency = serializers.ChoiceField(
        choices=['Beginner', 'Intermediate', 'Advanced', 'Expert'],
        default='Intermediate'
    )


class CertificationAwardSerializer(BaseFirestoreSerializer):
    """Serializer for CertificationAward model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    certificateName = serializers.CharField(max_length=100)
    issuer = serializers.CharField(max_length=100)
    yearIssued = serializers.IntegerField()
    
    def validate_yearIssued(self, value):
        """Validate year issued"""
        current_year = timezone.now().year
        if value < 1900 or value > current_year:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year}")
        return value


class ProjectSerializer(BaseFirestoreSerializer):
    """Serializer for Project model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    projectTitle = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=1000)
    technologiesUsed = serializers.ListField(
        child=serializers.CharField(max_length=50),
        default=list
    )
    projectLink = serializers.URLField(allow_blank=True, required=False)


class LanguageSerializer(BaseFirestoreSerializer):
    """Serializer for Language model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    languageName = serializers.CharField(max_length=50)
    proficiencyLevel = serializers.ChoiceField(
        choices=['Native', 'Fluent', 'Intermediate', 'Basic'],
        default='Intermediate'
    )


class OtherActivitySerializer(BaseFirestoreSerializer):
    """Serializer for OtherActivity model"""
    
    id = serializers.CharField(read_only=True)
    candidate_uid = serializers.CharField()
    activityType = serializers.ChoiceField(
        choices=['Volunteering', 'Extracurricular', 'Hobby', 'Community Service'],
        default='Volunteering'
    )
    description = serializers.CharField(max_length=500)


class CompleteProfileSerializer(BaseFirestoreSerializer):
    """Serializer for complete candidate profile"""
    
    candidate = CandidateSerializer()
    careerObjectives = CareerObjectiveSerializer(many=True, required=False)
    workExperiences = WorkExperienceSerializer(many=True, required=False)
    education = EducationSerializer(many=True, required=False)
    skills = SkillSerializer(many=True, required=False)
    certificationsAwards = CertificationAwardSerializer(many=True, required=False)
    projects = ProjectSerializer(many=True, required=False)
    languages = LanguageSerializer(many=True, required=False)
    otherActivities = OtherActivitySerializer(many=True, required=False)

