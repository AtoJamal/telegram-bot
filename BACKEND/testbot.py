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
from telegram.request import HTTPXRequest
import django
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict
import asyncio
import telegram

# Set up logging first
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Logging configured.")

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cvbot_backend.settings')
django.setup()

# Load environment variables
load_dotenv()

# Get Telegram bot token
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
private_channel_id = os.getenv('PRIVATE_CHANNEL_ID')

# Initialize Firebase
logger.info("Attempting to load Firebase credentials from: ../firebaseapikey.json")
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("../firebaseapikey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()
logger.info("Firestore client obtained.")

# Define conversation states
PAYMENT, REJECT_REASON = range(2)

# Dummy PROMPTS for testing
PROMPTS = {
    'en': {
        'payment_instructions': "Please send a payment screenshot.",
        'payment_screenshot_success': "Payment screenshot received!",
        'payment_confirmation': "You will be notified once verified.",
        'error_message': "An error occurred. Please try again or check your network.",
        'connection_error': "Failed to connect to Telegram API. Please check your internet connection and try again."
    }
}

class CVBot:
    def __init__(self, token: str):
        # Configure HTTPXRequest with supported parameters
        request = HTTPXRequest(
            connection_pool_size=10,
            connect_timeout=60.0,  # 60 seconds for connection
            read_timeout=60.0,     # 60 seconds for reading
            write_timeout=60.0     # 60 seconds for writing
        )
        logger.info("Initializing Application with token")
        # Fix: Use 'request' instead of 'http_request'
        self.application = Application.builder().token(token).request(request).build()
        self.user_sessions: Dict[str, Dict] = {}
        self.setup_handlers()
        logger.info("CVBot initialized successfully")
    
    def setup_handlers(self) -> None:
        """Set up conversation handlers for the bot"""
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                PAYMENT: [
                    MessageHandler(
                        filters.PHOTO | filters.Document.IMAGE | filters.Document.MimeType("application/pdf"),
                        self.handle_payment_screenshot
                    )
                ],
                REJECT_REASON: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reject_reason)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            per_message=False
        )
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        # Add callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.handle_admin_response))
        self.application.add_error_handler(self.error_handler)
    
    def get_user_session(self, user_id: str) -> dict:
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {'language': 'en', 'order_id': 'test_order_id'}
        return self.user_sessions[user_id]
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        await update.message.reply_text(PROMPTS['en']['payment_instructions'])
        return PAYMENT
    
    async def handle_payment_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        
        try:
            # Get user information
            user = update.effective_user
            user_info = f"👤 User: {user.first_name or ''} {user.last_name or ''}".strip()
            if user.username:
                user_info += f" (@{user.username})"
            user_info += f"\n🆔 User ID: {telegram_id}"
            user_info += f"\n📋 Order ID: {session.get('order_id', 'N/A')}"
            
            # Create inline keyboard for admin approval/rejection
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve_{telegram_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_{telegram_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Forward the image to private channel with user info and buttons
            if update.message.photo:
                # For photos, get the highest resolution version
                photo = update.message.photo[-1]
                await context.bot.send_photo(
                    chat_id=private_channel_id,
                    photo=photo.file_id,
                    caption=f"💳 Payment Screenshot Received\n\n{user_info}",
                    reply_markup=reply_markup
                )
                logger.info(f"Payment screenshot forwarded to private channel for user {telegram_id}")
            elif update.message.document:
                # For documents (PDF or images sent as files)
                document = update.message.document
                await context.bot.send_document(
                    chat_id=private_channel_id,
                    document=document.file_id,
                    caption=f"💳 Payment Document Received\n\n{user_info}",
                    reply_markup=reply_markup
                )
                logger.info(f"Payment document forwarded to private channel for user {telegram_id}")
                
        except Exception as e:
            logger.error(f"Error forwarding payment screenshot to private channel: {str(e)}")
            await update.message.reply_text("Payment received, but there was an issue processing it. Please contact support.")
            return ConversationHandler.END
        
        await update.message.reply_text(PROMPTS['en']['payment_screenshot_success'])
        await update.message.reply_text(PROMPTS['en']['payment_confirmation'])
        return ConversationHandler.END
    
    async def handle_reject_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Rejection reason received.")
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        await update.message.reply_text("Operation cancelled.")
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]
        return ConversationHandler.END
    
    async def handle_admin_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin approval/rejection responses"""
        query = update.callback_query
        await query.answer()  # Acknowledge the callback query
        
        try:
            # Parse the callback data
            action, user_id = query.data.split('_', 1)
            
            if action == "approve":
                # Send approval message to user
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="✅ **Payment Approved!**\n\nYour payment has been verified and approved. Thank you for your submission!"
                    )
                    # Update the admin message to show it was approved
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n✅ **APPROVED** by {query.from_user.first_name or 'Admin'}",
                        reply_markup=None
                    )
                    logger.info(f"Payment approved for user {user_id} by admin {query.from_user.id}")
                except Exception as e:
                    logger.error(f"Error sending approval message to user {user_id}: {str(e)}")
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n✅ **APPROVED** by {query.from_user.first_name or 'Admin'} (Error sending notification to user)",
                        reply_markup=None
                    )
                    
            elif action == "reject":
                # Send rejection message to user
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="❌ **Payment Rejected**\n\nYour payment submission has been rejected. Please contact support if you believe this was an error or if you need assistance."
                    )
                    # Update the admin message to show it was rejected
                    await query.edit_message_caption(
                        caption=f"{query.message.caption}\n\n❌ **REJECTED** by {query.from_user.first_name or 'Admin'}",
                        reply_markup=None
                    )
                    logger.info(f"Payment rejected for user {user_id} by admin {query.from_user.id}")
                except Exception as e:
                    logger.error(f"Error sending rejection message to user {user_id}: {str(e)}")
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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        telegram_id = str(update.effective_user.id)
        session = self.get_user_session(telegram_id)
        await update.message.reply_text("This is a test bot. Use /start to begin.")
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Update {update} caused error {context.error}")
        telegram_id = str(update.effective_user.id) if update and update.effective_user else "unknown"
        session = self.get_user_session(telegram_id)
        error_message = PROMPTS['en']['connection_error'] if isinstance(context.error, telegram.error.TimedOut) else PROMPTS['en']['error_message']
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(error_message)
            elif update.message:
                await update.message.reply_text(error_message)
            else:
                logger.warning("No valid message or callback query for error notification")
        except Exception as e:
            logger.error(f"Error sending error message to user {telegram_id}: {str(e)}")
    
    def run(self):
        """Start the bot with retry logic"""
        max_retries = 3
        retry_delay = 5.0
        for attempt in range(max_retries):
            try:
                logger.info("Starting Telegram bot with polling")
                # Use run_polling() directly - it handles the event loop internally
                self.application.run_polling(
                    poll_interval=1.0,     # Check for updates every 1 second
                    timeout=10,            # Timeout for long polling
                    bootstrap_retries=3,   # Retry bootstrap operations
                    close_loop=False       # Don't close the event loop
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

if __name__ == '__main__':
    bot = CVBot(telegram_bot_token)
    bot.run()
