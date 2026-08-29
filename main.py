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

# Dicionário para gerenciar o andamento e a pausa dos vídeos de cada cliente
sessoes_usuarios = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    msg = bot.send_message(message.chat.id, "Olá! Insira a senha de acesso:")
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
    
    if senha_digitada == 'start123vip':
        bot.send_message(chat_id, "✅ Acesso VIP liberado! Iniciando o envio...")
        bot.send_message(ADMIN_ID, f"🔔 *Acesso VIP:*\nO cliente {cliente_info} acessou com a senha VIP.", parse_mode="Markdown")
        iniciar_sessao_videos(chat_id)
        return

    response = supabase.table('senhas').select('codigo').eq('codigo', senha_digitada).execute()
    if response.data:
        supabase.table('senhas').delete().eq('codigo', senha_digitada).execute()
        bot.send_message(chat_id, "✅ Senha de prévia aceita! Iniciando os vídeos...")
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

    # Registra o cliente no sistema para controlar de onde ele parou
    sessoes_usuarios[chat_id] = {
        'videos': videos,
        'index': 0,
        'pausado': False
    }
    
    # Inicia o envio em segundo plano (para o botão de pausa funcionar em tempo real)
    threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()

def enviar_lote_videos(chat_id):
    sessao = sessoes_usuarios.get(chat_id)
    if not sessao:
        return

    videos = sessao['videos']
    
    while sessao['index'] < len(videos):
        if sessao['pausado']:
            # Se o cliente pausou, interrompe o envio e mostra botão de continuar
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("▶️ Continuar Envios", callback_data="continuar"))
            bot.send_message(chat_id, "⏸ *Envio de vídeos pausado.*", parse_mode="Markdown", reply_markup=markup)
            return

        video = videos[sessao['index']]
        
        # Cria o teclado flutuante com o botão Pausar
        markup_pausa = telebot.types.InlineKeyboardMarkup()
        markup_pausa.add(telebot.types.InlineKeyboardButton("⏸ Pausar", callback_data="pausar"))

        # Regra de proteção: Se for o ADMIN, recebe desbloqueado. Se for cliente, recebe blindado (protect_content=True)
        is_cliente = (chat_id != ADMIN_ID)
        
        try:
            bot.send_video(
                chat_id, 
                video['file_id'], 
                protect_content=is_cliente, 
                reply_markup=markup_pausa
            )
            
            sessao['index'] += 1
            
            # Lógica da tela de carregamento animada
            if sessao['index'] % 10 == 0 and sessao['index'] < len(videos):
                msg_carga = bot.send_message(chat_id, "🔄 *Preparando os próximos...*\n`🟩⬜⬜⬜` 25%", parse_mode="Markdown")
                time.sleep(1.2)
                bot.edit_message_text("🔄 *Carregando do servidor...*\n`🟩🟩⬜⬜` 50%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(1.2)
                bot.edit_message_text("🔄 *Quase lá...*\n`🟩🟩🟩⬜` 75%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(1.2)
                bot.edit_message_text("✅ *Tudo pronto!*\n`🟩🟩🟩🟩` 100%", chat_id, msg_carga.message_id, parse_mode="Markdown")
                time.sleep(1.0) # Tempo extra para o usuário ler "Tudo pronto!"
                bot.delete_message(chat_id, msg_carga.message_id)
                time.sleep(0.5) # Tempo extra de respiro para o vídeo não cair atropelando o anterior
            else:
                time.sleep(1.5) # Pausa padrão constante entre cada vídeo
                
        except Exception as e:
            print(f"Erro no envio: {e}")
            sessao['index'] += 1

    if sessao['index'] >= len(videos):
        bot.send_message(chat_id, "🎯 Todos os vídeos foram enviados com sucesso!")
        del sessoes_usuarios[chat_id]

# Função que escuta os cliques nos botões flutuantes
@bot.callback_query_handler(func=lambda call: call.data in ["pausar", "continuar"])
def botoes_pausa_acao(call):
    chat_id = call.message.chat.id
    sessao = sessoes_usuarios.get(chat_id)
    
    if not sessao:
        bot.answer_callback_query(call.id, "Sessão expirada. Digite /start de novo.", show_alert=True)
        return

    if call.data == "pausar":
        sessao['pausado'] = True
        bot.answer_callback_query(call.id, "Pausando...")
        # Remove o botão de pausa daquele vídeo específico para limpar a tela
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    elif call.data == "continuar":
        sessao['pausado'] = False
        bot.answer_callback_query(call.id, "Continuando o envio...")
        bot.delete_message(chat_id, call.message.message_id) # Apaga o aviso de pausa
        # Retoma o processo de onde parou em segundo plano
        threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()

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

