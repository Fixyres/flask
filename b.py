import logging
import base64
import requests
import telebot
from telebot import types
import os
import json

API_TOKEN = '7814832573:AAFzU8ussqOfGfV0atogRJ5tr9pMoGpp4YE'
GITHUB_TOKEN = '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'
GITHUB_REPO = 'fixyres/Modules'
ADMIN_CHAT_ID = -1002476551431
UPLOAD_FOLDER = 'uploads'
CONFIG_FOLDER = 'config'
CONFIG_FILE = os.path.join(CONFIG_FOLDER, 'modules_config.json')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(CONFIG_FOLDER):
    os.makedirs(CONFIG_FOLDER)

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(message.chat.id, f"👋 **Hello** [{message.from_user.full_name}](tg://user?id={message.from_user.id})!\n\n**To upload your module to** `FHeta`**, send it to me!**", parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not message.document.file_name.endswith('.py'):
        return None

    user_message = bot.send_message(message.chat.id, "📥 **Received your file! Now, let me forward it to the admins for approval.**", parse_mode='Markdown')
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    file_path = os.path.join(UPLOAD_FOLDER, message.document.file_name)
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    approve_keyboard = types.InlineKeyboardMarkup()
    approve_button = types.InlineKeyboardButton("✅ Approve", callback_data=f"approve:{message.document.file_name}:{message.from_user.id}:{user_message.message_id}")
    decline_button = types.InlineKeyboardButton("❌ Decline", callback_data=f"decline:{message.document.file_name}:{message.from_user.id}:{user_message.message_id}")
    approve_keyboard.add(approve_button, decline_button)

    bot.send_message(ADMIN_CHAT_ID, "📩 Do you approve it?", reply_markup=approve_keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve:') or call.data.startswith('decline:'))
def process_approval(call):
    data = call.data.split(':')
    action = data[0]
    file_name = data[1]
    user_id = int(data[2])
    user_message_id = int(data[3])

    bot.delete_message(ADMIN_CHAT_ID, call.message.id)

    if action == 'approve':
        upload_to_github(file_name, user_id, user_message_id)
    else:
        bot.send_message(user_id, "❌ **The addition of your module has been declined.**", parse_mode='Markdown')
        bot.delete_message(ADMIN_CHAT_ID, call.message.id)

def upload_to_github(file_name, user_id, user_message_id):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_name}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }
    file_path = os.path.join(UPLOAD_FOLDER, file_name)

    with open(file_path, 'rb') as file:
        content = file.read()
        encoded_content = base64.b64encode(content).decode()

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            existing_file = response.json()
            sha = existing_file['sha']
            data = {
                'message': f'Update {file_name}',
                'content': encoded_content,
                'sha': sha
            }
            response = requests.put(url, headers=headers, json=data)
            if response.status_code == 200:
                bot.send_message(ADMIN_CHAT_ID, f"✅ **Module** `{file_name[:-3]}` **updated successfully!**", parse_mode='Markdown')
                bot.send_message(user_id, f"✅ **Your module has been updated! You can find it by the query** `{file_name[:-3]}`**.**", parse_mode='Markdown')
                update_config(file_name, user_id)
                bot.delete_message(user_id, user_message_id)
            else:
                bot.send_message(user_id, "❌ **There was an error updating your module.**", parse_mode='Markdown')
        else:
            data = {
                'message': f'Add {file_name}',
                'content': encoded_content
            }
            response = requests.put(url, headers=headers, json=data)
            if response.status_code == 201:
                bot.send_message(ADMIN_CHAT_ID, f"✅ **Module** `{file_name[:-3]}` **uploaded successfully!**")
                bot.send_message(user_id, f"✅ **Your module has been added! You can find it by the query** `{file_name[:-3]}`**.**", parse_mode='Markdown')
                update_config(file_name, user_id)
                bot.delete_message(user_id, user_message_id)
            else:
                bot.send_message(user_id, "❌ **There was an error adding your module.**", parse_mode='Markdown')

def update_config(file_name, user_id):
    config_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{os.path.basename(CONFIG_FILE)}"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json'
    }

    response = requests.get(config_url, headers=headers)

    if response.status_code == 200:
        existing_file = response.json()
        sha = existing_file['sha']
        content = requests.get(existing_file['download_url']).content.decode()

        modules = {}
        if content:
            modules = json.loads(content)
        
        modules[file_name[:-3]] = user_id
        encoded_content = base64.b64encode(json.dumps(modules).encode()).decode()

        data = {
            'message': f'Update {os.path.basename(CONFIG_FILE)}',
            'content': encoded_content,
            'sha': sha
        }
        response = requests.put(config_url, headers=headers, json=data)
        if response.status_code == 200:
            logging.info("Config updated successfully.")
        else:
            logging.error(f"Failed to update config: {response.content}")
    else:
        modules = {file_name[:-3]: user_id}
        encoded_content = base64.b64encode(json.dumps(modules).encode()).decode()
        
        data = {
            'message': f'Add {os.path.basename(CONFIG_FILE)}',
            'content': encoded_content
        }
        response = requests.put(config_url, headers=headers, json=data)
        if response.status_code == 201:
            logging.info("Config created successfully.")
        else:
            logging.error(f"Failed to create config: {response.content}")

bot.polling()
