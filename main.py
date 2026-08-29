import telebot
import time
import random
import string
import threading
from supabase import create_client, Client

# Suas credenciais
API_TOKEN = '8927249466:AAGV-V28myKtBoMkBe4jGQcTFatWjqGnUlo'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZG9uaWdndnVlb2VtaHl5ZnN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgwMjA5ODQsImV4cCI6MjEwMzU5Njk4NH0.uRxXnRijkkkq6NYilV3nXKTwWQ4K-CVXq5pJgqCv1U4' 
ADMIN_ID = 8237036306

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

sessoes_usuarios = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Ao iniciar, garante que o teclado especial está fechado
    markup_remover = telebot.types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "Olá! Insira a senha de acesso:", reply_markup=markup_remover)
    bot.register_next_step_handler(msg, process_password)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    nova_senha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    try:
        supabase.table('senhas').insert({'codigo': nova_senha}).execute()
        bot.reply_to(message, f"🎟️ *Nova Senha de Prévia Criada!*\n\n`{nova_senha}`\n\n_Uso único. Copie e envie para o cliente._", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro ao criar senha no banco de dados.")

def process_password(message):
    chat_id = message.chat.id
    senha_digitada = message.text.strip()
    cliente_info = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    
    # Cria o Teclado Fixo Inferior com Pausa e Continuar
    markup_controles = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_controles.add("⏸ Pausar", "▶️ Continuar")
    
    if senha_digitada == 'start123vip':
        bot.send_message(chat_id, "✅ Acesso VIP liberado! Iniciando os vídeos...", reply_markup=markup_controles)
        bot.send_message(ADMIN_ID, f"🔔 *Acesso VIP:*\nO cliente {cliente_info} acessou com a senha VIP.", parse_mode="Markdown")
        iniciar_sessao_videos(chat_id)
        return

    response = supabase.table('senhas').select('codigo').eq('codigo', senha_digitada).execute()
    if response.data:
        supabase.table('senhas').delete().eq('codigo', senha_digitada).execute()
        bot.send_message(chat_id, "✅ Senha de prévia aceita! Iniciando os vídeos...", reply_markup=markup_controles)
        bot.send_message(ADMIN_ID, f"🔔 *Senha Única Usada:*\nO cliente {cliente_info} usou a senha `{senha_digitada}`.", parse_mode="Markdown")
        iniciar_sessao_videos(chat_id)
    else:
        bot.send_message(chat_id, "❌ Senha inválida ou já utilizada. Digite /start para tentar novamente.")

def iniciar_sessao_videos(chat_id):
    response = supabase.table('videos').select('file_id').execute()
    videos = response.data

    if not videos:
        bot.send_message(chat_id, "Nenhum vídeo cadastrado ainda.")
        return

    sessoes_usuarios[chat_id] = {
        'videos': videos,
        'index': 0,
        'pausado': False
    }
    threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()

# Controlador dos botões do teclado fixo
@bot.message_handler(func=lambda message: message.text in ["⏸ Pausar", "▶️ Continuar"])
def controle_pausa(message):
    chat_id = message.chat.id
    sessao = sessoes_usuarios.get(chat_id)
    
    if not sessao:
        bot.reply_to(message, "Nenhum envio em andamento.", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
        
    if message.text == "⏸ Pausar":
        if not sessao['pausado']:
            sessao['pausado'] = True
            bot.reply_to(message, "⏸ *Envio pausado.* (Pode demorar 1 segundo para o vídeo atual terminar de cair).", parse_mode="Markdown")
        else:
            bot.reply_to(message, "O envio já está pausado.")
            
    elif message.text == "▶️ Continuar":
        if sessao['pausado']:
            sessao['pausado'] = False
            bot.reply_to(message, "▶️ *Retomando os envios...*", parse_mode="Markdown")
            threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()
        else:
            bot.reply_to(message, "Os vídeos já estão sendo enviados.")

def enviar_lote_videos(chat_id):
    sessao = sessoes_usuarios.get(chat_id)
    if not sessao:
        return

    videos = sessao['videos']
    
    while sessao['index'] < len(videos):
        if sessao['pausado']:
            return # Interrompe a thread silenciosamente se estiver pausado

        video = videos[sessao['index']]
        is_cliente = (chat_id != ADMIN_ID)
        
        try:
            # Envia sem poluir com botão embaixo do vídeo
            bot.send_video(chat_id, video['file_id'], protect_content=is_cliente)
            sessao['index'] += 1
            
            # Tela de carregamento mais rápida
            if sessao['index'] % 10 == 0 and sessao['index'] < len(videos):
                msg_carga = bot.send_message(chat_id, "🔄 *Preparando os próximos...*\n`🟩⬜⬜⬜` 25%", parse_mode="Markdown")
                time.sleep(0.6)
                bot.edit_message_text("🔄 *Carregando do servidor...*\n`🟩🟩⬜⬜` 50%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(0.6)
                bot.edit_message_text("🔄 *Quase lá...*\n`🟩🟩🟩⬜` 75%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(0.6)
                bot.edit_message_text("✅ *Tudo pronto!*\n`🟩🟩🟩🟩` 100%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(0.7)
                bot.delete_message(chat_id, msg_carga.message_id)
                time.sleep(0.3) 
            else:
                # Intervalo mais rápido entre um vídeo e outro (0.7 segundos em vez de 1.5s)
                time.sleep(0.7)
                
        except Exception as e:
            print(f"Erro no envio: {e}")
            sessao['index'] += 1

    if sessao['index'] >= len(videos):
        # Remove o teclado fixo de pausar/continuar quando acaba
        markup_remover = telebot.types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "🎯 Todos os vídeos foram enviados com sucesso!", reply_markup=markup_remover)
        del sessoes_usuarios[chat_id]

@bot.message_handler(content_types=['video'])
def handle_video(message):
    if message.from_user.id != ADMIN_ID:
        return
    file_id = message.video.file_id
    try:
        supabase.table('videos').insert({'file_id': file_id}).execute()
        bot.reply_to(message, "📁 Vídeo salvo com sucesso no banco!")
    except Exception:
        bot.reply_to(message, "⚠️ Erro ao salvar vídeo.")

print("Bot iniciado...")
bot.infinity_polling()
