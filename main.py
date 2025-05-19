import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)

# Twilio client
client = Client(
    os.environ['TWILIO_ACCOUNT_SID'],
    os.environ['TWILIO_AUTH_TOKEN']
)

SANDBOX_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER = 'whatsapp:+5215612522186'

sessions = {}

# Estados de conversación
STATE_NAME = 'name'
STATE_WAIT_OK = 'wait_ok'
STATE_ADDRESS = 'address'
STATE_COMBO_COUNT = 'combo_count'
STATE_COMBO_TYPE = 'combo_type'
STATE_PROTEIN = 'protein'
STATE_BEVERAGE = 'beverage'
STATE_EXTRA = 'extra'

COMBO_OPTIONS = {
    '1': ("El Clásico Shingón", 185.00),
    '2': ("El Verde Shingón", 185.00),
    '3': ("El Que No Se Decide", 215.00),
}
PROTEIN_OPTIONS = {
    '1': ("Pollito", 0.00),
    '2': ("Carnita Asada", 0.00),
    '3': ("Cecina de Res", 45.00),
    '4': ("Sin proteína", 0.00),
}
BEVERAGE_OPTIONS = {
    '1': "Limonada Natural",
    '2': "Jamaica con Limón",
    '3': "Coca-Cola",
    '4': "Pepsi",
    '5': "Manzanita Sol",
    '6': "Squirt",
    '7': "Mirinda",
    '8': "Seven Up"
}
EXTRA_OPTIONS = {
    '1': ("Huevito duro", 18.00),
    '2': ("Huevito estrellado", 18.00),
    '3': ("Guacamole chingon", 45.00),
    '4': ("Dirty Horchata", 45.00),
    '5': ("Limonada Natural", 45.00),
    '6': ("Jamaica con Limón", 45.00),
    '7': ("Coca-Cola", 45.00),
    '8': ("Pepsi", 45.00),
    '9': ("Manzanita Sol", 45.00),
    '10': ("Mirinda", 45.00),
    '11': ("Seven Up", 45.00),
    '12': ("Ningun extra", 0.00)
}

@app.route("/ping")
def ping():
    return "Chilo está online 🔥", 200

@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming = request.values.get('Body', '').strip()
    sender = request.values.get('From')

    print(f"📩 {sender} escribió a Chilo: {incoming}")

    resp = MessagingResponse()
    msg = resp.message()

    def reply(text):
        msg.body(text)
        print(f"📤 Chilo respondió a {sender}: {text}")
        try:
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=f"🤖 *Chilo a {sender.split(':')[1]}:* {text}"
            )
        except Exception as e:
            print(f"❌ Error al reenviar respuesta a la tienda: {e}")

    session = sessions.get(sender, {'state': STATE_NAME, 'data': {}})
    state = session['state']
    data = session['data']

    if state == STATE_NAME:
        reply("¡Hola! 👋 soy *Chilo* 🤖 gracias por escribir a *Los Shelakeles*.")
        reply("¿Cómo te llamas?")
        session['state'] = STATE_WAIT_OK

    elif state == STATE_WAIT_OK:
        data['name'] = incoming.title()
        menu_link = "https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing"
        reply(
            f"Aquí te dejo el menú chingón: 📎 {menu_link}\n\n"
            "Échale un vistazo y cuando estés listo para ordenar escribe *OK*.\n"
            "Si prefieres ser atendido por un humano escribe *GO*."
        )
        session['state'] = STATE_ADDRESS

    elif state == STATE_ADDRESS:
        if incoming.lower() == 'ok':
            reply("¿Cuál es tu dirección para el envío?")
            session['state'] = STATE_COMBO_COUNT
        elif incoming.lower() == 'go':
            nombre = data.get('name', 'Cliente')
            telefono_raw = sender.split(':')[1]
            contact_link = f"https://wa.me/{telefono_raw}"
            reply("👌 En breve un humano te atenderá. ¡Gracias por preferir *Los Shelakeles*! 🌶️")
            try:
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=f"🤖➡️🧑 *{nombre}* solicitó atención humana. Contacto: {contact_link}"
                )
            except Exception as e:
                print(f"❌ Error al enviar notificación de humano: {e}")
            sessions.pop(sender, None)
            return str(resp)
        else:
            reply("Por favor escribe *OK* para ordenar o *GO* para ser atendido por un humano.")

    elif state == STATE_COMBO_COUNT:
        try:
            count = int(incoming)
            if count >= 5:
                nombre = data.get('name', 'Cliente')
                telefono_raw = sender.split(':')[1]
                contact_link = f"https://wa.me/{telefono_raw}"
                reply("🚨 Como tu pedido es grande, uno de nuestros humanos chingones te atenderá personalmente.")
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=f"📣 *{nombre}* quiere pedir {count} combos. Contacto: {contact_link}"
                )
                sessions.pop(sender, None)
                return str(resp)
            else:
                data['combo_count'] = count
                data['current_combo'] = 1
                session['state'] = STATE_COMBO_TYPE
                reply(f"¿Qué combo quieres para el Combo 1?\n" + "\n".join(
                    [f"{k}. {v[0]} - ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items()]))
        except ValueError:
            reply("Por favor, responde con un número válido de combos (1, 2, 3...)")

    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
