import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)

# Twilio REST client – variables in Replit Secrets
client = Client(
    os.environ['TWILIO_ACCOUNT_SID'],
    os.environ['TWILIO_AUTH_TOKEN']
)

# WhatsApp numbers
SANDBOX_NUMBER = 'whatsapp:+5215612268107'  # Chilo's number
STORE_NUMBER   = 'whatsapp:+5215612522186'  # Store number

# In-memory session store
sessions = {}

# Conversation states
STATE_AWAITING_NAME    = 'awaiting_name'
STATE_ASK_ADDRESS      = 'ask_address'
STATE_MAIN_MENU        = 'main_menu'
STATE_OPTION1_WAIT_OK  = 'option1_wait_ok'
STATE_ASK_COMBO_COUNT  = 'ask_combo_count'
STATE_ASK_COMBO_TYPE   = 'ask_combo_type'
STATE_ASK_PROTEIN      = 'ask_protein'
STATE_ASK_BEVERAGE     = 'ask_beverage'
STATE_ASK_EXTRA        = 'ask_extra'

# Helper: digit to emoji
digit_emoji = {d: f"{d}\u20E3" for d in '0123456789'}
def num_emoji(s: str) -> str:
    return ''.join(digit_emoji.get(d, d) for d in s)

# Menu data
MENU_LINK = "https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing"
COMBO_OPTIONS = {
    '1': ("El Clásico Shingón", 185.00),
    '2': ("El Verde Shingón",   185.00),
    '3': ("El Que No Se Decide",215.00),
}
PROTEIN_OPTIONS = {
    '1': ("Pollito",       0.00),
    '2': ("Carnita Asada", 0.00),
    '3': ("Cecina de Res",45.00),
    '4': ("Sin proteína",  0.00),
}
BEVERAGE_OPTIONS = {
    '1': "Limonada Natural",
    '2': "Jamaica con Limón",
    '3': "Coca-Cola",
    '4': "Pepsi",
    '5': "Manzanita Sol",
    '6': "Squirt",
    '7': "Mirinda",
    '8': "Seven Up",
}
EXTRA_OPTIONS = {
    '1':  ("Huevito duro",       18.00),
    '2':  ("Huevito estrellado", 18.00),
    '3':  ("Guacamole chingon",  45.00),
    '4':  ("Dirty Horchata",     45.00),
    '5':  ("Limonada Natural",   45.00),
    '6':  ("Jamaica con Limón",  45.00),
    '7':  ("Coca-Cola",          45.00),
    '8':  ("Pepsi",              45.00),
    '9':  ("Manzanita Sol",      45.00),
    '10': ("Mirinda",            45.00),
    '11': ("Seven Up",           45.00),
    '12': ("Ningun extra",        0.00),
}

@app.route("/", methods=["GET"])
def home():
    return "✅ Chilo Bot is running!"

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    incoming = request.values.get('Body','').strip()
    sender   = request.values.get('From')
    resp     = MessagingResponse()
    msg      = resp.message()

    # Retrieve or init session
    session = sessions.get(sender, {
        'state': None,
        'data': {
            'name':           None,
            'address':        None,
            'combos_total':   0,
            'current_combo':  0,
            'combos':         [],
        }
    })
    state = session['state']

    # 1. Awaiting name
    if state is None:
        msg.body(
            "¡Hola! 👋 Gracias por escribir a *Los Shelakeles*.\n"
            "Soy *Chilo* 🤖🌶️ y estoy para ayudarte a generar tu pedido.\n"
            "¿Me puedes dar tu nombre?"
        )
        session['state'] = STATE_AWAITING_NAME

    # 2. Ask address
    elif state == STATE_AWAITING_NAME:
        session['data']['name'] = incoming.title()
        msg.body("¿A qué dirección enviamos tu pedido?")
        session['state'] = STATE_ASK_ADDRESS

    # 3. Main menu
    elif state == STATE_ASK_ADDRESS:
        session['data']['address'] = incoming
        msg.body(
            "¿Con cuál opción comenzamos?\n\n"
            "1️⃣ Ver menú chingón  \n"
            "2️⃣ Armar pedido  \n"
            "3️⃣ Promos chingonas  \n"
            "4️⃣ Hablar con un humano"
        )
        session['state'] = STATE_MAIN_MENU

    # Main menu handling
    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Aquí está el menú: 📎 {MENU_LINK}")
            session['state'] = STATE_OPTION1_WAIT_OK

        elif incoming == '2':
            msg.body("🧾 ¿Cuántos combos vas a querer hoy? (1–9)")
            session['state'] = STATE_ASK_COMBO_COUNT

        elif incoming == '3':
            msg.body(
                "🔥 Estas son las promos chingonas:\n"
                "👉 https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP"
            )
            session = None

        elif incoming == '4':
            name = session['data']['name']
            contact_link = f"https://wa.me/{sender.split(':')[1]}"
            msg.body("👌 En breve uno de nuestros humanos te contactará.")
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=f"*{name}* solicita atención humana. {contact_link}"
            )
            session = None

        else:
            msg.body("Por favor, elige una opción del 1 al 4.")

    # Option1 wait OK
    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body("🧾 ¿Cuántos combos vas a querer hoy? (1–9)")
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body("Escribe 'ok' cuando estés listo o 4 para hablar con humano.")

    # Ask combo count
    elif state == STATE_ASK_COMBO_COUNT:
        try:
            count = int(incoming)
        except ValueError:
            msg.body("Por favor, indica un número válido (1–9)")
            if session: sessions[sender] = session
            return str(resp)
        if count >= 10:
            name = session['data']['name']
            link = f"https://wa.me/{sender.split(':')[1]}"
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=f"🚨 Pedido especial: {name} solicita {count} combos. {link}"
            )
            msg.body("🙌 Gracias por tu interés. Un humano te atenderá pronto.")
            session = None
        else:
            session['data']['combos_total'] = count
            session['data']['current_combo'] = 1
            session['state'] = STATE_ASK_COMBO_TYPE
            msg.body(
                f"Perfecto! 👊 Empezamos con el *Combo 1*:\n" +
                "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in COMBO_OPTIONS.items())
            )

    # Ask combo type
    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo': incoming})
            session['state'] = STATE_ASK_PROTEIN
            msg.body(
                f"🍗 ¿Qué proteína quieres para el *Combo {session['data']['current_combo']}*?:\n" +
                "\n".join(f"{num_emoji(k)} {v[0]}{' (+$%.2f)'%v[1] if v[1] else ''}" for k,v in PROTEIN_OPTIONS.items())
            )
        else:
            msg.body("Por favor elige 1, 2 o 3 según el combo.")

    # Ask protein
    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein'] = incoming
            session['state'] = STATE_ASK_BEVERAGE
            msg.body(
                f"🥤 ¿Qué bebida quieres para el *Combo {session['data']['current_combo']}*?:\n" +
                "\n".join(f"{num_emoji(k)} {v}" for k,v in BEVERAGE_OPTIONS.items())
            )
        else:
            msg.body("Por favor elige 1–4 según la proteína.")

    # Ask beverage
    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage'] = incoming
            session['state'] = STATE_ASK_EXTRA
            msg.body(
                f"🍳 ¿Qué extra quieres para el *Combo {session['data']['current_combo']}*?:\n" +
                "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in EXTRA_OPTIONS.items())
            )
        else:
            msg.body("Por favor elige 1–12 para el extra.")

    # Ask extra and immediate summary/next
    elif state == STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            data = session['data']
            total   = data['combos_total']
            current = data['current_combo']
            name    = data['name']
            address = data['address']
            combo   = data['combos'][-1]
            # Save extra
            combo['extra'] = incoming
            # Build combo summary
            cn, _  = COMBO_OPTIONS[combo['combo']]
            pn, _  = PROTEIN_OPTIONS[combo['protein']]
            bv     = BEVERAGE_OPTIONS[combo['beverage']]
            en, _  = EXTRA_OPTIONS[incoming]
            resumen_combo = (
                f"🧾 Combo {current}: {cn}\n"
                f"• Proteína: {pn}\n"
                f"• Bebida: {bv}\n"
                f"• Extra: {en}"
            )
            # Next combo or finalize
            if current < total:
                data['current_combo'] += 1
                session['state'] = STATE_ASK_COMBO_TYPE
                msg.body(
                    f"{resumen_combo}\n\n👍 ¡Listo! Vamos con el siguiente combo.\n"
                    f"*Combo {data['current_combo']}*, elige:"
                )
            else:
                # Finalize order
                short = name[:3].upper()
                tel   = sender.split(':')[1]
                pid   = f"{short}{tel[-4:]}{datetime.now().strftime('%d%m%y')}"
                # Calculate total & summary
                amount = 0
                lines = []
                for i,c in enumerate(data['combos'], start=1):
                    cn_i, cp_i = COMBO_OPTIONS[c['combo']]
                    pn_i, pp_i = PROTEIN_OPTIONS[c['protein']]
                    bv_i        = BEVERAGE_OPTIONS[c['beverage']]
                    en_i, ep_i  = EXTRA_OPTIONS[c['extra']]
                    amount += cp_i + pp_i + ep_i
                    lines.append(
                        f"• Combo {i}: {cn_i} | Prot: {pn_i} | Beb: {bv_i} | Extra: {en_i}"
                    )
                order_summary = "\n".join(lines)
                contact = f"https://wa.me/{tel}"
                # Send to store
                body_store = (
                    f"🛒 Nuevo pedido (ID: {pid})\n"
                    f"Cliente: {name}\n"
                    f"Dirección: {address}\n\n"
                    f"{order_summary}\n\n"
                    f"Total: ${amount:.2f}\n"
                    f"Contacto: {contact}"
                )
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=body_store
                )
                # Confirm to user
                msg.body(
                    f"{resumen_combo}\n\n"
                    f"✅ Pedido {pid} recibido!\n"
                    f"Total: ${amount:.2f}\n"
                    "En breve un humano confirmará el envío."
                )
                session = None
        else:
            msg.body("Por favor elige un extra válido (1–12).")

    else:
        msg.body("Ups, algo salió mal. Reiniciemos.")
        session = None

    # Save or clear session
    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 3000))
    app.run(host="0.0.0.0", port=port)
