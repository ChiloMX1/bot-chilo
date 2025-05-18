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

    print(f"📩 Mensaje recibido de {sender}: {incoming}")

    resp = MessagingResponse()
    msg = resp.message()

    session = sessions.get(sender, {'state': STATE_NAME, 'data': {}})
    state = session['state']
    data = session['data']

    if state == STATE_NAME:
        data['name'] = incoming.title()
        msg.body(f"¡Hola {data['name']}! ¿Cuál es tu dirección de entrega?")
        session['state'] = STATE_ADDRESS

    elif state == STATE_ADDRESS:
        data['address'] = incoming
        msg.body("¿Cuántos combos vas a querer hoy? (1–9)")
        session['state'] = STATE_COMBO_COUNT

    elif state == STATE_COMBO_COUNT:
        if not incoming.isdigit():
            msg.body("Por favor, indica un número válido de combos.")
            return str(resp)
        data['combos_total'] = int(incoming)
        data['current_combo'] = 1
        data['combos'] = []
        msg.body("Elige el combo 1:\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items()))
        session['state'] = STATE_COMBO_TYPE

    elif state == STATE_COMBO_TYPE:
        if incoming not in COMBO_OPTIONS:
            msg.body("Combo inválido. Elige 1, 2 o 3.")
            return str(resp)
        combo = {'combo': incoming}
        data['combos'].append(combo)
        msg.body("¿Qué proteína quieres?\n" + '\n'.join(f"{k}. {v[0]}" for k, v in PROTEIN_OPTIONS.items()))
        session['state'] = STATE_PROTEIN

    elif state == STATE_PROTEIN:
        if incoming not in PROTEIN_OPTIONS:
            msg.body("Opción inválida. Elige una proteína del 1 al 4.")
            return str(resp)
        data['combos'][-1]['protein'] = incoming
        msg.body("¿Qué bebida quieres?\n" + '\n'.join(f"{k}. {v}" for k, v in BEVERAGE_OPTIONS.items()))
        session['state'] = STATE_BEVERAGE

    elif state == STATE_BEVERAGE:
        if incoming not in BEVERAGE_OPTIONS:
            msg.body("Opción inválida. Elige una bebida del 1 al 8.")
            return str(resp)
        data['combos'][-1]['beverage'] = incoming
        msg.body("¿Deseas algún extra?\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in EXTRA_OPTIONS.items()))
        session['state'] = STATE_EXTRA

    elif state == STATE_EXTRA:
        if incoming not in EXTRA_OPTIONS:
            msg.body("Opción inválida. Elige un extra válido.")
            return str(resp)
        data['combos'][-1]['extra'] = incoming
        if data['current_combo'] < data['combos_total']:
            data['current_combo'] += 1
            msg.body(f"Combo {data['current_combo']} – Elige el tipo de combo:\n" + '\n'.join(f"{k}. {v[0]} – ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items()))
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

            msg.body("✅ ¡Gracias por tu pedido! Un humano te confirmará pronto el envío.")
            session = None

    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
