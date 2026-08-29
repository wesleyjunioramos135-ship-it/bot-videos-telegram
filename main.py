iimport telebot
import time
from supabase import create_client, Client

# Substitua com os seus dados reais
API_TOKEN = '8927249466:AAGV-V28myKtBoMkBe4jGQcTFatWjqGnUlo'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZG9uaWdndnVlb2VtaHl5ZnN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgwMjA5ODQsImV4cCI6MjEwMzU5Njk4NH0.uRxXnRijkkkq6NYilV3nXKTwWQ4K-CVXq5pJgqCv1U4'
ADMIN_ID = 8563298081

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, "Olá! Insira a senha de acesso:")
    bot.register_next_step_handler(msg, process_password)

def process_password(message):
    if message.text == 'start123vip':
        bot.send_message(message.chat.id, "✅ Senha correta! Iniciando o envio dos vídeos...")
        send_videos_in_batches(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Senha incorreta. Digite /start para tentar novamente.")

def send_videos_in_batches(chat_id):
    response = supabase.table('videos').select('file_id').execute()
    videos = response.data

    if not videos:
        bot.send_message(chat_id, "Nenhum vídeo encontrado no banco de dados.")
        return

    count = 0
    for video in videos:
        try:
            bot.send_video(chat_id, video['file_id'])
            count += 1

            if count % 10 == 0 and count < len(videos):
                progress_msg = bot.send_message(
                    chat_id, 
                    "⏳ *Aguarde 5 segundos...*\nCarregando os próximos vídeos [██████░░░░]", 
                    parse_mode="Markdown"
                )
                time.sleep(5)
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
        bot.reply_to(message, "⚠️ Erro ao salvar vídeo (pode já estar cadastrado).")

print("Bot iniciado...")
bot.infinity_polling()
