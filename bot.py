import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from models.todo import Todo, TaskState
from models.base import Database
from enum import IntEnum
from datetime import datetime, timedelta, time
import os
from dotenv import load_dotenv
import pytz
from openai import OpenAI
import requests

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Create logger
logger = logging.getLogger(__name__)

# Initialize database with absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "nosy_bot.db")
print(f"Using database at: {db_path}")
db = Database(db_path)

# Update Todo class to use our database instance
Todo.db = db

# Add states for conversation
WAITING_FOR_CANCEL_REASON = 1

# Store temporary data
cancel_task_ids = {}

# Add timezone configuration
TIMEZONE = pytz.timezone('Asia/Bangkok')  # UTC+7

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I am your bot. Nice to meet you!\n"
        "Type /help to know more on how to use me."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:
/help - Show this help message
/todo <description> - Add a new task
/focus <number> - Mark task as WIP
/did <description> - Log a completed task
/done <number> - Mark task as done
/cancel <number> - Cancel a task
/list - Show active tasks
/cancelled - Show cancelled tasks
/summarize <number_of_days> - Summarize completed tasks for the user
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
    
    task_id = Todo.create(user_id, task, TaskState.TODO)
    if task_id:
        await update.message.reply_text(f"Task added: {task} (ID: {task_id})")
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
    """Send periodic reminders to update task list during working hours on weekdays."""
    logger.info("Running check_progress job")
    
    # Get current time in UTC+7
    current_time = datetime.now(TIMEZONE)
    current_hour = current_time.hour
    current_weekday = current_time.weekday()  # 0-6 (Monday-Sunday)
    
    # Check if it's weekend (Saturday=5 or Sunday=6)
    if current_weekday >= 5:
        logger.info("Skipping check_progress - it's weekend")
        return
        
    # Check if it's outside working hours (9 AM - 5 PM)
    if current_hour < 9 or current_hour >= 17:
        logger.info(f"Skipping check_progress - outside working hours (current hour: {current_hour})")
        return
    
    try:
        users = Todo.get_all_users()
        logger.info(f"Sending reminders to {len(users)} users")
        
        for user_id in users:
            # Get user's name
            user_info = await context.bot.get_chat(user_id)
            username = user_info.first_name
            
            message = (
                f"Hey {username}! 👋 How are things going?\n\n"
                "Here's what you can do:\n"
                "/todo <description> - Add a new task\n"
                "/did <description> - Log a completed task\n"
                "/list - View your tasks\n"
                "/focus <number> - Mark task as In Progress\n"
                "/done <number> - Mark task as Complete"
            )
            
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
                f"Hi {username}! 🌅\n\n"
                f"What are you gonna do today? \n"
                f"Use /list to see your active tasks. \n"
                f"And use /todo to add a new task, like:\n"
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
    
    task_id = Todo.create(user_id, task, TaskState.TODO, image_file_id)
    if task_id:
        await update.message.reply_text(f"Task added: {task} (ID: {task_id})")
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

async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the cancel task process."""
    print("\n=== CANCEL TASK FUNCTION ===")
    print("[DEBUG] Entering cancel_task function")
    user_id = update.effective_user.id
    print(f"[DEBUG] User {user_id} initiated task cancellation")

    if not context.args:
        await update.message.reply_text("Please provide a task number.\nUsage: /cancel 1")
        return ConversationHandler.END
    
    try:
        task_id = int(context.args[0])
        print(f"[DEBUG] Task ID {task_id} received for cancellation")
        print(f"[DEBUG] Current conversation state: {context.user_data.get('state', 'None')}")
    except ValueError:
        await update.message.reply_text("Please provide a valid task number.")
        return ConversationHandler.END
    
    # Store the task_id temporarily
    cancel_task_ids[user_id] = task_id
    print(f"[DEBUG] Stored task_id {task_id} for user {user_id}")
    print(f"[DEBUG] Setting state to WAITING_FOR_CANCEL_REASON")
    context.user_data['state'] = WAITING_FOR_CANCEL_REASON
    
    await update.message.reply_text(
        "Why are you cancelling this task? Please provide a reason."
    )
    print("[DEBUG] Returning WAITING_FOR_CANCEL_REASON state")
    return WAITING_FOR_CANCEL_REASON

async def handle_cancel_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the cancel reason and update the task."""
    print("\n=== HANDLE CANCEL REASON FUNCTION ===")
    print("[DEBUG] Entering handle_cancel_reason function")
    print(f"[DEBUG] Current state: {context.user_data.get('state', 'None')}")
    print(f"[DEBUG] Message text received: {update.message.text}")
    
    user_id = update.effective_user.id
    task_id = cancel_task_ids.get(user_id)
    print(f"[DEBUG] User ID: {user_id}")
    print(f"[DEBUG] Task ID from storage: {task_id}")

    if not task_id:
        print("[DEBUG] No task_id found in storage")
        await update.message.reply_text("Something went wrong. Please try again.")
        return ConversationHandler.END
    
    cancel_reason = update.message.text
    print(f"[DEBUG] Cancel reason received: {cancel_reason}")

    if Todo.cancel_task(task_id, user_id, cancel_reason):
        print(f"[DEBUG] Successfully cancelled task {task_id}")
        await update.message.reply_text(f"Task {task_id} cancelled.\nReason: {cancel_reason}")
    else:
        print(f"[DEBUG] Failed to cancel task {task_id}")
        await update.message.reply_text(
            "Failed to cancel task. Please check if the task exists and isn't already completed."
        )
    
    # Clean up
    del cancel_task_ids[user_id]
    context.user_data.pop('state', None)
    print("[DEBUG] Cleanup completed, ending conversation")
    return ConversationHandler.END

async def list_cancelled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List cancelled tasks."""
    user_id = update.effective_user.id
    
    tasks = Todo.get_cancelled_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text("You have no cancelled tasks!")
        return
    
    await update.message.reply_text("❌ Cancelled Tasks:")
    for task_id, task, state, image_file_id, cancel_reason in tasks:
        message = f"❌ {task_id}. {task}\nReason: {cancel_reason}"
        
        if image_file_id:
            await update.message.reply_photo(
                photo=image_file_id,
                caption=message
            )
        else:
            await update.message.reply_text(message)

async def generate_weekly_summary(context: ContextTypes.DEFAULT_TYPE):
    """Generate and send weekly summaries for all users."""
    logger.info("Generating weekly summaries")
    
    # Get end date (now) and start date (7 days ago)
    end_date = datetime.now(TIMEZONE)
    start_date = end_date - timedelta(days=7)
    
    try:
        users = Todo.get_all_users()
        logger.info(f"Generating summaries for {len(users)} users")
        
        for user_id in users:
            # Get completed tasks for the week
            completed_tasks = Todo.get_tasks_completed_in_range(user_id, start_date, end_date)
            
            if not completed_tasks:
                continue  # Skip users with no completed tasks
            
            # Format tasks for GPT
            task_list = "\n".join([f"- {task}" for _, task, _, _ in completed_tasks])
            
            # Generate summary using GPT
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a friendly personal assistant. Write a brief, engaging summary of someone's week based on their completed tasks. Make it personal and encouraging. Keep it to 2-3 paragraphs."},
                        {"role": "user", "content": f"Here are the tasks they completed this week:\n{task_list}"}
                    ]
                )
                
                summary = response.choices[0].message.content
                
                # Get user's name
                user_info = await context.bot.get_chat(user_id)
                username = user_info.first_name
                
                # Send the weekly summary
                message = (
                    f"📖 Weekly Summary for {username}\n"
                    f"Week of {start_date.strftime('%B %d')} - {end_date.strftime('%B %d')}\n\n"
                    f"{summary}\n\n"
                    f"You completed {len(completed_tasks)} tasks this week! 🎉"
                )
                
                await context.bot.send_message(chat_id=user_id, text=message)
                logger.info(f"Sent weekly summary to user {user_id}")
                
            except Exception as e:
                logger.error(f"Error generating summary for user {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Error in weekly summary generation: {e}")

async def summarize_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summarize completed tasks for the user."""
    user_id = update.effective_user.id
    print('aaaa: ', user_id)
    
    # Get optional days parameter
    days = 7  # default
    if context.args:
        try:
            days = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "Invalid number of days. Using default (7 days).\n"
                "Usage: /summarize [number_of_days]"
            )
    
    # Send initial message
    status_message = await update.message.reply_text("🤔 Analyzing your completed tasks...")
    
    try:
        # Call the summary endpoint using requests
        response = requests.post(
            'http://localhost:2108/api/summarize_done',
            json={
                'user_id': user_id,
                'days': days
            }
        )
        
        data = response.json()
        
        if 'error' in data:
            await status_message.edit_text(f"❌ Error: {data['error']}")
            return
        
        # Format the response
        summary = data['summary']
        total_tasks = data.get('total_tasks', 0)
        
        message = (
            f"📊 *Summary of your last {days} days*\n\n"
            f"{summary}\n\n"
            f"Total tasks completed: {total_tasks}"
        )
        
        await status_message.edit_text(
            message,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        await status_message.edit_text(
            "❌ Sorry, I couldn't generate your summary right now. Please try again later."
        )

def main():
    """Start the bot."""
    # Get token from environment variable
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is not set!")
        return

    # Create the Application and pass your bot's token
    application = Application.builder().token(bot_token).build()

    # 1. First, add the conversation handler
    cancel_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("cancel", cancel_task)
        ],
        states={
            WAITING_FOR_CANCEL_REASON: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    handle_cancel_reason,
                    block=True
                )
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_task),
            CommandHandler("help", help_command)
        ],
        allow_reentry=True,
        name="cancel_conversation"
    )
    
    # Add conversation handler in group 1
    application.add_handler(cancel_conv_handler, group=1)

    # 2. Then add all other command handlers in group 2
    handlers_group2 = [
        CommandHandler("start", start),
        CommandHandler("help", help_command),
        CommandHandler("todo", add_task),
        CommandHandler("td", add_task),
        CommandHandler("did", did_task),
        CommandHandler("list", list_tasks),
        CommandHandler("l", list_tasks),
        CommandHandler("done_list", list_done),
        CommandHandler("focus", focus),
        CommandHandler("done", done_task),
        CommandHandler("cancelled", list_cancelled),
        CommandHandler("summarize", summarize_tasks),
        MessageHandler(
            filters.PHOTO & filters.CaptionRegex('^/todo'),
            handle_todo_photo
        ),
        MessageHandler(
            filters.PHOTO & filters.CaptionRegex('^/did'),
            handle_did_photo
        )
    ]

    # Add all other handlers in group 2
    for handler in handlers_group2:
        application.add_handler(handler, group=2)

    # Add job queues
    job_queue = application.job_queue
    
    # Check-in reminder during working hours (8-hour window)
    job_queue.run_repeating(
        check_progress,
        interval=7200,  # 2-hour interval
        first=10,
        name='check_progress'
    )
    logger.info("Configured check_progress job (2-hour interval)")
    
    # Daily morning reminder at 5 AM
    job_queue.run_daily(
        morning_reminder,
        time=time(hour=5, minute=0, tzinfo=TIMEZONE),  # 5:00 AM UTC+7
        days=(0, 1, 2, 3, 4, 5),  # Monday to Saturday (0 = Monday, 6 = Sunday)
        name='morning_reminder'
    )
    logger.info("Configured morning_reminder job (daily at 5 AM except Sundays)")

    # Add weekly summary on Sundays at 8 PM
    job_queue.run_daily(
        generate_weekly_summary,
        time=time(hour=20, minute=0, tzinfo=TIMEZONE),  # 8:00 PM UTC+7
        days=[6],  # Sunday only
        name='weekly_summary'
    )
    logger.info("Configured weekly_summary job (Sundays at 8 PM)")

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling()

if __name__ == '__main__':
    main() 