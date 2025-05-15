import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime
from threading import Timer

# Diccionario para seguimiento de pedidos activos
pedidos_activos = {}
seguimiento_activo = {}



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
STORE_NUMBER   = 'whatsapp:+5215612522186'   # asegúrate de incluir el "1" tras +52

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
# Menú de bebidas (Dirty Horchata pasa a EXTRA_OPTIONS)
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
    '5':  ("Limonada Natural",        45.00),
    '6':  ("Jamaica con Limón",       45.00),
    '7':  ("Coca-Cola",            45.00),
    '8':  ("Pepsi",                45.00),
    '9':  ("Manzanita Sol",        45.00),
    '10': ("Mirinda",              45.00),
    '11': ("Seven Up",             45.00),
    '12': ("Ningun extra",          0.00),
}

@app.route("/", methods=["GET"])
def home():
    return "✅ Chilo Bot is running!"

@app.route("/whatsapp", methods=['POST'])
def whatsapp():
    incoming = request.values.get('Body', '').strip()
    sender   = request.values.get('From')
    print(f"📩 Mensaje recibido de {sender}: {incoming}")

    resp     = MessagingResponse()
    msg      = resp.message()

    # Verifica si el cliente tiene un pedido activo
    if sender in pedidos_activos:
        datos = pedidos_activos[sender]
        estado = datos.get('estado', 1)
        esperando_reseña = datos.get('esperando_reseña', False)
        reseña_pedida = datos.get('reseña_pedida', False)
        hora_reseña = datos.get('hora_reseña')
        cerrado = datos.get('cerrado', False)

        # Si ya mandó reseña, cerrar pedido
        if reseña_pedida:
            pedidos_activos[sender]['cerrado'] = True
            pedidos_activos.pop(sender)

        # Si pasaron más de 2 hrs desde que se pidió reseña y no ha contestado, cerrar también
        elif esperando_reseña and hora_reseña:
            minutos_pasados = (datetime.now() - hora_reseña).total_seconds() / 60
            if minutos_pasados > 120:
                pedidos_activos[sender]['cerrado'] = True
                pedidos_activos.pop(sender)

        # Si el ticket no está cerrado aún, y sigue activo
        elif not cerrado:
            estados_texto = {
                1: "🧾 Pedido generado",
                2: "👨‍🍳 En preparación",
                3: "🥡 Listo para entregar",
                4: "🚗 En camino",
                5: "✅ Entregado",
            }
            status = estados_texto.get(estado, "Estado desconocido")
            msg.body(
                f"📦 El status de tu pedido es: *{status}*.\n"
                "Si necesitas más información, puedes contactar directamente con la tienda:\n"
                "👉 https://wa.me/5219993872027\n\n"
                "Gracias, *Chilo* 🤖🌶️"
            )
            return str(resp)





    session = sessions.get(sender, {
        'state': None,
        'data': {
            'name':           None,
            'combos_total':   0,
            'current_combo':  0,
            'combos':         [],
        }
    })
    # Validación del menú de seguimiento (solo responde si es la tienda)
    if sender == STORE_NUMBER and incoming in ['1', '2', '3', '4', '5']:
        print(f"🟢 Menú de seguimiento activado desde tienda: {incoming}")

        # Buscar el primer pedido activo del cliente
        print("📦 Pedidos activos actuales:", pedidos_activos)
        for user, data in pedidos_activos.items():
            if data['estado'] < 5:
                nombre_cliente = data['nombre']
                estado_actual = int(incoming)
                id_pedido = data['id']

                estados = {
                    1: "✅ Tu orden ha sido generada.",
                    2: "👨‍🍳 Estamos preparando tu pedido.",
                    3: "🛎️ Tu pedido ya está listo para entregar.",
                    4: "🛵 Tu pedido ha sido enviado.",
                    5: f"🥡 {nombre_cliente}, tu pedido ha sido entregado. ¡Gracias por tu preferencia!"
                }

                print(f"📤 Enviando estado {estado_actual} a {user} ({nombre_cliente})")

                # Enviar mensaje al cliente
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=user,
                    body=estados[estado_actual]
                )

                # Actualizar estado
                pedidos_activos[user]['estado'] = estado_actual

                # Si es entregado (5), programar reseña
                if estado_actual == 5:
                    pedidos_activos[user]['esperando_reseña'] = True
                    pedidos_activos[user]['reseña_pedida'] = True
                    pedidos_activos[user]['hora_reseña'] = datetime.now()

                    def enviar_reseña():
                        client.messages.create(
                            from_=SANDBOX_NUMBER,
                            to=user,
                            body=(
                                f"{nombre_cliente}, espero que hayas disfrutado tus chilaquiles 🍽️.\n"
                                "¿Tienes algún comentario o sugerencia? Tu opinión es muy valiosa para nosotros 🙏"
                            )
                        )
                        print(f"📩 Se envió mensaje de reseña a {nombre_cliente}")

                    Timer(1800, enviar_reseña).start()


                break
        else:
            print("⚠️ No se encontró ningún pedido activo para actualizar.")
        return ('', 204)

    state = session['state']

    if state is None:
        msg.body(
            "¡Hola! 👋 Gracias por escribir a *Los Shelakeles*.\n"
            "Soy *Chilo* 🤖🌶️ y estoy para ayudarte a generar tu pedido.\n"
            "¿Me puedes dar tu nombre por favor?"
        )
        session['state'] = STATE_AWAITING_NAME

    elif state == STATE_AWAITING_NAME:
        name = incoming.title()
        session['data']['name'] = name
        msg.body(
            f"¡Excelente, {name}! 🚚\n"
            "¿A qué dirección se enviaria tu pedido? Esto para que podamos calcular el costo de envío"
        )
        session['state'] = STATE_ASK_ADDRESS

    elif state == STATE_ASK_ADDRESS:
        address = incoming
        session['data']['address'] = address
        msg.body(
            "¿Con cuál opción comenzamos? 🌶️\n\n"
            "1️⃣ Ver menú chingón  \n"
            "2️⃣ Ya sé qué quiero, armemos el pedido  \n"
            "3️⃣ Promos chingonas de hoy  \n"
            "4️⃣ Hablar con un humano"
        )
        session['state'] = STATE_MAIN_MENU


    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Claro que sí! Aquí está el menú chingón: 📎 {MENU_LINK}")
            def send_ok():
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=sender,
                    body="Estoy aquí para ayudarte, escribe ok cuando estés listo para armar tu pedido Chilalover."
                )
            Timer(5.0, send_ok).start()
            session['state'] = STATE_OPTION1_WAIT_OK

        elif incoming == '2':
            msg.body(
                "Perfecto Chilalover 😎, vamos a armar tu pedido.\n"
                "🧾 ¿Cuántos combos vas a querer hoy?\n"
                "Responde con un número (1, 2, 3...)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT

        elif incoming == '3':
            msg.body(
                "🔥 Estas son las promos chingonas activas este mes:\n"
                "👉 Promo del mes ...\n"
                "¿Quieres entrar al grupo exclusivo de *Promos Chingonas* para que te enteres antes que nadie de nuestras promos?\n"
                "1️⃣ Sí, agrégame\n2️⃣ No, gracias"
            )
            session['state'] = 'promos_optin'

        elif incoming == '4':
            name = session['data'].get('name', 'Cliente')
            phone = sender.split("whatsapp:")[1].lstrip("+")
            contact_link = f"https://wa.me/{phone}"

            msg.body(
                "👌 ¡Chingón! En breve uno de nuestros humanos chingones te va a contactar por este medio.\n"
                "Gracias por preferir *Los Shelakeles*, Chilalover. 🌶️"
            )

            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=(
                    f"*{name}* quiere hablar con un humano 🤖➡️🧑\n"
                    f"📞 Contacto directo: {contact_link}"
                )
            )

            session = None

        else:
            msg.body("No entendí, elige una opción del 1 al 4.")

    elif state == STATE_OPTION1_WAIT_OK:
        name = session['data']['name']
        if incoming.lower() == 'ok':
            msg.body(
                "🧾 ¡Chingón! ¿Cuántos combos vas a querer hoy?\n"
                "Responde con un número (1, 2, 3...)."
            )
            session['state'] = STATE_ASK_COMBO_COUNT
        elif incoming == '1':
            msg.body("En breve un humano te atenderá. ¡Gracias!")
            session = None
        else:
            msg.body(
                f"Disculpa {name}, no entendí. Escribe *ok* para continuar "
                "o presiona *1* para hablar con un humano."
            )

    elif state == STATE_ASK_COMBO_COUNT:
        try:
            count = int(incoming)
        except ValueError:
            msg.body("Disculpa, no entendí. ¿Cuántos combos vas a querer hoy? (1–9)")
            sessions[sender] = session
            return str(resp)

        if count >= 10:
            name = session['data']['name']
            phone = sender.split("whatsapp:")[1].lstrip("+")
            contact_link = f"https://wa.me/{phone}"

            # Notificar a la tienda
            store_body = (
                f"🚨 *Pedido especial* 🚨\n"
                f"Cliente: {name}\n"
                f"Cantidad de combos: {count}\n"
                f"Contacto: {contact_link}\n"
                "Favor de atender personalmente para asegurar la mejor atención."
            )
            client.messages.create(
                from_=SANDBOX_NUMBER,
                to=STORE_NUMBER,
                body=store_body
            )

            # Notificar al cliente
            msg.body(
                "🙌 ¡Gracias por tu interés! Como tu pedido es de más de 10 combos, "
                "te vamos a atender personalmente 💬. En unos momentos un humano te responderá "
                "para cerrar el pedido."
            )
            session = None
        else:
            session['data']['combos_total'] = count
            session['data']['current_combo'] = 1
            session['state'] = STATE_ASK_COMBO_TYPE
            msg.body(
                f"Perfecto! 👊 Empezamos con el *Combo 1*:\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]} ..... ${v[1]:.2f}"
                    for k, v in COMBO_OPTIONS.items()
                )
            )


    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo': incoming})
            session['state'] = STATE_ASK_PROTEIN
            msg.body(
                f"🍗 ¿Qué proteína quieres para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]}{' + $%.2f' % v[1] if v[1] else ''}"
                    for k, v in PROTEIN_OPTIONS.items()
                )
            )
        else:
            msg.body("Disculpa, elige 1, 2 o 3 según el combo que quieres.")

    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein'] = incoming
            session['state'] = STATE_ASK_BEVERAGE
            msg.body(
                f"🥤 ¿Qué bebida quieres para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v}"
                    for k, v in BEVERAGE_OPTIONS.items()
                )
            )
        else:
            msg.body("Disculpa, elige 1–4 según la proteína.")

    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage'] = incoming
            session['state'] = STATE_ASK_EXTRA
            msg.body(
                f"🍳 ¿Qué extra quieres para el *Combo {session['data']['current_combo']}*?\n\n"
                + "\n".join(
                    f"{num_emoji(k)} {v[0]} ..... ${v[1]:.2f}"
                    for k, v in EXTRA_OPTIONS.items()
                )
            )
        else:
            msg.body("Disculpa, elige una opción del 1 al 9 para la bebida.")

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
                "Confírmame con:\n1️⃣ Así está OK 👌\n2️⃣ Quiero corregirlo"
            )
        else:
            msg.body("Disculpa, elige un extra válido (1–12).")

    elif state == STATE_SUMMARY_CONFIRM:
        total   = session['data']['combos_total']
        current = session['data']['current_combo']
        name    = session['data']['name']
        address = session['data']['address']

        if incoming == '1':
            if current < total:
                # … lógica de múltiples combos …
                pass
            else:
                # ——— 1) Generar ID del pedido ———
                nombre_corto  = name[:3].upper()
                telefono_raw  = sender.split("whatsapp:")[1].lstrip("+")
                ultimos_dig   = telefono_raw[-4:]
                fecha         = datetime.now().strftime("%d%m%y")
                id_pedido     = f"{nombre_corto}{ultimos_dig}{fecha}"

                # ——— 2) Guardar el pedido en pedidos_activos ———
                pedidos_activos[sender] = {
                    'id':           id_pedido,
                    'nombre':       name,
                    'estado':       1,
                    'hora_entrega': datetime.now(),
                    'esperando_reseña': False,
                    'reseña_pedida':   False,
                    'cerrado': False
                }

                print(f"✅ Pedido guardado en pedidos_activos: {pedidos_activos}")


                # ——— 3) Calcular total y generar resumen ———
                amount = 0
                lines  = []
                for i, c in enumerate(session['data']['combos'], start=1):
                    cn, cp = COMBO_OPTIONS[c['combo']]
                    pn, pp = PROTEIN_OPTIONS[c['protein']]
                    bv     = BEVERAGE_OPTIONS[c['beverage']]
                    en, ep = EXTRA_OPTIONS[c['extra']]
                    amount += cp + pp + ep
                    lines.append(f"• Combo {i}: {cn} | Prot: {pn}{' (+$%.2f)'%pp if pp else ''} | Beb: {bv} | Extra: {en}{' (+$%.2f)'%ep if ep else ''}")
                order_summary = "\n".join(lines)

                # ——— 4) Enviar resumen a la tienda con dirección y formato limpio ———
                body_store = (
                    f"🛒 *Nuevo pedido recibido*\n"
                    f"*ID del pedido:* `{id_pedido}`\n"
                    f"*Cliente:* {name}\n"
                    f"*Dirección:* {address}\n\n"
                    f"📦 *Detalles del pedido:*\n" +
                    "\n".join(
                        f"{num_emoji(str(i))} *{COMBO_OPTIONS[c['combo']][0]}*\n"
                        f"   • Proteína: {PROTEIN_OPTIONS[c['protein']][0]}\n"
                        f"   • Bebida: {BEVERAGE_OPTIONS[c['beverage']]}\n"
                        f"   • Extra: {EXTRA_OPTIONS[c['extra']][0]}"
                        for i, c in enumerate(session['data']['combos'], start=1)
                    ) + 
                    f"\n\n💰 *Total:* ${amount:.2f}\n"
                    f"📞 *Contacto:* https://wa.me/{telefono_raw}"
                )


                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=body_store
                )

                # ——— 5) Enviar menú de seguimiento a la tienda ———
                seguimiento_msg = (
                    f"📝 *Seguimiento para pedido {id_pedido}*:\n"
                    "Responde con el número del estado actual:\n\n"
                    "1️⃣ En preparación\n"
                    "2️⃣ Orden lista\n"
                    "3️⃣ Lista para envío\n"
                    "4️⃣ En camino\n"
                    "5️⃣ Entregado"
                )
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=seguimiento_msg
                )

                # ——— 6) Confirmación al cliente con nota de envío ———
                msg.body(
                    f"✅ Pedido completo (ID: {id_pedido})\n\n"
                    f"{order_summary}\n\n"
                    f"Total: ${amount:.2f}\n"
                    "En breve un humano te confirmará el costo de envío. 📦"
                )

                # Cerrar sesión
                session = None

        elif incoming == '2':
            # … lógica de corrección …
            session['data']['combos'].pop()
            session['state'] = STATE_ASK_COMBO_TYPE
            msg.body("OK, corrijamos tu combo:")
        else:
            msg.body("Responde 1️⃣ para confirmar o 2️⃣ para corregir.")




    elif state == 'promos_optin':
        if incoming == '1':
            msg.body("¡Perfecto! Únete aquí al grupo: https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP 💥")
        elif incoming == '2':
            msg.body("No hay falla, Chilalover. Si cambias de opinión, aquí estaré 🌶️")
        else:
            msg.body("Disculpa, no entendí. Contesta 1️⃣ para unirte o 2️⃣ para rechazar.")
        session = None

    else:
        msg.body("Ups, algo salió mal. Reiniciemos. 🌶️")
        session = None

    # Si el cliente tiene reseña pendiente
    if sender in pedidos_activos and pedidos_activos[sender].get('esperando_reseña'):
        nombre = pedidos_activos[sender]['nombre']
        id_pedido = pedidos_activos[sender].get('id', 'SINID')

        # Reenviar reseña a la tienda
        client.messages.create(
            from_=SANDBOX_NUMBER,
            to=STORE_NUMBER,
            body=(
                f"⭐ *Reseña recibida de {nombre}* (ID: {id_pedido}):\n“{incoming}”"
            )
        )
        pedidos_activos.pop(sender)
        return str(resp)



    # Guardar o borrar sesión
    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
