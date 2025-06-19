from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
import json

app = Flask(__name__)
app.secret_key = "optimus_prime_secret"
BASE_URL = "http://127.0.0.1:5000"

# Helper: Call backend API


def call_api(endpoint, method="GET", data=None):
    try:
        headers = {"Content-Type": "application/json"}
        if method == "POST":
            response = requests.post(
                f"{BASE_URL}/{endpoint}", json=data, headers=headers, timeout=30)
        else:
            response = requests.get(
                f"{BASE_URL}/{endpoint}", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("chatbot"))
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "").strip()
        if not identifier or not password:
            flash("Vui lòng nhập đầy đủ thông tin", "danger")
            return render_template("login.html")
        result = call_api("login", "POST", {
                          "identifier": identifier, "password": password})
        if result and "account" in result:
            session["username"] = result["account"]
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for("chatbot"))
        else:
            flash(result.get("error", "Đăng nhập thất bại"), "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("username"):
        return redirect(url_for("chatbot"))
    if request.method == "POST":
        account = request.form.get("account", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if not account or not email or not password:
            flash("Vui lòng nhập đầy đủ thông tin", "danger")
            return render_template("register.html")
        result = call_api("register", "POST", {
                          "account": account, "email": email, "password": password})
        if result and "error" not in result:
            flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
            return redirect(url_for("login"))
        else:
            flash(result.get("error", "Đăng ký thất bại"), "danger")
    return render_template("register.html")


@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if not session.get("username"):
        flash("Vui lòng đăng nhập", "danger")
        return redirect(url_for("login"))
    bot_list = call_api("getChatbotList") or []
    bot_names = [bot["name"]
                 for bot in bot_list] if isinstance(bot_list, list) else []
    selected_bot = request.form.get(
        "chatbot_name", bot_names[0] if bot_names else "OptimusPrime")
    history = call_api(
        f"history/{session['username']}/{selected_bot}") or {"history": []}
    messages = history.get("history", [])
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            result = call_api("chat", "POST", {
                "account": session["username"],
                "chatbotName": selected_bot,
                "message": message
            })
            if result and "response" in result:
                messages.append({"text": message, "isUser": True})
                messages.append({"text": result["response"], "isUser": False})
            else:
                flash(result.get("error", "Không thể gửi tin nhắn"), "danger")
    return render_template("chatbot.html", bot_names=bot_names, selected_bot=selected_bot, messages=messages)


@app.route("/callbot", methods=["GET", "POST"])
def callbot():
    if not session.get("username"):
        flash("Vui lòng đăng nhập", "danger")
        return redirect(url_for("login"))
    bot_list = call_api("getCallbotList") or []
    bot_names = [bot["name"]
                 for bot in bot_list] if isinstance(bot_list, list) else []
    selected_bot = request.form.get(
        "callbot_name", bot_names[0] if bot_names else "Garen")
    history = call_api(
        f"history/{session['username']}/{selected_bot}") or {"history": []}
    messages = history.get("history", [])
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            result = call_api("call", "POST", {
                "account": session["username"],
                "callbotName": selected_bot,
                "message": message
            })
            if result and "response" in result:
                messages.append({"text": message, "isUser": True})
                messages.append({"text": result["response"], "isUser": False})
            else:
                flash(result.get("error", "Không thể gửi tin nhắn"), "danger")
    return render_template("callbot.html", bot_names=bot_names, selected_bot=selected_bot, messages=messages)


@app.route("/logout")
def logout():
    session.pop("username", None)
    flash("Đăng xuất thành công!", "success")
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
