import os
import imaplib
import email
import datetime
import json
from email.header import decode_header
import openai
from twilio.rest import Client
from dotenv import load_dotenv

# === WCZYTANIE ZMIENNYCH ŚRODOWISKOWYCH ===
load_dotenv()




EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = 'imap.gmail.com'

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Brakuje klucza OPENAI_API_KEY w środowisku!")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

MY_PHONE = os.getenv("MY_PHONE")            # np. whatsapp:+48534298346
PARTNER_PHONE = os.getenv("PARTNER_PHONE")  # np. whatsapp:+48570079082

twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

# Twilio sandboxowy numer nadawcy
TWILIO_SANDBOX_NUMBER = 'whatsapp:+14155238886'

FIRM_SENDERS = [
    'ksiegowa@...', 'biuro.kapiczynska@gmail.com',
    'e-faktury@kaufland.pl', 'pl-imv-ima@kaufland.pl',
    'biuro@liron-polska.pl', 'marketing@paczkownia.pl',
    'franczyza@paczkownia.com.pl', 'b2b@pelczykgroup.pl'
]

def decode_mime_header(header):
    decoded = decode_header(header)
    result = []
    for part, encoding in decoded:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(encoding if encoding else 'utf-8', errors='ignore'))
            except:
                result.append(part.decode('utf-8', errors='ignore'))
        else:
            result.append(part)
    return ''.join(result)

def fetch_recent_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")
    date_since = (datetime.datetime.today() - datetime.timedelta(days=3)).strftime("%d-%b-%Y")

    result, data = mail.search(None, f'(SINCE "{date_since}")')
    emails = []

    for num in data[0].split():
        _, msg_data = mail.fetch(num, '(RFC822)')
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        sender = email.utils.parseaddr(msg.get("From"))[1]
        subject = decode_mime_header(msg.get("Subject", ""))
        date = msg.get("Date", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors='ignore')
        else:
            body = msg.get_payload(decode=True).decode(errors='ignore')

        emails.append({
            "from": sender,
            "subject": subject,
            "date": date,
            "body": body.strip()
        })

    return emails

def summarize_emails(emails):
    if not emails:
        return "Brak nowych wiadomości."
    content = "\n\n".join(
        f"FROM: {email['from']}\nSUBJECT: {email['subject']}\n{email['body']}" for email in emails
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "pisz po polsku. Stwórz zwięzłe podsumowanie w punktach wiadomości e-mail z ostatniego dnia."},
            {"role": "user", "content": content}
        ],
        temperature=0.3,
        max_tokens=500
    )
    return response.choices[0].message.content.strip()

def send_whatsapp_message(to, body):
    try:
        twilio_client.messages.create(
            from_=TWILIO_SANDBOX_NUMBER,
            to=to,
            body=body
        )
    except Exception as e:
        print(f"Błąd przy wysyłaniu WhatsAppa do {to}: {e}")

if __name__ == "__main__":
    try:
        all_emails = fetch_recent_emails()
        firm_emails = [e for e in all_emails if e['from'].lower() in FIRM_SENDERS]
        private_emails = [e for e in all_emails if e['from'].lower() not in FIRM_SENDERS]

        if firm_emails:
            summary_firm = summarize_emails(firm_emails)
            send_whatsapp_message(MY_PHONE, "📬 Firmowe:\n" + summary_firm)
            send_whatsapp_message(PARTNER_PHONE, "📬 Firmowe:\n" + summary_firm)

        if private_emails:
            summary_private = summarize_emails(private_emails)
            send_whatsapp_message(MY_PHONE, "📥 Prywatne:\n" + summary_private)

    except Exception as e:
        send_whatsapp_message(MY_PHONE, f"🚨 Błąd w aplikacji:\n{str(e)}")
        print(f"Błąd krytyczny: {e}")
