import telebot
import time
import random
import string
from supabase import create_client, Client

# Suas credenciais
API_TOKEN = '8927249466:AAGV-V28myKtBoMkBe4jGQcTFatWjqGnUlo'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZG9uaWdndnVlb2VtaHl5ZnN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgwMjA5ODQsImV4cCI6MjEwMzU5Njk4NH0.uRxXnRijkkkq6NYilV3nXKTwWQ4K-CVXq5pJgqCv1U4' 
ADMIN_ID = 8237036306

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, "Olá! Insira a senha de acesso:")
    bot.register_next_step_handler(msg, process_password)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    # Verifica se quem deu o comando é você (Admin)
    if message.from_user.id != ADMIN_ID:
        return
    
    # Gera uma senha aleatória de 6 caracteres (letras e números)
    nova_senha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    try:
        supabase.table('senhas').insert({'codigo': nova_senha}).execute()
        bot.reply_to(message, f"🎟️ *Nova Senha de Prévia Criada!*\n\n`{nova_senha}`\n\n_Esta senha é de uso único. Copie e envie para o cliente._", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro ao criar senha no banco de dados.")

def process_password(message):
    senha_digitada = message.text.strip()
    
    # Pega o @username ou o ID do cliente para te notificar
    cliente_info = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    
    # 1. Verifica se é a senha mestra (VIP)
    if senha_digitada == 'start123vip':
        bot.send_message(message.chat.id, "✅ Acesso VIP liberado! Iniciando o envio...")
        bot.send_message(ADMIN_ID, f"🔔 *Notificação de Acesso:*\nO cliente {cliente_info} acessou o bot usando a **Senha VIP**.", parse_mode="Markdown")
        send_videos_in_batches(message.chat.id)
        return

    # 2. Verifica no banco se é uma senha de prévia (Uso único)
    response = supabase.table('senhas').select('codigo').eq('codigo', senha_digitada).execute()
    
    if response.data:
        # Achou a senha! Agora deleta ela do banco para ninguém mais usar
        supabase.table('senhas').delete().eq('codigo', senha_digitada).execute()
        
        bot.send_message(message.chat.id, "✅ Senha de prévia aceita! Iniciando os vídeos...")
        bot.send_message(ADMIN_ID, f"🔔 *Notificação de Acesso:*\nO cliente {cliente_info} resgatou a senha de prévia `{senha_digitada}`. Ela foi queimada e não pode mais ser usada.", parse_mode="Markdown")
        send_videos_in_batches(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Senha inválida ou já utilizada. Digite /start para tentar novamente.")

def send_videos_in_batches(chat_id):
    response = supabase.table('videos').select('file_id').execute()
    videos = response.data

    if not videos:
        bot.send_message(chat_id, "Nenhum vídeo cadastrado ainda.")
        return

    count = 0
    for video in videos:
        try:
            # protect_content=True bloqueia prints, encaminhamentos e salvamentos na galeria
            bot.send_video(chat_id, video['file_id'], protect_content=True)
            count += 1

            # Pausa suave de 1.5 segundos ENTRE CADA VÍDEO para dar tempo do cliente respirar
            time.sleep(1.5)

            # A cada 10 vídeos, faz a animação da barra de progresso
            if count % 10 == 0 and count < len(videos):
                progress_msg = bot.send_message(chat_id, "⏳ *Carregando...*\n[░░░░]", parse_mode="Markdown")
                
                # Animação preenchendo 4 barrinhas
                for i in range(1, 5):
                    time.sleep(1.2) # Tempo entre cada frame da animação
                    bars = "█" * i + "░" * (4 - i) # Lógica das 4 barras
                    bot.edit_message_text(
                        f"⏳ *Carregando...*\n[{bars}]", 
                        chat_id=chat_id, 
                        message_id=progress_msg.message_id, 
                        parse_mode="Markdown"
                    )
                
                bot.delete_message(chat_id, progress_msg.message_id)
                
        except Exception as e:
            print(f"Erro ao enviar vídeo: {e}")

    bot.send_message(chat_id, "🎯 Todos os vídeos foram enviados com sucesso!")

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
