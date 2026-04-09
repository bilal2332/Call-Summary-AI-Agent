import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_credentials():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/log_call_summary', methods=['POST'])
def log_call_summary():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)

        sheet_id = str(data.get('sheet_id', '')).strip()
        if not sheet_id:
            return jsonify({"success": False, "message": "sheet_id is required"}), 400

        now = datetime.now()
        row = [
            now.strftime('%Y-%m-%d'),
            now.strftime('%I:%M %p'),
            str(data.get('caller_name', 'Unknown')),
            str(data.get('caller_phone', 'Unknown')),
            str(data.get('purpose', '')),
            str(data.get('outcome', '')),
            str(data.get('notes', ''))
        ]

        sheets = build('sheets', 'v4', credentials=get_credentials())
        sheets.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range='Sheet1!A:G',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        return jsonify({"success": True, "message": "Call logged successfully"})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
