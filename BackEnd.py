from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import sqlite3
import os
import bcrypt
import re
import tiktoken
from agents.scheduler_agent import agent
import json

app = Flask(__name__)
CORS(app)

# Đường dẫn database SQLite
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Database.db")

# Khởi tạo SQLite database
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                account TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account) REFERENCES users (account)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Chatbots (
                avatarResId INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                system_message TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Callbots (
                avatarResId INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                system_message TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_information (
                account TEXT PRIMARY KEY,
                name TEXT,
                house TEXT,
                birth_year INTEGER,
                email TEXT,
                hierarchy TEXT,
                position TEXT NOT NULL CHECK (position IN ('High Commander', 'Legion Commander', 'Captain', 'Lieutenant', 'Soldier')),
                legion TEXT CHECK (legion IN ('Crusader Legion', 'Steel Legion', 'Celestial Legion') OR legion IS NULL),
                company TEXT CHECK (
                    (legion = 'Crusader Legion' AND (company IN ('Crusader Battalion', 'Knight Division') OR company IS NULL)) OR
                    (legion = 'Steel Legion' AND (company IN ('Shieldwall Division', 'Siege Engine Corps') OR company IS NULL)) OR
                    (legion = 'Celestial Legion' AND (company IN ('Divine Vanguard', 'Holy Guard Division') OR company IS NULL)) OR
                    legion IS NULL
                ),
                platoon TEXT CHECK (platoon IN ('Knight Squad', 'Vanguard Unit', 'Scouting Party') OR platoon IS NULL),
                FOREIGN KEY (account) REFERENCES users(account),
                FOREIGN KEY (email) REFERENCES users(email)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deleted_profiles (
                account TEXT NOT NULL,
                email TEXT NOT NULL,
                deleted_by TEXT NOT NULL,
                time_deleted TEXT NOT NULL,
                FOREIGN KEY (account) REFERENCES users(account)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timetable_events (
                id TEXT PRIMARY KEY, -- ID duy nhất cho sự kiện (có thể dùng UUID)
                title TEXT NOT NULL, -- Tên sự kiện (e.g., "Huấn luyện bắn súng")
                start_time INTEGER NOT NULL, -- Thời gian bắt đầu (timestamp)
                end_time INTEGER NOT NULL, -- Thời gian kết thúc (timestamp)
                location TEXT, -- Địa điểm (có thể null)
                participants TEXT, -- Danh sách ID nhân sự (lưu dưới dạng JSON hoặc chuỗi phân tách)
                type TEXT NOT NULL, -- Loại sự kiện (TRAINING, PATROL, MEETING, OTHER)
                status TEXT NOT NULL -- Trạng thái (PENDING, ONGOING, COMPLETED)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gears_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account TEXT NOT NULL,
            gear_type TEXT NOT NULL CHECK (gear_type IN ('HELMET', 'ARMOR', 'GAUNTLET', 'LONG_SWORD', 'ZWEIHANDER', 'BOW', 'ARROW', 'SHIELD', 'HORSE')),
            gear_quantity INTEGER NOT NULL CHECK (gear_quantity >= 0 AND (gear_type = 'HORSE' AND gear_quantity = 0 OR gear_type != 'HORSE')),
            gear_name TEXT CHECK (gear_type = 'HORSE' AND gear_name IS NOT NULL OR gear_type != 'HORSE'),
            FOREIGN KEY (account) REFERENCES users(account) ON DELETE CASCADE
        )
        """)
        conn.commit()

init_db()

#Tools
tools = [
    {
    "name": "schedule_training",
    "description": "Function to schedule for training",
    "strict": True,
    "parameters": {
        "type": "object",
        "required": [
            "time_start",
            "time_end",
            "host",
            "content"
        ],
        "properties": {
            "time_start": {
                "type": "string",
                "description": "Start time of the training session in ISO 8601 format"
            },
            "time_end": {
                "type": "string",
                "description": "End time of the training session in ISO 8601 format"
            },
            "host": {
                "type": "string",
                "description": "Name of the host for the training session"
            },
            "content": {
                "type": "string",
                "description": "Description of the training content"
            }
        },
        "additionalProperties": False
    }
}
]
position_tree = {
    "High Commander": ["Legion Commander", "Captain", "Lieutenant", "Soldier"],
    "Legion Commander": ["Captain", "Lieutenant", "Soldier"],
    "Captain": ["Lieutenant", "Soldier"],
    "Lieutenant": ["Soldier"],
    "Soldier": []
}
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


# Hàm tạo bảng messages cho user và chatbot
def create_user_messages_table(account, chatbot):
    # Đảm bảo tên bảng hợp lệ (thay ký tự không hợp lệ)
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    table_name = f"messages_{safe_account}_to_{re.sub(r'[^a-zA-Z0-9_]', '_', chatbot)}"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                is_user INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    return table_name

# Hàm tóm tắt lịch sử chat
def generate_summary(account, messages):
    chat_text = "\n".join([f"{'User' if msg['is_user'] else 'Bot'}: {msg['text']}" for msg in messages])
    prompt = f"Summarize the following chat history concisely, capturing key context and user preferences:\n\n{chat_text}\n\nSummary:"
    response = client.chat.completions.create(
        model="gemma2:2b",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100
    )
    summary = response.choices[0].message.content.strip()
    return summary

def count_tokens(text):
    """Ước tính số lượng tokens trong một đoạn text."""
    # Sử dụng GPT-2 tokenizer như một ước lượng gần đúng
    encoding = tiktoken.get_encoding("gpt2")
    return len(encoding.encode(text))

def prepare_messages_with_token_limit(system_msg, chat_history, user_input, max_tokens=4096):
    """Chuẩn bị messages cho model với giới hạn token."""
    messages = [{"role": "system", "content": f"{system_msg}, if you do not know the answer, reply 'I don't know'. Keep your response under 200 words."}]
    # Ước tính tokens cho system message và user input mới
    system_tokens = count_tokens(system_msg)
    new_input_tokens = count_tokens(user_input)
    
    # Dự trữ tokens cho response (khoảng 1/3 tổng số tokens)
    reserved_tokens = max_tokens // 3
    available_tokens = max_tokens - system_tokens - new_input_tokens - reserved_tokens
    
    # Thêm tin nhắn từ chat history cho đến khi đạt giới hạn token
    current_tokens = 0
    included_messages = []
    
    for entry in reversed(chat_history):
        user_input_check = entry["content"] if entry.get("role") == "user" else ""
        response = entry["content"] if entry.get("role") == "assistant" else ""
        msg_tokens = count_tokens(user_input_check) + count_tokens(response)
        if current_tokens + msg_tokens > available_tokens:
            break
        included_messages.insert(0, entry)
        current_tokens += msg_tokens
    
    # Tạo messages từ những tin nhắn đã được lọc
    for entry in included_messages:
        if entry["role"] in ["user", "assistant"]:
            messages.append({"role": entry["role"], "content": entry["content"]})
    
    # Thêm user input mới
    messages.append({"role": "user", "content": f"Focus your response: {user_input}"})
    return messages

#Hàm gộp legend, company, platoon vào position bằng switch case
def get_title(position, legion, company, platoon):
    match position:
        case "Soldier":
            return f"{position} of the {platoon}, serving under the {company}, sworn to the command of the {legion}"
        case "Lieutenant":
            return f"{position} of the {company}, sworn to the command of the {legion}" 
        case "Captain":
            return f"{position} sworn to the command of the {legion}"
        case "Legion Commander":
            return f"{position} of the {legion}, in service to the High Commander of the Grand Armies"
        case "High Commander":
            return f"{position} of the Grand Armies"
        
#Hàm gộp tên và house
def get_name_and_house(name, house):
    return f"{name} of house {house}"

# Endpoint: Đăng ký
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    account = data.get("account", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not account or not email or not password:
        return jsonify({"error": "Missing 'account', 'email', or 'password'"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT account, email FROM users WHERE account = ? OR email = ?", (account, email))
            if cursor.fetchone():
                return jsonify({"error": "account or email already exists"}), 409

            cursor.execute("INSERT INTO users (account, email, password) VALUES (?, ?, ?)", 
                          (account, email, hashed_password))
            # Thêm bản ghi user_information cho account mới
            cursor.execute("INSERT INTO user_information (account) VALUES (?)", (account,))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "account or email already exists"}), 409

    return jsonify({"message": "Registration successful"})

# Endpoint: Đăng nhập
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    identifier = data.get("identifier", "").strip()
    password = data.get("password", "").strip()

    if not identifier or not password:
        return jsonify({"error": "Missing 'identifier' or 'password'"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account, password FROM users WHERE account = ? OR email = ?", 
                      (identifier, identifier))
        result = cursor.fetchone()

        if result and bcrypt.checkpw(password.encode('utf-8'), result[1].encode('utf-8')):
            return jsonify({"message": "Login successful", "account": result[0]})
        
        cursor.execute("SELECT account FROM deleted_profiles")
        deleted_account = [row[0] for row in cursor.fetchall()]
        if identifier in deleted_account:
            cursor.execute("SELECT deleted_by, time_deleted FROM deleted_profiles WHERE account = ?", (identifier,))
            deleted_info = cursor.fetchone()
            cursor.execute("SELECT name, house, position, legion, company, platoon FROM user_information WHERE account = ?", (deleted_info[0],))
            deleted_name = cursor.fetchone()
            return jsonify({"error": f"Account has been deleted, by",
                            "name": f"{deleted_name[0]} of house {deleted_name[1]}",
                            "title": get_title(deleted_name[2], deleted_name[3], deleted_name[4], deleted_name[5]),
                            "time_deleted": f"{deleted_info[1]}"}), 401

        return jsonify({"error": "Invalid account/email or password"}), 402

#Endpoint: lấy user_information
@app.route("/getProfile/<account>", methods=["GET"])
def get_profile(account):
    with sqlite3.connect(DB_PATH) as conn:   
        cursor = conn.cursor()
        cursor.execute("SELECT account, name, house, birth_year, email, hierarchy, position, legion, company, platoon FROM user_information WHERE account = ?", (account,))
        row = cursor.fetchone()
        if row:
            keys = ["account", "name", "house", "birth_year", "email", "hierarchy", "position", "legion", "company", "platoon"]
            keys.append("title")
            data = dict(zip(keys, row))
            #Gộp họ và tên
            if data["name"] and data["house"]:
                data["name"] = f'{data["name"]} of house {data["house"]}'
            data.pop("house", None)
            
            # Tính tuổi nếu có birth_year
            if data.get("birth_year"):
                try:
                    year = int(data["birth_year"])
                    now = datetime.now().year
                    data["age"] = now - year
                except Exception as e:
                    print(f"Exception: {e}")    
            else:
                data["age"] = None

            data["title"] = get_title(data["position"], data["legion"], data["company"], data["platoon"])

            data.pop("platoon", None)
            data.pop("company", None)
            data.pop("legion", None)
            return jsonify(data)
        else:
            return jsonify({"error": "User information not found"}), 404

#Endpoint: lấy danh sách các chatbot
@app.route("/getChatbotList", methods=["GET"])
def get_chatbot_list():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, avatarResId FROM Chatbots")
        chatbots = cursor.fetchall()
        result = [{"name": row[0], "avatarResId": row[1]} for row in chatbots]
    return jsonify(result)

#Endpoint: lấy danh sách các Callbots
@app.route("/getCallbotList", methods=["GET"])
def get_Callbots_list():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, avatarResId FROM Callbots")
        chatbots = cursor.fetchall()
        result = [{"name": row[0], "avatarResId": row[1]} for row in chatbots]
    return jsonify(result)
    
#Endpoint: Tạo đoạn chat user và chatbot
@app.route("/make_message/<account>/<chatbot>", methods=["POST"])
def make_message(account, chatbot):
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    create_user_messages_table(safe_account, chatbot)

# Hàm tạo bảng calls cho user và callbot
def create_user_calls_table(account, callbot):
    # Đảm bảo tên bảng hợp lệ (thay ký tự không hợp lệ)
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    table_name = f"calls_{safe_account}_to_{re.sub(r'[^a-zA-Z0-9_]', '_', callbot)}"

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name, house, birth_year, position, legion, company, platoon FROM user_information WHERE account = ?", (account,))
        user_info = cursor.fetchone()
        if user_info:
            name, house, birth_year, position, legion, company, platoon = user_info
            title = get_title(position, legion, company, platoon)
            name = f"{name} of house {house}"
            if birth_year:
                now = datetime.now().year
                age = now - int(birth_year)
            else:
                age = None
            data = {"name": name, "title": title, "account": account, "age": age}
            #bỏ data vào promt
            prompt = f"""
            I am {data["name"]}, {data["title"]}, {data["age"]} years old.
            I am calling you to {callbot}.
            """
            #bỏ prompt vào text
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                is_user INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, ?)", (prompt, True))
        conn.commit()
    return table_name

# Endpoint: Gửi tin nhắn và nhận phản hồi
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    account = data.get("account", "").strip()
    chatbot = data.get("chatbotName", "").strip()
    safe_chatbot = re.sub(r'[^a-zA-Z0-9_]', '_', chatbot)
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    table_name = f"messages_{safe_account}_to_{safe_chatbot}"
    create_user_messages_table(safe_account, chatbot)

    if not user_input or not account or not chatbot:
        return jsonify({"error": "Missing 'message' or 'account' or 'chatbot'"}), 400

        # Nếu message chứa từ "schedule" thì trích xuất thông tin
    if "schedule" in user_input.lower():
        # Gọi hàm trích xuất thông tin bằng LLM
        extracted = extract_training_info_with_llm(user_input, client)
        if not extracted or not all(field in extracted for field in ["content", "time_start", "time_end"]):
            return jsonify({"error": "Could not extract training info from message"})

        # Gọi hàm schedule_training với các tham số đã trích xuất
        training_order = agent.schedule_training(
            content=extracted["content"],
            account=account,
            time_start=extracted["time_start"],
            time_end=extracted["time_end"],
            herald=chatbot
        )
        response = client.chat.completions.create(
            model="gemma2:2b",
            messages=[{"role": "user", "content": f"{training_order}\nPlease create a concise and natural confirmation message in English."}],
            max_tokens=100
        )
        print(json.dumps(agent.schedule_db, indent=2, ensure_ascii=False))
        return jsonify({"response": f"{response.choices[0].message.content}\nThis is a temporary message and will not be saved."})
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Lấy tóm tắt ngữ cảnh gần nhất (nếu có)
        cursor.execute("SELECT summary_text FROM summaries WHERE account = ? ORDER BY timestamp DESC LIMIT 1", (account,))
        summary_result = cursor.fetchone()
        summary = summary_result[0] if summary_result else ""

        # Lấy tối đa 15 tin nhắn gần nhất
        cursor.execute(f"SELECT text, is_user FROM {table_name} ORDER BY timestamp DESC LIMIT 15")
        recent_messages = cursor.fetchall()[::-1]  # đảo ngược lại thứ tự thời gian

        # Chuyển đổi thành định dạng phù hợp với OpenAI API
        chat_history = []
        for text, is_user in recent_messages:
            role = "user" if is_user else "assistant"
            chat_history.append({"role": role, "content": text})

        # Lấy system_message từ bảng Chatbots
        cursor.execute("SELECT system_message FROM Chatbots WHERE name = ?", (chatbot,))
        chatbot_system_message_result = cursor.fetchone()
        chatbot_system_message = chatbot_system_message_result[0] if chatbot_system_message_result and chatbot_system_message_result[0] else None
 
    # Tạo system message
    system_message = chatbot_system_message if chatbot_system_message else "You are Optimus Prime"
    if summary:
        system_message += f"\nPrevious context summary: {summary}"

    # Chuẩn bị messages gửi đến AI model
    messages = prepare_messages_with_token_limit(system_message, chat_history, user_input)  
    # Gọi model để lấy phản hồi
    response = client.chat.completions.create(
        model="gemma2:2b",
        messages=messages,
        stream=False,
        max_tokens=100
    )

    reply = response.choices[0].message

    #Lưu tin nhắn vào database
    cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, ?)", (user_input, True))
    conn.commit()
    #Lưu phản hồi vào database
    cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, ?)", (reply.content, False))
    conn.commit()
    return jsonify({"response": reply.content})

#Endpoint: xác định các cấp dưới
@app.route("/getLowerLevel/<account>", methods=["GET"])
def get_lower_level(account):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT position FROM user_information WHERE account = ?", (account,))
        position = cursor.fetchone()[0]
        sub_positions = position_tree.get(position, [])
        return jsonify(sub_positions)

# Endpoint: Lấy lịch sử chat
@app.route("/history/<account>/<chatbot>", methods=["GET"])
def get_history(account, chatbot):
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    safe_chatbot = re.sub(r'[^a-zA-Z0-9_]', '_', chatbot)
    table_name = f"messages_{safe_account}_to_{safe_chatbot}"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT text, is_user FROM {table_name} ORDER BY timestamp")
            history = [{"text": row[0], "isUser": bool(row[1])} for row in cursor.fetchall()]
            return jsonify({"history": history})
        except sqlite3.OperationalError:
            return jsonify({"history": []})  # Bảng không tồn tại

#Endpoint: trích xuất thông tin từ tin nhắn
def extract_training_info_with_llm(message, client):
    prompt = f"""
Extract the following fields from the message below:
- content: the subject or topic of the training
- time_start: the start time (with day if available)
- time_end: the end time (with day if available)

Message: "{message}"

Return the result as a JSON object with keys: host, content, time_start, time_end.
"""
    response = client.chat.completions.create(
        model="gemma2:2b",  
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    import json
    import re
    text = response.choices[0].message.content
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            print(json.loads(match.group(0)))
            return json.loads(match.group(0))
        except Exception as e:
            print("JSON parse error:", e)
    return None

#Endpoint: lấy danh sách subordinates
@app.route("/getSubordinates/<account>", methods=["GET"])
def get_subordinates(account):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Lấy thông tin của account
        cursor.execute("SELECT position, legion, company, platoon FROM user_information WHERE account = ?", (account,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "User not found"}), 404
        position, legion, company, platoon = user_row

        sub_positions = position_tree.get(position, [])

        # Truy vấn danh sách cấp dưới theo phạm vi
        if position == "High Commander":
            cursor.execute(
                f"SELECT account, name, house, position, legion, company, platoon, email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))})",
                sub_positions
            )
        elif position == "Legion Commander":
            cursor.execute(
                f"SELECT account, name, house, position, legion, company, platoon, email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND legion = ?",
                sub_positions + [legion]
            )
        elif position == "Captain":
            cursor.execute(
                f"SELECT account, name, house, position, legion, company, platoon, email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND company = ?",
                sub_positions + [company]
            )
        elif position == "Lieutenant":
            cursor.execute(
                f"SELECT account, name, house, position, legion, company, platoon, email FROM user_information WHERE position IN (?) AND platoon = ?",
                sub_positions + [platoon]
            )
        else:
            return jsonify([])

        subordinates = cursor.fetchall()

        result = [
            {
                "name": get_name_and_house(row[1], row[2]),
                "title": get_title(row[3], row[4], row[5], row[6]),
                "email": row[7]
            }   
            for row in subordinates
        ]
    return jsonify(result)

#Endpoint: Thay đổi position
@app.route("/changePosition/<account>", methods=["POST"])
def change_position(account):
    data = request.get_json()
    subordinateName = data.get("subordinateName", "").strip()
    subordinateEmail = data.get("subordinateEmail", "").strip()
    newPosition = data.get("newPosition", "").strip()

    name, house = subordinateName.split(" of house ")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE user_information SET position = ? WHERE name = ? AND house = ? AND email = ?", (newPosition, name, house, subordinateEmail))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Subordinate's name and email do not match"}), 404
    return jsonify({"message": "Position updated successfully"})

#Hàm xoá profile nếu profile thuộc subordinate của account
@app.route("/deleteProfile", methods=["POST"])
def delete_profile():
    data = request.get_json()
    account = data.get("accountRequest", "").strip()
    target = data.get("accountToDelete", "").strip()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Lấy thông tin của account (người gọi)
        cursor.execute("SELECT position, legion, company, platoon FROM user_information WHERE account = ?", (account,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"error": "Account not found"}), 404
        position, legion, company, platoon = user_row
        # Xác định các cấp dưới
        sub_positions = position_tree.get(position, [])
        # Truy vấn danh sách cấp dưới theo phạm vi
        if position == "High Commander":
            cursor.execute(
                f"SELECT email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))})",
                sub_positions
            )
        elif position == "Legion Commander":
            cursor.execute(
                f"SELECT email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND legion = ?",
                sub_positions + [legion]
            )
        elif position == "Captain":
            cursor.execute(
                f"SELECT email FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND company = ?",
                sub_positions + [company]
            )
        elif position == "Lieutenant":
            cursor.execute(
                f"SELECT email FROM user_information WHERE position IN (?) AND platoon = ?",
                sub_positions + [platoon]
            )
        else:
            return jsonify({"error": "No permission"}), 403

        subordinates = cursor.fetchall()
        subordinate_emails = {row[0] for row in subordinates}

        if target not in subordinate_emails:
            return jsonify({"error": "Target is not your subordinate"}), 403

        # Xóa profile nếu là subordinate
        cursor.execute("SELECT account FROM user_information WHERE email = ?", (target,))
        account_deleted = cursor.fetchone()[0]
        cursor.execute("INSERT INTO deleted_profiles (account, email, deleted_by, time_deleted) VALUES (?, ?, ?, ?)", (account_deleted, target, account, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cursor.execute("DELETE FROM user_information WHERE email = ?", (target,))
        conn.commit()
        cursor.execute("DELETE FROM users WHERE account = ?", (account_deleted,))
        conn.commit()
    return jsonify({"message": "Profile deleted successfully"})

# Endpoint: Gửi tin nhắn và nhận phản hồi
@app.route("/call", methods=["POST"])
def call():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    account = data.get("account", "").strip()
    callbot = data.get("callbotName", "").strip()
    safe_callbot = re.sub(r'[^a-zA-Z0-9_]', '_', callbot)
    safe_account = re.sub(r'[^a-zA-Z0-9_]', '_', account)
    table_name = f"calls_{safe_account}_to_{safe_callbot}"
    table_name = create_user_calls_table(safe_account, callbot)

    if not user_input or not account or not callbot:
        return jsonify({"error": "Missing 'message' or 'account' or 'callbot'"}), 400
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Lấy tóm tắt ngữ cảnh gần nhất (nếu có)
        cursor.execute("SELECT summary_text FROM summaries WHERE account = ? ORDER BY timestamp DESC LIMIT 1", (account,))
        summary_result = cursor.fetchone()
        summary = summary_result[0] if summary_result else ""

        # Lấy tối đa 15 tin nhắn gần nhất
        cursor.execute(f"SELECT text, is_user FROM {table_name} ORDER BY timestamp DESC LIMIT 15")
        recent_messages = cursor.fetchall()[::-1]  # đảo ngược lại thứ tự thời gian

        # Chuyển đổi thành định dạng phù hợp với OpenAI API
        chat_history = []
        for text, is_user in recent_messages:
            role = "user" if is_user else "assistant"
            chat_history.append({"role": role, "content": text})

        # Lấy system_message từ bảng Callbots
        cursor.execute("SELECT system_message FROM Callbots WHERE name = ?", (callbot,))
        callbot_system_message_result = cursor.fetchone()
        callbot_system_message = callbot_system_message_result[0] if callbot_system_message_result and callbot_system_message_result[0] else None
 
    # Tạo system message
    system_message = callbot_system_message if callbot_system_message else "You are Garen, the God King"
    if summary:
        system_message += f"\nPrevious context summary: {summary}"

    # Chuẩn bị messages gửi đến AI model
    messages = prepare_messages_with_token_limit(system_message, chat_history, user_input)  
    # Gọi model để lấy phản hồi
    response = client.chat.completions.create(
        model="gemma2:2b",
        messages=messages,
        stream=False,
        max_tokens=100
    )

    reply = response.choices[0].message

    #Lưu tin nhắn vào database
    cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, ?)", (user_input, True))
    conn.commit()
    #Lưu phản hồi vào database
    cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, ?)", (reply.content, False))
    conn.commit()
    return jsonify({"response": reply.content})

#Hàm lấy gear ngựa thì có tên ngựa, gear khác thì không có tên, gear có số lượng, ngựa thì không có số lượng
@app.route("/getGears/<account>", methods=["GET"])
def get_gears(account):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT gear_type, gear_quantity, gear_name FROM gears_list WHERE account = ?", (account,))
        gears = cursor.fetchall()
        gears_list = []
        for gear in gears:
            gear_dict = {
                "type": gear[0],
                "quantity": gear[1],
                "horseName": gear[2]
            }
            gears_list.append(gear_dict)
        return jsonify(gears_list)
    
#Hàm sync
@app.route("/syncGear", methods=["POST"])
def sync_gear():
    try:
        data = request.get_json()

        account = data.get("account")
        action = data.get("action")
        gear_type = data.get("type")
        quantity = data.get("quantity")  # Có thể là None nếu là ngựa
        image_res_id = data.get("imageResId")
        horse_name = data.get("horseName")  # Có thể là None

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            if action == "add":
                cursor.execute("""
                    INSERT INTO gears_list (id, account, gear_type, gear_quantity, gear_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (image_res_id, account, gear_type, quantity, horse_name))
                conn.commit()
                return jsonify({"message": "Gear added successfully"}), 200

            elif action == "delete":
                cursor.execute("""
                    DELETE FROM gears_list 
                    WHERE account = ? AND gear_type = ? AND id = ?
                """, (account, gear_type, image_res_id))
                conn.commit()
                return jsonify({"message": "Gear deleted successfully"}), 200

            else:
                return jsonify({"error": "Invalid action"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)