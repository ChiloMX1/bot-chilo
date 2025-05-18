import os
from threading import Timer
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from datetime import datetime

app = Flask(__name__)

# Configuración de Twilio
twilio_account_sid = os.environ['TWILIO_ACCOUNT_SID']
twilio_auth_token  = os.environ['TWILIO_AUTH_TOKEN']
client             = Client(twilio_account_sid, twilio_auth_token)

# Número de Chilo y número de la tienda\N# Chilo atiende inicialmente, tienda recibe pedidos\CHILO_NUMBER     = 'whatsapp:+5215612268107'
STORE_NUMBER     = 'whatsapp:+5215612522186'

# Sesiones de usuario en memoria
sessions = {}

# Estados de la conversación
STATE_AWAIT_NAME      = 'await_name'
STATE_ASK_ADDRESS     = 'ask_address'
STATE_MAIN_MENU       = 'main_menu'
STATE_ASK_COUNT       = 'ask_count'
STATE_ASK_COMBO       = 'ask_combo'
STATE_ASK_PROTEIN     = 'ask_protein'
STATE_ASK_BEVERAGE    = 'ask_beverage'
STATE_ASK_EXTRA       = 'ask_extra'
STATE_SUMMARY         = 'summary'

# Utilidad para emojis numéricos
digit_emoji = {str(i): f"{i}️⃣" for i in range(10)}
def num_emoji(s): return ''.join(digit_emoji[d] for d in s)

# Datos de menú
MENU_LINK = "https://drive.google.com/file/d/1Mm8i1YtES9su0tl8XX8UqokQSiWeV3vQ/view?usp=sharing"
COMBO_OPTIONS = {'1': ("El Clásico Shingón",185.00), '2': ("El Verde Shingón",185.00), '3': ("El Que No Se Decide",215.00)}
PROTEIN_OPTIONS = {'1': ("Pollito",0.00), '2': ("Carnita Asada",0.00), '3': ("Cecina de Res",45.00), '4': ("Sin proteína",0.00)}
BEVERAGE_OPTIONS = {'1':"Limonada Natural",'2':"Jamaica con Limón",'3':"Coca-Cola",'4':"Pepsi",'5':"Manzanita Sol",'6':"Squirt",'7':"Mirinda",'8':"Seven Up"}
EXTRA_OPTIONS = {
    '1':("Huevito duro",18.00),'2':("Huevito estrellado",18.00),'3':("Guacamole chingon",45.00),
    '4':("Dirty Horchata",45.00),'5':("Limonada Natural",45.00),'6':("Jamaica con Limón",45.00),
    '7':("Coca-Cola",45.00),'8':("Pepsi",45.00),'9':("Manzanita Sol",45.00),'10':("Mirinda",45.00),
    '11':("Seven Up",45.00),'12':("Ningún extra",0.00)
}

@app.route('/', methods=['GET'])
def home(): return 'Chilo Bot Running.'

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    incoming = request.values.get('Body','').strip()
    sender   = request.values.get('From')
    resp     = MessagingResponse()
    msg      = resp.message()

    # Si viene de Chilo (inicial)
    if sender == CHILO_NUMBER:
        session = sessions.get(sender, {'state':None,'data':{}})
        state   = session['state']

        if state is None:
            msg.body("¡Hola! Soy Chilo 🤖🌶️. ¿Cuál es tu nombre?")
            session['state']=STATE_AWAIT_NAME

        elif state == STATE_AWAIT_NAME:
            name = incoming.title()
            session['data']['name']=name
            msg.body(
                f"Excelente {name}! ¿A qué dirección enviamos tu pedido?"
            )
            session['state']=STATE_ASK_ADDRESS

        elif state == STATE_ASK_ADDRESS:
            session['data']['address']=incoming
            msg.body(
                f"¿Con qué quieres empezar?\n1️⃣ Ver menú\n2️⃣ Armar pedido\n3️⃣ Promos Vigentes\n4️⃣ Hablar con un humano"
            )
            session['state']=STATE_MAIN_MENU

        elif state == STATE_MAIN_MENU:
            if incoming=='1':
                msg.body(f"Aquí el menú: 📎 {MENU_LINK}")
                session['state']=STATE_MAIN_MENU
            elif incoming=='2':
                msg.body("¿Cuántos combos deseas? (número)")
                session['state']=STATE_ASK_COUNT
            elif incoming=='3':
                msg.body("¡Promos chingonas! Únete al grupo: https://chat.whatsapp.com/KmgrQT4Fan0DG7wClcSwfP")
                session=None
            elif incoming=='4':
                name= session['data']['name']
                contact=f"https://wa.me/{sender.split(':')[1]}"
                msg.body("Te conecto con un humano...")
                client.messages.create(from_=CHILO_NUMBER,to=STORE_NUMBER,body=f"{name} solicita un humano. {contact}")
                session=None
            else:
                msg.body("Elige 1–4.")

        elif state==STATE_ASK_COUNT:
            try:
                count=int(incoming)
            except:
                msg.body("Número inválido.")
                sessions[sender]=session
                return str(resp)
            session['data']['count']=count
            session['data']['current']=1
            msg.body(
                f"Combo 1, elige:\n"+
                "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in COMBO_OPTIONS.items())
            )
            session['state']=STATE_ASK_COMBO

        elif state==STATE_ASK_COMBO:
            if incoming in COMBO_OPTIONS:
                session['data'].setdefault('combos',[]).append({'combo':incoming})
                msg.body(
                    f"Proteína para Combo {session['data']['current']}:\n"+
                    "\n".join(f"{num_emoji(k)} {v[0]}{' +$'+str(v[1]) if v[1] else ''}" for k,v in PROTEIN_OPTIONS.items())
                )
                session['state']=STATE_ASK_PROTEIN
            else: msg.body("Elige 1–3.")

        elif state==STATE_ASK_PROTEIN:
            if incoming in PROTEIN_OPTIONS:
                session['data']['combos'][-1]['protein']=incoming
                msg.body(
                    f"Bebida para Combo {session['data']['current']}:\n"+
                    "\n".join(f"{num_emoji(k)} {v}" for k,v in BEVERAGE_OPTIONS.items())
                )
                session['state']=STATE_ASK_BEVERAGE
            else: msg.body("Elige 1–4.")

        elif state==STATE_ASK_BEVERAGE:
            if incoming in BEVERAGE_OPTIONS:
                session['data']['combos'][-1]['beverage']=incoming
                msg.body(
                    f"Extra para Combo {session['data']['current']}:\n"+
                    "\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in EXTRA_OPTIONS.items())
                )
                session['state']=STATE_ASK_EXTRA
            else: msg.body("Elige 1–8.")

        elif state==STATE_ASK_EXTRA:
            if incoming in EXTRA_OPTIONS:
                session['data']['combos'][-1]['extra']=incoming
                # Avanzar o finalizar
                cur = session['data']['current']
                tot = session['data']['count']
                if cur<tot:
                    session['data']['current']+=1
                    msg.body("👍 ¡Listo! Vamos con el siguiente combo. Elige:")
                    msg.body("\n".join(f"{num_emoji(k)} {v[0]} — ${v[1]:.2f}" for k,v in COMBO_OPTIONS.items()))
                    session['state']=STATE_ASK_COMBO
                else:
                    # Resumen final\... (enviar a tienda)
                    data=session['data']
                    name=data['name']; addr=data['address']
                    phone=sender.split(':')[1]
                    # Generar ID
                    short=name[:3].upper(); last4=phone[-4:]
                    date=datetime.now().strftime("%d%m%y")
                    pid=f"{short}{last4}{date}"
                    # Calcular total y resumen
                    total=0; lines=[]
                    for i,c in enumerate(data['combos'],1):
                        cn,cp=COMBO_OPTIONS[c['combo']]
                        pn,pp=PROTEIN_OPTIONS[c['protein']]
                        bv=BEVERAGE_OPTIONS[c['beverage']]
                        en,ep=EXTRA_OPTIONS[c['extra']]
                        total+=cp+pp+ep
                        lines.append(f"Combo {i}: {cn} | Prot: {pn} | Beb: {bv} | Extra: {en}")
                    summary="\n".join(lines)
                    store_msg=(f"Nuevo pedido {pid}\nCliente:{name}\nDir:{addr}\n"+summary+f"\nTotal:${total:.2f}\nContacto:https://wa.me/{phone}")
                    client.messages.create(from_=CHILO_NUMBER,to=STORE_NUMBER,body=store_msg)
                    msg.body(f"✅ Pedido enviado! (ID:{pid})\n{summary}\nTotal:${total:.2f}")
                    session=None
            else: msg.body("Elige 1–12.")

        # Guardar o limpiar sesión
        if session: sessions[sender]=session
        else: sessions.pop(sender,None)
        return str(resp)

    # Si no es Chilo, redirigir al webhook de tienda
    return '',204

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
