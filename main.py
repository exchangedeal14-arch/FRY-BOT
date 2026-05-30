import os
import logging
from threading import Thread
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pyrogram import Client
from pyrogram.types import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Userbot")

# --- RAILWAY AUTO-PORT FIX ---
def run_fake_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('', port)
    try:
        httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
        logger.info(f"Railway port verification active on port {port}")
        httpd.serve_forever()
    except Exception as e:
        logger.error(f"Server error: {e}")

Thread(target=run_fake_server, daemon=True).start()

# --- ENVIRONMENT VARIABLES ---
API_ID = int(os.environ.get("API_ID", 21987250))
API_HASH = os.environ.get("API_HASH", "d91bb537b5ed554e5ba360d314187a68")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

app = Client(
    "my_userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING.strip() if SESSION_STRING else None,
    in_memory=True
)

# In-Memory Database
shortcuts_db = {}
user_states = {}

@app.on_message()
async def handle_all_messages(client, message: Message):
    if not message.text:
        return
        
    if not message.from_user or not message.from_user.is_self:
        return

    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- HANDLING SAVE STATE (Must come first to intercept incoming text) ---
    if user_id in user_states and user_states[user_id]["action"] == "waiting_for_msg":
        shortcut_name = user_states[user_id]["shortcut_name"]
        
        # Storing markdown text safely
        shortcuts_db[shortcut_name] = message.text.markdown
        del user_states[user_id]
        
        # Delete your input message and send a fresh confirmation
        await message.delete()
        await client.send_message(chat_id, f"✅ **Saved successfully!**\nYou can now use `.{shortcut_name}` anywhere.")
        return

    # --- COMMAND 1: .alive ---
    if text.lower() == ".alive":
        await message.edit_text("✨ Zyron Userbot is Active and Running Smoothly!")
        return

    # --- COMMAND 2: .list ---
    if text.lower() == ".list":
        if not shortcuts_db:
            await message.edit_text("❌ No shortcuts found! Use `.add <name>` to create one.")
        else:
            shortcuts_list = "\n".join([f"🔹 .{k}" for k in shortcuts_db.keys()])
            await message.edit_text(f"📋 **Your Saved Shortcuts:**\n\n{shortcuts_list}")
        return

    # --- COMMAND 3: .del <name> ---
    if text.startswith(".del "):
        try:
            shortcut_name = text.split(" ", 1)[1].lower()
            if shortcut_name in shortcuts_db:
                del shortcuts_db[shortcut_name]
                await message.edit_text(f"✅ Shortcut `.{shortcut_name}` has been deleted successfully.")
            else:
                await message.edit_text(f"❌ Shortcut `.{shortcut_name}` not found!")
        except Exception as e:
            logger.error(f"Error in del command: {e}")
        return

    # --- COMMAND 4: .add <name> ---
    if text.startswith(".add ") or text.startswith("/add "):
        try:
            shortcut_name = text.split(" ", 1)[1].lower()
            user_states[user_id] = {"action": "waiting_for_msg", "shortcut_name": shortcut_name}
            await message.edit_text(f"📝 **Send the message you want to save for `.{shortcut_name}`**\n*(Bold, Mono, Italic formatting is fully supported)*")
        except Exception as e:
            logger.error(f"Error in add command: {e}")
        return

    # --- TRIGGERING THE SHORTCUT ---
    if text.startswith("."):
        shortcut_trigger = text[1:].lower()
        if shortcut_trigger in shortcuts_db:
            saved_reply = shortcuts_db[shortcut_trigger]
            
            # Send the saved markdown message and delete the trigger command
            await client.send_message(chat_id, saved_reply)
            await message.delete()
            return

if __name__ == "__main__":
    logger.info("Starting Fully Loaded Userbot...")
    app.run()
    
