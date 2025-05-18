import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

# Diccionario para seguimiento de pedidos activos
pedidos_activos = {}

app = Flask(__name__)

@app.route("/ping", methods=["GET"])
def ping():
    return "Chilo está online 🔥", 200

# Twilio REST client – define estas variables en Replit Secrets
client = Client(
    os.environ['TWILIO_ACCOUNT_SID'],
    os.environ['TWILIO_AUTH_TOKEN']
)

# WhatsApp sandbox and store numbers
SANDBOX_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER   = 'whatsapp:+5215612522186'   # incluye el "1" tras +52

# In‐memory session store (para producción, usa una base de datos)
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
STATE_SUMMARY_CONFIRM  = 'summary_confirm'

# Helper: turn a digit string "12" into "1️⃣2️⃣"
digit_emoji = {
    '0':'0️⃣','1':'1️⃣','2':'2️⃣','3':'3️⃣','4':'4️⃣',
    '5':'5️⃣','6':'6️⃣','7':'7️⃣','8':'8️⃣','9':'9️⃣'
}
def num_emoji(s: str) -> str:
    return ''.join(digit_emoji[d] for d in s)

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
    '8': "Seven Up"
}
EXTRA_OPTIONS = {
    '1':  ("Huevito duro",         18.00),
    '2':  ("Huevito estrellado",   18.00),
    '3':  ("Guacamole chingon",    45.00),
    '4':  ("Dirty Horchata",       45.00),
    '5':  ("Limonada Natural",     45.00),
    '6':  ("Jamaica con Limón",    45.00),
    '7':  ("Coca-Cola",            45.00),
    '8':  ("Pepsi",                45.00),
    '9':  ("Manzanita Sol",        45.00),
    '10': ("Mirinda",              45.00),
    '11': ("Seven Up",             45.00),
    '12': ("Ningun extra",         0.00),
}

@app.route("/", methods=["GET"])
def home():
    return "✅ Chilo Bot is running!"

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    incoming = request.values.get('Body', '').strip()
    sender   = request.values.get('From')
    print(f"📩 Mensaje recibido de {sender}: {incoming}")

    resp = MessagingResponse()
    msg  = resp.message()

    # --- Manejo de sesiones ---
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

    # --- 1) SALUDO Y DIRECCIÓN ---
    if state is None:
        msg.body(
            "¡Hola! 👋 Gracias por escribir a *Los Shelakeles*.\n"
            "Soy *Chilo* 🤖🌶️ y estoy para ayudarte a generar tu pedido.\n"
            "¿Me puedes dar tu nombre?"
        )
        session['state'] = STATE_AWAITING_NAME

    elif state == STATE_AWAITING_NAME:
        session['data']['name'] = incoming.title()
        msg.body(
            f"¡Excelente, {session['data']['name']}! 🚚\n"
            "¿A qué dirección enviamos tu pedido?"
        )
        session['state'] = STATE_ASK_ADDRESS

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

    # --- 2) MENÚ PRINCIPAL ---
    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Claro que sí! Aquí está el menú chingón: 📎 {MENU_LINK}")
            def send_ok():
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=sender,
                    body="Estoy aquí para ayudarte, escribe *ok* cuando estés listo para armar tu pedido."
                )
            Timer(5.0, send_ok).start()
            session['state'] = STATE_OPTION1_WAIT_OK

        elif incoming == '2':
            msg.body(
                "Perfecto 😎, vamos a armar tu pedido.\n"
                "🧾 ¿Cuántos combos vas a querer hoy?\n"
                "Responde con un número (1, 2, 3...)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT

        elif incoming == '3':
            msg.body(
                "🔥 Estas son las promos chingonas activas este mes:\n"
                "👉 Promo del mes ...\n"
                "¿Quieres entrar al grupo exclusivo de *Promos Chingonas*?\n"
                "1️⃣ Sí, agrégame\n2️⃣ No, gracias"
            )
            session['state'] = 'promos_optin'

        elif incoming == '4':
            name = session['data']['name']
            phone = sender.split("whatsapp:")[1].lstrip("+")
            contact_link = f"https://wa.me/{phone}"
            msg.body(
                "👌 ¡Chingón! En breve un humano te contactará.\n"
                "Gracias por preferir *Los Shelakeles*."
            )
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=(
                    f"*{name}* solicita atención humana 🤖➡️🧑\n"
                    f"Contacto: {contact_link}"
                )
            )
            session = None

        else:
            msg.body("No entendí, elige una opción (1–4).")

    # --- 3) OPCIÓN 1: OK PARA ARMAR PEDIDO ---
    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body(
                "🧾 ¡Chingón! ¿Cuántos combos vas a querer hoy?\n"
                "Responde con un número (1, 2, 3...)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body("Escribe *ok* cuando estés listo o *1* para hablar con un humano.")

    # --- 4) CUÁNTOS COMBOS ---
    elif state == STATE_ASK_COMBO_COUNT:
        try:
            count = int(incoming)
        except ValueError:
            msg.body("No entendí. Dime cuántos combos (1–9).")
            sessions[sender] = session
            return str(resp)

        if count >= 10:
            # pedido especial
            name = session['data']['name']
            phone = sender.split("whatsapp:")[1].lstrip("+")
            contact_link = f"https://wa.me/{phone}"
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=(
                    f"🚨 *Pedido especial* 🚨\n"
                    f"Cliente: {name}\n"
                    f"Combos: {count}\n"
                    f"Contacto: {contact_link}"
                )
            )
            msg.body(
                "🙌 ¡Gracias! Como pides 10+ combos, un humano te atenderá pronto."
            )
            session = None

        else:
            session['data']['combos_total']  = count
            session['data']['current_combo'] = 1
            session['state'] = STATE_ASK_COMBO_TYPE
            # envío primer menú de combos
            msg.body(
                f"Perfecto! 👊 Empezamos con el *Combo 1*:\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]} ..... ${v[1]:.2f}"
                    for k, v in COMBO_OPTIONS.items()
                )
            )

    # --- 5) TIPO DE COMBO ---
    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo': incoming})
            session['state'] = STATE_ASK_PROTEIN
            msg.body(
                f"🍗 ¿Qué proteína para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]}{' + $%.2f' % v[1] if v[1] else ''}"
                    for k, v in PROTEIN_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige 1, 2 o 3 según el combo.")

    # --- 6) PROTEÍNA ---
    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein'] = incoming
            session['state'] = STATE_ASK_BEVERAGE
            msg.body(
                f"🥤 ¿Qué bebida para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v}"
                    for k, v in BEVERAGE_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige 1–4 para la proteína.")

    # --- 7) BEBIDA ---
    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage'] = incoming
            session['state'] = STATE_ASK_EXTRA
            msg.body(
                f"🍳 ¿Qué extra para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]} ..... ${v[1]:.2f}"
                    for k, v in EXTRA_OPTIONS.items()
                )
            )
        else:
            msg.body("Elige una opción válida para la bebida.")

    # --- 8) EXTRA Y CONFIRMACIÓN DE CADA COMBO ---
    elif state == STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            session['data']['combos'][-1]['extra'] = incoming
            session['state'] = STATE_SUMMARY_CONFIRM
            idx   = session['data']['current_combo']
            combo = session['data']['combos'][-1]
            cn, cp = COMBO_OPTIONS[combo['combo']]
            pn, pp = PROTEIN_OPTIONS[combo['protein']]
            bv     = BEVERAGE_OPTIONS[combo['beverage']]
            en, ep = EXTRA_OPTIONS[combo['extra']]

            msg.body(
                f"🧾 Tu *Combo {idx}* quedó así:\n\n"
                f"✅ Combo: {cn}\n"
                f"✅ Proteína: {pn}{' (+$%.2f)'%pp if pp else ''}\n"
                f"✅ Bebida: {bv}\n"
                f"✅ Extra: {en}{' (+$%.2f)'%ep if ep else ''}\n\n"
                "Confírmame con:\n1️⃣ Así está OK"
            )
        else:
            msg.body("Elige un extra válido (1–12).")

    # --- 9) LÓGICA PARA CONFIRMAR CADA COMBO Y PASAR AL SIGUIENTE ---
    elif state == STATE_SUMMARY_CONFIRM:
        total   = session['data']['combos_total']
        current = session['data']['current_combo']
        name    = session['data']['name']
        address = session['data']['address']

        if incoming == '1':
            if current < total:
                # *** AQUÍ REENVIAMOS EL MENÚ DE COMBOS PARA EL SIGUIENTE ***
                session['data']['current_combo'] += 1
                session['state'] = STATE_ASK_COMBO_TYPE
                msg.body(
                    f"👍 ¡Listo! Vamos con el siguiente combo.\n\n"
                    + "\n".join(
                        f"{num_emoji(k)} {v[0]} ..... ${v[1]:.2f}"
                        for k, v in COMBO_OPTIONS.items()
                    )
                )
            else:
                # --- Es el último combo: calculamos total, generamos ID, y enviamos a tienda ---
                # 1) Generar ID:
                nombre_corto = name[:3].upper()
                telefono_raw = sender.split("whatsapp:")[1].lstrip("+")
                ultimos_dig  = telefono_raw[-4:]
                fecha        = datetime.now().strftime("%d%m%y")
                id_pedido    = f"{nombre_corto}{ultimos_dig}{fecha}"

                # 2) Calcular total y resumen:
                amount = 0
                lines  = []
                for i, c in enumerate(session['data']['combos'], start=1):
                    cn, cp = COMBO_OPTIONS[c['combo']]
                    pn, pp = PROTEIN_OPTIONS[c['protein']]
                    bv     = BEVERAGE_OPTIONS[c['beverage']]
                    en, ep = EXTRA_OPTIONS[c['extra']]
                    amount += cp + pp + ep
                    lines.append(
                        f"• Combo {i}: {cn} | Prot: {pn}{' (+$%.2f)'%pp if pp else ''} | "
                        f"Beb: {bv} | Extra: {en}{' (+$%.2f)'%ep if ep else ''}"
                    )
                order_summary = "\n".join(lines)

                # 3) Construir cuerpo para la tienda:
                body_store = (
                    f"🛒 *Nuevo pedido recibido*\n"
                    f"*ID:* `{id_pedido}`\n"
                    f"*Cliente:* {name}\n"
                    f"*Dirección:* {address}\n\n"
                    f"📦 *Detalles:*\n{order_summary}\n\n"
                    f"💰 *Total:* ${amount:.2f}\n"
                    f"📞 *Contacto:* https://wa.me/{telefono_raw}"
                )
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=body_store
                )

                # 4) Guardar en pedidos_activos:
                pedidos_activos[sender] = {
                    'id':     id_pedido,
                    'nombre': name,
                    'estado': 1
                }

                # 5) Confirmación al cliente:
                msg.body(
                    f"✅ Pedido completo (ID: {id_pedido})\n\n"
                    f"{order_summary}\n\n"
                    f"💰 Total: ${amount:.2f}\n"
                    "En breve un humano confirmará el costo de envío. 📦"
                )

                session = None

        else:
            msg.body("Responde *1️⃣* para confirmar.")

    # --- 10) PROMOS OPT-IN ---
    elif state == 'promos_optin':
        if incoming == '1':
            msg.body("¡Perfecto! Únete al grupo: https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP")
        else:
            msg.body("¡Entendido! Si cambias de opinión, aquí estaré.")
        session = None

    else:
        msg.body("Ups, algo salió mal. Reiniciemos. 🌶️")
        session = None

    # Guardar o borrar sesión
    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
