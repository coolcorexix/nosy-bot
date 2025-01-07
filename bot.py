import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from models.todo import Todo, TaskState
from enum import IntEnum
from datetime import datetime, timedelta, time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Create logger
logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text("""
    Hi {user.first_name}! I am your bot. Nice to meet you! 
    Type /help to know more on how to use me.
    """)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:
/help - Show this help message
/todo <description> - Add a new task
/focus <number> - Mark task as WIP
/did <description> - Log a completed task
/done <number> - Mark task as done
/list - Show active tasks
    """
    await update.message.reply_text(help_text)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a task to the todo list."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Please provide a task description.\n"
            "Usage: /todo Buy groceries\n"
            "Or send a photo with caption: /todo Buy these items"
        )
        return
    
    task = ' '.join(context.args)
    
    if Todo.create(user_id, task, TaskState.TODO):
        await update.message.reply_text(f"Task added: {task}")
    else:
        await update.message.reply_text("Failed to add task. Please try again.")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List active tasks (not done)."""
    user_id = update.effective_user.id
    
    tasks = Todo.get_all_by_user(user_id)
    
    if not tasks:
        await update.message.reply_text("You have no active tasks! Use /todo to add one.")
        return
    
    await update.message.reply_text("📋 Active Tasks:")
    for task_id, task, state, image_file_id in tasks:
        emoji = "📌" if state == "TODO" else "🚀"  # Only TODO or WIP states
        message = f"{emoji} {task_id}. {task} [{state}]"
        
        if image_file_id:
            await update.message.reply_photo(
                photo=image_file_id,
                caption=message
            )
        else:
            await update.message.reply_text(message)

async def list_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List completed tasks."""
    user_id = update.effective_user.id
    
    tasks = Todo.get_done_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text("You haven't completed any tasks yet!")
        return
    
    await update.message.reply_text("✅ Completed Tasks:")
    for task_id, task, state, image_file_id in tasks:
        message = f"✅ {task_id}. {task}"
        
        if image_file_id:
            await update.message.reply_photo(
                photo=image_file_id,
                caption=message
            )
        else:
            await update.message.reply_text(message)

async def focus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a task as WIP."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Please provide a task number.\nUsage: /focus 1")
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task number.")
        return
    
    if Todo.update_state(task_id, user_id, TaskState.WIP):
        await update.message.reply_text(f"Task {task_id} is now in progress! 🚀")
    else:
        await update.message.reply_text("Failed to update task state. Please check the task number.")

async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a task as done."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Please provide a task number.\nUsage: /done 1")
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a valid task number.")
        return
    
    if Todo.update_state(task_id, user_id, TaskState.DONE):
        await update.message.reply_text(f"Task {task_id} completed! 🎉")
    else:
        await update.message.reply_text("Failed to update task state. Please check the task number.")

async def did_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log a completed task."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Please provide what you did.\n"
            "Usage: /did Completed the presentation\n"
            "Or send a photo with caption: /did Finished this task"
        )
        return
    
    task = ' '.join(context.args)
    
    if Todo.create(user_id, task, TaskState.DONE):
        await update.message.reply_text(f"✅ Logged completed task: {task}")
    else:
        await update.message.reply_text("Failed to log the task. Please try again.")

async def check_progress(context: ContextTypes.DEFAULT_TYPE):
    """Send periodic reminders to update task list."""
    logger.info("Running check_progress job")
    
    message = (
        "🔔 How are things going?\n\n"
        "Commands:\n"
        "/todo <description> - Add a new task\n"
        "/did <description> - Log a completed task\n"
        "/list - View your tasks\n"
        "/focus <number> - Mark task as In Progress\n"
        "/done <number> - Mark task as Complete"
    )
    
    try:
        users = Todo.get_all_users()
        logger.info(f"Sending reminders to {len(users)} users")
        
        for user_id in users:
            await context.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Sent reminder to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send reminders: {e}")

async def morning_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send morning reminder to plan daily tasks."""
    logger.info("Running morning reminder job")
    
    # Check if it's Sunday (weekday() returns 6 for Sunday)
    if datetime.now().weekday() == 6:
        logger.info("Skipping morning reminder - it's Sunday")
        return
    
    try:
        users = Todo.get_all_users()
        logger.info(f"Sending morning reminders to {len(users)} users")
        
        for user_id in users:
            user_info = await context.bot.get_chat(user_id)
            username = user_info.first_name
            
            message = (
                f"Hey {username}! 🌅\n\n"
                f"Help me list out the things you gonna do today. "
                f"I would love to help you keep track of them!\n\n"
                f"Just use /todo followed by your task description, like:\n"
                f"/todo Complete project presentation"
            )
            
            await context.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Sent morning reminder to user {user_id}")
            
    except Exception as e:
        logger.error(f"Failed to send morning reminders: {e}")

# Add these new handlers for photos
async def handle_todo_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos with /todo caption."""
    if not update.message.caption or not update.message.caption.startswith('/todo'):
        return
    
    user_id = update.effective_user.id
    image_file_id = update.message.photo[-1].file_id
    logger.info(f"Handling todo photo with file ID: {image_file_id}")
    
    # Get caption text without the command
    task = update.message.caption.replace('/todo', '').strip()
    if not task:
        task = "📷 Image task"
    
    if Todo.create(user_id, task, TaskState.TODO, image_file_id):
        await update.message.reply_text(f"Task added: {task}")
    else:
        await update.message.reply_text("Failed to add task. Please try again.")

async def handle_did_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos with /did caption."""
    if not update.message.caption or not update.message.caption.startswith('/did'):
        return
    
    user_id = update.effective_user.id
    image_file_id = update.message.photo[-1].file_id
    logger.info(f"Handling did photo with file ID: {image_file_id}")
    
    # Get caption text without the command
    task = update.message.caption.replace('/did', '').strip()
    if not task:
        task = "📷 Image task completed"
    
    if Todo.create(user_id, task, TaskState.DONE, image_file_id):
        await update.message.reply_text(f"✅ Logged completed task: {task}")
    else:
        await update.message.reply_text("Failed to log the task. Please try again.")

def main():
    """Start the bot."""
    # Get token from environment variable
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return

    # Create the Application and pass your bot's token
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("todo", add_task))
    application.add_handler(CommandHandler("did", did_task))
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("done_list", list_done))
    application.add_handler(CommandHandler("focus", focus))
    application.add_handler(CommandHandler("done", done_task))

    # Add photo handlers
    application.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex('^/todo'),
        handle_todo_photo
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO & filters.CaptionRegex('^/did'),
        handle_did_photo
    ))

    # Add job queues
    job_queue = application.job_queue
    
    # 2-hour check-in reminder
    job_queue.run_repeating(
        check_progress, 
        interval=7200,
        first=10,
        name='check_progress'
    )
    logger.info("Configured check_progress job (2-hour interval)")
    
    # Daily morning reminder at 5 AM
    job_queue.run_daily(
        morning_reminder,
        time=time(hour=5, minute=0),  # 5:00 AM
        days=(0, 1, 2, 3, 4, 5),  # Monday to Saturday (0 = Monday, 6 = Sunday)
        name='morning_reminder'
    )
    logger.info("Configured morning_reminder job (daily at 5 AM except Sundays)")

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main() 