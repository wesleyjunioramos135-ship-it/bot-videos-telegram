import telebot
from telebot.apihelper import ApiTelegramException
import time
import random
import threading
from supabase import create_client, Client

# ================= CONFIGURAÇÕES =================
API_TOKEN = '8925863309:AAGTAFBTb8hIECknfDbUVnCP9djOU45nI5c'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZG9uaWdndnVlb2VtaHl5ZnN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgwMjA5ODQsImV4cCI6MjEwMzU5Njk4NH0.uRxXnRijkkkq6NYilV3nXKTwWQ4K-CVXq5pJgqCv1U4' 
ADMIN_ID = 8237036306
GRUPO_VIP_ID = -1003608844775 # Coloque o ID do Grupo VIP AQUI
# =================================================

TEMPO_MINIMO_SEGUNDOS = 1  
TEMPO_MAXIMO_SEGUNDOS = 3  

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

NOMES_FAKES = ["João V.", "Marcos Silva", "Lucas", "Gabriel_99", "Pedro H.", "Rafa", "Thiago", "Mateus_01", "Diego", "Carlos", "Ana", "Bia_12", "Vitor"]

# Variáveis Globais
motor_rodando_1 = False
motor_rodando_2 = False
index_estoque = 0 

# O estado padrão começa inativo (O bot não faz NADA se você mandar mídia solta)
estado_admin = 'inativo' 

@bot.message_handler(commands=['start', 'ajuda'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    texto = (
        "🤖 *MOTOR VIP - MULTI ESTOQUE*\n\n"
        "📦 *Como salvar conteúdos:*\n"
        "🔹 `/salvar1` - Começa a salvar vídeos na Tabela 1\n"
        "🔹 `/salvar2` - Começa a salvar vídeos na Tabela 2\n"
        "🔹 `/parar` - Para de salvar (Bot entra em modo de repouso)\n\n"
        "▶️ *Como ligar a metralhadora:*\n"
        "🚀 `/ligar1` (ou /ligar) - Roda a Tabela 1\n"
        "🚀 `/ligar2` - Roda a Tabela 2\n"
        "⏸ `/desligar` - Pausa o motor\n\n"
        "📊 `/estoque` - Ver quantidades salvas"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

# ================= COMANDOS DE SALVAMENTO =================

@bot.message_handler(commands=['salvar1'])
def modo_salvar1(message):
    global estado_admin
    if message.from_user.id != ADMIN_ID: return
    estado_admin = 'salvar1'
    bot.reply_to(message, "✅ *MODO GRAVAÇÃO 1 ATIVADO*\nTudo que você me mandar agora será salvo na **Tabela 1**.", parse_mode="Markdown")

@bot.message_handler(commands=['salvar2'])
def modo_salvar2(message):
    global estado_admin
    if message.from_user.id != ADMIN_ID: return
    estado_admin = 'salvar2'
    bot.reply_to(message, "✅ *MODO GRAVAÇÃO 2 ATIVADO*\nTudo que você me mandar agora será salvo na **Tabela 2**.", parse_mode="Markdown")

@bot.message_handler(commands=['parar'])
def modo_normal(message):
    global estado_admin
    if message.from_user.id != ADMIN_ID: return
    estado_admin = 'inativo'
    bot.reply_to(message, "✅ *GRAVAÇÃO PAUSADA*\nO bot entrou em modo de repouso e ignorará mídias soltas.", parse_mode="Markdown")

# ================= COMANDOS DO MOTOR AUTOMÁTICO =================

@bot.message_handler(commands=['ligar', 'ligar1'])
def ligar_motor1(message):
    global motor_rodando_1, motor_rodando_2, index_estoque
    if message.from_user.id != ADMIN_ID: return
    
    if motor_rodando_1:
        bot.reply_to(message, "⚠️ A Tabela 1 já está rodando!")
        return
        
    motor_rodando_1 = True
    motor_rodando_2 = False # Desliga a tabela 2 por segurança
    index_estoque = 0
    bot.reply_to(message, "✅ *Metralhadora Ligada (Tabela 1)!*", parse_mode="Markdown")
    threading.Thread(target=loop_postagens_automaticas, args=(1,)).start()

@bot.message_handler(commands=['ligar2'])
def ligar_motor2(message):
    global motor_rodando_1, motor_rodando_2, index_estoque
    if message.from_user.id != ADMIN_ID: return
    
    if motor_rodando_2:
        bot.reply_to(message, "⚠️ A Tabela 2 já está rodando!")
        return
        
    motor_rodando_2 = True
    motor_rodando_1 = False # Desliga a tabela 1 por segurança
    index_estoque = 0
    bot.reply_to(message, "✅ *Metralhadora Ligada (Tabela 2)!*", parse_mode="Markdown")
    threading.Thread(target=loop_postagens_automaticas, args=(2,)).start()

@bot.message_handler(commands=['desligar'])
def desligar_motor(message):
    global motor_rodando_1, motor_rodando_2
    if message.from_user.id != ADMIN_ID: return
    
    motor_rodando_1 = False
    motor_rodando_2 = False
    bot.reply_to(message, "⏸ *Todos os Motores foram DESLIGADOS!*", parse_mode="Markdown")

@bot.message_handler(commands=['estoque'])
def ver_estoque(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        res1 = supabase.table('estoque_vip').select('*', count='exact').execute()
        res2 = supabase.table('estoque_vip2').select('*', count='exact').execute()
        total1 = len(res1.data) if res1.data else 0
        total2 = len(res2.data) if res2.data else 0
        bot.reply_to(message, f"📦 *Tabela 1:* {total1} conteúdos\n📦 *Tabela 2:* {total2} conteúdos", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Erro ao acessar o banco.")

# ================= CAPTURADOR DE MÍDIA =================

@bot.message_handler(content_types=['text', 'photo', 'video'])
def capturar_mensagens(message):
    global estado_admin
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text.startswith('/'): return

    tipo = 'text' if message.content_type == 'text' else message.content_type
    texto = message.text if tipo == 'text' else message.caption
    file_id = None
    
    if tipo == 'photo': file_id = message.photo[-1].file_id
    elif tipo == 'video': file_id = message.video.file_id

    # O que fazer dependendo do comando que você deu antes?
    if estado_admin == 'salvar1':
        try:
            supabase.table('estoque_vip').insert({'tipo': tipo, 'file_id': file_id, 'texto': texto}).execute()
            bot.reply_to(message, "💾 *Salvo na Tabela 1!*", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"⚠️ Erro ao salvar 1: {e}")
            
    elif estado_admin == 'salvar2':
        try:
            supabase.table('estoque_vip2').insert({'tipo': tipo, 'file_id': file_id, 'texto': texto}).execute()
            bot.reply_to(message, "💾 *Salvo na Tabela 2!*", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"⚠️ Erro ao salvar 2: {e}")
            
    else:
        # MODO INATIVO: O bot não faz ABSOLUTAMENTE NADA. 
        # Ignora o envio silenciosamente para não atrapalhar nem vazar mídias pro grupo.
        return

# ================= MOTOR AUTOMÁTICO (RODA EM SEGUNDO PLANO) =================

def loop_postagens_automaticas(tabela_num):
    global motor_rodando_1, motor_rodando_2, index_estoque
    
    nome_tabela = 'estoque_vip' if tabela_num == 1 else 'estoque_vip2'
    
    while (tabela_num == 1 and motor_rodando_1) or (tabela_num == 2 and motor_rodando_2):
        try:
            res = supabase.table(nome_tabela).select('*').order('id').execute()
            conteudos = res.data
        except Exception:
            conteudos = []
        
        if conteudos:
            if index_estoque >= len(conteudos):
                index_estoque = 0
                
            item = conteudos[index_estoque]
            nome_fake = random.choice(NOMES_FAKES)
            assinatura = f"👤 *{nome_fake}:* "

            try:
                if item['tipo'] == 'text':
                    bot.send_message(GRUPO_VIP_ID, assinatura + item['texto'], parse_mode="Markdown", disable_web_page_preview=False)
                elif item['tipo'] == 'photo':
                    legenda = f"{assinatura}\n{item['texto']}" if item['texto'] else assinatura
                    bot.send_photo(GRUPO_VIP_ID, item['file_id'], caption=legenda, parse_mode="Markdown")
                elif item['tipo'] == 'video':
                    legenda = f"{assinatura}\n{item['texto']}" if item['texto'] else assinatura
                    bot.send_video(GRUPO_VIP_ID, item['file_id'], caption=legenda, parse_mode="Markdown")
                    
                index_estoque += 1
                
            except ApiTelegramException as e:
                # FREIO DE SEGURANÇA: Espera se o Telegram der bloqueio de velocidade
                if e.error_code == 429:
                    tempo_punicao = e.result_json['parameters']['retry_after']
                    time.sleep(tempo_punicao)
                else:
                    index_estoque += 1
            except Exception as e:
                index_estoque += 1
        
        # Sorteia 1 a 3 segundos (Velocidade Máxima)
        segundos_espera = random.randint(TEMPO_MINIMO_SEGUNDOS, TEMPO_MAXIMO_SEGUNDOS)
        
        for _ in range(segundos_espera):
            if (tabela_num == 1 and not motor_rodando_1) or (tabela_num == 2 and not motor_rodando_2):
                break
            time.sleep(1)

print("Bot Multi-Estoque Iniciado...")
bot.infinity_polling()
