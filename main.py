import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

# Diccionario para seguimiento de pedidos activos
datos_pedidos = {}
seguimiento_activo = {}

app = Flask(__name__)

@app.route("/ping", methods=["GET"])
def ping():
    return "Chilo está online 🔥", 200

# Twilio REST client
env_sid = os.environ.get('TWILIO_ACCOUNT_SID')
env_token = os.environ.get('TWILIO_AUTH_TOKEN')
client = Client(env_sid, env_token)

# WhatsApp sandbox y tienda
SANDBOX_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER   = 'whatsapp:+5215612522186'

# Sesiones en memoria
sessions = {}

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
STATE_SUMMARY_CONFIRM  = 'summary_confirm'
STATE_PROMOS_OPTIN     = 'promos_optin'

# Emojis para números
digit_emoji = {str(i): f"{i}️⃣" for i in range(10)}
def num_emoji(s: str) -> str:
    return ''.join(digit_emoji.get(d, d) for d in s)

# Menús\MENU_LINK = "https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing"
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
    '12': ("Ningún extra",       0.00),
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

    # 1️⃣ Interceptar reseña temprana (30 minutos)
    if sender in datos_pedidos:
        pd = datos_pedidos[sender]
        if pd.get('esperando_reseña') and not pd.get('reseña_pedida'):
            mins = (datetime.now() - pd['hora_entrega']).total_seconds() / 60
            if mins < 30:
                msg.body("🕒 Un humano atenderá tu mensaje en breve.")
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=STORE_NUMBER,
                    body=f"📩 Cliente {pd['nombre']} escribió: “{incoming}”"
                )
                return str(resp)

    # 2️⃣ Actualizaciones SOLO desde la tienda con seguimiento activo
    if sender == STORE_NUMBER and incoming in ['1','2','3','4','5']:
        for user, pd in datos_pedidos.copy().items():
            if pd.get('estado',0) < 5 and pd['id'] in seguimiento_activo:
                nombre = pd['nombre']
                est     = int(incoming)
                txts = {
                    1: f"✅ {nombre}, pedido generado (ID: {pd['id']}).",
                    2: f"👨‍🍳 {nombre}, preparando (ID: {pd['id']}).",
                    3: f"🛎️ {nombre}, listo (ID: {pd['id']}).",
                    4: f"🛵 {nombre}, en camino (ID: {pd['id']}).",
                    5: f"🥡 {nombre}, entregado. ¡Gracias! (ID: {pd['id']}).",
                }
                client.messages.create(
                    from_=SANDBOX_NUMBER,
                    to=user,
                    body=txts[est]
                )
                datos_pedidos[user]['estado'] = est
                if est == 5:
                    datos_pedidos[user]['hora_entrega'] = datetime.now()
                    datos_pedidos[user]['esperando_reseña'] = True
                break
        return str(resp)

    # 3️⃣ Flujo de conversación con el cliente
    session = sessions.get(sender, {'state': None, 'data': {}})
    state   = session['state']

    if state is None:
        msg.body(
            "¡Hola! 👋 Soy Chilo 🤖🌶. ¿Cómo te llamas?"
        )
        session['state'] = STATE_AWAITING_NAME

    elif state == STATE_AWAITING_NAME:
        session['data']['nombre'] = incoming.title()
        msg.body(f"¡Genial, {session['data']['nombre']}! 🚚\n¿A qué dirección? 🌍")
        session['state'] = STATE_ASK_ADDRESS

    elif state == STATE_ASK_ADDRESS:
        session['data']['direccion'] = incoming
        msg.body(
            "¿Qué deseas hacer ahora? 🌶️\n"
            "1️⃣ Ver menú chingón\n"
            "2️⃣ Armar un pedido\n"
            "3️⃣ Promos\n"
            "4️⃣ Humano"
        )
        session['state'] = STATE_MAIN_MENU

    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Aquí el menú: 📎 {MENU_LINK}")
            Timer(5, lambda: client.messages.create(
                from_=SANDBOX_NUMBER, to=sender,
                body="Escribe OK cuando quieras armar tu pedido."
            )).start()
            session['state'] = STATE_OPTION1_WAIT_OK
        elif incoming == '2':
            msg.body("🧾 ¿Cuántos combos? Responde con número.")
            session['state'] = STATE_ASK_COMBO_COUNT
        elif incoming == '3':
            msg.body("🔥 Promos calientes!\n1️⃣ Sí\n2️⃣ No")
            session['state'] = STATE_PROMOS_OPTIN
        elif incoming == '4':
            link = f"https://wa.me/{sender.split(':')[1]}"
            msg.body("👌 En breve un humano te contacta.")
            client.messages.create(
                from_=SANDBOX_NUMBER, to=STORE_NUMBER,
                body=f"{session['data']['nombre']} solicita humano: {link}"
            )
            session = {}
        else:
            msg.body("Opción 1–4, por favor.")

    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body("🧾 ¿Cuántos combos? (1–9)")
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body("Escribe OK o 4 para humano.")

    elif state == STATE_ASK_COMBO_COUNT:
        try: num = int(incoming)
        except: 
            msg.body("Número inválido. 1–9")
            sessions[sender] = session
            return str(resp)
        if num >=10:
            client.messages.create(
                from_=SANDBOX_NUMBER,to=STORE_NUMBER,
                body=f"🚨 Pedido grande: {num} combos de {session['data']['nombre']}"
            )
            msg.body("Te atenderá humano pronto.")
            session = {}
        else:
            session['data']['combos_total']=num
            session['data']['current_combo']=1
            session['state']=STATE_ASK_COMBO_TYPE
            msg.body(
                "Elige combo:\n"+
                "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in COMBO_OPTIONS.items())
            )

    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data'].setdefault('combos',[]).append({'combo':incoming})
            session['state']=STATE_ASK_PROTEIN
            idx=session['data']['current_combo']
            msg.body(
                f"Combo {idx}, proteína:\n"+
                "\n".join(f"{num_emoji(k)} {v[0]}{' + $%.2f'%v[1] if v[1] else ''}" for k,v in PROTEIN_OPTIONS.items())
            )
        else: msg.body("Elige 1–3.")

    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein']=incoming
            session['state']=STATE_ASK_BEVERAGE
            idx=session['data']['current_combo']
            msg.body(
                f"Combo {idx}, bebida:\n"+
                "\n".join(f"{num_emoji(k)} {v}" for k,v in BEVERAGE_OPTIONS.items())
            )
        else: msg.body("Elige 1–8.")

    elif state==STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage']=incoming
            session['state']=STATE_ASK_EXTRA
            idx=session['data']['current_combo']
            msg.body(
                f"Combo {idx}, extra:\n"+
                "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in EXTRA_OPTIONS.items())
            )
        else: msg.body("Elige 1–12.")

    elif state==STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            session['data']['combos'][-1]['extra']=incoming
            session['state']=STATE_SUMMARY_CONFIRM
            idx=session['data']['current_combo']
            c=session['data']['combos'][-1]
            cn,cp=COMBO_OPTIONS[c['combo']]
            pn,pp=PROTEIN_OPTIONS[c['protein']]
            bv=BEVERAGE_OPTIONS[c['beverage']]
            en,ep=EXTRA_OPTIONS[c['extra']]
            msg.body(f"🧾 Tu combo {idx}: {cn}\nProt: {pn}{' (+$%.2f)'%pp if pp else ''}\nBeb: {bv}\nExp: {en}{' (+$%.2f)'%ep if ep else ''}\n\n1️⃣ OK 2️⃣ Corregir")
        else: msg.body("Elige 1–12.")

    elif state==STATE_SUMMARY_CONFIRM:
        total=session['data']['combos_total']
        curr=session['data']['current_combo']
        nombre=session['data']['nombre']
        dire=session['data']['direccion']
        if incoming=='1':
            if curr<total:
                session['data']['current_combo']+=1
                session['state']=STATE_ASK_COMBO_TYPE
                idx=session['data']['current_combo']
                msg.body("Elige combo %d:\n"%idx+"\n".join(f"{num_emoji(k)} {v[0]}" for k,v in COMBO_OPTIONS.items()))
            else:
                # generar resumen e id
                short=nombre[:3].upper()
                tel=sender.split(':')[1]
                ult=tel[-4:]
                fecha=datetime.now().strftime('%d%m%y')
                pid=f"{short}{ult}{fecha}"
                amt=0
                lines=[]
                for i,c in enumerate(session['data']['combos'],1):
                    cn,cp=COMBO_OPTIONS[c['combo']]
                    pn,pp=PROTEIN_OPTIONS[c['protein']]
                    bv=BEVERAGE_OPTIONS[c['beverage']]
                    en,ep=EXTRA_OPTIONS[c['extra']]
                    amt+=cp+pp+ep
                    lines.append(f"• Combo {i}: {cn} | Prot: {pn}{' (+$%.2f)'%pp if pp else ''} | Beb: {bv} | Extra: {en}{' (+$%.2f)'%ep if ep else ''}")
                summ="\n".join(lines)
                # enviar tienda
                client.messages.create(from_=SANDBOX_NUMBER,to=STORE_NUMBER,body=f"🛒Nuevo pedido {pid}\nCliente: {nombre}\nDir: {dire}\n{summ}\nTotal: ${amt:.2f}")
                # seguimiento tienda
                client.messages.create(from_=SANDBOX_NUMBER,to=STORE_NUMBER,body=f"📝Seguimiento {pid}: 1️⃣ Prep 2️⃣ Listo 3️⃣ Env 4️⃣ Camino 5️⃣ Entregado")
                seguimiento_activo[pid]=True
                datos_pedidos[sender]={'id':pid,'nombre':nombre,'estado':1,'hora_entrega':datetime.now(),'esperando_reseña':False,'reseña_pedida':False}
                msg.body(f"✅ Pedido {pid} confirmado!\n{summ}\nTotal: ${amt:.2f}\nEn breve costo envío.")
                session=None
        elif incoming=='2':
            session['data']['combos'].pop()
            session['state']=STATE_ASK_COMBO_TYPE
            msg.body("Corregimos tu combo:")
        else: msg.body("1️⃣ OK o 2️⃣ Corregir.")

    elif state==STATE_PROMOS_OPTIN:
        msg.body("Grupo promos: https://chat.whatsapp.com/...💥" if incoming=='1' else "OK, aquí sigo.")
        session=None

    else:
        msg.body("Oops, reiniciemos.")
        session=None

    # reseña final
    if sender in datos_pedidos and datos_pedidos[sender].get('esperando_reseña'):
        client.messages.create(from_=SANDBOX_NUMBER,to=STORE_NUMBER,body=f"⭐Reseña de {datos_pedidos[sender]['nombre']}: “{incoming}”")
        datos_pedidos.pop(sender)
        return str(resp)

    # guardar sesión
    if session: sessions[sender]=session
    else: sessions.pop(sender,None)

    return str(resp)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",3000)))
