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
STATE_ADDRESS = 'address'
STATE_WAIT_OK = 'wait_ok'
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
    incoming = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From')

    print(f"📩 Mensaje recibido de {sender}: {incoming}")

    resp = MessagingResponse()
    msg = resp.message()

    def reply(text):
        msg.body(text)
        print(f"📤 Chilo respondió: {text}")

    session = sessions.get(sender, {'state': STATE_NAME, 'data': {}})
    state = session['state']
    data = session['data']

    if state == STATE_NAME:
        reply("¡Hola! 👋 soy *Chilo* 🤖 gracias por escribir a *Los Shelakeles*.")
        reply("¿Cómo te llamas?")
        session['state'] = STATE_ADDRESS

    elif state == STATE_ADDRESS:
        data['name'] = incoming.title()
        menu_link = "https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing"
        reply(
            f"Aquí te dejo el menú chingón: 📎 {menu_link}\n\n"
            "Échale un vistazo y cuando estés listo para ordenar escribe *OK*.\n"
            "Si prefieres ser atendido por un humano escribe *GO*."
        )
        session['state'] = STATE_WAIT_OK

    elif state == STATE_WAIT_OK:
        if incoming == 'ok':
            reply("¿Cuál es tu dirección para el envío?")
            session['state'] = STATE_COMBO_COUNT
        elif incoming == 'go':
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
                print(f"📤 Chilo notificó atención humana para {nombre}: {contact_link}")
            except Exception as e:
                print(f"❌ Error al enviar notificación de humano: {e}")
            sessions.pop(sender, None)
            return str(resp)
        else:
            reply("Por favor escribe *OK* para ordenar o *GO* para ser atendido por un humano.")

    elif state == STATE_COMBO_COUNT:
        data['address'] = incoming
        reply("¿Cuántos combos vas a querer hoy?")
        session['state'] = 'combo_wait'

    elif session['state'] == 'combo_wait':
        if not incoming.isdigit():
            reply("Por favor, indica un número válido de combos.")
            return str(resp)

        combo_count = int(incoming)
        if combo_count >= 5:
            nombre = data.get('name', 'Cliente')
            telefono_raw = sender.split(':')[1]
            contact_link = f"https://wa.me/{telefono_raw}"
            reply("🙌 Como tu pedido es grande (5 combos o más), te vamos a atender personalmente.")
            try:
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=f"📢 *{nombre}* quiere hacer un pedido grande. Contacto: {contact_link}"
                )
                print(f"📤 Pedido grande notificado a la tienda: {contact_link}")
            except Exception as e:
                print(f"❌ Error al enviar mensaje de pedido grande: {e}")
            sessions.pop(sender, None)
            return str(resp)

        data['combos_total'] = combo_count
        data['current_combo'] = 1
        data['combos'] = []
        reply("Combo 1 – Elige tipo de combo:\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items()))
        session['state'] = STATE_COMBO_TYPE

    elif state == STATE_COMBO_TYPE:
        if incoming not in COMBO_OPTIONS:
            reply("Combo inválido. Elige 1, 2 o 3.")
            return str(resp)
        combo = {'combo': incoming}
        data['combos'].append(combo)
        reply("¿Qué proteína quieres?\n" + '\n'.join(f"{k}. {v[0]}" for k, v in PROTEIN_OPTIONS.items()))
        session['state'] = STATE_PROTEIN

    elif state == STATE_PROTEIN:
        if incoming not in PROTEIN_OPTIONS:
            reply("Opción inválida. Elige una proteína del 1 al 4.")
            return str(resp)
        data['combos'][-1]['protein'] = incoming
        reply("¿Qué bebida quieres?\n" + '\n'.join(f"{k}. {v}" for k, v in BEVERAGE_OPTIONS.items()))
        session['state'] = STATE_BEVERAGE

    elif state == STATE_BEVERAGE:
        if incoming not in BEVERAGE_OPTIONS:
            reply("Opción inválida. Elige una bebida del 1 al 8.")
            return str(resp)
        data['combos'][-1]['beverage'] = incoming
        reply("¿Deseas algún extra?\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in EXTRA_OPTIONS.items()))
        session['state'] = STATE_EXTRA

    elif state == STATE_EXTRA:
        if incoming not in EXTRA_OPTIONS:
            reply("Opción inválida. Elige un extra válido.")
            return str(resp)
        data['combos'][-1]['extra'] = incoming
        if data['current_combo'] < data['combos_total']:
            data['current_combo'] += 1
            reply(f"Combo {data['current_combo']} – Elige tipo de combo:\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items()))
            session['state'] = STATE_COMBO_TYPE
        else:
            nombre = data['name']
            direccion = data['address']
            telefono_raw = sender.split(':')[1]
            resumen = ""
            total = 0
            for i, c in enumerate(data['combos'], 1):
                cn, cp = COMBO_OPTIONS[c['combo']]
                pn, pp = PROTEIN_OPTIONS[c['protein']]
                bv = BEVERAGE_OPTIONS[c['beverage']]
                en, ep = EXTRA_OPTIONS[c['extra']]
                total += cp + pp + ep
                resumen += f"• Combo {i}: {cn}, Prot: {pn}, Beb: {bv}, Extra: {en}\n"

            mensaje_generado = (
                f"📦 *Nuevo Pedido*\n"
                f"👤 Cliente: {nombre}\n"
                f"📍 Dirección: {direccion}\n"
                f"📱 Contacto: https://wa.me/{telefono_raw}\n"
                f"\n{resumen}\n💰 Total: ${total:.2f}"
            )

            try:
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=mensaje_generado
                )
                print(f"📤 Chilo notificó a la tienda: {mensaje_generado}")
            except Exception as e:
                print(f"❌ Error al enviar mensaje a la tienda: {e}")

            reply("✅ ¡Gracias por tu pedido! Un humano te confirmará pronto el envío.")
            session = None

    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
