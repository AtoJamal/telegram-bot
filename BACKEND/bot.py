
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
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_skills)
                ],
                COLLECT_CAREER_OBJECTIVE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_career_objective)
                ],
                COLLECT_CERTIFICATIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_certifications)
                ],
                COLLECT_PROJECTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_projects)
                ],
                COLLECT_LANGUAGES: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_languages)
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
                'candidate_data': {},
                'work_experiences': [],
                'education': [],
                'skills': [],
                'career_objectives': [],
                'certifications': [],
                'projects': [],
                'languages': [],
                'activities': [],
                'current_field': None
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
            session['current_field'] = 'availability'
            await update.message.reply_text(
                "Please describe your availability (e.g., 'Immediately', '2 weeks notice', etc.):"
            )
            return COLLECT_CONTACT_INFO
        elif current_field == 'availability':
            session['candidate_data']['availability'] = update.message.text
            await update.message.reply_text(
                "Now let's collect your professional experience.\n"
                "Please describe your most recent job position (job title, company, duration, responsibilities):"
            )
            return COLLECT_PROFESSIONAL_INFO

    async def collect_professional_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect professional experience from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        # Store the work experience
        session['work_experiences'].append({
            'description': update.message.text,
            'jobTitle': 'To be specified',  # Will parse in a more advanced version
            'companyName': 'To be specified'
        })
        
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
            await query.edit_message_text(
                "Please describe your next job position (job title, company, duration, responsibilities):"
            )
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "continue_education":
            await query.edit_message_text(
                "Please describe your education (degree, institution, year):"
            )
            return COLLECT_EDUCATION

    async def collect_education(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect education information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        session['education'].append({
            'description': update.message.text,
            'degreeName': 'To be specified',  # Will parse in a more advanced version
            'institutionName': 'To be specified'
        })
        
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
        
        if query.data == "add_another_edu":
            await query.edit_message_text(
                "Please describe your next education entry (degree, institution, year):"
            )
            return COLLECT_EDUCATION
        elif query.data == "continue_skills":
            await query.edit_message_text(
                "Please list your skills (comma separated):"
            )
            return COLLECT_SKILLS

    async def collect_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect skills from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        skills = [skill.strip() for skill in update.message.text.split(',')]
        for skill in skills:
            session['skills'].append({
                'skillName': skill,
                'proficiency': 'Intermediate'  # Default, can be updated later
            })
        
        await update.message.reply_text(
            "Skills added. Now please write your career objective/summary:"
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
            "Now please list any certifications or awards you have (comma separated):"
        )
        return COLLECT_CERTIFICATIONS

    async def collect_certifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect certifications from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        certs = [cert.strip() for cert in update.message.text.split(',')]
        for cert in certs:
            session['certifications'].append({
                'certificateName': cert,
                'issuer': 'To be specified'  # Can be updated later
            })
        
        await update.message.reply_text(
            "Now please describe any significant projects you've worked on (one at a time, type 'done' when finished):"
        )
        return COLLECT_PROJECTS

    async def collect_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect projects from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        if update.message.text.lower() != 'done':
            session['projects'].append({
                'projectTitle': 'Project',  # Can be specified in a more advanced version
                'description': update.message.text
            })
            await update.message.reply_text(
                "Project added. Please describe another project or type 'done' to continue."
            )
            return COLLECT_PROJECTS
        else:
            await update.message.reply_text(
                "Now please list languages you speak and your proficiency level (e.g., 'English:Fluent,Amharic:Native'):"
            )
            return COLLECT_LANGUAGES

    async def collect_languages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect languages from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        
        lang_entries = [entry.strip() for entry in update.message.text.split(',')]
        for entry in lang_entries:
            if ':' in entry:
                lang, proficiency = entry.split(':', 1)
                session['languages'].append({
                    'languageName': lang.strip(),
                    'proficiencyLevel': proficiency.strip()
                })
        
        await update.message.reply_text(
            "Finally, please describe any other activities (volunteering, hobbies, etc.):"
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
        summary += f"Location: {session['candidate_data'].get('city', '')}, {session['candidate_data'].get('country', '')}\n\n"
        
        summary += "Work Experience:\n"
        for exp in session['work_experiences']:
            summary += f"- {exp.get('description', '')}\n"
        
        summary += "\nEducation:\n"
        for edu in session['education']:
            summary += f"- {edu.get('description', '')}\n"
        
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
            await query.edit_message_text(
                "Please describe your most recent job position (job title, company, duration, responsibilities):"
            )
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "edit_education":
            session['education'] = []
            await query.edit_message_text(
                "Please describe your education (degree, institution, year):"
            )
            return COLLECT_EDUCATION
        elif query.data == "edit_skills":
            session['skills'] = []
            await query.edit_message_text(
                "Please list your skills (comma separated):"
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
            await query.edit_message_text(
                "Please list any certifications or awards you have (comma separated):"
            )
            return COLLECT_CERTIFICATIONS
        elif query.data == "edit_projects":
            session['projects'] = []
            await query.edit_message_text(
                "Please describe any significant projects you've worked on (one at a time, type 'done' when finished):"
            )
            return COLLECT_PROJECTS
        elif query.data == "edit_languages":
            session['languages'] = []
            await query.edit_message_text(
                "Please list languages you speak and your proficiency level (e.g., 'English:Fluent,Amharic:Native'):"
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
