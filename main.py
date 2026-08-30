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

# MODO KAMIKAZE: Quase sem intervalo de tempo
TEMPO_MINIMO_SEGUNDOS = 1  
TEMPO_MAXIMO_SEGUNDOS = 3  

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

NOMES_FAKES = ["João V.", "Marcos Silva", "Lucas", "Gabriel_99", "Pedro H.", "Rafa", "Thiago", "Mateus_01", "Diego", "Carlos", "Ana", "Bia_12", "Vitor"]

motor_rodando = False
index_estoque = 0 

@bot.message_handler(commands=['start', 'ajuda'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID: return
    texto = (
        "🤖 *MOTOR VIP - VELOCIDADE MÁXIMA*\n\n"
        "Comandos:\n"
        "▶️ `/ligar` - Ativa a metralhadora (1 a 3 seg)\n"
        "⏸ `/desligar` - Pausa o fluxo\n"
        "📦 `/estoque` - Ver quantidade de conteúdos"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['ligar'])
def ligar_motor(message):
    global motor_rodando
    if message.from_user.id != ADMIN_ID: return
    
    if motor_rodando:
        bot.reply_to(message, "⚠️ O motor já está rodando!")
        return
        
    motor_rodando = True
    bot.reply_to(message, "✅ *Fluxo MÁXIMO Ligado!*\nO bot vai enviar até o Telegram pedir arrego.", parse_mode="Markdown")
    threading.Thread(target=loop_postagens_automaticas).start()

@bot.message_handler(commands=['desligar'])
def desligar_motor(message):
    global motor_rodando
    if message.from_user.id != ADMIN_ID: return
    
    motor_rodando = False
    bot.reply_to(message, "⏸ *Fluxo DESLIGADO!*", parse_mode="Markdown")

@bot.message_handler(commands=['estoque'])
def ver_estoque(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        res = supabase.table('estoque_vip').select('*', count='exact').execute()
        total = len(res.data) if res.data else 0
        bot.reply_to(message, f"📦 Você tem *{total}* conteúdos fakes no estoque.", parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, "⚠️ Erro ao acessar o banco.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def guardar_no_estoque(message):
    if message.from_user.id != ADMIN_ID: return
    if message.text and message.text.startswith('/'): return

    tipo = 'text' if message.content_type == 'text' else message.content_type
    texto = message.text if tipo == 'text' else message.caption
    file_id = None
    if tipo == 'photo': file_id = message.photo[-1].file_id
    elif tipo == 'video': file_id = message.video.file_id

    try:
        supabase.table('estoque_vip').insert({'tipo': tipo, 'file_id': file_id, 'texto': texto}).execute()
        bot.reply_to(message, "💾 *Salvo no estoque!*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao salvar: {e}")

def loop_postagens_automaticas():
    global motor_rodando
    global index_estoque
    
    while motor_rodando:
        try:
            res = supabase.table('estoque_vip').select('*').order('id').execute()
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
                # O SISTEMA DE FREIO: Se o Telegram bloquear por flood (erro 429)
                if e.error_code == 429:
                    tempo_punicao = e.result_json['parameters']['retry_after']
                    print(f"Velocidade excedida! O Telegram exigiu uma pausa de {tempo_punicao} segundos.")
                    time.sleep(tempo_punicao)
                    # Não avança o index para ele tentar mandar a mesma mensagem de novo quando voltar
                else:
                    index_estoque += 1
            except Exception as e:
                index_estoque += 1
        
        # Sorteia apenas 1 a 3 segundos (Velocidade Máxima Teórica)
        segundos_espera = random.randint(TEMPO_MINIMO_SEGUNDOS, TEMPO_MAXIMO_SEGUNDOS)
        
        for _ in range(segundos_espera):
            if not motor_rodando:
                break
            time.sleep(1)

print("Bot Turbo Máximo Iniciado...")
bot.infinity_polling()

