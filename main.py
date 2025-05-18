import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

# Configuración de Twilio
client = Client(
    os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN']
)

# Números de WhatsApp
CHILO_NUMBER = 'whatsapp:+5215612268107'
STORE_NUMBER = 'whatsapp:+5215612522186'

# Almacenes en memoria
sessions = {}

# Estados de conversación
STATE_ASK_NAME        = 'ask_name'
STATE_ASK_ADDRESS     = 'ask_address'
STATE_MAIN_MENU       = 'main_menu'
STATE_OPTION1_WAIT_OK = 'option1_wait_ok'
STATE_ASK_COMBO_COUNT = 'ask_combo_count'
STATE_ASK_COMBO_TYPE  = 'ask_combo_type'
STATE_ASK_PROTEIN     = 'ask_protein'
STATE_ASK_BEVERAGE    = 'ask_beverage'
STATE_ASK_EXTRA       = 'ask_extra'

# Emoji para números
digit_emoji = {str(i): f"{i}\uFE0F\u20E3" for i in range(10)}
def num_emoji(s): return ''.join(digit_emoji[c] for c in s)

# Datos de menú
MENU_LINK = 'https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing'
COMBO_OPTIONS = {
    '1': ('El Clásico Shingón', 185.00),
    '2': ('El Verde Shingón', 185.00),
    '3': ('El Que No Se Decide', 215.00),
}
PROTEIN_OPTIONS = {
    '1': ('Pollito', 0),
    '2': ('Carnita Asada', 0),
    '3': ('Cecina de Res', 45),
    '4': ('Sin proteína', 0),
}
BEVERAGE_OPTIONS = {
    '1': 'Limonada Natural',
    '2': 'Jamaica con Limón',
    '3': 'Coca-Cola',
    '4': 'Pepsi',
    '5': 'Manzanita Sol',
    '6': 'Squirt',
    '7': 'Mirinda',
    '8': 'Seven Up',
}
EXTRA_OPTIONS = {
    str(i+1): opt for i, opt in enumerate([
        ('Huevito duro', 18), ('Huevito estrellado', 18), ('Guacamole chingon', 45),
        ('Dirty Horchata', 45), ('Limonada Natural', 45), ('Jamaica con Limón', 45),
        ('Coca-Cola', 45), ('Pepsi', 45), ('Manzanita Sol', 45), ('Mirinda', 45),
        ('Seven Up', 45), ('Ningun extra', 0)
    ])
}

# App Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Chilo Bot is running!"

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming = request.values.get('Body', '').strip()
    sender = request.values.get('From')
    resp = MessagingResponse()
    msg = resp.message()

    if sender == STORE_NUMBER:
        return str(resp)

    session = sessions.get(sender, {
        'state': None,
        'data': {'name': None, 'address': None, 'combos': [], 'total': 0, 'current': 0}
    })
    state = session['state']

    if state is None:
        msg.body('¡Hola! 👋 Soy Chilo. ¿Cómo te llamas?')
        session['state'] = STATE_ASK_NAME

    elif state == STATE_ASK_NAME:
        session['data']['name'] = incoming.title()
        msg.body(f'¡Hola {session["data"]["name"]}! 🚚 ¿A qué dirección enviamos tu pedido?')
        session['state'] = STATE_ASK_ADDRESS

    elif state == STATE_ASK_ADDRESS:
        session['data']['address'] = incoming
        msg.body(
            '¿Con cuál opción comenzamos? 🌶️\n'
            '1️⃣ Ver menú chingón\n'
            '2️⃣ Ya sé qué quiero\n'
            '3️⃣ Promos chingonas\n'
            '4️⃣ Hablar con un humano'
        )
        session['state'] = STATE_MAIN_MENU

    elif state == STATE_MAIN_MENU:
        if incoming == '1':
            msg.body(f'Menú: {MENU_LINK}')
            Timer(3, lambda: client.messages.create(
                from_=CHILO_NUMBER, to=sender,
                body='Escribe OK cuando estés listo para pedir.'
            )).start()
            session['state'] = STATE_OPTION1_WAIT_OK

        elif incoming == '2':
            msg.body('¿Cuántos combos quieres?')
            session['state'] = STATE_ASK_COMBO_COUNT

        elif incoming == '3':
            msg.body('🔥 Promos chingonas de hoy! Únete al grupo: https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP')
            session = None

        elif incoming == '4':
            phone = sender.split(':')[1]
            client.messages.create(
                from_=CHILO_NUMBER, to=STORE_NUMBER,
                body=f'*{session["data"]["name"]}* solicita humano → https://wa.me/{phone}'
            )
            msg.body('Un humano te atenderá pronto.')
            session = None
        else:
            msg.body('Elige 1–4.')

    elif state == STATE_OPTION1_WAIT_OK:
        if incoming.lower() == 'ok':
            msg.body('¿Cuántos combos quieres?')
            session['state'] = STATE_ASK_COMBO_COUNT
        else:
            msg.body('Escribe OK cuando estés listo.')

    elif state == STATE_ASK_COMBO_COUNT:
        try:
            cnt = int(incoming)
        except ValueError:
            msg.body('Número inválido, intenta de nuevo.')
            sessions[sender] = session
            return str(resp)
        session['data']['total'] = cnt
        session['data']['current'] = 1
        menu = '\n'.join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items())
        msg.body(f'Combo 1, elige uno:\n{menu}')
        session['state'] = STATE_ASK_COMBO_TYPE

    elif state == STATE_ASK_COMBO_TYPE:
        if incoming in COMBO_OPTIONS:
            session['data']['combos'].append({'combo': incoming})
            menu = '\n'.join(f"{num_emoji(k)} {v[0]}" for k, v in PROTEIN_OPTIONS.items())
            msg.body(f'Proteína combo {session["data"]["current"]}:\n{menu}')
            session['state'] = STATE_ASK_PROTEIN
        else:
            msg.body('Elige 1–3.')

    elif state == STATE_ASK_PROTEIN:
        if incoming in PROTEIN_OPTIONS:
            session['data']['combos'][-1]['protein'] = incoming
            menu = '\n'.join(f"{num_emoji(k)} {v}" for k, v in BEVERAGE_OPTIONS.items())
            msg.body(f'Bebida combo {session["data"]["current"]}:\n{menu}')
            session['state'] = STATE_ASK_BEVERAGE
        else:
            msg.body('Elige 1–8.')

    elif state == STATE_ASK_BEVERAGE:
        if incoming in BEVERAGE_OPTIONS:
            session['data']['combos'][-1]['beverage'] = incoming
            menu = '\n'.join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k, v in EXTRA_OPTIONS.items())
            msg.body(f'Extra combo {session["data"]["current"]}:\n{menu}')
            session['state'] = STATE_ASK_EXTRA
        else:
            msg.body('Elige 1–12.')

    elif state == STATE_ASK_EXTRA:
        if incoming in EXTRA_OPTIONS:
            d = session['data']
            curr = d['current']
            tot  = d['total']
            d['combos'][-1]['extra'] = incoming
            c = d['combos'][-1]
            cn, _ = COMBO_OPTIONS[c['combo']]
            pn, _ = PROTEIN_OPTIONS[c['protein']]
            bv     = BEVERAGE_OPTIONS[c['beverage']]
            en, _ = EXTRA_OPTIONS[c['extra']]
            resumen = f"Combo {curr}: {cn}\n• Proteína: {pn}\n• Bebida: {bv}\n• Extra: {en}"
            if curr < tot:
                d['current'] += 1
                menu = '\n'.join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k, v in COMBO_OPTIONS.items())
                msg.body(f"{resumen}\n👍 ¡Listo! Vamos con el siguiente.\nCombo {d['current']}, elige:\n{menu}")
            else:
                name = d['name']
                addr = d['address']
                phone = sender.split(':')[1]
                fecha = datetime.now().strftime('%d%m%y')
                pid = f"{name[:3].upper()}{phone[-4:]}{fecha}"
                total_amt = 0
                lines = []
                for i, c in enumerate(d['combos'], 1):
                    cn, cp = COMBO_OPTIONS[c['combo']]
                    pn, pp = PROTEIN_OPTIONS[c['protein']]
                    bv     = BEVERAGE_OPTIONS[c['beverage']]
                    en, ep = EXTRA_OPTIONS[c['extra']]
                    total_amt += cp + pp + ep
                    lines.append(f"• Combo{i}: {cn} | {pn} | {bv} | {en}")
                full = '\n'.join(lines)
                body = (
                    f"🛒 Pedido {pid}\n"
                    f"Cliente: {name}\n"
                    f"Dirección: {addr}\n\n"
                    f"{full}\n\n"
                    f"💰 Total: ${total_amt:.2f}\n"
                    f"📞 Contacto: https://wa.me/{phone}"
                )
                client.messages.create(from_=CHILO_NUMBER, to=STORE_NUMBER, body=body)
                msg.body(f"✅ Pedido {pid}\n{full}\n💰 Total: ${total_amt:.2f}\nPronto confirmamos envío.")
                session = None
        else:
            msg.body('Extra inválido.')

    if session:
        sessions[sender] = session
    else:
        sessions.pop(sender, None)

    return str(resp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)))
