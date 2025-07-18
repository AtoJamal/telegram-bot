
from django.db import models
from django.core.validators import RegexValidator, URLValidator
from django.utils import timezone
from typing import List, Dict, Optional, Any
import firebase_admin
from firebase_admin import firestore, credentials
from datetime import datetime, timedelta
import uuid
from google.cloud.firestore_v1 import FieldFilter
from datetime import datetime
from typing import Dict, Any, Optional


class BaseFirestoreModel:
    """Base class for Firestore models with common operations"""
    
    def __init__(self, **kwargs):
        self.created_at = kwargs.pop('created_at', datetime.now())
        self.updated_at = kwargs.pop('updated_at', datetime.now())
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary for Firestore"""
        data = {k: v for k, v in self.__dict__.items() 
               if not k.startswith('_') and v is not None}
        # Convert datetime to ISO format if needed
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model instance from Firestore document data"""
        # Convert string dates back to datetime objects
        date_fields = ['created_at', 'updated_at']
        for field in date_fields:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)
    
    def validate_required_fields(self, required_fields: list):
        """Validate that required fields are present"""
        missing = [field for field in required_fields if not getattr(self, field, None)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")


class User(BaseFirestoreModel):
    """User model corresponding to 'users' collection"""
    
    ROLE_CHOICES = [
        ('candidate', 'Candidate'),
        ('admin', 'Admin'),
        ('designer', 'Designer'),
    ]
    
    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid', '')  # Firebase Auth UID
        self.email = kwargs.get('email', '')
        self.firstName = kwargs.get('firstName', '')
        self.middleName = kwargs.get('middleName', '')
        self.lastName = kwargs.get('lastName', '')
        self.roles = kwargs.get('roles', ['candidate'])
        self.isActive = kwargs.get('isActive', True)
        self.createdAt = kwargs.get('createdAt', timezone.now())
        self.lastLoginAt = kwargs.get('lastLoginAt', None)
        super().__init__(**kwargs)
    
    def save(self):
        """Save user to Firestore"""
        from django.conf import settings
        db = firestore.client()
        doc_ref = db.collection('users').document(self.uid)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_uid(cls, uid: str):
        """Get user by Firebase Auth UID"""
        db = firestore.client()
        doc_ref = db.collection('users').document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_by_email(cls, email: str):
        """Get user by email"""
        db = firestore.client()
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        docs = query.stream()
        for doc in docs:
            return cls.from_dict(doc.to_dict())
        return None
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles
    
    def get_full_name(self) -> str:
        """Get user's full name"""
        parts = [self.firstName, self.middleName, self.lastName]
        return ' '.join(filter(None, parts))


class Admin(BaseFirestoreModel):
    """Admin model corresponding to 'admins' collection"""
    
    ADMIN_LEVEL_CHOICES = [
        ('superAdmin', 'Super Admin'),
        ('contentAdmin', 'Content Admin'),
        ('paymentAdmin', 'Payment Admin'),
    ]
    
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', '')
        self.adminLevel = kwargs.get('adminLevel', 'contentAdmin')
        super().__init__(**kwargs)
    
    def save(self):
        """Save admin to Firestore"""
        db = firestore.client()
        doc_ref = db.collection('admins').document(self.user_id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_user_id(cls, user_id: str):
        """Get admin by user ID"""
        db = firestore.client()
        doc_ref = db.collection('admins').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_all_admins(cls):
        """Get all admins"""
        db = firestore.client()
        docs = db.collection('admins').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Designer(BaseFirestoreModel):
    """Designer model corresponding to 'designers' collection"""
    
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', '')
        self.specialization = kwargs.get('specialization', [])
        self.isAvailable = kwargs.get('isAvailable', True)
        self.assignedOrders = kwargs.get('assignedOrders', [])
        self.lastAssignedOrderAt = kwargs.get('lastAssignedOrderAt', None)
        self.portfolioUrl = kwargs.get('portfolioUrl', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save designer to Firestore"""
        db = firestore.client()
        doc_ref = db.collection('designers').document(self.user_id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_user_id(cls, user_id: str):
        """Get designer by user ID"""
        db = firestore.client()
        doc_ref = db.collection('designers').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_available_designers(cls):
        """Get all available designers"""
        db = firestore.client()
        query = db.collection('designers').where('isAvailable', '==', True)
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]
    
    def assign_order(self, order_id: str):
        """Assign order to designer"""
        if order_id not in self.assignedOrders:
            self.assignedOrders.append(order_id)
            self.lastAssignedOrderAt = timezone.now()
            self.save()
    
    def complete_order(self, order_id: str):
        """Remove order from assigned orders when completed"""
        if order_id in self.assignedOrders:
            self.assignedOrders.remove(order_id)
            self.save()


class Template(BaseFirestoreModel):
    """Template model corresponding to 'templates' collection"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.canvaLink = kwargs.get('canvaLink', '')
        self.thumbnailUrl = kwargs.get('thumbnailUrl', '')
        self.isActive = kwargs.get('isActive', True)
        super().__init__(**kwargs)
    
    def save(self):
        """Save template to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('templates').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_id(cls, template_id: str):
        """Get template by ID"""
        db = firestore.client()
        doc_ref = db.collection('templates').document(template_id)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_active_templates(cls, limit: int = 10, offset: int = 0):
        """Get active templates with pagination"""
        db = firestore.client()
        query = db.collection('templates').where('isActive', '==', True).limit(limit).offset(offset)
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]
    
    @classmethod
    def get_all_active_templates(cls):
        """Get all active templates"""
        db = firestore.client()
        query = db.collection('templates').where('isActive', '==', True)
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Order(BaseFirestoreModel):
    """Order model corresponding to 'orders' collection"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('awaiting_review', 'Awaiting Review'),
        ('completed', 'Completed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id', '')
        self.candidateId = kwargs.get('candidateId', '')
        self.designerId = kwargs.get('designerId', '')
        self.templateId = kwargs.get('templateId', '')
        self.deliveryDate = kwargs.get('deliveryDate', None)
        self.finalCvUrl = kwargs.get('finalCvUrl', '')
        self.paymentScreenshotUrl = kwargs.get('paymentScreenshotUrl', '')
        self.orderedAt = kwargs.get('orderedAt', timezone.now())
        self.paymentVerified = kwargs.get('paymentVerified', False)
        self.status = kwargs.get('status', 'pending')
        self.statusDetails = kwargs.get('statusDetails', '')  # New field for verification details
        self.notes = kwargs.get('notes', '')
        self.lastStatusUpdate = kwargs.get('lastStatusUpdate', timezone.now())
        self.telegramUserId = kwargs.get('telegramUserId', '')
    
    def save(self):
        """Save order to Firestore"""
        required_fields = ['id', 'candidateId', 'telegramUserId', 'status']
        self.validate_required_fields(required_fields)
        if not self.id:
            self.id = str(uuid.uuid4())
        self.updated_at = datetime.now()  # Update timestamp
        db = firestore.client()
        doc_ref = db.collection('orders').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_id(cls, order_id: str):
        """Get order by ID"""
        db = firestore.client()
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_by_candidate_id(cls, candidate_id: str) -> List['Order']:
        """Get orders by candidate ID"""
        db = firestore.client()
        query = db.collection('orders').where('candidateId', '==', candidate_id)
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]
    
    @classmethod
    def get_by_status(cls, status: str) -> List['Order']:
        """Get orders by status"""
        db = firestore.client()
        query = db.collection('orders').where('status', '==', status)
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]
    
    @classmethod
    def get_pending_verification(cls) -> List['Order']:
        """Get orders pending payment verification"""
        return cls.get_by_status('pending_verification')
    
    @classmethod
    def get_verified_orders(cls) -> List['Order']:
        """Get verified orders ready for assignment"""
        return cls.get_by_status('verified')
    
    @classmethod
    def get_completed_orders_for_delivery(cls) -> List['Order']:
        """Get completed orders ready for delivery"""
        db = firestore.client()
        query = db.collection('orders').where('status', '==', 'completed').where('deliveryDate', '<=', timezone.now())
        docs = query.stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]
    
    def update_status(self, new_status: str, status_details: str = '', notes: str = ''):
        """Update order status and details"""
        if new_status not in [choice[0] for choice in self.STATUS_CHOICES]:
            raise ValueError(f"Invalid status: {new_status}")
        self.status = new_status
        self.statusDetails = status_details or self.statusDetails  # Update statusDetails if provided
        self.lastStatusUpdate = timezone.now()
        if notes:
            self.notes = notes
        
        # Set delivery date for verified orders
        if new_status == 'verified' and not self.deliveryDate:
            self.deliveryDate = timezone.now() + timedelta(days=3)
        
        self.save()
    
    def approve_payment(self):
        """Approve payment and update status to verified"""
        self.paymentVerified = True
        self.update_status('verified', status_details='Payment approved')
    
    def reject_payment(self, reason: str = ''):
        """Reject payment and update status"""
        self.paymentVerified = False
        self.update_status('rejected', status_details=reason or 'Payment rejected')
    
    def assign_to_designer(self, designer_id: str):
        """Assign order to designer"""
        self.designerId = designer_id
        self.update_status('assigned')
    
    def mark_completed(self, cv_url: str):
        """Mark order as completed with CV URL"""
        self.finalCvUrl = cv_url
        self.update_status('completed')
    
    def mark_delivered(self):
        """Mark order as delivered"""
        self.update_status('delivered')
class Candidate(BaseFirestoreModel):
    """Candidate model corresponding to 'candidates' collection"""
    
    def __init__(self, **kwargs):
        self.uid = kwargs.get('uid', '')  # Firebase Auth UID
        self.firstName = kwargs.get('firstName', '')
        self.middleName = kwargs.get('middleName', '')
        self.lastName = kwargs.get('lastName', '')
        self.phoneNumber = kwargs.get('phoneNumber', '')
        self.emailAddress = kwargs.get('emailAddress', '')
        self.linkedinProfile = kwargs.get('linkedinProfile', '')
        self.city = kwargs.get('city', '')
        self.country = kwargs.get('country', '')
        self.profileUrl = kwargs.get('profileUrl', '')
        self.availability = kwargs.get('availability', '')
        self.lastUpdatedAt = kwargs.get('lastUpdatedAt', timezone.now())
        self.telegramUserId = kwargs.get('telegramUserId', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save candidate to Firestore"""
        db = firestore.client()
        
        # Ensure we have a UID before saving
        if not self.uid:
            self.uid = str(uuid.uuid4())  # Generate a new UUID if none exists
        
        doc_ref = db.collection('candidates').document(self.uid)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_uid(cls, uid: str):
        """Get candidate by UID"""
        db = firestore.client()
        doc_ref = db.collection('candidates').document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        return None
    
    @classmethod
    def get_by_telegram_user_id(cls, telegram_user_id: str):
        """Get candidate by Telegram user ID"""
        db = firestore.client()
        query = db.collection('candidates').where(filter=FieldFilter('telegramUserId', '==', telegram_user_id)).limit(1)
        docs = query.stream()
        for doc in docs:
            return cls.from_dict(doc.to_dict())
        return None
    def get_full_name(self) -> str:
        """Get candidate's full name"""
        parts = [self.firstName, self.middleName, self.lastName]
        return ' '.join(filter(None, parts))


# Subcollection Models
class CareerObjective(BaseFirestoreModel):
    """Career objective subcollection model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.summaryText = kwargs.get('summaryText', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save career objective to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('careerObjectives').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get career objectives for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('careerObjectives').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class WorkExperience(BaseFirestoreModel):
    """Work experience subcollection model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.jobTitle = kwargs.get('jobTitle', '')
        self.companyName = kwargs.get('companyName', '')
        self.location = kwargs.get('location', '')
        self.startDate = kwargs.get('startDate', None)
        self.endDate = kwargs.get('endDate', None)
        self.description = kwargs.get('description', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save work experience to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('workExperiences').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get work experiences for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('workExperiences').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Education(BaseFirestoreModel):
    """Education subcollection model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.degreeName = kwargs.get('degreeName', '')
        self.institutionName = kwargs.get('institutionName', '')
        self.startDate = kwargs.get('startDate', None)
        self.endDate = kwargs.get('endDate', None)
        self.gpa = kwargs.get('gpa', '')
        self.achievementsHonors = kwargs.get('achievementsHonors', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save education to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('education').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get education records for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('education').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Skill(BaseFirestoreModel):
    """Skill subcollection model"""
    
    PROFICIENCY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Expert', 'Expert'),
    ]
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.skillName = kwargs.get('skillName', '')
        self.category = kwargs.get('category', '')
        self.proficiency = kwargs.get('proficiency', 'Intermediate')
        super().__init__(**kwargs)
    
    def save(self):
        """Save skill to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('skills').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get skills for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('skills').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class CertificationAward(BaseFirestoreModel):
    """Certification/Award subcollection model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.certificateName = kwargs.get('certificateName', '')
        self.issuer = kwargs.get('issuer', '')
        self.yearIssued = kwargs.get('yearIssued', None)
        super().__init__(**kwargs)
    
    def save(self):
        """Save certification/award to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('certificationsAwards').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get certifications/awards for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('certificationsAwards').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Project(BaseFirestoreModel):
    """Project subcollection model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.projectTitle = kwargs.get('projectTitle', '')
        self.description = kwargs.get('description', '')
        self.technologiesUsed = kwargs.get('technologiesUsed', [])
        self.projectLink = kwargs.get('projectLink', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save project to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('projects').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get projects for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('projects').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class Language(BaseFirestoreModel):
    """Language subcollection model"""
    
    PROFICIENCY_CHOICES = [
        ('Native', 'Native'),
        ('Fluent', 'Fluent'),
        ('Intermediate', 'Intermediate'),
        ('Basic', 'Basic'),
    ]
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.languageName = kwargs.get('languageName', '')
        self.proficiencyLevel = kwargs.get('proficiencyLevel', 'Intermediate')
        super().__init__(**kwargs)
    
    def save(self):
        """Save language to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('languages').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get languages for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('languages').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


class OtherActivity(BaseFirestoreModel):
    """Other activity subcollection model"""
    
    ACTIVITY_TYPES = [
        ('Volunteering', 'Volunteering'),
        ('Extracurricular', 'Extracurricular'),
        ('Hobby', 'Hobby'),
        ('Community Service', 'Community Service'),
    ]
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '')
        self.candidate_uid = kwargs.get('candidate_uid', '')
        self.activityType = kwargs.get('activityType', 'Volunteering')
        self.description = kwargs.get('description', '')
        super().__init__(**kwargs)
    
    def save(self):
        """Save other activity to Firestore"""
        db = firestore.client()
        if not self.id:
            self.id = str(uuid.uuid4())
        doc_ref = db.collection('candidates').document(self.candidate_uid).collection('otherActivities').document(self.id)
        doc_ref.set(self.to_dict())
        return self
    
    @classmethod
    def get_by_candidate(cls, candidate_uid: str):
        """Get other activities for a candidate"""
        db = firestore.client()
        docs = db.collection('candidates').document(candidate_uid).collection('otherActivities').stream()
        return [cls.from_dict(doc.to_dict()) for doc in docs]


# Helper class for managing candidate data with all subcollections
class CandidateManager:
    """Helper class to manage candidate data with all subcollections"""
    
    def __init__(self, candidate_uid: str):
        self.candidate_uid = candidate_uid
        self.candidate = Candidate.get_by_uid(candidate_uid)
    
    def get_complete_profile(self) -> Dict[str, Any]:
        """Get complete candidate profile with all subcollections"""
        if not self.candidate:
            return {}
        
        profile = self.candidate.to_dict()
        profile.update({
            'careerObjectives': [obj.to_dict() for obj in CareerObjective.get_by_candidate(self.candidate_uid)],
            'workExperiences': [exp.to_dict() for exp in WorkExperience.get_by_candidate(self.candidate_uid)],
            'education': [edu.to_dict() for edu in Education.get_by_candidate(self.candidate_uid)],
            'skills': [skill.to_dict() for skill in Skill.get_by_candidate(self.candidate_uid)],
            'certificationsAwards': [cert.to_dict() for cert in CertificationAward.get_by_candidate(self.candidate_uid)],
            'projects': [proj.to_dict() for proj in Project.get_by_candidate(self.candidate_uid)],
            'languages': [lang.to_dict() for lang in Language.get_by_candidate(self.candidate_uid)],
            'otherActivities': [act.to_dict() for act in OtherActivity.get_by_candidate(self.candidate_uid)],
        })
        
        return profile
    
    def update_candidate_timestamp(self):
        """Update candidate's lastUpdatedAt timestamp"""
        if self.candidate:
            self.candidate.lastUpdatedAt = timezone.now()
            self.candidate.save()