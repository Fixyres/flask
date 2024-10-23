import logging
import base64
import requests
import telebot
from telebot import types
import os

API_TOKEN = '7814832573:AAFzU8ussqOfGfV0atogRJ5tr9pMoGpp4YE'
GITHUB_TOKEN = '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'
GITHUB_REPO = 'Fixyres/Modules'
ADMIN_CHAT_ID = -1002476551431
UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(API_TOKEN)

user_messages = {}

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(message.chat.id, f"👋 **Hello** [{message.from_user.full_name}](tg://user?id={message.from_user.id})!\n\n**To upload your module to** `FHeta`, **send it to me!**", parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not message.document.file_name.endswith('.py'):
        return None
    
    msg = bot.send_message(message.chat.id, "📥 **Received your file! Now, let me forward it to the admins for approval.**", parse_mode='Markdown')
    
    user_messages[message.from_user.id] = msg.message_id
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_path = os.path.join(UPLOAD_FOLDER, message.document.file_name)
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    admin_message = bot.send_document(ADMIN_CHAT_ID, message.document.file_id)

    approve_keyboard = types.InlineKeyboardMarkup()
    approve_button = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve:{message.document.file_name}:{admin_message.message_id}:{message.from_user.id}")
    decline_button = types.InlineKeyboardButton("❌ Decline", callback_data=f"decline:{message.document.file_name}:{admin_message.message_id}:{message.from_user.id}")
    approve_keyboard.add(approve_button, decline_button)

    bot.send_message(ADMIN_CHAT_ID, "📩 Do you approve it?", reply_markup=approve_keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve:') or call.data.startswith('decline:'))
def process_approval(call):
    data = call.data.split(':')
    action = data[0]
    file_name = data[1]
    admin_message_id = int(data[2])
    user_id = int(data[3])

    bot.delete_message(ADMIN_CHAT_ID, admin_message_id)
    bot.delete_message(ADMIN_CHAT_ID, call.message.message_id)

    if user_id in user_messages:
        bot.delete_message(user_id, user_messages[user_id])
        del user_messages[user_id]

    if action == 'approve':
        upload_to_github(file_name)
        bot.send_message(ADMIN_CHAT_ID, f"✅ Module `{file_name[:-3]}` approved!", parse_mode='Markdown')
        bot.send_message(user_id, f"✅ Your module has been approved! You can find it by the query `{file_name[:-3]}`.", parse_mode='Markdown')
    else:
        bot.send_message(ADMIN_CHAT_ID, f"❌ You have successfully declined the submission of `{file_name[:-3]}`!", parse_mode='Markdown')
        bot.send_message(user_id, "❌ The addition of your module has been declined.", parse_mode='Markdown')

def upload_to_github(file_name):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_name}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    file_path = os.path.join(UPLOAD_FOLDER, file_name)
    with open(file_path, 'rb') as file:
        content = file.read()
        encoded_content = base64.b64encode(content).decode()
        data = {
            'message': f'Add {file_name}',
            'content': encoded_content
        }
        response = requests.put(url, headers=headers, json=data)
        if response.status_code == 201:
            print("File uploaded successfully.")
        elif response.status_code == 200:
            print("File updated successfully.")
        else:
            print(f"Failed to upload file: {response.content}")

bot.polling()
