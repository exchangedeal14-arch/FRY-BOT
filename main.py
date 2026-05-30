import os
import logging
import sqlite3
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

# --- PERSISTENT SQLITE DATABASE ---
DB_FILE = "shortcuts.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shortcuts (
            name TEXT PRIMARY KEY,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_shortcut(name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM shortcuts WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def save_shortcut(name, content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO shortcuts (name, content) VALUES (?, ?)", (name, content))
    conn.commit()
    conn.close()

def delete_shortcut(name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shortcuts WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def list_shortcuts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM shortcuts")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


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

user_states = {}

@app.on_message()
async def handle_all_messages(client, message: Message):
    if not message.text or not message.from_user or not message.from_user.is_self:
        return

    text = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- STATE INTERCEPTOR: SAVING SHORTCUT CONTENT ---
    if user_id in user_states and user_states[user_id]["action"] == "waiting_for_msg":
        shortcut_name = user_states[user_id]["shortcut_name"]
        
        save_shortcut(shortcut_name, message.text)
        del user_states[user_id]
        
        await message.delete()
        await client.send_message(chat_id, f"✅ **Saved successfully!**\nYou can now use `.{shortcut_name}` anywhere.")
        return

    # --- COMMAND 1: .alive ---
    if text.lower() == ".alive":
        await message.edit_text("✨ Zyron Userbot is Active and Running Smoothly!")
        return

    # --- COMMAND 2: .list ---
    if text.lower() == ".list":
        shortcuts = list_shortcuts()
        if not shortcuts:
            await message.edit_text("❌ No shortcuts found! Use `.add <name>` to create one.")
        else:
            shortcuts_list = "\n".join([f"🔹 .{k}" for k in shortcuts])
            await message.edit_text(f"📋 **Your Saved Shortcuts:**\n\n{shortcuts_list}")
        return

    # --- COMMAND 3: .del <name> ---
    if text.startswith(".del "):
        try:
            shortcut_name = text.split(" ", 1)[1].strip().lower()
            if get_shortcut(shortcut_name):
                delete_shortcut(shortcut_name)
                await message.edit_text(f"✅ Shortcut `.{shortcut_name}` has been deleted successfully.")
            else:
                await message.edit_text(f"❌ Shortcut `.{shortcut_name}` not found!")
        except Exception as e:
            logger.error(f"Error in del command: {e}")
        return

    # --- COMMAND 4: .add <name> or .a <name> ---
    if text.startswith(".a ") or text.startswith(".add "):
        try:
            shortcut_name = text.split(" ", 1)[1].strip().lower()
            user_states[user_id] = {"action": "waiting_for_msg", "shortcut_name": shortcut_name}
            await message.edit_text(f"📝 **Send the message you want to save for `.{shortcut_name}`**\n*(Formatting is fully supported)*")
        except Exception as e:
            logger.error(f"Error in add command: {e}")
        return

    # --- TRIGGERING THE SHORTCUT ---
    if text.startswith("."):
        parts = text.split(" ", 1)
        shortcut_trigger = parts[0][1:].lower() 
        
        saved_reply = get_shortcut(shortcut_trigger)
        if saved_reply:
            extra_text = f"\n{parts[1]}" if len(parts) > 1 else ""
            
            # Check if the trigger command was replying to another message
            reply_to_id = message.reply_to_message.id if message.reply_to_message else None
            
            # Send the shortcut, targetting the reply message ID if it exists
            await client.send_message(
                chat_id, 
                f"{saved_reply}{extra_text}", 
                reply_to_message_id=reply_to_id
            )
            await message.delete()
            return

if __name__ == "__main__":
    logger.info("Starting Fully Loaded Userbot...")
    app.run()
    
