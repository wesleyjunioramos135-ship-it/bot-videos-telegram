import telebot
import time
from supabase import create_client, Client

# Substitua com os seus dados reais
API_TOKEN = '8906869920:AAER7XNMG9iZatgfwLCp-K3J-OqhGE0DrTI'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co/rest/v1/'
SUPABASE_KEY = 'sb_publishable_HLSpiUKa9XQqx2AE1Y48uw___aemm9X'
ADMIN_ID = 8906869920

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
