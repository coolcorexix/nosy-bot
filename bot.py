import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from models.todo import Todo
from enum import IntEnum
from datetime import datetime, timedelta

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
    await update.message.reply_text(f'Hi {user.first_name}! I am your bot. Nice to meet you!')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
Available commands:
/start - Start the bot
/help - Show this help message
/task <task description> - Add a new task
/list - Show all your tasks
/done <task number> - Mark a task as done (removes it)
/start_task <task number> - Mark a task as WIP
/done <task number> - Mark a task as done
    """
    await update.message.reply_text(help_text)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a task to the todo list."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Please provide a task description.\nUsage: /task Buy groceries")
        return
    
    task = ' '.join(context.args)
    
    if Todo.create(user_id, task):
        await update.message.reply_text(f"Task added: {task}")
    else:
        await update.message.reply_text("Failed to add task. Please try again.")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all tasks."""
    user_id = update.effective_user.id
    
    tasks = Todo.get_all_by_user(user_id)
    
    if not tasks:
        await update.message.reply_text("You have no tasks!")
        return
    
    task_list = []
    for task_id, task, state in tasks:
        emoji = "📌" if state == "TODO" else "🚀" if state == "WIP" else "✅"
        task_list.append(f"{emoji} {task_id}. {task} [{state}]")
    
    await update.message.reply_text("Your tasks:\n" + "\n".join(task_list))

async def start_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a task as WIP."""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Please provide a task number.\nUsage: /start_task 1")
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

async def check_progress(context: ContextTypes.DEFAULT_TYPE):
    """Check progress on active tasks."""
    active_tasks = Todo.get_active_tasks()
    
    for task_id, user_id, task, state in active_tasks:
        state_name = TaskState(state).name
        message = (
            f"🔔 Progress Check-in!\n"
            f"Task: {task}\n"
            f"Current State: {state_name}\n\n"
            f"Update status with:\n"
            f"/start_task {task_id} - Mark as In Progress\n"
            f"/done {task_id} - Mark as Complete"
        )
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user_id}: {e}")

def main():
    """Start the bot."""
    # Create the Application and pass your bot's token
    application = Application.builder().token('7946888295:AAHN9z2ZCQjKIzXuVWAw3Lovo05apgYO8IM').build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("task", add_task))
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("start_task", start_task))
    application.add_handler(CommandHandler("done", done_task))

    # Add job queue for periodic check-ins
    job_queue = application.job_queue
    job_queue.run_repeating(check_progress, interval=30, first=30)

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 