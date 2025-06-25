import os
import imaplib
import email
import datetime
from email.header import decode_header
from openai import OpenAI
from twilio.rest import Client

# === KONFIGURACJA Z .ENV ===
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
IMAP_SERVER = 'imap.gmail.com'

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

MY_PHONE = os.getenv("MY_PHONE")
PARTNER_PHONE = os.getenv("PARTNER_PHONE")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

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
    date_since = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
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

def send_sms(to, body):
    twilio_client.messages.create(
        body=body,
        from_=TWILIO_PHONE,
        to=to
    )

if __name__ == "__main__":
    all_emails = fetch_recent_emails()
    firm_emails = [e for e in all_emails if e['from'].lower() in FIRM_SENDERS]
    private_emails = [e for e in all_emails if e['from'].lower() not in FIRM_SENDERS]

    if firm_emails:
        summary_firm = summarize_emails(firm_emails)
        send_sms(MY_PHONE, "📬 Firmowe:\n" + summary_firm)
        send_sms(PARTNER_PHONE, "📬 Firmowe:\n" + summary_firm)

    if private_emails:
        summary_private = summarize_emails(private_emails)
        send_sms(MY_PHONE, "📥 Prywatne:\n" + summary_private)
