import logging
import os
import re
from dotenv import load_dotenv
from telegram import Update, User
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest
import telegram

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
private_channel_id = os.getenv('PRIVATE_CHANNEL_ID')

class TestBot:
    def __init__(self, token: str):
        # Configure HTTPXRequest for robust network handling
        request = HTTPXRequest(
            connection_pool_size=10,
            connect_timeout=60.0,
            read_timeout=60.0,
            write_timeout=60.0
        )
        logger.info("Initializing Application with token")
        self.application = Application.builder().token(token).request(request).build()
        
        # Cache for username to user_id mapping
        self.user_cache = {}
        
        self.setup_handlers()
        logger.info("TestBot initialized successfully")

    def setup_handlers(self) -> None:
        """Set up message handlers for the bot"""
        # Handle photo or document uploads in the private channel
        self.application.add_handler(MessageHandler(
            filters.Chat(int(private_channel_id)) & (filters.PHOTO | filters.Document.ALL),
            self.handle_file_upload
        ))
        
        # Handle all private messages to build user cache
        self.application.add_handler(MessageHandler(
            filters.ChatType.PRIVATE,
            self.cache_user_info
        ))
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("register", self.register_command))
        
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user = update.effective_user
        if user and user.username:
            username = user.username.lower()
            user_id = user.id
            self.user_cache[username] = user_id
            logger.info(f"✅ User registered via /start: @{username} -> {user_id}")
            
            await update.message.reply_text(
                f"👋 Hello @{user.username}!\n\n"
                f"🤖 This bot can forward files to you from authorized channels.\n"
                f"✅ You are now registered and can receive files!\n\n"
                f"📝 Your user ID: {user_id}"
            )
        else:
            await update.message.reply_text(
                "👋 Hello! This bot can forward files to you.\n\n"
                "⚠️ Please set a username in your Telegram settings to receive files."
            )
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /register command"""
        user = update.effective_user
        if user and user.username:
            username = user.username.lower()
            user_id = user.id
            self.user_cache[username] = user_id
            logger.info(f"✅ User registered via /register: @{username} -> {user_id}")
            
            await update.message.reply_text(
                f"✅ Registration successful!\n\n"
                f"👤 Username: @{user.username}\n"
                f"🆔 User ID: {user_id}\n\n"
                f"📁 You can now receive files through this bot!"
            )
        else:
            await update.message.reply_text(
                "❌ Registration failed!\n\n"
                "Please set a username in your Telegram settings first, then try /register again."
            )

    async def debug_all_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Debug handler to see all messages in the private channel"""
        message = update.message or update.channel_post
        if not message:
            return
            
        logger.info(f"🔍 DEBUG: Message received in private channel")
        logger.info(f"   Chat ID: {message.chat_id}")
        logger.info(f"   Message ID: {message.message_id}")
        logger.info(f"   Text: {message.text}")
        logger.info(f"   Caption: {message.caption}")
        logger.info(f"   Has photo: {bool(message.photo)}")
        logger.info(f"   Has document: {bool(message.document)}")
        logger.info(f"   From user: {message.from_user.username if message.from_user else 'Channel post'}")
        logger.info(f"   Update type: {'channel_post' if update.channel_post else 'message'}")

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
            # This is a long shot - try to get member info
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
        logger.info(f"=== FILE UPLOAD HANDLER TRIGGERED ===")
        logger.info(f"Update received: {update}")
        
        # Handle both regular messages and channel posts
        message = update.message or update.channel_post
        if not message:
            logger.warning("No message or channel_post in update")
            return
            
        if not message.chat_id:
            logger.warning("No chat_id in message")
            return

        logger.info(f"Message chat_id: {message.chat_id} (type: {type(message.chat_id)})")
        logger.info(f"Expected private_channel_id: {private_channel_id} (type: {type(private_channel_id)})")
        
        # More flexible chat ID comparison
        if str(message.chat_id) != str(private_channel_id):
            logger.warning(f"Message from wrong chat: {message.chat_id}, expected: {private_channel_id}")
            return
        
        logger.info("✅ Message is from the correct private channel")

        # Check what type of content we have
        has_photo = bool(message.photo)
        has_document = bool(message.document)
        logger.info(f"Content check - Photo: {has_photo}, Document: {has_document}")
        
        if not (has_photo or has_document):
            logger.warning("No photo or document found in message")
            await message.reply_text("❌ No photo or document found. Please upload a file with the message.")
            return

        # Check for text with username
        message_text = message.caption if message.caption else message.text
        logger.info(f"Message text/caption: '{message_text}'")
        if not message_text:
            logger.debug("No text or caption provided with file")
            await message.reply_text("Please include a username (e.g., @username) with the file.")
            return

        # Extract username using regex (supports both @username and username)
        username_match = re.search(r'@?(\w+)', message_text)
        if not username_match:
            logger.debug(f"No valid username found in message: {message_text}")
            await message.reply_text("No valid username found. Please include a username (with or without '@').")
            return

        username = username_match.group(1)  # Extract username without @
        full_username = f"@{username}"
        logger.info(f"Processing file upload for username: {full_username}")

        try:
            # Resolve username to user ID
            target_user_id = await self.resolve_username_to_id(username, context)
            logger.info(f"Resolved {full_username} to user ID: {target_user_id}")
            
        except ValueError as e:
            logger.error(f"Username resolution failed: {str(e)}")
            await message.reply_text(
                f"❌ Could not find user {full_username}\n\n"
                f"**Possible solutions:**\n"
                f"1️⃣ Ask {full_username} to start a conversation with this bot by sending /start\n"
                f"2️⃣ Make sure the username is spelled correctly\n"
                f"3️⃣ Ensure the username is public (not private)\n"
                f"4️⃣ The user might need to send any message to this bot first\n\n"
                f"💡 **Tip**: The bot can only send files to users who have interacted with it before!"
            )
            return
        except Exception as e:
            logger.error(f"Unexpected error resolving username {full_username}: {str(e)}")
            await message.reply_text(f"Error finding user {full_username}. Please try again.")
            return

        # Resend the file to the user
        try:
            if message.photo:
                photo = message.photo[-1]  # Get highest resolution
                sent_message = await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=photo.file_id,
                    caption=None  # Send without caption to maintain privacy
                )
                logger.info(f"Photo sent to user ID {target_user_id}")
                
            elif message.document:
                document = message.document
                sent_message = await context.bot.send_document(
                    chat_id=target_user_id,
                    document=document.file_id,
                    caption=None  # Send without caption to maintain privacy
                )
                logger.info(f"Document sent to user ID {target_user_id}")
                
            else:
                logger.debug("No photo or document found in message")
                await message.reply_text("No valid file (photo or document) found.")
                return

            # Confirm successful delivery to the private channel
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

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors and notify appropriately"""
        logger.error(msg="Exception while handling update:", exc_info=context.error)
        
        # Only reply if we have a message to reply to
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⚠️ An error occurred while processing your request. Please try again."
                )
            except Exception as reply_error:
                logger.error(f"Could not send error message: {str(reply_error)}")

    def run(self):
        """Start the bot with retry logic"""
        max_retries = 3
        retry_delay = 5.0
        
        for attempt in range(max_retries):
            try:
                logger.info("Starting Telegram bot with polling")
                self.application.run_polling(
                    poll_interval=1.0,
                    timeout=20,  # Increased timeout
                    bootstrap_retries=3,
                    close_loop=False,
                    drop_pending_updates=True  # Clear old updates on startup
                )
                return
                
            except telegram.error.TimedOut as e:
                logger.error(f"Telegram API connection timed out (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Failed to connect to Telegram API.")
                    raise
                    
            except telegram.error.NetworkError as e:
                logger.error(f"Network error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("Max retries reached due to network errors.")
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error running bot: {str(e)}")
                raise

if __name__ == "__main__":
    # Validate environment variables
    if not telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env file")
        raise ValueError("Missing TELEGRAM_BOT_TOKEN")
    
    if not private_channel_id:
        logger.error("PRIVATE_CHANNEL_ID not set in .env file")
        raise ValueError("Missing PRIVATE_CHANNEL_ID")
    
    try:
        # Validate that private_channel_id is a valid integer
        channel_id_int = int(private_channel_id)
        logger.info(f"✅ Private channel ID validated: {channel_id_int}")
    except ValueError:
        logger.error("PRIVATE_CHANNEL_ID must be a valid integer")
        raise ValueError("PRIVATE_CHANNEL_ID must be a valid integer")
    
    logger.info(f"🤖 Bot token: {telegram_bot_token[:10]}...{telegram_bot_token[-4:]}")
    logger.info(f"📢 Private channel ID: {private_channel_id}")
    logger.info("Starting TestBot...")
    bot = TestBot(telegram_bot_token)
    bot.run()