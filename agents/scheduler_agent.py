import uuid
from datetime import datetime
import sqlite3
import os
import re

# Truy vấn DB để lấy account các cấp dưới
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Database.db")


class TrainingSchedulerAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.schedule_db = {}  # Lưu tạm các lịch training

    def schedule_training(self, content, account, time_start, time_end, herald):
        """
        Function to schedule for training
        """
        # Lấy thông tin người gửi
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT hierarchy, name, position, legion, company, platoon FROM user_information WHERE account = ?", (account,))
            user_row = cursor.fetchone()
            if user_row:
                hierarchy, name, position, legion, company, platoon = user_row
                host = f"{hierarchy} {name}".strip()
                command_authority = f"{position}".strip()
                sender_legion = f"{legion}".strip()    
                sender_company = f"{company}".strip()
                sender_platoon = f"{platoon}".strip()

        # Generate training ID
        training_id = str(uuid.uuid4())
        
        # Store training information
        training_info = {
            "training_id": training_id,
            "host": host,
            "content": content,
            "herald": herald,
            "time_start": time_start,
            "time_end": time_end,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }

        training_order = f"""
        - Content: {content}
        - Host: {host}
        - Time: from {time_start} to {time_end}
        - Herald: {herald}
        """


        # Truy vấn các account cấp dưới cùng legion
        notified_accounts = self.get_notified_accounts(position, sender_legion, sender_company, sender_platoon)

        # Lưu vào training_info
        training_info["notified_accounts"] = notified_accounts
        self.schedule_db[training_id] = training_info

    
        for acc in notified_accounts:
            table_name = f"messages_{re.sub(r'[^a-zA-Z0-9_]', '_', acc)}_to_{re.sub(r'[^a-zA-Z0-9_]', '_', herald)}"
            # Tạo bảng nếu chưa có
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
                # Lấy thông tin người nhận để cá nhân hóa message
                cursor.execute(f"SELECT hierarchy, name, position FROM user_information WHERE account = ?", (acc,))
                user_row = cursor.fetchone()  
                if user_row:
                    hierarchy, name, position = user_row
                    receiver = f"{hierarchy} {name}".strip()
                    position = f"{position}".strip()
                else:
                    receiver = acc
                # Gửi thông báo
                notification_message = f"Dear {receiver},\nYou have a new training order from {host} ({command_authority}):\n{training_order}"
                cursor.execute(f"INSERT INTO {table_name} (text, is_user) VALUES (?, 0)", (notification_message,))
                conn.commit()
        
        return f"A training session has been scheduled with the following details:\n{training_order}"

    def get_subordinate_positions(self, position):
        position_tree = {
            "High Commander": ["Legion Commander", "Captain", "Lieutenant", "Soldier"],
            "Legion Commander": ["Captain", "Lieutenant", "Soldier"],
            "Captain": ["Lieutenant", "Soldier"],
            "Lieutenant": ["Soldier"],
            "Soldier": []
        }
        return position_tree.get(position, [])

    def get_notified_accounts(self, position, legion, company, platoon):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if position == "High Commander":
                # Gửi cho tất cả Legion Commander, Captain, Lieutenant, Soldier
                sub_positions = ["Legion Commander", "Captain", "Lieutenant", "Soldier"]
                cursor.execute(
                    f"SELECT account FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))})",
                    sub_positions
                )
            elif position == "Legion Commander":
                sub_positions = ["Captain", "Lieutenant", "Soldier"]
                cursor.execute(
                    f"SELECT account FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND legion = ?",
                    sub_positions + [legion]
                )
            elif position == "Captain":
                sub_positions = ["Lieutenant", "Soldier"]
                cursor.execute(
                    f"SELECT account FROM user_information WHERE position IN ({','.join(['?']*len(sub_positions))}) AND company = ?",
                    sub_positions + [company]
                )
            elif position == "Lieutenant":
                sub_positions = ["Soldier"]
                cursor.execute(
                    f"SELECT account FROM user_information WHERE position IN (?) AND platoon = ?",
                    sub_positions + [platoon]
                )
            else:
                return []
            return [row[0] for row in cursor.fetchall()]

# Khởi tạo agent toàn cục
agent = TrainingSchedulerAgent(agent_id="training_scheduler_001")

