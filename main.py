import os
from twilio.rest import Client

# === KONFIGURACJA Z .ENV ===
TWILIO_PHONE = os.getenv("TWILIO_PHONE")            # np. whatsapp:+48576113230
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# === TESTOWA WYSYŁKA WIADOMOŚCI BEZ SZABLONU ===
def send_whatsapp_test(to, body):
    try:
        message = twilio_client.messages.create(
            from_=TWILIO_PHONE,
            to=to,
            body=body  # zwykły tekst, bez szablonu
        )
        print(f"Wysłano test: SID={message.sid}")
    except Exception as e:
        print(f"❌ Błąd przy wysyłaniu: {e}")

# === MAIN ===
if __name__ == "__main__":
    try:
        send_whatsapp_test("whatsapp:+48534298346", "🧪 Test: Czy doszło?")
    except Exception as e:
        print(f"❌ Błąd główny: {e}")
