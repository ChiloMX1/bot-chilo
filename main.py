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

# WhatsApp sandbox and store numbers
SANDBOX_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER   = 'whatsapp:+5215612522186'  # incluye el '1' tras +52

# In‐memory session store
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

# Emoji helper
digit_emoji = {d: f"{d}\u20E3" for d in '0123456789'}
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
    '8': "Seven Up",
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
    '12': ("Ningun extra",          0.00),
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

    session = sessions.get(sender, {'state': None, 'data': {'name':None,'address':None,'combos':[], 'combos_total':0,'current_combo':0}})
    state   = session['state']

    if state is None:
        msg.body(
            "¡Hola! 👋 Gracias por escribir a *Los Shelakeles*.\n"
            "Soy *Chilo* 🤖🌶️ y estoy para ayudarte a generar tu pedido.\n"
            "¿Me puedes dar tu nombre?"
        )
        session['state'] = STATE_AWAITING_NAME

    elif state == STATE_AWAITING_NAME:
        session['data']['name'] = incoming.title()
        msg.body("¿A qué dirección enviamos tu pedido?")
        session['state'] = STATE_ASK_ADDRESS

    elif state == STATE_ASK_ADDRESS:
        session['data']['address'] = incoming
        msg.body(
            "Elige opción:\n"
            "1️⃣ Ver menú  \n"
            "2️⃣ Armar pedido  \n"
            "3️⃣ Promos  \n"
            "4️⃣ Hablar con un humano"
        )
        session['state'] = STATE_MAIN_MENU

    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f"Aquí está el menú: 📎 {MENU_LINK}")
            session['state'] = STATE_OPTION1_WAIT_OK
        elif incoming == '2':
            msg.body("¿Cuántos combos quieres? (1–9)")
            session['state'] = STATE_ASK_COMBO_COUNT
        elif incoming == '3':
            msg.body("🔥 Promo del mes... Únete al grupo: https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP")
            session = None
        elif incoming == '4':
            name = session['data']['name']
            link = f"https://wa.me/{sender.split(':')[1]}"
            msg.body("En breve un humano te contactará.")
            client.messages.create(from_=SANDBOX_NUMBER, to=STORE_NUMBER,
                body=f"*{name}* solicita atención humana. Contacto: {link}")
            session = None
        else:
            msg.body("Elige 1–4.")

    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body("¿Cuántos combos quieres? (1–9)")
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body("Escribe 'ok' cuando estés listo o 4 para humano.")

    elif state == STATE_ASK_COMBO_COUNT:
        try:
            cnt = int(incoming)
        except:
            msg.body("Elige un número válido (1–9).")
            return str(resp)
        if cnt >=10:
            name=session['data']['name']; link=f"https://wa.me/{sender.split(':')[1]}"
            client.messages.create(from_=SANDBOX_NUMBER,to=STORE_NUMBER,
                body=f"🚨 Pedido especial: {name} trae {cnt} combos. Contacto: {link}")
            msg.body("Tu pedido es mayor a 10 combos: te atenderá un humano.")
            session=None
        else:
            session['data']['combos_total']=cnt; session['data']['current_combo']=1
            session['state']=STATE_ASK_COMBO_TYPE
            msg.body("Elige combo 1:\n"+"\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in COMBO_OPTIONS.items()))

    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo':incoming}); session['state']=STATE_ASK_PROTEIN
            msg.body("Elige proteína:\n"+"\n".join(f"{num_emoji(k)} {v[0]}{' +$'+str(v[1]) if v[1] else ''}" for k,v in PROTEIN_OPTIONS.items()))
        else:
            msg.body("Elige 1–3.")

    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein']=incoming; session['state']=STATE_ASK_BEVERAGE
            msg.body("Elige bebida:\n"+"\n".join(f"{num_emoji(k)} {v}" for k,v in BEVERAGE_OPTIONS.items()))
        else:
            msg.body("Elige 1–4.")

    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage']=incoming; session['state']=STATE_ASK_EXTRA
            msg.body("Elige extra:\n"+"\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in EXTRA_OPTIONS.items()))
        else:
            msg.body("Elige 1–12.")

    elif state == STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            session['data']['combos'][-1]['extra']=incoming; session['state']=STATE_SUMMARY_CONFIRM
            idx=session['data']['current_combo']; c=session['data']['combos'][-1]
            cn,cp=COMBO_OPTIONS[c['combo']]; pn,pp=PROTEIN_OPTIONS[c['protein']]
            bv=BEVERAGE_OPTIONS[c['beverage']]; en,ep=EXTRA_OPTIONS[c['extra']]
            msg.body(f"Combo {idx}: {cn}\nProteína: {pn}{' +$'+str(pp) if pp else ''}\nBebida: {bv}\nExtra: {en}{' +$'+str(ep) if ep else ''}\n1️⃣ OK  2️⃣ Corregir")
        else:
            msg.body("Elige 1–12.")

    elif state == STATE_SUMMARY_CONFIRM:
        total=session['data']['combos_total']; cur=session['data']['current_combo']; name=session['data']['name']
        address=session['data']['address']
        if incoming=='1':
            if cur<total:
                session['data']['current_combo']+=1; session['state']=STATE_ASK_COMBO_TYPE
                msg.body("Elige combo " + str(session['data']['current_combo']))
            else:
                # genera ID y envía a la tienda
                short=name[:3].upper(); tel=sender.split(':')[1]; dig=tel[-4:]; fecha=datetime.now().strftime("%d%m%y"); pid=f"{short}{dig}{fecha}"
                # calcula total y resumen
                amt=0; lines=[]
                for i,c in enumerate(session['data']['combos'],start=1):
                    cn,cp=COMBO_OPTIONS[c['combo']]; pn,pp=PROTEIN_OPTIONS[c['protein']]; epv=EXTRA_OPTIONS[c['extra']][1]
                    amt+=cp+pp+epv; lines.append(f"Combo {i}: {cn} | Prot {pn} | Beb {BEVERAGE_OPTIONS[c['beverage']]} | Extra {EXTRA_OPTIONS[c['extra']][0]}")
                summary="\n".join(lines)
                body_store= f"Nuevo pedido {pid}\nCliente: {name}\nDir: {address}\n{summary}\nTotal: ${amt:.2f}\nContacto: https://wa.me/{tel}"
                client.messages.create(from_=SANDBOX_NUMBER,to=STORE_NUMBER,body=body_store)
                msg.body(f"✅ Pedido {pid} recibido!\n{summary}\nTotal: ${amt:.2f} \nEn breve confirmaremos envío.")
                session=None
        else:
            msg.body("Responde 1 para confirmar o 2 para corregir.")

    else:
        msg.body("Ups, algo salió mal. Reiniciemos.")
        session=None

    if session: sessions[sender]=session
    else: sessions.pop(sender,None)
    return str(resp)

if __name__ == "__main__":
    port=int(os.environ.get("PORT",3000))
    app.run(host="0.0.0.0",port=port)
