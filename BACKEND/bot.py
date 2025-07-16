import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from mainapp.models import (
    Candidate,
    Order,
    CandidateManager,
    WorkExperience,
    Education,
    Skill,
    CareerObjective,
    CertificationAward,
    Project,
    Language,
    OtherActivity
)
import uuid
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import django
from typing import Dict, List

# Ensure Python version is 3.6 or higher
import sys
if sys.version_info < (3, 6):
    raise RuntimeError("This bot requires Python 3.6 or higher")

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cvbot_backend.settings')
django.setup()

# Load environment variables
load_dotenv()

# Get Telegram bot token
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize Firebase only if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("../firebaseapikey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
(
    START,
    COLLECT_PERSONAL_INFO,
    COLLECT_CONTACT_INFO,
    COLLECT_PROFESSIONAL_INFO,
    COLLECT_EDUCATION,
    COLLECT_SKILLS,
    COLLECT_CAREER_OBJECTIVE,
    COLLECT_CERTIFICATIONS,
    COLLECT_PROJECTS,
    COLLECT_LANGUAGES,
    COLLECT_ACTIVITIES,
    CONFIRM_ORDER,
    PAYMENT
) = range(13)

class CVBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).read_timeout(30).write_timeout(30).connect_timeout(30).build()
        self.user_sessions: Dict[str, Dict] = {}  # Dictionary to store user-specific data
        self.setup_handlers()
        
    def setup_handlers(self) -> None:
        """Set up conversation handlers for the bot"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                START: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.start_collecting_info)
                ],
                COLLECT_PERSONAL_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_personal_info)
                ],
                COLLECT_CONTACT_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_contact_info)
                ],
                COLLECT_PROFESSIONAL_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_professional_info),
                    CallbackQueryHandler(self.handle_professional_info_choice, pattern="^(add_another_work|continue_education)$")
                ],
                COLLECT_EDUCATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_education),
                    CallbackQueryHandler(self.handle_education_choice, pattern="^(add_another_edu|continue_skills)$")
                ],
                COLLECT_SKILLS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_skills),
                    CallbackQueryHandler(self.handle_skills_choice, pattern="^(add_another_skill|continue_career)$")
                ],
                COLLECT_CAREER_OBJECTIVE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_career_objective)
                ],
                COLLECT_CERTIFICATIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_certifications),
                    CallbackQueryHandler(self.handle_certifications_choice, pattern="^(add_another_cert|continue_projects)$")
                ],
                COLLECT_PROJECTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_projects),
                    CallbackQueryHandler(self.handle_projects_choice, pattern="^(add_another_project|continue_languages)$")
                ],
                COLLECT_LANGUAGES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_languages),
                    CallbackQueryHandler(self.handle_languages_choice, pattern="^(add_another_language|continue_activities)$")
                ],
                COLLECT_ACTIVITIES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_activities)
                ],
                CONFIRM_ORDER: [
                    CallbackQueryHandler(self.confirm_order, pattern="^confirm_"),
                    CallbackQueryHandler(self.edit_info, pattern="^edit_")
                ],
                PAYMENT: [
                    MessageHandler(filters.PHOTO, self.handle_payment_screenshot)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            per_message=False
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_error_handler(self.error_handler)

    def get_user_session(self, user_id: str) -> dict:
        """Get or create a user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'candidate_data': {'availability': 'To be specified'},  # Initialize with default availability
                'work_experiences': [],
                'education': [],
                'skills': [],
                'career_objectives': [],
                'certifications': [],
                'projects': [],
                'languages': [],
                'activities': [],
                'current_field': None,
                'current_work_experience': {},  # Temporary storage for work experience fields
                'current_education': {},  # Temporary storage for education fields
                'current_skill': {},  # Temporary storage for skill fields
                'current_certification': {},  # Temporary storage for certification fields
                'current_project': {},  # Temporary storage for project fields
                'current_language': {}  # Temporary storage for language fields
            }
        return self.user_sessions[user_id]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send welcome message and start the conversation"""
        user = update.effective_user
        telegram_id = str(user.id)
        
        # Initialize user session
        session = self.get_user_session(telegram_id)
        
        # Check if candidate exists
        candidate = Candidate.get_by_telegram_user_id(telegram_id)
        if candidate:
            await update.message.reply_text(
                "Welcome back! You already have a profile. "
                "Would you like to update your information or create a new CV?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Update Profile", callback_data="update_profile")],
                    [InlineKeyboardButton("Create New CV", callback_data="new_cv")]
                ])
            )
            return START
        else:
            await update.message.reply_text(
                "Welcome to the CV Bot! Let's create your professional CV.\n\n"
                "Please enter your first name:"
            )
            session['current_field'] = 'firstName'
            return COLLECT_PERSONAL_INFO

    async def start_collecting_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user choice to update profile or create new CV"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "update_profile":
            # Load existing profile data
            candidate = Candidate.get_by_telegram_user_id(telegram_id)
            session['candidate_data'] = candidate.to_dict()
            # Ensure availability is set to default if not present
            session['candidate_data']['availability'] = session['candidate_data'].get('availability', 'To be specified')
            
            # Load all subcollections
            manager = CandidateManager(candidate.uid)
            profile = manager.get_complete_profile()
            
            session['work_experiences'] = profile.get('workExperiences', [])
            session['education'] = profile.get('education', [])
            session['skills'] = profile.get('skills', [])
            session['career_objectives'] = profile.get('careerObjectives', [])
            session['certifications'] = profile.get('certificationsAwards', [])
            session['projects'] = profile.get('projects', [])
            session['languages'] = profile.get('languages', [])
            session['activities'] = profile.get('otherActivities', [])
            
            await query.edit_message_text(
                "Which section would you like to update?",
                reply_markup=self.get_profile_sections_keyboard()
            )
            return START
        else:
            await query.edit_message_text(
                "Let's create a new CV. Please enter your first name:"
            )
            session['current_field'] = 'firstName'
            return COLLECT_PERSONAL_INFO

    def get_profile_sections_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard for profile sections"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Personal Info", callback_data="edit_personal")],
            [InlineKeyboardButton("Contact Info", callback_data="edit_contact")],
            [InlineKeyboardButton("Work Experience", callback_data="edit_work")],
            [InlineKeyboardButton("Education", callback_data="edit_education")],
            [InlineKeyboardButton("Skills", callback_data="edit_skills")],
            [InlineKeyboardButton("Career Objective", callback_data="edit_career")],
            [InlineKeyboardButton("Certifications", callback_data="edit_certs")],
            [InlineKeyboardButton("Projects", callback_data="edit_projects")],
            [InlineKeyboardButton("Languages", callback_data="edit_languages")],
            [InlineKeyboardButton("Other Activities", callback_data="edit_activities")]
        ])

    async def collect_personal_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect personal information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'firstName':
            session['candidate_data']['firstName'] = update.message.text
            session['current_field'] = 'middleName'
            await update.message.reply_text("Great! Now please enter your middle name (if any):")
            return COLLECT_PERSONAL_INFO
        elif current_field == 'middleName':
            session['candidate_data']['middleName'] = update.message.text
            session['current_field'] = 'lastName'
            await update.message.reply_text("Now please enter your last name:")
            return COLLECT_PERSONAL_INFO
        elif current_field == 'lastName':
            session['candidate_data']['lastName'] = update.message.text
            await update.message.reply_text(
                "Now let's collect your contact information.\n"
                "Please enter your phone number (e.g., +251911223344):"
            )
            session['current_field'] = 'phoneNumber'
            return COLLECT_CONTACT_INFO

    async def collect_contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect contact information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'phoneNumber':
            session['candidate_data']['phoneNumber'] = update.message.text
            session['current_field'] = 'emailAddress'
            await update.message.reply_text("Please enter your email address:")
            return COLLECT_CONTACT_INFO
        elif current_field == 'emailAddress':
            session['candidate_data']['emailAddress'] = update.message.text
            session['current_field'] = 'linkedinProfile'
            await update.message.reply_text(
                "Please enter your LinkedIn profile URL (if any, or type 'skip'):"
            )
            return COLLECT_CONTACT_INFO
        elif current_field == 'linkedinProfile':
            if update.message.text.lower() != 'skip':
                session['candidate_data']['linkedinProfile'] = update.message.text
            session['current_field'] = 'city'
            await update.message.reply_text("Please enter your city of residence:")
            return COLLECT_CONTACT_INFO
        elif current_field == 'city':
            session['candidate_data']['city'] = update.message.text
            session['current_field'] = 'country'
            await update.message.reply_text("Please enter your country:")
            return COLLECT_CONTACT_INFO
        elif current_field == 'country':
            session['candidate_data']['country'] = update.message.text
            await update.message.reply_text(
                "Now let's collect your professional experience.\n"
                "Please enter the job title for your most recent position:"
            )
            session['current_field'] = 'work_jobTitle'
            session['current_work_experience'] = {}  # Initialize for new work experience
            return COLLECT_PROFESSIONAL_INFO

    async def collect_professional_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect professional experience from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'work_jobTitle':
            session['current_work_experience']['jobTitle'] = update.message.text
            session['current_field'] = 'work_companyName'
            await update.message.reply_text("Please enter the company name:")
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_companyName':
            session['current_work_experience']['companyName'] = update.message.text
            session['current_field'] = 'work_location'
            await update.message.reply_text("Please enter the location of this position (e.g., city, country):")
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_location':
            session['current_work_experience']['location'] = update.message.text
            session['current_field'] = 'work_description'
            await update.message.reply_text("Please describe your responsibilities and duration (e.g., 'Managed projects, 2019-2021'):")
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_description':
            session['current_work_experience']['description'] = update.message.text
            # Store the completed work experience
            session['work_experiences'].append(session['current_work_experience'].copy())
            session['current_work_experience'] = {}  # Reset for next entry
            await update.message.reply_text(
                "Work experience added. Would you like to add another position?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_work")],
                    [InlineKeyboardButton("Continue", callback_data="continue_education")]
                ])
            )
            return COLLECT_PROFESSIONAL_INFO

    async def handle_professional_info_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another work experience or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "add_another_work":
            session['current_field'] = 'work_jobTitle'
            await query.edit_message_text(
                "Please enter the job title for your next position:"
            )
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "continue_education":
            session['current_field'] = 'edu_degreeName'
            session['current_education'] = {}  # Initialize for new education
            await query.edit_message_text(
                "Please enter your degree name (e.g., 'Bachelor of Science in Computer Science'):"
            )
            return COLLECT_EDUCATION

    async def collect_education(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect education information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'edu_degreeName':
            session['current_education']['degreeName'] = update.message.text
            session['current_field'] = 'edu_institutionName'
            await update.message.reply_text("Please enter the institution name (e.g., 'Addis Ababa University'):")
            return COLLECT_EDUCATION
        elif current_field == 'edu_institutionName':
            session['current_education']['institutionName'] = update.message.text
            session['current_field'] = 'edu_gpa'
            await update.message.reply_text("Please enter your GPA (e.g., '3.5/4.0', or type 'skip' if not applicable):")
            return COLLECT_EDUCATION
        elif current_field == 'edu_gpa':
            session['current_education']['gpa'] = update.message.text if update.message.text.lower() != 'skip' else None
            session['current_field'] = 'edu_description'
            await update.message.reply_text("Please describe your education, including the year (e.g., 'Graduated in 2020'):")
            return COLLECT_EDUCATION
        elif current_field == 'edu_description':
            session['current_education']['description'] = update.message.text
            session['current_field'] = 'edu_achievementsHonors'
            await update.message.reply_text("Please list any achievements or honors (e.g., 'Dean's List', or type 'skip' if none):")
            return COLLECT_EDUCATION
        elif current_field == 'edu_achievementsHonors':
            session['current_education']['achievementsHonors'] = update.message.text if update.message.text.lower() != 'skip' else None
            # Store the completed education entry
            session['education'].append(session['current_education'].copy())
            session['current_education'] = {}  # Reset for new entry
            await update.message.reply_text(
                "Education added. Would you like to add another education entry?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_edu")],
                    [InlineKeyboardButton("Continue", callback_data="continue_skills")]
                ])
            )
            return COLLECT_EDUCATION

    async def handle_education_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another education entry or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == 'add_another_edu':
            session['current_field'] = 'edu_degreeName'
            await query.edit_message_text(
                "Please enter your degree name (e.g., 'Bachelor of Science in Computer Science'):"
            )
            return COLLECT_EDUCATION
        elif query.data == 'continue_skills':
            session['current_field'] = 'skill_skillName'
            session['current_skill'] = {}  # Initialize for new skill
            await query.edit_message_text(
                "Please enter a skill (e.g., 'Python'):"
            )
            return COLLECT_SKILLS

    async def collect_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect skills from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'skill_skillName':
            session['current_skill']['skillName'] = update.message.text
            session['current_field'] = 'skill_proficiency'
            await update.message.reply_text("Please enter your proficiency level for this skill (e.g., 'Beginner', 'Intermediate', 'Advanced'):")
            return COLLECT_SKILLS
        elif current_field == 'skill_proficiency':
            session['current_skill']['proficiency'] = update.message.text
            # Store the completed skill
            session['skills'].append(session['current_skill'].copy())
            session['current_skill'] = {}  # Reset for next entry
            await update.message.reply_text(
                "Skill added. Would you like to add another skill?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_skill")],
                    [InlineKeyboardButton("Continue", callback_data="continue_career")]
                ])
            )
            return COLLECT_SKILLS

    async def handle_skills_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another skill or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "add_another_skill":
            session['current_field'] = 'skill_skillName'
            await query.edit_message_text(
                "Please enter another skill (e.g., 'Python'):"
            )
            return COLLECT_SKILLS
        elif query.data == "continue_career":
            await query.edit_message_text(
                "Please write your career objective/summary:"
            )
            return COLLECT_CAREER_OBJECTIVE

    async def collect_career_objective(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect career objective from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        session['career_objectives'].append({
            'summaryText': update.message.text
        })
        
        await update.message.reply_text(
            "Now please enter a certification or award (e.g., 'AWS Certified Developer'):"
        )
        session['current_field'] = 'cert_certificateName'
        session['current_certification'] = {}  # Initialize for new certification
        return COLLECT_CERTIFICATIONS

    async def collect_certifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect certifications from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'cert_certificateName':
            session['current_certification']['certificateName'] = update.message.text
            session['current_field'] = 'cert_issuer'
            await update.message.reply_text("Please enter the issuer of this certification (e.g., 'Amazon Web Services'):")
            return COLLECT_CERTIFICATIONS
        elif current_field == 'cert_issuer':
            session['current_certification']['issuer'] = update.message.text
            # Store the completed certification
            session['certifications'].append(session['current_certification'].copy())
            session['current_certification'] = {}  # Reset for next entry
            await update.message.reply_text(
                "Certification added. Would you like to add another certification or award?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_cert")],
                    [InlineKeyboardButton("Continue", callback_data="continue_projects")]
                ])
            )
            return COLLECT_CERTIFICATIONS

    async def handle_certifications_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another certification or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "add_another_cert":
            session['current_field'] = 'cert_certificateName'
            await query.edit_message_text(
                "Please enter another certification or award (e.g., 'AWS Certified Developer'):"
            )
            return COLLECT_CERTIFICATIONS
        elif query.data == "continue_projects":
            session['current_field'] = 'project_projectTitle'
            session['current_project'] = {}  # Initialize for new project
            await query.edit_message_text(
                "Please enter the title of a significant project (e.g., 'E-commerce Platform Development'):"
            )
            return COLLECT_PROJECTS

    async def collect_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect projects from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'project_projectTitle':
            session['current_project']['projectTitle'] = update.message.text
            session['current_field'] = 'project_description'
            await update.message.reply_text("Please describe the project, including key details and duration (e.g., 'Developed a web application, 2020-2021'):")
            return COLLECT_PROJECTS
        elif current_field == 'project_description':
            session['current_project']['description'] = update.message.text
            session['current_field'] = 'project_projectLink'
            await update.message.reply_text("Please provide a link to the project (e.g., GitHub repository, live demo, or type 'skip' if none):")
            return COLLECT_PROJECTS
        elif current_field == 'project_projectLink':
            if update.message.text.lower() != 'skip':
                session['current_project']['projectLink'] = update.message.text
            # Store the completed project
            session['projects'].append(session['current_project'].copy())
            session['current_project'] = {}  # Reset for next entry
            await update.message.reply_text(
                "Project added. Would you like to add another project?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_project")],
                    [InlineKeyboardButton("Continue", callback_data="continue_languages")]
                ])
            )
            return COLLECT_PROJECTS

    async def handle_projects_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another project or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "add_another_project":
            session['current_field'] = 'project_projectTitle'
            await query.edit_message_text(
                "Please enter the title of another project (e.g., 'E-commerce Platform Development'):"
            )
            return COLLECT_PROJECTS
        elif query.data == "continue_languages":
            session['current_field'] = 'lang_languageName'
            session['current_language'] = {}  # Initialize for new language
            await query.edit_message_text(
                "Please enter a language you speak (e.g., 'English'):"
            )
            return COLLECT_LANGUAGES

    async def collect_languages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect languages from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        current_field = session['current_field']
        
        if current_field == 'lang_languageName':
            session['current_language']['languageName'] = update.message.text
            session['current_field'] = 'lang_proficiencyLevel'
            await update.message.reply_text("Please enter your proficiency level for this language (e.g., 'Fluent', 'Native', 'Intermediate'):")
            return COLLECT_LANGUAGES
        elif current_field == 'lang_proficiencyLevel':
            session['current_language']['proficiencyLevel'] = update.message.text
            # Store the completed language
            session['languages'].append(session['current_language'].copy())
            session['current_language'] = {}  # Reset for next entry
            await update.message.reply_text(
                "Language added. Would you like to add another language?\n"
                "Please select an option below:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Add Another", callback_data="add_another_language")],
                    [InlineKeyboardButton("Continue", callback_data="continue_activities")]
                ])
            )
            return COLLECT_LANGUAGES

    async def handle_languages_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another language or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "add_another_language":
            session['current_field'] = 'lang_languageName'
            await query.edit_message_text(
                "Please enter another language you speak (e.g., 'English'):"
            )
            return COLLECT_LANGUAGES
        elif query.data == "continue_activities":
            await query.edit_message_text(
                "Please describe any other activities (volunteering, hobbies, etc.):"
            )
            return COLLECT_ACTIVITIES

    async def collect_activities(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect other activities from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        session['activities'].append({
            'activityType': 'Other',
            'description': update.message.text
        })
        
        # Show summary of all collected information
        summary = "Here's a summary of your information:\n\n"
        summary += f"Name: {session['candidate_data'].get('firstName', '')} {session['candidate_data'].get('middleName', '')} {session['candidate_data'].get('lastName', '')}\n"
        summary += f"Contact: {session['candidate_data'].get('phoneNumber', '')} | {session['candidate_data'].get('emailAddress', '')}\n"
        summary += f"Location: {session['candidate_data'].get('city', '')}, {session['candidate_data'].get('country', '')}\n"
        summary += f"Availability: {session['candidate_data'].get('availability', 'To be specified')}\n\n"
        
        summary += "Work Experience:\n"
        for exp in session['work_experiences']:
            summary += f"- {exp.get('jobTitle', 'N/A')} at {exp.get('companyName', 'N/A')}, {exp.get('location', 'N/A')}\n"
            summary += f"  Responsibilities: {exp.get('description', 'N/A')}\n"
        
        summary += "\nEducation:\n"
        for edu in session['education']:
            summary += f"- {edu.get('degreeName', 'N/A')} from {edu.get('institutionName', 'N/A')}\n"
            summary += f"  GPA: {edu.get('gpa', 'N/A')}\n"
            summary += f"  Description: {edu.get('description', 'N/A')}\n"
            summary += f"  Achievements/Honors: {edu.get('achievementsHonors', 'None')}\n"
        
        summary += "\nSkills:\n"
        for skill in session['skills']:
            summary += f"- {skill.get('skillName', 'N/A')} (Proficiency: {skill.get('proficiency', 'N/A')})\n"
        
        summary += "\nCertifications/Awards:\n"
        for cert in session['certifications']:
            summary += f"- {cert.get('certificateName', 'N/A')} from {cert.get('issuer', 'N/A')}\n"
        
        summary += "\nProjects:\n"
        for project in session['projects']:
            summary += f"- {project.get('projectTitle', 'N/A')}\n"
            summary += f"  Description: {project.get('description', 'N/A')}\n"
            if project.get('projectLink'):
                summary += f"  Link: {project.get('projectLink')}\n"
        
        summary += "\nLanguages:\n"
        for lang in session['languages']:
            summary += f"- {lang.get('languageName', 'N/A')} (Proficiency: {lang.get('proficiencyLevel', 'N/A')})\n"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="confirm_yes"),
                InlineKeyboardButton("✏️ Edit", callback_data="edit_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=summary,
            reply_markup=reply_markup
        )
        return CONFIRM_ORDER

    async def confirm_order(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle order confirmation"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "confirm_yes":
            # Create or update candidate
            candidate = Candidate.get_by_telegram_user_id(telegram_id)
            if not candidate:
                candidate = Candidate(
                    uid=str(uuid.uuid4()),
                    telegramUserId=telegram_id,
                    **session['candidate_data']
                )
                candidate.save()
            else:
                # Update existing candidate
                for key, value in session['candidate_data'].items():
                    setattr(candidate, key, value)
                candidate.save()
            
            # Save all subcollections
            for work_exp in session['work_experiences']:
                WorkExperience(
                    candidate_uid=candidate.uid,
                    **work_exp
                ).save()
            
            for edu in session['education']:
                Education(
                    candidate_uid=candidate.uid,
                    **edu
                ).save()
            
            for skill in session['skills']:
                Skill(
                    candidate_uid=candidate.uid,
                    **skill
                ).save()
            
            for career_obj in session['career_objectives']:
                CareerObjective(
                    candidate_uid=candidate.uid,
                    **career_obj
                ).save()
            
            for cert in session['certifications']:
                CertificationAward(
                    candidate_uid=candidate.uid,
                    **cert
                ).save()
            
            for project in session['projects']:
                Project(
                    candidate_uid=candidate.uid,
                    **project
                ).save()
            
            for lang in session['languages']:
                Language(
                    candidate_uid=candidate.uid,
                    **lang
                ).save()
            
            for activity in session['activities']:
                OtherActivity(
                    candidate_uid=candidate.uid,
                    **activity
                ).save()
            
            # Create order
            order = Order(
                id=str(uuid.uuid4()),
                candidateId=candidate.uid,
                telegramUserId=telegram_id,
                status="awaiting_payment"
            )
            order.save()
            
            # Store order ID in session
            session['order_id'] = order.id
            
            # Send payment instructions
            await query.edit_message_text(
                text="Please make a payment of 100 Birr to:\n\n"
                     "Bank: Commercial Bank of Ethiopia\n"
                     "Account: 1000123456789\n"
                     "Name: CV Bot Service\n\n"
                     "After payment, please upload a screenshot of the payment confirmation."
            )
            
            return PAYMENT
        else:
            await query.edit_message_text(
                "Which section would you like to edit?",
                reply_markup=self.get_profile_sections_keyboard()
            )
            return START

    async def edit_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle request to edit information"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        
        if query.data == "edit_personal":
            session['current_field'] = 'firstName'
            await query.edit_message_text("Please enter your first name:")
            return COLLECT_PERSONAL_INFO
        elif query.data == "edit_contact":
            session['current_field'] = 'phoneNumber'
            await query.edit_message_text("Please enter your phone number:")
            return COLLECT_CONTACT_INFO
        elif query.data == "edit_work":
            session['work_experiences'] = []
            session['current_field'] = 'work_jobTitle'
            await query.edit_message_text(
                "Please enter the job title for your most recent position:"
            )
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "edit_education":
            session['education'] = []
            session['current_field'] = 'edu_degreeName'
            session['current_education'] = {}  # Reset for new education
            await query.edit_message_text(
                "Please enter your degree name (e.g., 'Bachelor of Science in Computer Science'):"
            )
            return COLLECT_EDUCATION
        elif query.data == "edit_skills":
            session['skills'] = []
            session['current_field'] = 'skill_skillName'
            session['current_skill'] = {}  # Reset for new skill
            await query.edit_message_text(
                "Please enter a skill (e.g., 'Python'):"
            )
            return COLLECT_SKILLS
        elif query.data == "edit_career":
            session['career_objectives'] = []
            await query.edit_message_text(
                "Please write your career objective/summary:"
            )
            return COLLECT_CAREER_OBJECTIVE
        elif query.data == "edit_certs":
            session['certifications'] = []
            session['current_field'] = 'cert_certificateName'
            session['current_certification'] = {}  # Reset for new certification
            await query.edit_message_text(
                "Please enter a certification or award (e.g., 'AWS Certified Developer'):"
            )
            return COLLECT_CERTIFICATIONS
        elif query.data == "edit_projects":
            session['projects'] = []
            session['current_field'] = 'project_projectTitle'
            session['current_project'] = {}  # Reset for new project
            await query.edit_message_text(
                "Please enter the title of a significant project (e.g., 'E-commerce Platform Development'):"
            )
            return COLLECT_PROJECTS
        elif query.data == "edit_languages":
            session['languages'] = []
            session['current_field'] = 'lang_languageName'
            session['current_language'] = {}  # Reset for new language
            await query.edit_message_text(
                "Please enter a language you speak (e.g., 'English'):"
            )
            return COLLECT_LANGUAGES
        elif query.data == "edit_activities":
            session['activities'] = []
            await query.edit_message_text(
                "Please describe any other activities (volunteering, hobbies, etc.):"
            )
            return COLLECT_ACTIVITIES

    async def handle_payment_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle payment screenshot upload"""
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        
        photo = update.message.photo[-1]  # Get highest resolution photo
        photo_file = await photo.get_file()
        
        # In a real implementation, you would:
        # 1. Upload this to Firebase Storage
        # 2. Get the public URL
        # 3. Update the order with payment_screenshot_url
        order = Order.get_by_id(session['order_id'])
        order.paymentScreenshotUrl = "pending_upload"  # Replace with actual URL
        order.update_status("pending_verification")
        
        await update.message.reply_text(
            "Thank you! Your payment is being processed. "
            "We will notify you once it's verified. "
            "Please come back later."
        )
        
        # Clear user session
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]
        
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the current conversation"""
        telegram_id = str(update.effective_user.id)
        
        # Clear user session
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]
        
        await update.message.reply_text(
            "Operation cancelled. Type /start to begin again."
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message"""
        await update.message.reply_text(
            "Use /start to create or update your CV profile.\n"
            "Use /cancel to stop the current operation."
        )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors and handle connection issues"""
        logger.error(msg="Exception while handling update:", exc_info=context.error)
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred. Please try again or contact support."
            )

def main() -> None:
    """Run the bot"""
    bot = CVBot(telegram_bot_token)
    bot.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()