import os
import json
import logging
from flask import Flask, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import pytz

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]

SPREADSHEET_ID = '10_xs6PcT6X0-POe2236tLo4mDdGXLwplOpCYjtbJPT8'
CALENDAR_ID = 'chbilal.2332@gmail.com'

def get_credentials():
    creds_raw = os.environ.get('GOOGLE_CREDENTIALS', '')
    creds_dict = json.loads(creds_raw)
    return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

def get_sheets_service():
    return build('sheets', 'v4', credentials=get_credentials())

@app.route('/')
def home():
    return jsonify({"status": "ok"})

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)

        name = str(data.get('name', 'Guest'))
        date_str = str(data.get('date', ''))
        time_str = str(data.get('time', ''))
        party_size = data.get('party_size', 1)
        phone = str(data.get('phone', ''))
        calendar_id = str(data.get('calendar_id', CALENDAR_ID))

        from datetime import timedelta
        dt_str = f"{date_str} {time_str}"
        formats = ['%Y-%m-%d %I:%M %p', '%Y-%m-%d %H:%M', '%Y-%m-%d %I:%M%p']
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(dt_str.strip(), fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return jsonify({"success": False, "message": f"Could not parse: {dt_str}"}), 400

        tz = pytz.timezone('America/Chicago')
        dt_start = tz.localize(dt)
        dt_end = dt_start + timedelta(hours=1)

        event = {
            'summary': f'Reservation - {name} (Party of {party_size})',
            'description': f'Name: {name}\nParty size: {party_size}\nPhone: {phone}',
            'start': {'dateTime': dt_start.isoformat(), 'timeZone': 'America/Chicago'},
            'end': {'dateTime': dt_end.isoformat(), 'timeZone': 'America/Chicago'},
        }

        service = get_calendar_service()
        service.events().insert(calendarId=calendar_id, body=event).execute()

        return jsonify({"success": True, "message": f"Booking confirmed for {name} on {date_str} at {time_str} for {party_size} guests."})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/log_call', methods=['POST'])
def log_call():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        data = payload.get('args', payload)

        tz = pytz.timezone('America/Chicago')
        now = datetime.now(tz)
        date = now.strftime('%Y-%m-%d')
        time = now.strftime('%I:%M %p')

        name = str(data.get('name', 'Unknown'))
        phone = str(data.get('phone', ''))
        purpose = str(data.get('purpose', ''))
        outcome = str(data.get('outcome', ''))
        notes = str(data.get('notes', ''))

        row = [date, time, name, phone, purpose, outcome, notes]

        sheets = get_sheets_service()
        sheets.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Sheet1!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        return jsonify({"success": True, "message": "Call logged successfully."})

    except Exception as e:
        app.logger.error(f"ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/check_availability', methods=['POST'])
def check_availability():
    return jsonify({"available": True, "message": "We have availability. What date works for you?"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
