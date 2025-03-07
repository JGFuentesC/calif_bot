import functions_framework
import google.auth
from google.auth.transport.requests import Request
from google.auth import jwt
import requests
import json
import os
import logging

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_SECRET = os.environ.get("TELEGRAM_SECRET_TOKEN")

DFCX_PROJECT_ID = os.environ.get("DFCX_PROJECT_ID")
DFCX_AGENT_LOCATION = os.environ.get("DFCX_AGENT_LOCATION")
DFCX_AGENT_ID = os.environ.get("DFCX_AGENT_ID")

def generate_auth_token():
    credentials, _ = google.auth.default()
    auth_req = Request()
    credentials.refresh(auth_req)
    return credentials.token

def process_telegram_message(update):
    try:
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "")

        if chat_id and user_text:
            logging.info(f"Procesando mensaje de {chat_id}: {user_text}")
            dfcx_response = send_to_dialogflow(user_text, str(chat_id))
            send_telegram_message(chat_id, dfcx_response)
    except Exception as e:
        logging.error(f"Error en process_telegram_message: {str(e)}")
        send_telegram_message(chat_id, "⚠️ Ocurrió un error procesando tu mensaje.")

def send_to_dialogflow(text, session_id):
    url = f"https://dialogflow.googleapis.com/v3/projects/{DFCX_PROJECT_ID}/locations/{DFCX_AGENT_LOCATION}/agents/{DFCX_AGENT_ID}/sessions/{session_id}:detectIntent"

    headers = {
        "Authorization": f"Bearer {generate_auth_token()}",
        "Content-Type": "application/json"
    }

    payload = {
        "queryInput": {
            "text": {
                "text": text
            },
            "languageCode": "es"
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        
        logging.info("Dialogflow Response: %s", json.dumps(result, indent=2))
        
        query_result = result.get("queryResult", {})
        response_messages = query_result.get("responseMessages", [])

        
        all_texts = []
        for msg in response_messages:
            if "text" in msg and "text" in msg["text"]:
                all_texts.extend(msg["text"]["text"])
            elif "payload" in msg:
                payload_data = msg.get("payload", {})
                if "telegram" in payload_data:
                    all_texts.append(payload_data["telegram"])

        
        if not all_texts:
            matched_intent = query_result.get("match", {}).get("intent", {}).get("displayName", "Intent desconocido")
            all_texts.append(f"[⚠️ Sin respuesta de Dialogflow, Intent detectado: {matched_intent}]")

        return "\n".join(all_texts)
    
    return f"Error: {response.status_code}, {response.text}"

def send_telegram_message(chat_id, text):
    MAX_LENGTH = 4000 

    for i in range(0, len(text), MAX_LENGTH):
        payload = {
            "chat_id": chat_id,
            "text": text[i:i+MAX_LENGTH]
        }
        requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

@functions_framework.http
def telegram_webhook(request):
    if request.method != "POST":
        return "Invalid request", 405
    
    telegram_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if telegram_token != TELEGRAM_SECRET:
        return "Unauthorized", 403
    
    try:
        update = request.get_json()
        process_telegram_message(update)
        return "OK", 200
    except Exception as e:
        return f"Error: {str(e)}", 500