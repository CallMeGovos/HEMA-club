import uuid
from datetime import datetime

# Định nghĩa cấu trúc message theo chuẩn agent2agent
def create_agent_message(sender_id, receiver_id, content, message_type="request"):
    return {
        "message_id": str(uuid.uuid4()),
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "timestamp": datetime.now().isoformat(),
        "type": message_type,
        "content": content
    }

# Hàm gọi LLM để tạo phản hồi văn bản tự nhiên
def generate_natural_response(prompt):
    try:
        # Giả lập phản hồi LLM (có thể thay thế bằng API thực tế)
        return f"[LLM response for prompt: {prompt[:30]}...]"
    except Exception as e:
        return f"Error calling LLM: {str(e)}"

# Agent class theo chuẩn ADK
class TrainingSchedulerAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.schedule_db = {}  # Temporary storage for training schedules (can be replaced with a real DB)

    def schedule_training(self, time_start, time_end, host, content):
        """
        Function to schedule for training
        """
        # Generate training ID
        training_id = str(uuid.uuid4())
        
        # Store training information
        training_info = {
            "training_id": training_id,
            "time_start": time_start,
            "time_end": time_end,
            "host": host,
            "content": content,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        self.schedule_db[training_id] = training_info

        # Create prompt for LLM to generate natural response
        prompt = f"""
        A training session has been scheduled with the following details: 
        - Time: from {time_start} to {time_end}
        - Host: {host}
        - Content: {content}
        Please create a concise and natural confirmation message in English.
        """
        confirmation_message = generate_natural_response(prompt)

       # Tạo message theo chuẩn agent2agent
        message = create_agent_message(
            sender_id=self.agent_id,
            receiver_id="client",  # Assuming client as receiver
            content={
                "training_info": training_info,
                "confirmation_message": confirmation_message
            },
            message_type="response"
        )
        return message

    def process_message(self, message):
        # Xử lý message từ agent khác (theo chuẩn agent2agent)
        if message["type"] == "request" and "schedule_training" in message["content"]:
            data = message["content"]["schedule_training"]
            print(f"dang xu ly message: {message}")
            return self.schedule_training(
                data["time_start"],
                data["time_end"],
                data["host"],
                data["content"]
            )
        else:
            return create_agent_message(
                self.agent_id,
                message["sender_id"],
                {"error": "Unsupported message type or content"},
                "error"
            )

# Khởi tạo agent toàn cục
agent = TrainingSchedulerAgent(agent_id="training_scheduler_001")

# Hàm handler thay cho endpoint REST
def schedule_training_handler(data, client):
    print("Received data:", data)
    if "message" not in data:
        return {"error": "Missing 'message' field"}
    try:
        llm_result = extract_training_info_with_llm(data["message"], client)
        if not llm_result or not all(field in llm_result for field in ["host", "content", "time_start", "time_end"]):
            return {"error": "Could not extract training info from message"}
        response = agent.schedule_training(
            time_start=llm_result["time_start"],
            time_end=llm_result["time_end"],
            host=llm_result["host"],
            content=llm_result["content"]
        )
        return response
    except Exception as e:
        error_message = create_agent_message(
            agent.agent_id,
            "client",
            {"error": f"Error scheduling training: {str(e)}"},
            "error"
        )
        return error_message

def agent_message_handler(message):
    print(f"dang xu ly message: {message}")
    try:
        # Dùng agent toàn cục, không khởi tạo lại
        response = agent.process_message(message)
        return response
    except Exception as e:
        error_message = create_agent_message(
            agent.agent_id,
            "unknown",
            {"error": f"Error processing message: {str(e)}"},
            "error"
        )
        return error_message

def extract_training_info_with_llm(message, client):
    prompt = f"""
Extract the following fields from the message below:
- host: the name of the person requesting the training
- content: the subject or topic of the training
- time_start: the start time (with day if available)
- time_end: the end time (with day if available)

Message: "{message}"

Return the result as a JSON object with keys: host, content, time_start, time_end.
"""
    response = client.chat.completions.create(
        model="gemma2:2b",  # hoặc model bạn đang dùng
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    import json
    import re
    # Tìm đoạn JSON trong response
    text = response.choices[0].message.content
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            print("JSON parse error:", e)
    return None