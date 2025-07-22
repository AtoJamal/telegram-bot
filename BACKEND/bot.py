import logging
import os
import re
from datetime import datetime
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
from telegram.request import HTTPXRequest
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
import firebase_admin
from firebase_admin import credentials, firestore
import django
from typing import Dict, List
import asyncio
import telegram

# Ensure Python version is 3.6 or higher
import sys
if sys.version_info < (3, 6):
    raise RuntimeError("This bot requires Python 3.6 or higher")

PROMPTS = {
    'en': {
        'welcome_new': "Welcome to the CV Bot! Let's create your professional CV.\n\nPlease enter your first name:",
        'welcome_back': "Welcome back! You already have a profile. Would you like to update your information or create a new CV?",
        'select_language': "Please select your preferred language:\nእባክዎ የሚፈልጉትን ቋንቋ ይምረጡ፡",
        'update_profile': "Update Profile",
        'new_cv': "Create New CV",
        'edit_section': "Which section would you like to update?",
        'personal_info': "Personal Info",
        'contact_info': "Contact Info",
        'work_experience': "Work Experience",
        'education': "Education",
        'skills': "Skills",
        'career_objective': "Career Objective",
        'certifications': "Certifications",
        'projects': "Projects",
        'languages': "Languages",
        'other_activities': "Other Activities",
        'first_name': "Please enter your first name:",
        'middle_name': "Great! Now please enter your middle name (if any):",
        'last_name': "Now please enter your last name:",
        'phone_number': "Now let's collect your contact information.\nPlease enter your phone number (e.g., +251911223344):",
        'email_address': "Please enter your email address:",
        'linkedin_profile': "Please enter your LinkedIn profile URL (if any, or type 'skip'):",
        'city': "What city do you currently live in?",
        'country': "Please enter your country:",
        'job_title': "Let's capture your professional experience. What was the job title of your most recent role?(e.g., Software Engineer) If you're a recent graduate or have limited work history, please provide the job title for your most relevant internship(e.g., Networking Intern):",
        'company_name': "Please enter the company name for this job position. If it was an internship, you can also list the university or institution where it took place (e.g.,Microsoft, Ethio Telecom, University of Gondar ).",
        'work_location': "Where was this job or internship located? (e.g., 'Addis Ababa, Ethiopia', 'Remote', 'Nairobi, Kenya', 'New York, USA')",
        'work_description': "Now, let's detail your responsibilities and the timeframe for this job position or internship. Briefly explain what you did, your key accomplishments, and the start and end dates \n\n(e.g., 'Conducted lab experiments, prepared reports for senior scientists (Sept 2020 - May 2021)'",
        'add_another_work': "Work experience added. Would you like to add another position?\nPlease select an option below:",
        'add_another': "Add Another",
        'continue': "Continue",
        'degree_name': "What's your degree name? (e.g., 'Bachelor of Science in Computer Science', 'Master of Business Administration', 'PhD in Biology')",
        'institution_name': "Please provide the name of the university or institution where you obtained this degree(e.g,  'Mekelle University').",
        'gpa': "What was your GPA for this degree? (e.g., '3.5/4.0', '4.0/5.0', or type 'skip' if you prefer not to include it)",
        'edu_description': "Please tell us the start and end dates for this degree(e.g., 'Sept 2018 - June 2022', '2016 - 2019', 'Aug 2020 - Present').",
        'achievements_honors': "Please list any achievements or honors (e.g., 'Dean's List', or type 'skip' if none):",
        'add_another_edu': "Degree added. Would you like to add another degree entry?\nPlease select an option below:",
        'skill_name': "What's a key skill you gained from your degree? This could be a technical skill, a research method (e.g., 'Graphic Design' , 'Data Analysis')",
        'skill_proficiency': "Please enter your proficiency level for this skill (e.g., 'Beginner', 'Intermediate', 'Advanced'):",
        'add_another_skill': "Skill added. Would you like to add another skill?\nPlease select an option below:",
        'career_summary': "Please tell us the name of your high school and its location. Include the city and country (e.g., \n'Menelik II Secondary School, Addis Ababa, Ethiopia'.",
        'certificate_name': "Have you earned any certifications or awards? Please list one here. This could be a professional certification, an academic award, or a recognition for a specific skill.(e.g.,  'AWS Certified Developer'):",
        'issuer': "Please tell us the name of the organization or institution that issued this certification (e.g., \n'Amazon Web Services').",
        'add_another_cert': "Certification added. Would you like to add another certification?\nPlease select an option below:",
        'project_title': "Tell us about a key research, project, or final year university project you completed. What was its title?(e.g.,  'Study on Renewable Energy Integration in Rural Areas')",
        'project_description': "Now, give us a detailed description of your research, project, or final year project/research. Focus on your contributions, methodologies used, outcomes, and the start and end dates(e.g., \nDeveloped a web application using Python and Django, managing database integration and user authentication (Sept 2022 - April 2023)'",
        'project_link': "Please provide a link to the project/research (e.g., GitHub repository, live demo, google drive, or type 'skip' if none):",
        'add_another_project': "Project added. Would you like to add another project?\nPlease select an option below:",
        'language_name': "Please enter a language you speak, one at a time (e.g., 'Amharic','English'):",
        'language_proficiency': "Please enter your proficiency level for this language (e.g., 'Fluent', 'Native', 'Intermediate'):",
        'add_another_language': "Language added. Would you like to add another language?\nPlease select an option below:",
        'activities': "Please describe any other activities (volunteering, hobbies, etc.):",
        'summary_header': "Here's a summary of your information:\n\n",
        'summary_name': "Name",
        'summary_contact': "Contact",
        'summary_location': "Location",
        'summary_availability': "Availability",
        'summary_work': "Work Experience",
        'summary_responsibilities': "Responsibilities",
        'summary_education': "Education",
        'summary_gpa': "GPA",
        'summary_edu_description': "Description",
        'summary_achievements': "Achievements/Honors",
        'summary_skills': "Skills",
        'summary_proficiency': "Proficiency",
        'summary_certifications': "Certifications/Awards",
        'summary_projects': "Projects",
        'summary_project_link': "Link",
        'summary_languages': "Languages",
        'confirm': "✅ Confirm",
        'edit': "✏️ Edit",
        'payment_instructions': "Please make a payment of 100 Birr to:\n\nBank: Commercial Bank of Ethiopia\nAccount: 1000649561382\nName: Jemal Hussen Hassen\n\nAfter payment, please upload a screenshot of the payment confirmation.",
        'payment_confirmation': "Thank you! Your payment is being processed. We will notify you once it's verified. Please come back later.",
        'cancel_message': "Operation cancelled. Type /start to begin again.",
        'help_message': "Use /start to create or update your CV profile.\nUse /cancel to stop the current operation.",
        'error_message': "An error occurred. Please try again or contact support.",
        'profile_image_prompt': "Please upload your profile image as a photo or file (JPG, JPEG, PNG, PDF only, max 5 MB). Type 'skip' to proceed without an image. Note: DOC, DOCX, and similar formats are not supported.",
        'profile_image_success': "Profile image uploaded successfully. Proceed to professional information?",
        'invalid_file_type': "Invalid file type. Please upload a JPG, JPEG, PNG, or PDF file. DOC, DOCX, and similar formats are not supported.",
        'file_too_large': "File too large. Please upload an image or file under 5 MB.",
        'profile_image_skip': "Profile image skipped. Proceed to professional information?",
        'continue_professional': "Continue to Professional Info",
        'payment_instructions': "Please make a payment of 100 Birr to:\n\nBank: Commercial Bank of Ethiopia\nAccount: 1000649561382\nName: Jemal Hussen Hassen\n\nAfter payment, please upload a screenshot of the payment confirmation (JPG, JPEG, PNG, PDF only, max 5 MB). Note: DOC, DOCX, and similar formats are not supported.",
        'payment_screenshot_success': "Payment screenshot uploaded successfully. Awaiting verification.",
        'payment_verified': "Your payment has been verified! Your CV is being processed.",
        'payment_rejected': "Your payment was rejected: {reason}. Please start a new order with /start.",
        'payment_approved': "Your payment has been approved! Your CV is being processed and will be delivered soon.",
        'reject_reason_prompt': "Please provide the reason for rejecting the payment.",
        

    },
    'am': {
        'welcome_new': "ወደ CV ቦት እንኳን በደህና መጡ! የፕሮፌሽናል ሲቪዎን እንፍጠር።\n\nእባክዎ የመጀመሪያ ስምዎን ያስገቡ፡",
        'welcome_back': "እንኳን ተመልሰው መጡ! ቀድሞ ፕሮፋይል አለዎት። መረጃዎን ማዘመን ወይም አዲስ ሲቪ መፍጠር ይፈልጋሉ?",
        'select_language': "እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ፡\nPlease select your preferred language:",
        'update_profile': "ፕሮፋይል አዘምን",
        'new_cv': "አዲስ ሲቪ ፍጠር",
        'edit_section': "የትኛውን ክፍል ማዘመን ይፈልጋሉ?",
        'personal_info': "የግል መረጃ",
        'contact_info': "የእውቂያ መረጃ",
        'work_experience': "የሥራ ልምድ",
        'education': "ትምህርት",
        'skills': "ችሎታዎች",
        'career_objective': "የሙያ ግብ",
        'certifications': "ሰርቲፊኬቶች/ሽልማቶች",
        'projects': "ፕሮጀክቶች",
        'languages': "ቋንቋዎች",
        'other_activities': "ሌሎች እንቅስቃሴዎች",
        'first_name': "እባክዎ የመጀመሪያ ስምዎን ያስገቡ፡",
        'middle_name': "በጣም ጥሩ! አሁን የአባት ስምዎን (ካለ) ያስገቡ፡",
        'last_name': "አሁን የአያት ስምዎን ያስገቡ፡",
        'phone_number': "አሁን የእውቂያ መረጃዎን እንሰብስብ።\nእባክዎ የስልክ ቁጥርዎን ያስገቡ (ለምሳሌ፡ +251911223344):",
        'email_address': "እባክዎ የኢሜይል አድራሻዎን ያስገቡ፡",
        'linkedin_profile': "እባክዎ የሊንክዲን ፕሮፋይል ዩአርኤልዎን ያስገቡ (ካለ፣ ወይም 'skip' ይፃፉ):",
        'city': "እባክዎ የሚኖሩበትን ከተማ ያስገቡ፡",
        'country': "እባክዎ አገርዎን ያስገቡ፡",
        'job_title': "ሙያዊ ልምድዎን እንመዝግብ። የቅርብ ጊዜ የሥራ ቦታዎ የሥራ መደብ (Job Title) ምን ነበር?(e.g., Software Engineer) የቅርብ ጊዜ ተመራቂ ከሆኑ ወይም ብዙ የሥራ ልምድ ከሌለዎት፣ እባክዎ በጣም ተዛማጅ የሆነውን የልምምድ ስራዎ internship(e.g., Networking Intern):",
        'company_name': "እባክዎ ለዚህ የስራ ቦታ የኩባንያውን ስም ያስገቡ። ልምምድ (internship) ከሆነ፣ የተካሄደበትን ዩኒቨርሲቲ ወይም ተቋም መጥቀስ ይችላሉ (e.g.,Microsoft, Ethio Telecom, University of Gondar (for an internship)).",
        'work_location': "ይህ ስራ ወይም (internship) የት ነበር የሚገኘው?(ለምሳሌ፡ ከተማ፣ አገር):",
        'work_description': "አሁን፣ የዚህን ስራ  ወይም የልምምድ ስራ (internship) ኃላፊነቶችዎን እና የጊዜ ገደቡን በዝርዝር እንመልከት። ምን እንዳደረጉ፣ ዋና ዋና ስኬቶችዎን፣ እና የጀመሩበትንና የጨረሱበትን ቀን በአጭሩ ያብራሩ። \n\n(e.g. 'የቤተ ሙከራ ሙከራዎችን አከናውኛለሁ፣ ለአዛውንት ሳይንቲስቶች ሪፖርቶችን አዘጋጅቻለሁ (መስከረም 2020 - ግንቦት 2021)'.",
        'add_another_work': "የሥራ ልምድ ታክሏል። ሌላ ቦታ መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'add_another': "ሌላ ጨምር",
        'continue': "ቀጥል",
        'degree_name': "የዲግሪዎ ስም ምንድን ነው? (ለምሳሌ፦ 'የኮምፒውተር ሳይንስ ባችለር ኦፍ ሳይንስ', 'ማስተር ኦፍ ቢዝነስ አድሚኒስትሬሽን', 'የባዮሎጂ ፒኤችዲ'):",
        'institution_name': "እባክዎ ይህንን ዲግሪ ያገኙበትን የዩኒቨርሲቲ ወይም የተቋም ስም ያስገቡ(e.g.,  'መቀሌ ዩኒቨርሲቲ'):",
        'gpa': "ለዚህ ዲግሪ የነበረው GPA ስንት ነበር? (ለምሳሌ፦ '3.5/4.0', '4.0/5.0'፣ ወይም ማካተት ካልፈለጉ 'skip' ብለው ይጻፉ)",
        'edu_description': "እባክዎ የዚህን ዲግሪ የመጀመሪያ እና የመጨረሻ ቀናት ይንገሩን (e.g., 'Sept 2018 - June 2022', '2016 - 2019', 'Aug 2020 - Present')",
        'achievements_honors': "እባክዎ ማንኛውንም ስኬቶች ወይም ክብር ይዘርዝሩ (ለምሳሌ፡ 'የዲን ዝርዝር'፣ ወይም 'skip' ይፃፉ ከሌለ):",
        'add_another_edu': "ዲግሪ ታክሏል። ሌላ ዲግሪ መግቢያ መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'skill_name': "ከዲግሪዎ ያገኙት ቁልፍ ክህሎት ምንድን ነው? ይህ ቴክኒካዊ ክህሎት፣ የምርምር ዘዴ (e.g., 'Graphic Design' , 'Data Analysis')",
        'skill_proficiency': "እባክዎ ለዚህ ችሎታ የብቃት ደረጃዎን ያስገቡ (ለምሳሌ፡ 'ጀማሪ'፣ 'መካከለኛ'፣ 'ከፍተኛ'):",
        'add_another_skill': "ችሎታ ታክሏል። ሌላ ችሎታ መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'career_summary': "እባክዎ የሁለተኛ ደረጃ ትምህርት ቤትዎን ስም እና የሚገኝበትን ቦታ ይንገሩን። ከተማውን እና ሀገሩን ያካትቱ(e.g., \n'Menelik II Secondary School, Addis Ababa, Ethiopia'.",
        'certificate_name': "ማናቸውም ሰርተፍኬቶች ወይም ሽልማቶች አግኝተዋል? እባክዎ አንዱን እዚህ ይዘርዝሩ። ይህ ሙያዊ ሰርተፍኬት፣ አካዳሚያዊ ሽልማት ወይም ለአንድ የተወሰነ ክህሎት እውቅና ሊሆን ይችላል (e.g.,'AWS Certified Developer'):",
        'issuer': "እባክዎ ይህንን ሰርተፍኬት ወይም ሽልማት የሰጠው ድርጅት ወይም ተቋም ስም ያስገቡ(e.g, \n'Amazon Web Services'):",
        'add_another_cert': "ሰርቲፊኬት ታክሏል። ሌላ ሰርቲፊኬት መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'project_title': "ስለ አንድ ቁልፍ ፕሮጀክት፣ ጥናት ወይም የመጨረሻ ዓመት የዩኒቨርሲቲ ፕሮጀክት ይንገሩን። ርዕሱ ምን ነበር?(e.g 'Study on Renewable Energy Integration in Rural Areas')",
        'project_description': "አሁን፣ ስለ ፕሮጀክትዎ፣ ጥናትዎ ወይም የመጨረሻ ዓመት የዩኒቨርሲቲ ፕሮጀክትዎ ዝርዝር መግለጫ ይስጡን። በእርስዎ አስተዋፅዖዎች፣ ጥቅም ላይ የዋሉ ዘዴዎች፣ ውጤቶች እና የጀመሩበትና የጨረሱበት ቀናት ላይ ያተኩሩ። (e.g., 'Developed a web application using Python and Django, managing database integration and user authentication (Sept 2022 - April 2023)', ).",
        'project_link': "እባክዎ የሪሰርቹን/የፕሮጀክቱን አገናኝ(link) ያቅርቡ (e.g., GitHub repository, live demo, or type 'skip' if none):",
        'add_another_project': "ፕሮጀክት/ሪሰርች ታክሏል። ሌላ ፕሮጀክት/ሪሰርች መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'language_name': "እባክዎ የሚናገሩትን ቋንቋ ያስገቡ (e.g., 'Amahric', 'English'):",
        'language_proficiency': "እባክዎ ለዚህ ቋንቋ የብቃት ደረጃዎን ያስገቡ (ለምሳሌ፡ 'Fluent'፣ 'Native'፣ 'Intermediate'):",
        'add_another_language': "ቋንቋ ታክሏል። ሌላ ቋንቋ መጨመር ይፈልጋሉ?\nእባክዎ ከታች አማራጭ ይምረጡ፡",
        'activities': "እባክዎ ሌሎች እንቅስቃሴዎችን (በጎ ፈቃደኝነት፣ የትርፍ ጊዜ ማሳለፊያዎች፣ ወዘተ) ይግለፁ፡",
        'summary_header': "የመረጃዎ ማጠቃለያ ይኸው፡\n\n",
        'summary_name': "ስም",
        'summary_contact': "እውቂያ",
        'summary_location': "መገኛ ቦታ",
        'summary_availability': "የሚገኝነት",
        'summary_work': "የሥራ ልምድ",
        'summary_responsibilities': "ኃላፊነቶች",
        'summary_education': "ትምህርት",
        'summary_gpa': "ጂፒኤ",
        'summary_edu_description': "መግለጫ",
        'summary_achievements': "ስኬቶች/ክብር",
        'summary_skills': "ችሎታዎች",
        'summary_proficiency': "ብቃት",
        'summary_certifications': "ሰርቲፊኬቶች/ሽልማቶች",
        'summary_projects': "ፕሮጀክቶች",
        'summary_project_link': "አገናኝ",
        'summary_languages': "ቋንቋዎች",
        'confirm': "✅ አረጋግጥ",
        'edit': "✏️ አርም",
        'payment_instructions': "እባክዎ 100 ብር ይክፈሉ፡\n\nባንክ፡ የኢትዮጵያ ንግድ ባንክ\nመለያ፡ 1000649561382\nስም፡ Jemal Hussen Hassen አገልግሎት\n\nክፍያ ከፈጸሙ በኋላ፣ እባክዎ የክፍያ ማረጋገጫ ፎቶ ይስቀሉ።",
        'payment_confirmation': "እናመሰግናለን! ክፍያዎ በሂደት ላይ ነው። ከተረጋገጠ በኋላ እናሳውቅዎታለን። እባክዎ ቆይተው ይመለሱ።",
        'cancel_message': "ክወናው ተሰርዟል። እንደገና ለመጀመር /start ይፃፉ።",
        'help_message': "ሲቪ ፕሮፋይልዎን ለመፍጠር ወይም ለማዘመን /start ይጠቀሙ።\nክወናውን ለማቆም /cancel ይጠቀሙ።",
        'error_message': "ስህተት ተከስቷል። እባክዎ እንደገና ይሞክሩ ወይም ድጋፍ ያግኙ።",
        'profile_image_prompt': "እባክዎ የፕሮፋይል ምስልዎን እንደ ፎቶ ወይም ፋይል (JPG, JPEG, PNG, PDF ብቻ፣ ከፍተኛ 5 ሜባ) ይስቀሉ። ያለ ምስል ለመቀጠል 'skip' ይፃፉ። ማሳሰቢያ፡ DOC, DOCX እና ተመሳሳይ ቅርጸቶች አይደገፉም።",
        'profile_image_success': "የፕሮፋይል ምስል በተሳካ ሁኔታ ተሰቅሏል። ወደ ሙያዊ መረጃ መቀጠል?",
        'invalid_file_type': "የተሳሳተ የፋይል አይነት። እባክዎ JPG, JPEG, PNG ወይም PDF ፋይል ይስቀሉ። DOC, DOCX እና ተመሳሳይ ቅርጸቶች አይደገፉም።",
        'file_too_large': "ፋይሉ በጣም ትልቅ ነው። እባክዎ ከ5 ሜባ በታች ያለ ምስል ወይም ፋይል ይስቀሉ።",
        'profile_image_skip': "የፕሮፋይል ምስል ተዘልሏል። ወደ ሙያዊ መረጃ መቀጠል?",
        'continue_professional': "ወደ ሙያዊ መረጃ ቀጥል",
        'payment_instructions': "እባክዎ 100 ብር ይክፈሉ፡\n\nባንክ፡ የኢትዮጵያ ንግድ ባንክ\nመለያ፡ 1000649561382\nስም፡ Jemal Hussen Hassen\n\nክፍያ ከፈጸሙ በኋላ፣ እባክዎ የክፍያ ማረጋገጫ ፎቶ (JPG, JPEG, PNG, PDF ብቻ፣ ከፍተኛ 5 ሜባ) ይስቀሉ። ማሳሰቢያ፡ DOC, DOCX እና ተመሳሳይ ቅርጸቶች አይደገፉም።",
        'payment_screenshot_success': "የክፍያ ማረጋገጫ ፎቶ በተሳካ ሁኔታ ተሰቅሏል። ማረጋገጫ በመጠበቅ ላይ።",
        'payment_verified': "ክፍያዎ ተረጋግጧል! ሲቪዎ በመዘጋጀት ላይ ነው።",
        'payment_rejected': "ክፍያዎ ተቀባይነት አላገኘም፡ {reason}። እባክዎ ከ/start ጋር አዲስ ትዕዛዝ ይጀምሩ።",
        'payment_approved': "ክፍያዎ ተፈቅዷል! ሲቪዎ በመዘጋጀት ላይ ነው እና በቅርቡ ይደርሰዎታል።",
        'reject_reason_prompt': "እባክዎ ክፍያውን ለመከልከል ምክንያቱን ያቅርቡ።",
    }
}


# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cvbot_backend.settings')
django.setup()

# Load environment variables
load_dotenv()

# Get Telegram bot token and private channel ID
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
private_channel_id = os.getenv('PRIVATE_CHANNEL_ID')

# Initialize Firebase only if not already initialized
logger = logging.getLogger(__name__)
logger.info("Attempting to load Firebase credentials from: ./firebaseapikey.json")
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("./firebaseapikey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
logger.info("Firestore client obtained.")

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Define conversation states
(
    SELECT_LANGUAGE,
    START,
    COLLECT_PERSONAL_INFO,
    COLLECT_CONTACT_INFO,
    COLLECT_PROFILE_IMAGE,
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
) = range(15)

class CVBot:
    def __init__(self, token: str):
        # Configure HTTPXRequest with supported parameters
        request = HTTPXRequest(
            connection_pool_size=10,
            connect_timeout=60.0,
            read_timeout=60.0,
            write_timeout=60.0
        )
        logger.info("Initializing Application with token")
        self.application = Application.builder().token(token).request(request).post_init(self.post_init).build()
        self.user_sessions: Dict[str, Dict] = {}  # Dictionary to store user-specific data
        self.user_cache: Dict[str, int] = {}  # Cache for username to user_id mapping
        self.setup_handlers()
        logger.info("CVBot initialized successfully")

    async def post_init(self, application: Application) -> None:
        """Called after application initialization to start background tasks"""
        self.start_background_tasks()

    def setup_handlers(self) -> None:
        """Set up conversation handlers for the bot"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                SELECT_LANGUAGE: [
                    CallbackQueryHandler(self.select_language, pattern="^lang_")
                ],
                START: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.start_collecting_info),
                    CallbackQueryHandler(self.start_collecting_info, pattern="^(update_profile|new_cv)$")
                ],
                COLLECT_PERSONAL_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_personal_info)
                ],
                COLLECT_CONTACT_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_contact_info)
                ],
                COLLECT_PROFILE_IMAGE: [
                    MessageHandler(
                        filters.PHOTO | filters.Document.IMAGE | filters.Document.MimeType("application/pdf") | filters.TEXT,
                        self.collect_profile_image
                    ),
                    CallbackQueryHandler(self.handle_profile_image_choice, pattern="^continue_professional$")
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
                    MessageHandler(
                        filters.PHOTO | filters.Document.IMAGE | filters.Document.MimeType("application/pdf"),
                        self.handle_payment_screenshot
                    )
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            per_message=False
        )
        
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_admin_response, pattern="^(approve_|reject_)"))
        self.application.add_handler(MessageHandler(filters.Chat(int(private_channel_id)) & filters.REPLY, self.handle_admin_reply))
        self.application.add_handler(MessageHandler(filters.Chat(int(private_channel_id)) & (filters.PHOTO | filters.Document.ALL) & ~filters.REPLY, self.handle_file_upload))
        self.application.add_handler(MessageHandler(filters.Chat(int(private_channel_id)) & ~filters.REPLY & ~(filters.PHOTO | filters.Document.ALL), self.ignore_non_reply_messages))
        self.application.add_handler(MessageHandler(filters.ChatType.PRIVATE, self.cache_user_info))
        self.application.add_error_handler(self.error_handler)

    def start_background_tasks(self) -> None:
        """Start background tasks for polling order status changes"""
        self.application.create_task(self.poll_order_status_changes())

    async def poll_order_status_changes(self) -> None:
        """Poll Firestore for order status changes and send notifications"""
        while True:
            try:
                for telegram_id, session in list(self.user_sessions.items()):
                    if 'order_id' not in session or 'chat_id' not in session:
                        logger.debug(f"Skipping session for telegram_id {telegram_id}: missing order_id or chat_id")
                        continue
                    order = Order.get_by_id(session['order_id'])
                    if not order:
                        logger.debug(f"Order {session['order_id']} not found for telegram_id {telegram_id}")
                        continue
                    if order.status in ['verified', 'rejected'] and not session.get('notified', False):
                        if order.status == 'verified':
                            await self.application.bot.send_message(
                                chat_id=session['chat_id'],
                                text=self.get_prompt(session, 'payment_verified')
                            )
                            logger.info(f"Sent payment verified notification to chat_id {session['chat_id']} for order {session['order_id']}")
                        elif order.status == 'rejected':
                            reason = order.statusDetails or "No reason provided"
                            await self.application.bot.send_message(
                                chat_id=session['chat_id'],
                                text=self.get_prompt(session, 'payment_rejected').format(reason=reason)
                            )
                            logger.info(f"Sent payment rejected notification to chat_id {session['chat_id']} for order {session['order_id']}")
                        session['notified'] = True
            except Exception as e:
                logger.error(f"Error in poll_order_status_changes: {str(e)}")
            await asyncio.sleep(300)  # Poll every 5 minutes

    async def cache_user_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Cache user information when they interact with the bot"""
        if update.effective_user and update.effective_user.username:
            username = update.effective_user.username.lower()
            user_id = update.effective_user.id
            self.user_cache[username] = user_id
            logger.debug(f"Cached user: @{username} -> {user_id}")

    async def resolve_username_to_id(self, username: str, context: ContextTypes.DEFAULT_TYPE) -> int:
        """
        Try to resolve a username to a user ID using multiple methods
        """
        # Remove @ if present and convert to lowercase for consistency
        clean_username = username.replace('@', '').lower()
        full_username = f"@{clean_username}"
        
        logger.info(f"🔍 Attempting to resolve username: {full_username}")
        
        # Method 1: Check cache first
        if clean_username in self.user_cache:
            logger.info(f"✅ Found {full_username} in cache: {self.user_cache[clean_username]}")
            return self.user_cache[clean_username]
        
        # Method 2: Try to get chat info directly (works for public usernames and users who have interacted)
        try:
            logger.info(f"🔄 Trying get_chat for {full_username}")
            chat = await context.bot.get_chat(full_username)  # Use full username with @
            if chat.type == 'private':
                user_id = chat.id
                self.user_cache[clean_username] = user_id
                logger.info(f"✅ Resolved {full_username} via get_chat: {user_id}")
                return user_id
            else:
                logger.warning(f"❌ {full_username} is not a private chat (type: {chat.type})")
        except telegram.error.BadRequest as e:
            logger.warning(f"❌ Could not resolve {full_username} via get_chat: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error with get_chat for {full_username}: {str(e)}")
        
        # Method 3: Check if user is in the private channel (admin only feature)
        try:
            logger.info(f"🔄 Checking channel administrators for {full_username}")
            administrators = await context.bot.get_chat_administrators(private_channel_id)
            for admin in administrators:
                if admin.user.username and admin.user.username.lower() == clean_username:
                    user_id = admin.user.id
                    self.user_cache[clean_username] = user_id
                    logger.info(f"✅ Found {full_username} as channel admin: {user_id}")
                    return user_id
        except Exception as e:
            logger.warning(f"❌ Could not check channel administrators: {str(e)}")
        
        # Method 4: Try to get channel members (this usually fails for channels, but worth trying)
        try:
            logger.info(f"🔄 Trying to get chat member info for {full_username}")
            member = await context.bot.get_chat_member(private_channel_id, full_username)
            if member and member.user:
                user_id = member.user.id
                self.user_cache[clean_username] = user_id
                logger.info(f"✅ Found {full_username} as channel member: {user_id}")
                return user_id
        except Exception as e:
            logger.warning(f"❌ Could not get chat member info: {str(e)}")
        
        # If all methods fail, provide detailed error message
        logger.error(f"❌ Could not resolve username {full_username} using any method")
        raise ValueError(f"Could not resolve username {full_username} to user ID")

    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle file uploads in the private channel and resend to specified user"""
        logger.info("=== FILE UPLOAD HANDLER TRIGGERED ===")
        message = update.message or update.channel_post
        if not message or not message.chat_id:
            logger.warning("No message or chat_id in update")
            return

        if str(message.chat_id) != str(private_channel_id):
            logger.warning(f"Message from wrong chat: {message.chat_id}, expected: {private_channel_id}")
            return

        has_photo = bool(message.photo)
        has_document = bool(message.document)
        logger.info(f"Content check - Photo: {has_photo}, Document: {has_document}")
        
        if not (has_photo or has_document):
            logger.warning("No photo or document found in message")
            await message.reply_text("❌ No photo or document found. Please upload a file with a username.")
            return

        message_text = message.caption if message.caption else message.text
        logger.info(f"Message text/caption: '{message_text}'")
        if not message_text:
            logger.debug("No text or caption provided with file")
            await message.reply_text("Please include a username (e.g., @username) with the file.")
            return

        username_match = re.search(r'@?(\w+)', message_text)
        if not username_match:
            logger.debug(f"No valid username found in message: {message_text}")
            await message.reply_text("No valid username found. Please include a username (with or without '@').")
            return

        username = username_match.group(1)
        full_username = f"@{username}"
        logger.info(f"Processing file upload for username: {full_username}")

        try:
            target_user_id = await self.resolve_username_to_id(username, context)
            logger.info(f"Resolved {full_username} to user ID: {target_user_id}")
            
        except ValueError as e:
            logger.error(f"Username resolution failed: {str(e)}")
            await message.reply_text(
                f"Could not find user {full_username}. "
                f"Please ensure:\n"
                f"1. The username is correct\n"
                f"2. The user has started a conversation with this bot\n"
                f"3. The username is public"
            )
            return
        except Exception as e:
            logger.error(f"Unexpected error resolving username {full_username}: {str(e)}")
            await message.reply_text(f"Error finding user {full_username}. Please try again.")
            return

        try:
            if message.photo:
                photo = message.photo[-1]
                sent_message = await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=photo.file_id,
                    caption=None
                )
                logger.info(f"Photo sent to user ID {target_user_id}")
                
            elif message.document:
                document = message.document
                sent_message = await context.bot.send_document(
                    chat_id=target_user_id,
                    document=document.file_id,
                    caption=None
                )
                logger.info(f"Document sent to user ID {target_user_id}")
                
            else:
                logger.debug("No photo or document found in message")
                await message.reply_text("No valid file (photo or document) found.")
                return

            file_type = "photo" if message.photo else "document"
            await message.reply_text(
                f"✅ {file_type.capitalize()} sent to {full_username} successfully."
            )

        except telegram.error.Forbidden:
            logger.error(f"Bot blocked by user ID {target_user_id}")
            await message.reply_text(
                f"❌ Failed to send file to {full_username}. "
                f"The user has blocked this bot or hasn't started a conversation with it."
            )
        except telegram.error.BadRequest as e:
            logger.error(f"Bad request when sending to user ID {target_user_id}: {str(e)}")
            await message.reply_text(
                f"❌ Failed to send file to {full_username}. "
                f"Error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error sending file to user ID {target_user_id}: {str(e)}")
            await message.reply_text(
                f"❌ An unexpected error occurred while sending the file to {full_username}."
            )

    def get_user_session(self, user_id: str) -> dict:
        """Get or create a user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'language': 'en',
                'candidate_data': {'availability': 'To be specified'},
                'work_experiences': [],
                'education': [],
                'skills': [],
                'career_objectives': [],
                'certifications': [],
                'projects': [],
                'languages': [],
                'activities': [],
                'current_field': None,
                'current_work_experience': {},
                'current_education': {},
                'current_skill': {},
                'current_certification': {},
                'current_project': {},
                'current_language': {}
            }
        return self.user_sessions[user_id]

    def get_prompt(self, session: dict, key: str) -> str:
        """Get the appropriate prompt based on the user's language"""
        return PROMPTS[session['language']][key]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send welcome message and prompt for language selection"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        
        await update.message.reply_text(
            self.get_prompt(session, 'select_language'),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("English", callback_data="lang_en")],
                [InlineKeyboardButton("አማርኛ (Amharic)", callback_data="lang_am")]
            ])
        )
        return SELECT_LANGUAGE

    async def select_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle language selection"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        session['language'] = query.data.split('_')[1]
        
        candidate = Candidate.get_by_telegram_user_id(telegram_id)
        if candidate:
            await query.edit_message_text(
                self.get_prompt(session, 'welcome_back'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'update_profile'), callback_data="update_profile")],
                    [InlineKeyboardButton(self.get_prompt(session, 'new_cv'), callback_data="new_cv")]
                ])
            )
            return START
        else:
            await query.edit_message_text(
                self.get_prompt(session, 'welcome_new')
            )
            session['current_field'] = 'firstName'
            return COLLECT_PERSONAL_INFO

    async def start_collecting_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle user choice to update profile or create new CV"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "update_profile":
            candidate = Candidate.get_by_telegram_user_id(telegram_id)
            session['candidate_data'] = candidate.to_dict()
            session['candidate_data']['availability'] = session['candidate_data'].get('availability', 'To be specified')
            
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
                self.get_prompt(session, 'edit_section'),
                reply_markup=self.get_profile_sections_keyboard(session)
            )
            return START
        else:
            await query.edit_message_text(
                self.get_prompt(session, 'welcome_new')
            )
            session['current_field'] = 'firstName'
            return COLLECT_PERSONAL_INFO

    def get_profile_sections_keyboard(self, session: dict) -> InlineKeyboardMarkup:
        """Create keyboard for profile sections in the selected language"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(self.get_prompt(session, 'personal_info'), callback_data="edit_personal")],
            [InlineKeyboardButton(self.get_prompt(session, 'contact_info'), callback_data="edit_contact")],
            [InlineKeyboardButton(self.get_prompt(session, 'profile_image'), callback_data="edit_profile_image")],
            [InlineKeyboardButton(self.get_prompt(session, 'work_experience'), callback_data="edit_work")],
            [InlineKeyboardButton(self.get_prompt(session, 'education'), callback_data="edit_education")],
            [InlineKeyboardButton(self.get_prompt(session, 'skills'), callback_data="edit_skills")],
            [InlineKeyboardButton(self.get_prompt(session, 'career_objective'), callback_data="edit_career")],
            [InlineKeyboardButton(self.get_prompt(session, 'certifications'), callback_data="edit_certs")],
            [InlineKeyboardButton(self.get_prompt(session, 'projects'), callback_data="edit_projects")],
            [InlineKeyboardButton(self.get_prompt(session, 'languages'), callback_data="edit_languages")],
            [InlineKeyboardButton(self.get_prompt(session, 'other_activities'), callback_data="edit_activities")]
        ])

    async def collect_personal_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect personal information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'firstName':
            session['candidate_data']['firstName'] = update.message.text
            session['current_field'] = 'middleName'
            await update.message.reply_text(self.get_prompt(session, 'middle_name'))
            return COLLECT_PERSONAL_INFO
        elif current_field == 'middleName':
            session['candidate_data']['middleName'] = update.message.text
            session['current_field'] = 'lastName'
            await update.message.reply_text(self.get_prompt(session, 'last_name'))
            return COLLECT_PERSONAL_INFO
        elif current_field == 'lastName':
            session['candidate_data']['lastName'] = update.message.text
            session['current_field'] = 'phoneNumber'
            await update.message.reply_text(self.get_prompt(session, 'phone_number'))
            return COLLECT_CONTACT_INFO

    async def collect_contact_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect contact information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'phoneNumber':
            session['candidate_data']['phoneNumber'] = update.message.text
            session['current_field'] = 'emailAddress'
            await update.message.reply_text(self.get_prompt(session, 'email_address'))
            return COLLECT_CONTACT_INFO
        elif current_field == 'emailAddress':
            session['candidate_data']['emailAddress'] = update.message.text
            session['current_field'] = 'linkedinProfile'
            await update.message.reply_text(self.get_prompt(session, 'linkedin_profile'))
            return COLLECT_CONTACT_INFO
        elif current_field == 'linkedinProfile':
            if update.message.text.lower() != 'skip':
                session['candidate_data']['linkedinProfile'] = update.message.text
            session['current_field'] = 'city'
            await update.message.reply_text(self.get_prompt(session, 'city'))
            return COLLECT_CONTACT_INFO
        elif current_field == 'city':
            session['candidate_data']['city'] = update.message.text
            session['current_field'] = 'country'
            await update.message.reply_text(self.get_prompt(session, 'country'))
            return COLLECT_CONTACT_INFO
        elif current_field == 'country':
            session['candidate_data']['country'] = update.message.text
            await update.message.reply_text(self.get_prompt(session, 'profile_image_prompt'))
            return COLLECT_PROFILE_IMAGE

    async def collect_profile_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect profile image from candidate"""
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        max_size = 5 * 1024 * 1024
        allowed_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        
        try:
            if update.message.text and update.message.text.lower() == 'skip':
                await update.message.reply_text(
                    self.get_prompt(session, 'profile_image_skip'),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(self.get_prompt(session, 'continue_professional'), callback_data="continue_professional")]
                    ])
                )
                return COLLECT_PROFILE_IMAGE
            elif update.message.photo:
                photo = update.message.photo[-1]
                if photo.file_size > max_size:
                    await update.message.reply_text(self.get_prompt(session, 'file_too_large'))
                    return COLLECT_PROFILE_IMAGE
                file = await photo.get_file()
                session['candidate_data']['profileUrl'] = file.file_path
                user = update.effective_user
                caption = f"🖼️ Profile Image Received\n\n👤 User: {user.first_name or ''} {user.last_name or ''}".strip()
                if user.username:
                    caption += f" (@{user.username})"
                caption += f"\n🆔 User ID: {telegram_id}"
                await update.message.copy(
                    chat_id=private_channel_id,
                    caption=caption
                )
            elif update.message.document:
                document = update.message.document
                if document.file_size > max_size:
                    await update.message.reply_text(self.get_prompt(session, 'file_too_large'))
                    return COLLECT_PROFILE_IMAGE
                if document.mime_type not in allowed_mime_types:
                    await update.message.reply_text(self.get_prompt(session, 'invalid_file_type'))
                    return COLLECT_PROFILE_IMAGE
                if document.file_name:
                    extension = document.file_name.split('.')[-1].lower()
                    if extension not in allowed_extensions:
                        await update.message.reply_text(self.get_prompt(session, 'invalid_file_type'))
                        return COLLECT_PROFILE_IMAGE
                file = await document.get_file()
                session['candidate_data']['profileUrl'] = file.file_path
                user = update.effective_user
                caption = f"🖼️ Profile Image Received\n\n👤 User: {user.first_name or ''} {user.last_name or ''}".strip()
                if user.username:
                    caption += f" (@{user.username})"
                caption += f"\n🆔 User ID: {telegram_id}"
                await update.message.copy(
                    chat_id=private_channel_id,
                    caption=caption
                )
            else:
                await update.message.reply_text(self.get_prompt(session, 'profile_image_prompt'))
                return COLLECT_PROFILE_IMAGE
            
            await update.message.reply_text(
                self.get_prompt(session, 'profile_image_success'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'continue_professional'), callback_data="continue_professional")]
                ])
            )
            return COLLECT_PROFILE_IMAGE
        except Exception as e:
            logger.error(f"Error in collect_profile_image: {str(e)}")
            await update.message.reply_text(self.get_prompt(session, 'error_message'))
            return COLLECT_PROFILE_IMAGE

    async def handle_profile_image_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to proceed after profile image"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "continue_professional":
            session['current_field'] = 'work_jobTitle'
            session['current_work_experience'] = {}
            await query.edit_message_text(self.get_prompt(session, 'job_title'))
            return COLLECT_PROFESSIONAL_INFO

    async def collect_professional_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect professional experience from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'work_jobTitle':
            session['current_work_experience']['jobTitle'] = update.message.text
            session['current_field'] = 'work_companyName'
            await update.message.reply_text(self.get_prompt(session, 'company_name'))
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_companyName':
            session['current_work_experience']['companyName'] = update.message.text
            session['current_field'] = 'work_location'
            await update.message.reply_text(self.get_prompt(session, 'work_location'))
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_location':
            session['current_work_experience']['location'] = update.message.text
            session['current_field'] = 'work_description'
            await update.message.reply_text(self.get_prompt(session, 'work_description'))
            return COLLECT_PROFESSIONAL_INFO
        elif current_field == 'work_description':
            session['current_work_experience']['description'] = update.message.text
            session['work_experiences'].append(session['current_work_experience'].copy())
            session['current_work_experience'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_work'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_work")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_education")]
                ])
            )
            return COLLECT_PROFESSIONAL_INFO

    async def handle_professional_info_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another work experience or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "add_another_work":
            session['current_field'] = 'work_jobTitle'
            await query.edit_message_text(self.get_prompt(session, 'job_title'))
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "continue_education":
            session['current_field'] = 'edu_degreeName'
            session['current_education'] = {}
            await query.edit_message_text(self.get_prompt(session, 'degree_name'))
            return COLLECT_EDUCATION

    async def collect_education(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect education information from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'edu_degreeName':
            session['current_education']['degreeName'] = update.message.text
            session['current_field'] = 'edu_institutionName'
            await update.message.reply_text(self.get_prompt(session, 'institution_name'))
            return COLLECT_EDUCATION
        elif current_field == 'edu_institutionName':
            session['current_education']['institutionName'] = update.message.text
            session['current_field'] = 'edu_gpa'
            await update.message.reply_text(self.get_prompt(session, 'gpa'))
            return COLLECT_EDUCATION
        elif current_field == 'edu_gpa':
            session['current_education']['gpa'] = update.message.text if update.message.text.lower() != 'skip' else None
            session['current_field'] = 'edu_description'
            await update.message.reply_text(self.get_prompt(session, 'edu_description'))
            return COLLECT_EDUCATION
        elif current_field == 'edu_description':
            session['current_education']['description'] = update.message.text
            session['current_field'] = 'edu_achievementsHonors'
            await update.message.reply_text(self.get_prompt(session, 'achievements_honors'))
            return COLLECT_EDUCATION
        elif current_field == 'edu_achievementsHonors':
            session['current_education']['achievementsHonors'] = update.message.text if update.message.text.lower() != 'skip' else None
            session['education'].append(session['current_education'].copy())
            session['current_education'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_edu'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_edu")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_skills")]
                ])
            )
            return COLLECT_EDUCATION

    async def handle_education_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another education entry or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == 'add_another_edu':
            session['current_field'] = 'edu_degreeName'
            await query.edit_message_text(self.get_prompt(session, 'degree_name'))
            return COLLECT_EDUCATION
        elif query.data == 'continue_skills':
            session['current_field'] = 'skill_skillName'
            session['current_skill'] = {}
            await query.edit_message_text(self.get_prompt(session, 'skill_name'))
            return COLLECT_SKILLS

    async def collect_skills(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect skills from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'skill_skillName':
            session['current_skill']['skillName'] = update.message.text
            session['current_field'] = 'skill_proficiency'
            await update.message.reply_text(self.get_prompt(session, 'skill_proficiency'))
            return COLLECT_SKILLS
        elif current_field == 'skill_proficiency':
            session['current_skill']['proficiency'] = update.message.text
            session['skills'].append(session['current_skill'].copy())
            session['current_skill'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_skill'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_skill")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_career")]
                ])
            )
            return COLLECT_SKILLS

    async def handle_skills_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another skill or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "add_another_skill":
            session['current_field'] = 'skill_skillName'
            await query.edit_message_text(self.get_prompt(session, 'skill_name'))
            return COLLECT_SKILLS
        elif query.data == "continue_career":
            await query.edit_message_text(self.get_prompt(session, 'career_summary'))
            return COLLECT_CAREER_OBJECTIVE

    async def collect_career_objective(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect career objective from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        
        session['career_objectives'].append({
            'summaryText': update.message.text
        })
        
        await update.message.reply_text(self.get_prompt(session, 'certificate_name'))
        session['current_field'] = 'cert_certificateName'
        session['current_certification'] = {}
        return COLLECT_CERTIFICATIONS

    async def collect_certifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect certifications from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'cert_certificateName':
            session['current_certification']['certificateName'] = update.message.text
            session['current_field'] = 'cert_issuer'
            await update.message.reply_text(self.get_prompt(session, 'issuer'))
            return COLLECT_CERTIFICATIONS
        elif current_field == 'cert_issuer':
            session['current_certification']['issuer'] = update.message.text
            session['certifications'].append(session['current_certification'].copy())
            session['current_certification'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_cert'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_cert")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_projects")]
                ])
            )
            return COLLECT_CERTIFICATIONS

    async def handle_certifications_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another certification or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "add_another_cert":
            session['current_field'] = 'cert_certificateName'
            await query.edit_message_text(self.get_prompt(session, 'certificate_name'))
            return COLLECT_CERTIFICATIONS
        elif query.data == "continue_projects":
            session['current_field'] = 'project_projectTitle'
            session['current_project'] = {}
            await query.edit_message_text(self.get_prompt(session, 'project_title'))
            return COLLECT_PROJECTS

    async def collect_projects(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect projects from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'project_projectTitle':
            session['current_project']['projectTitle'] = update.message.text
            session['current_field'] = 'project_description'
            await update.message.reply_text(self.get_prompt(session, 'project_description'))
            return COLLECT_PROJECTS
        elif current_field == 'project_description':
            session['current_project']['description'] = update.message.text
            session['current_field'] = 'project_projectLink'
            await update.message.reply_text(self.get_prompt(session, 'project_link'))
            return COLLECT_PROJECTS
        elif current_field == 'project_projectLink':
            if update.message.text.lower() != 'skip':
                session['current_project']['projectLink'] = update.message.text
            session['projects'].append(session['current_project'].copy())
            session['current_project'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_project'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_project")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_languages")]
                ])
            )
            return COLLECT_PROJECTS

    async def handle_projects_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another project or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "add_another_project":
            session['current_field'] = 'project_projectTitle'
            await query.edit_message_text(self.get_prompt(session, 'project_title'))
            return COLLECT_PROJECTS
        elif query.data == "continue_languages":
            session['current_field'] = 'lang_languageName'
            session['current_language'] = {}
            await query.edit_message_text(self.get_prompt(session, 'language_name'))
            return COLLECT_LANGUAGES

    async def collect_languages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect languages from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        current_field = session['current_field']
        
        if current_field == 'lang_languageName':
            session['current_language']['languageName'] = update.message.text
            session['current_field'] = 'lang_proficiencyLevel'
            await update.message.reply_text(self.get_prompt(session, 'language_proficiency'))
            return COLLECT_LANGUAGES
        elif current_field == 'lang_proficiencyLevel':
            session['current_language']['proficiencyLevel'] = update.message.text
            session['languages'].append(session['current_language'].copy())
            session['current_language'] = {}
            await update.message.reply_text(
                self.get_prompt(session, 'add_another_language'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(self.get_prompt(session, 'add_another'), callback_data="add_another_language")],
                    [InlineKeyboardButton(self.get_prompt(session, 'continue'), callback_data="continue_activities")]
                ])
            )
            return COLLECT_LANGUAGES

    async def handle_languages_choice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle the user's choice to add another language or continue"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "add_another_language":
            session['current_field'] = 'lang_languageName'
            await query.edit_message_text(self.get_prompt(session, 'language_name'))
            return COLLECT_LANGUAGES
        elif query.data == "continue_activities":
            await query.edit_message_text(self.get_prompt(session, 'activities'))
            return COLLECT_ACTIVITIES

    async def collect_activities(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Collect other activities from candidate"""
        user = update.effective_user
        telegram_id = str(user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        
        session['activities'].append({
            'activityType': 'Other',
            'description': update.message.text
        })
        
        summary = self.get_prompt(session, 'summary_header')
        summary += f"{self.get_prompt(session, 'summary_name')}: {session['candidate_data'].get('firstName', '')} {session['candidate_data'].get('middleName', '')} {session['candidate_data'].get('lastName', '')}\n"
        
        summary += f"{self.get_prompt(session, 'summary_contact')}: {session['candidate_data'].get('phoneNumber', '')} | {session['candidate_data'].get('emailAddress', '')}\n"
        summary += f"{self.get_prompt(session, 'summary_location')}: {session['candidate_data'].get('city', '')}, {session['candidate_data'].get('country', '')}\n"
        summary += f"{self.get_prompt(session, 'summary_availability')}: {session['candidate_data'].get('availability', 'To be specified')}\n\n"
        
        summary += f"{self.get_prompt(session, 'summary_work')}:\n"
        for exp in session['work_experiences']:
            summary += f"- {exp.get('jobTitle', 'N/A')} at {exp.get('companyName', 'N/A')}, {exp.get('location', 'N/A')}\n"
            summary += f"  {self.get_prompt(session, 'summary_responsibilities')}: {exp.get('description', 'N/A')}\n"
        
        summary += f"\n{self.get_prompt(session, 'summary_education')}:\n"
        for edu in session['education']:
            summary += f"- {edu.get('degreeName', 'N/A')} from {edu.get('institutionName', 'N/A')}\n"
            summary += f"  {self.get_prompt(session, 'summary_gpa')}: {edu.get('gpa', 'N/A')}\n"
            summary += f"  {self.get_prompt(session, 'summary_edu_description')}: {edu.get('description', 'N/A')}\n"
            summary += f"  {self.get_prompt(session, 'summary_achievements')}: {edu.get('achievementsHonors', 'None')}\n"
        
        summary += f"\n{self.get_prompt(session, 'summary_skills')}:\n"
        for skill in session['skills']:
            summary += f"- {skill.get('skillName', 'N/A')} ({self.get_prompt(session, 'summary_proficiency')}: {skill.get('proficiency', 'N/A')})\n"
        
        summary += f"\n{self.get_prompt(session, 'summary_certifications')}:\n"
        for cert in session['certifications']:
            summary += f"- {cert.get('certificateName', 'N/A')} from {cert.get('issuer', 'N/A')}\n"
        
        summary += f"\n{self.get_prompt(session, 'summary_projects')}:\n"
        for project in session['projects']:
            summary += f"- {project.get('projectTitle', 'N/A')}\n"
            summary += f"  {self.get_prompt(session, 'summary_edu_description')}: {project.get('description', 'N/A')}\n"
            if project.get('projectLink'):
                summary += f"  {self.get_prompt(session, 'summary_project_link')}: {project.get('projectLink')}\n"
        
        summary += f"\n{self.get_prompt(session, 'summary_languages')}:\n"
        for lang in session['languages']:
            summary += f"- {lang.get('languageName', 'N/A')} ({self.get_prompt(session, 'summary_proficiency')}: {lang.get('proficiencyLevel', 'N/A')})\n"
        
        keyboard = [
            [
                InlineKeyboardButton(self.get_prompt(session, 'confirm'), callback_data="confirm_yes"),
                InlineKeyboardButton(self.get_prompt(session, 'edit'), callback_data="edit_no")
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
        session['chat_id'] = query.message.chat_id
        
        if query.data == "confirm_yes":
            candidate = Candidate.get_by_telegram_user_id(telegram_id)
            if not candidate:
                candidate = Candidate(
                    uid=str(uuid.uuid4()),
                    telegramUserId=telegram_id,
                    **session['candidate_data']
                )
                candidate.save()
            else:
                for key, value in session['candidate_data'].items():
                    setattr(candidate, key, value)
                candidate.save()
            
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
            
            order = Order(
                id=str(uuid.uuid4()),
                candidateId=candidate.uid,
                telegramUserId=telegram_id,
                status="awaiting_payment"
            )
            order.save()
            
            session['order_id'] = order.id
            session['notified'] = False
            
            await query.edit_message_text(self.get_prompt(session, 'payment_instructions'))
            return PAYMENT
        else:
            await query.edit_message_text(
                self.get_prompt(session, 'edit_section'),
                reply_markup=self.get_profile_sections_keyboard(session)
            )
            return START

    async def edit_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle request to edit information"""
        query = update.callback_query
        await query.answer()
        
        telegram_id = str(query.from_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = query.message.chat_id
        
        if query.data == "edit_personal":
            session['current_field'] = 'firstName'
            await query.edit_message_text(self.get_prompt(session, 'first_name'))
            return COLLECT_PERSONAL_INFO
        elif query.data == "edit_contact":
            session['current_field'] = 'phoneNumber'
            await query.edit_message_text(self.get_prompt(session, 'phone_number'))
            return COLLECT_CONTACT_INFO
        elif query.data == "edit_profile_image":
            session['current_field'] = None
            await query.edit_message_text(self.get_prompt(session, 'profile_image_prompt'))
            return COLLECT_PROFILE_IMAGE
        elif query.data == "edit_work":
            session['work_experiences'] = []
            session['current_field'] = 'work_jobTitle'
            await query.edit_message_text(self.get_prompt(session, 'job_title'))
            return COLLECT_PROFESSIONAL_INFO
        elif query.data == "edit_education":
            session['education'] = []
            session['current_field'] = 'edu_degreeName'
            session['current_education'] = {}
            await query.edit_message_text(self.get_prompt(session, 'degree_name'))
            return COLLECT_EDUCATION
        elif query.data == "edit_skills":
            session['skills'] = []
            session['current_field'] = 'skill_skillName'
            session['current_skill'] = {}
            await query.edit_message_text(self.get_prompt(session, 'skill_name'))
            return COLLECT_SKILLS
        elif query.data == "edit_career":
            session['career_objectives'] = []
            await query.edit_message_text(self.get_prompt(session, 'career_summary'))
            return COLLECT_CAREER_OBJECTIVE
        elif query.data == "edit_certs":
            session['certifications'] = []
            session['current_field'] = 'cert_certificateName'
            session['current_certification'] = {}
            await query.edit_message_text(self.get_prompt(session, 'certificate_name'))
            return COLLECT_CERTIFICATIONS
        elif query.data == "edit_projects":
            session['projects'] = []
            session['current_field'] = 'project_projectTitle'
            session['current_project'] = {}
            await query.edit_message_text(self.get_prompt(session, 'project_title'))
            return COLLECT_PROJECTS
        elif query.data == "edit_languages":
            session['languages'] = []
            session['current_field'] = 'lang_languageName'
            session['current_language'] = {}
            await query.edit_message_text(self.get_prompt(session, 'language_name'))
            return COLLECT_LANGUAGES
        elif query.data == "edit_activities":
            session['activities'] = []
            await query.edit_message_text(self.get_prompt(session, 'activities'))
            return COLLECT_ACTIVITIES

    async def handle_payment_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle payment screenshot upload"""
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        session['chat_id'] = update.effective_chat.id
        
        max_size = 5 * 1024 * 1024
        allowed_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        
        try:
            user = update.effective_user
            user_info = f"👤 User: {user.first_name or ''} {user.last_name or ''}".strip()
            if user.username:
                user_info += f" (@{user.username})"
            user_info += f"\n🆔 User ID: {telegram_id}"
            user_info += f"\n📋 Order ID: {session.get('order_id', 'N/A')}"
            user_info += f"\n📞 Phone: {session['candidate_data'].get('phoneNumber', 'N/A')}"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{telegram_id}_{session['order_id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{telegram_id}_{session['order_id']}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.message.photo:
                photo = update.message.photo[-1]
                file = await photo.get_file()
                if file.file_size > max_size:
                    await update.message.reply_text(self.get_prompt(session, 'file_too_large'))
                    return PAYMENT
                file_url = file.file_path
                await context.bot.send_photo(
                    chat_id=private_channel_id,
                    photo=photo.file_id,
                    caption=f"💳 Payment Screenshot Received\n\n{user_info}",
                    reply_markup=reply_markup
                )
                logger.info(f"Payment screenshot forwarded to private channel for user {telegram_id}, order {session['order_id']}")
            elif update.message.document:
                document = update.message.document
                if document.file_size > max_size:
                    await update.message.reply_text(self.get_prompt(session, 'file_too_large'))
                    return PAYMENT
                if document.mime_type not in allowed_mime_types:
                    await update.message.reply_text(self.get_prompt(session, 'invalid_file_type'))
                    return PAYMENT
                if document.file_name:
                    extension = document.file_name.split('.')[-1].lower()
                    if extension not in allowed_extensions:
                        await update.message.reply_text(self.get_prompt(session, 'invalid_file_type'))
                        return PAYMENT
                file = await document.get_file()
                file_url = file.file_path
                await context.bot.send_document(
                    chat_id=private_channel_id,
                    document=document.file_id,
                    caption=f"💳 Payment Document Received\n\n{user_info}",
                    reply_markup=reply_markup
                )
                logger.info(f"Payment document forwarded to private channel for user {telegram_id}, order {session['order_id']}")
            else:
                await update.message.reply_text(self.get_prompt(session, 'payment_instructions'))
                return PAYMENT
            
            order = Order.get_by_id(session['order_id'])
            if not order:
                logger.error(f"Order {session['order_id']} not found for telegram_id {telegram_id}")
                await update.message.reply_text(self.get_prompt(session, 'error_message'))
                return PAYMENT
            
            order.paymentScreenshotUrl = file_url
            order.update_status("pending_verification", status_details="Payment screenshot submitted, awaiting admin verification")
            order.save()
            
            await update.message.reply_text(self.get_prompt(session, 'payment_screenshot_success'))
            await update.message.reply_text(self.get_prompt(session, 'payment_confirmation'))
            
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error in handle_payment_screenshot: {str(e)}")
            await update.message.reply_text(self.get_prompt(session, 'error_message'))
            return PAYMENT

    async def handle_admin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin approval/rejection responses"""
        query = update.callback_query
        await query.answer()
        
        try:
            action, telegram_id, order_id = query.data.split('_', 2)
            
            session = self.get_user_session(telegram_id)
            if 'chat_id' not in session:
                logger.error(f"No chat_id found for telegram_id {telegram_id} in session")
                await query.message.reply_text("Error: User session not found.")
                return
            
            order = Order.get_by_id(order_id)
            if not order:
                logger.error(f"Order {order_id} not found for telegram_id {telegram_id}")
                await query.message.reply_text("Error: Order not found.")
                return
            
            if action == "approve":
                try:
                    order.approve_payment()
                    await context.bot.send_message(
                        chat_id=session['chat_id'],
                        text=self.get_prompt(session, 'payment_verified')
                    )
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n✅ **APPROVED** by {query.from_user.first_name or 'Admin'}",
                        reply_markup=None
                    )
                    logger.info(f"Payment approved for user {telegram_id}, order {order_id} by admin {query.from_user.id}")
                    session['notified'] = True
                except Exception as e:
                    logger.error(f"Error sending approval message to user {telegram_id}: {str(e)}")
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n✅ **APPROVED** by {query.from_user.first_name or 'Admin'} (Error sending notification to user)",
                        reply_markup=None
                    )
            elif action == "reject":
                try:
                    reason = "No reason provided"
                    order.reject_payment(reason)
                    await context.bot.send_message(
                        chat_id=session['chat_id'],
                        text=self.get_prompt(session, 'payment_rejected').format(reason=reason)
                    )
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n❌ **REJECTED** by {query.from_user.first_name or 'Admin'}",
                        reply_markup=None
                    )
                    logger.info(f"Payment rejected for user {telegram_id}, order {order_id} by admin {query.from_user.id}")
                    session['notified'] = True
                except Exception as e:
                    logger.error(f"Error sending rejection message to user {telegram_id}: {str(e)}")
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n❌ **REJECTED** by {query.from_user.first_name or 'Admin'} (Error sending notification to user)",
                        reply_markup=None
                    )
                    
        except ValueError:
            logger.error(f"Invalid callback data format: {query.data}")
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n⚠️ **ERROR**: Invalid callback data",
                reply_markup=None
            )
        except Exception as e:
            logger.error(f"Error handling admin response: {str(e)}")
            await query.message.reply_text("An error occurred while processing your response.")

    async def handle_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin replies in the private channel to approve or reject payments"""
        if not update.message or not update.message.chat_id:
            logger.debug("Ignoring update with no message or chat_id")
            return
        
        if str(update.message.chat_id) != private_channel_id:
            logger.debug(f"Ignoring message from chat_id {update.message.chat_id}, expected {private_channel_id}")
            return
        
        reply_text = update.message.text.lower() if update.message.text else ""
        if not (reply_text.startswith('approve') or reply_text.startswith('reject:')):
            logger.debug(f"Ignoring reply with text: {reply_text}")
            return
        
        try:
            if not update.message.reply_to_message or not update.message.reply_to_message.caption:
                logger.debug("Ignoring reply with no valid reply_to_message or caption")
                return
            
            caption = update.message.reply_to_message.caption
            if not caption.startswith('💳 Payment'):
                logger.debug(f"Ignoring reply with invalid caption: {caption}")
                return
            
            try:
                order_id = caption.split('Order ID: ')[1].split('\n')[0].strip()
            except IndexError:
                logger.error(f"Failed to parse order_id from caption: {caption}")
                return
            
            order = Order.get_by_id(order_id)
            if not order:
                logger.error(f"Order {order_id} not found")
                return
            
            telegram_id = order.telegramUserId
            session = self.get_user_session(telegram_id)
            if 'chat_id' not in session:
                logger.error(f"No chat_id found for telegram_id {telegram_id} in session")
                return
            
            if reply_text == 'approve':
                order.approve_payment()
                logger.info(f"Order {order_id} approved: paymentVerified={order.paymentVerified}, status={order.status}, statusDetails={order.statusDetails}")
                if not session.get('notified', False):
                    await self.application.bot.send_message(
                        chat_id=session['chat_id'],
                        text=self.get_prompt(session, 'payment_verified')
                    )
                    logger.info(f"Sent immediate payment verified notification to chat_id {session['chat_id']} for order {order_id}")
                    session['notified'] = True
            elif reply_text.startswith('reject:'):
                reason = reply_text[7:].strip() or 'No reason provided'
                order.reject_payment(reason)
                logger.info(f"Order {order_id} rejected: paymentVerified={order.paymentVerified}, status={order.status}, statusDetails={order.statusDetails}")
                if not session.get('notified', False):
                    await self.application.bot.send_message(
                        chat_id=session['chat_id'],
                        text=self.get_prompt(session, 'payment_rejected').format(reason=reason)
                    )
                    logger.info(f"Sent immediate payment rejected notification to chat_id {session['chat_id']} for order {order_id}")
                    session['notified'] = True
        
        except Exception as e:
            logger.error(f"Error in handle_admin_reply: {str(e)}")

    async def ignore_non_reply_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Ignore non-reply messages in the private channel"""
        logger.debug(f"Ignoring non-reply message in private channel: {update.message.text if update.message.text else 'No text'}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancel the current conversation"""
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]
        
        await update.message.reply_text(self.get_prompt(session, 'cancel_message'))
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message"""
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        await update.message.reply_text(self.get_prompt(session, 'help_message'))

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors and handle connection issues"""
        logger.error(msg="Exception while handling update:", exc_info=context.error)
        
        if update and update.effective_message and update.effective_user:
            telegram_id = str(update.effective_user.id)
            session = self.get_user_session(telegram_id)
            await update.effective_message.reply_text(self.get_prompt(session, 'error_message'))
        else:
            logger.debug("No effective message or user available to send error message")

    def run(self):
        """Start the bot with retry logic"""
        max_retries = 3
        retry_delay = 5.0
        for attempt in range(max_retries):
            try:
                logger.info("Starting Telegram bot with polling")
                self.application.run_polling(
                    poll_interval=1.0,
                    timeout=10,
                    bootstrap_retries=3,
                    close_loop=False
                )
                return
            except telegram.error.TimedOut as e:
                logger.error(f"Telegram API connection timed out (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached. Failed to connect to Telegram API.")
                    raise
            except Exception as e:
                logger.error(f"Error running bot: {str(e)}")
                raise

if __name__ == "__main__":
    bot = CVBot(telegram_bot_token)
    bot.run()