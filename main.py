import telebot
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

# MODO TURBO ATIVADO: Mensagens super rápidas (entre 3 e 7 segundos)
TEMPO_MINIMO_SEGUNDOS = 3  
TEMPO_MAXIMO_SEGUNDOS = 7  

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

NOMES_FAKES = ["João V.", "Marcos Silva", "Lucas", "Gabriel_99", "Pedro H.", "Rafa", "Thiago", "Mateus_01", "Diego", "Carlos", "Ana", "Bia_12", "Vitor"]

motor_rodando = False
index_estoque = 0  # Variável que controla a fila para criar o Loop Infinito

@bot.message_handler(commands=['start', 'ajuda'])
def send_welcome(message):
    if message.from_user.id != ADMIN_ID:
        return
    texto = (
        "🤖 *BEM-VINDO AO MOTOR AUTOMÁTICO VIP (MODO TURBO)*\n\n"
        "Envie mensagens de texto, links, fotos ou vídeos aqui no privado para abastecer o estoque.\n\n"
        "Comandos:\n"
        "▶️ `/ligar` - Ativa a metralhadora de mensagens (3 a 7 seg)\n"
        "⏸ `/desligar` - Pausa o fluxo\n"
        "📦 `/estoque` - Ver quantidade de conteúdos salvos"
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
    bot.reply_to(message, "✅ *Fluxo TURBO Ligado!*\nO bot vai metralhar o grupo sem parar.", parse_mode="Markdown")
    threading.Thread(target=loop_postagens_automaticas).start()

@bot.message_handler(commands=['desligar'])
def desligar_motor(message):
    global motor_rodando
    if message.from_user.id != ADMIN_ID: return
    
    motor_rodando = False
    bot.reply_to(message, "⏸ *Fluxo DESLIGADO!*\nPostagens pausadas.", parse_mode="Markdown")

@bot.message_handler(commands=['estoque'])
def ver_estoque(message):
    if message.from_user.id != ADMIN_ID: return
    
    try:
        res = supabase.table('estoque_vip').select('*', count='exact').execute()
        total = len(res.data) if res.data else 0
        bot.reply_to(message, f"📦 Você tem *{total}* conteúdos fakes no estoque.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro ao acessar o banco.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def guardar_no_estoque(message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text and message.text.startswith('/'):
        return

    tipo = ''
    file_id = None
    texto = None

    if message.content_type == 'text':
        tipo = 'text'
        texto = message.text
    elif message.content_type == 'photo':
        tipo = 'photo'
        file_id = message.photo[-1].file_id
        texto = message.caption
    elif message.content_type == 'video':
        tipo = 'video'
        file_id = message.video.file_id
        texto = message.caption

    try:
        dados = {'tipo': tipo, 'file_id': file_id, 'texto': texto}
        supabase.table('estoque_vip').insert(dados).execute()
        bot.reply_to(message, "💾 *Salvo no estoque!*", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Erro ao salvar no Supabase: {e}")

def loop_postagens_automaticas():
    global motor_rodando
    global index_estoque
    
    while motor_rodando:
        try:
            # Puxa os dados em ordem
            res = supabase.table('estoque_vip').select('*').order('id').execute()
            conteudos = res.data
        except Exception:
            conteudos = []
        
        if conteudos:
            # Se chegar no final, zera e volta pro começo (Loop Infinito)
            if index_estoque >= len(conteudos):
                index_estoque = 0
                
            item = conteudos[index_estoque]
            nome_fake = random.choice(NOMES_FAKES)
            assinatura = f"👤 *{nome_fake}:* "

            try:
                if item['tipo'] == 'text':
                    msg_final = assinatura + item['texto']
                    bot.send_message(GRUPO_VIP_ID, msg_final, parse_mode="Markdown", disable_web_page_preview=False)
                
                elif item['tipo'] == 'photo':
                    legenda = f"{assinatura}\n{item['texto']}" if item['texto'] else assinatura
                    bot.send_photo(GRUPO_VIP_ID, item['file_id'], caption=legenda, parse_mode="Markdown")
                
                elif item['tipo'] == 'video':
                    legenda = f"{assinatura}\n{item['texto']}" if item['texto'] else assinatura
                    bot.send_video(GRUPO_VIP_ID, item['file_id'], caption=legenda, parse_mode="Markdown")
                    
                # Avança para a próxima mensagem
                index_estoque += 1
                
            except Exception as e:
                # Se o Telegram bloquear momentaneamente por velocidade (FloodWait), ele aguarda um pouco e tenta o próximo
                print(f"Erro ao postar: {e}")
                index_estoque += 1
                time.sleep(5) 
        
        # Sorteia apenas de 3 a 7 segundos!
        segundos_espera = random.randint(TEMPO_MINIMO_SEGUNDOS, TEMPO_MAXIMO_SEGUNDOS)
        
        for _ in range(segundos_espera):
            if not motor_rodando:
                break
            time.sleep(1)

print("Bot Automático Turbo Iniciado...")
bot.infinity_polling()

