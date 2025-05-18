import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)

# Twilio REST client – define estas variables en Replit Secrets
client = Client(
    os.environ['TWILIO_ACCOUNT_SID'],
    os.environ['TWILIO_AUTH_TOKEN']
)

# Números WhatsApp (Twilio y tienda)
SANDBOX_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER   = 'whatsapp:+5215612522186'

# Sesiones en memoria
sessions = {}
pedidos_activos = {}

# Estados de conversación
STATE_AWAITING_NAME    = 'awaiting_name'
STATE_ASK_ADDRESS      = 'ask_address'
STATE_MAIN_MENU        = 'main_menu'
STATE_OPTION1_WAIT_OK  = 'option1_wait_ok'
STATE_ASK_COMBO_COUNT  = 'ask_combo_count'
STATE_ASK_COMBO_TYPE   = 'ask_combo_type'
STATE_ASK_PROTEIN      = 'ask_protein'
STATE_ASK_BEVERAGE     = 'ask_beverage'
STATE_ASK_EXTRA        = 'ask_extra'

# Emoji helper
digit_emoji = {
    '0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣',
    '5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'
}
def num_emoji(s: str) -> str:
    return ''.join(digit_emoji[d] for d in s)

# Menús
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
    '8': "Seven Up"
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
    incoming = request.values.get('Body', '').strip()
    sender   = request.values.get('From')
    resp     = MessagingResponse()
    msg      = resp.message()

    # Recuperar o crear sesión
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

    # 1) Saludo y pedir nombre
    if state is None:
        msg.body(
            "¡Hola! 👋 Gracias por escribir a *Los Shelakeles*.\n"
            "Soy *Chilo* 🤖🌶️ y estoy para ayudarte a generar tu pedido.\n"
            "¿Me puedes dar tu nombre?"
        )
        session['state'] = STATE_AWAITING_NAME

    # 2) Guardar nombre y pedir dirección
    elif state == STATE_AWAITING_NAME:
        session['data']['name'] = incoming.title()
        msg.body(f"¡Excelente, {session['data']['name']}! 🚚\n¿A qué dirección enviamos tu pedido?")
        session['state'] = STATE_ASK_ADDRESS

    # 3) Guardar dirección y mostrar menú principal
    elif state == STATE_ASK_ADDRESS:
        session['data']['address'] = incoming
        msg.body(
            "¿Con cuál opción comenzamos? 🌶️\n\n"
            "1️⃣ Ver menú chingón  \n"
            "2️⃣ Ya sé qué quiero, armemos el pedido  \n"
            "3️⃣ Promos chingonas de hoy  \n"
            "4️⃣ Hablar con un humano"
        )
        session['state'] = STATE_MAIN_MENU

    # 4) Manejo de menú principal
    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Claro que sí! Aquí está el menú chingón: 📎 {MENU_LINK}")
            Timer(5.0, lambda: client.messages.create(
                from_=SANDBOX_NUMBER,
                to=sender,
                body="Escribe *ok* cuando estés listo para armar tu pedido."
            )).start()
            session['state'] = STATE_OPTION1_WAIT_OK

        elif incoming == '2':
            msg.body(
                "Perfecto 😎, ¿cuántos combos vas a querer hoy?\n"
                "Responde con un número (1–9)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT

        elif incoming == '3':
            msg.body(
                "🔥 Promos de hoy:\n👉 Promo del mes …\n"
                "¿Entras al grupo de *Promos Chingonas*?\n"
                "1️⃣ Sí\n2️⃣ No"
            )
            session['state'] = 'promos_optin'

        elif incoming == '4':
            name = session['data']['name']
            phone = sender.split("whatsapp:")[1]
            msg.body("👌 En un momento te contacta un humano.")
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=f"*{name}* solicita atención humana. 📞 +{phone}"
            )
            session = None

        else:
            msg.body("Elige 1–4, porfa.")

    # 5) OK tras ver menú
    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body(
                "🧾 ¡Chingón! ¿Cuántos combos vas a querer hoy?\n"
                "Responde con un número (1–9)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body("Escribe *ok* cuando estés listo.")

    # 6) Número de combos
    elif state == STATE_ASK_COMBO_COUNT:
        try:
            count = int(incoming)
        except ValueError:
            msg.body("Dime un número válido (1–9).")
            sessions[sender] = session
            return str(resp)

        if count >= 10:
            name = session['data']['name']
            phone = sender.split("whatsapp:")[1]
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=(
                    f"🚨 Pedido especial 🚨\n"
                    f"Cliente: {name}\n"
                    f"Combos: {count}\n"
                    f"Contacto: +{phone}"
                )
            )
            msg.body("¡Gracias! Un humano te atenderá.")
            session = None
        else:
            session['data']['combos_total']  = count
            session['data']['current_combo'] = 1
            session['state'] = STATE_ASK_COMBO_TYPE
            msg.body(
                f"Combo 1️⃣:\n" +
                "\n".join(
                    f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}"
                    for k, v in COMBO_OPTIONS.items()
                )
            )

    # 7) Elegir combo
    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo': incoming})
            session['state'] = STATE_ASK_PROTEIN
            msg.body(
                f"Proteína para Combo {session['data']['current_combo']}:\n" +
                "\n".join(
                    f"{num_emoji(k)} {v[0]}{' +$%.2f' % v[1] if v[1] else ''}"
                    for k, v in PROTEIN_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige 1, 2 o 3.")

    # 8) Proteína
    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein'] = incoming
            session['state'] = STATE_ASK_BEVERAGE
            msg.body(
                f"Bebida para Combo {session['data']['current_combo']}:\n" +
                "\n".join(
                    f"{num_emoji(k)} {v}"
                    for k, v in BEVERAGE_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige 1–4.")

    # 9) Bebida
    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage'] = incoming
            session['state'] = STATE_ASK_EXTRA
            msg.body(
                f"Extra para Combo {session['data']['current_combo']}:\n" +
                "\n".join(
                    f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}"
                    for k, v in EXTRA_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige 1–8.")

    # 10) Extra → resumen y siguiente combo / terminar
    elif state == STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            session['data']['combos'][-1]['extra'] = incoming
            d = session['data']
            idx = d['current_combo']
            total = d['combos_total']
            combo = d['combos'][-1]
            # datos del combo
            cn, _ = COMBO_OPTIONS[combo['combo']]
            pn, _ = PROTEIN_OPTIONS[combo['protein']]
            bv     = BEVERAGE_OPTIONS[combo['beverage']]
            en, _ = EXTRA_OPTIONS[combo['extra']]

            # responder resumen de este combo
            msg.body(
                f"🧾 *Combo {idx}: {cn}*\n"
                f"• Proteína: {pn}\n"
                f"• Bebida: {bv}\n"
                f"• Extra: {en}"
            )

            # ¿Hay otro combo?
            if idx < total:
                d['current_combo'] += 1
                session['state'] = STATE_ASK_COMBO_TYPE
                msg.body(
                    f"👍 ¡Vamos con el siguiente!\n\n"
                    + "\n".join(
                        f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}"
                        for k, v in COMBO_OPTIONS.items()
                    )
                )
            else:
                # último combo → finalizar pedido
                name    = d['name']
                address = d['address']
                phone   = sender.split("whatsapp:")[1]
                # generar ID
                idp = f"{name[:3].upper()}{phone[-4:]}{datetime.now().strftime('%d%m%y')}"
                # calcular total y resumen completo
                amount = 0
                lines  = []
                for i, c in enumerate(d['combos'], 1):
                    cn, cp = COMBO_OPTIONS[c['combo']]
                    pn, pp = PROTEIN_OPTIONS[c['protein']]
                    bv     = BEVERAGE_OPTIONS[c['beverage']]
                    en, ep = EXTRA_OPTIONS[c['extra']]
                    amount += cp + pp + ep
                    lines.append(f"• Combo {i}: {cn} | Prot: {pn} | Beb: {bv} | Extra: {en}")
                resumen = "\n".join(lines)
                # enviar a tienda
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=(
                        f"🛒 *Nuevo pedido*\n"
                        f"ID: `{idp}`\n"
                        f"Cliente: {name}\n"
                        f"Dirección: {address}\n\n"
                        f"{resumen}\n\n"
                        f"💰 Total: ${amount:.2f}\n"
                        f"📞 Contacto: +{phone}"
                    )
                )
                # confirmar al cliente
                msg.body(
                    f"✅ Pedido completo (ID: {idp})\n"
                    f"{resumen}\n"
                    f"💰 Total: ${amount:.2f}\n"
                    "En breve un humano confirmará el envío."
                )
                # guardar activo si lo necesitas
                pedidos_activos[sender] = {'id': idp, 'nombre': name, 'estado': 1}
                session = None

        else:
            msg.body("Elige un extra válido (1–12).")

    # PROMOS
    elif state == 'promos_optin':
        if incoming == '1':
            msg.body("¡Únete aquí! https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP")
        else:
            msg.body("OK, si cambias avísame.")
        session = None

    else:
        msg.body("Algo falló. Reiniciemos.")
        session = None

    # Guardar o borrar sesión
    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
