import telebot
import time
import random
import string
import threading
from supabase import create_client, Client

# Configurações e Credenciais
API_TOKEN = '8927249466:AAGV-V28myKtBoMkBe4jGQcTFatWjqGnUlo'
SUPABASE_URL = 'https://modoniggvueoemhyyfsx.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZG9uaWdndnVlb2VtaHl5ZnN4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgwMjA5ODQsImV4cCI6MjEwMzU5Njk4NH0.uRxXnRijkkkq6NYilV3nXKTwWQ4K-CVXq5pJgqCv1U4' 
ADMIN_ID = 8237036306

# Link de contato para fechamento do VIP
LINK_ADMIN_PRIVADO = "https://t.me/agiuavipp"

# Configurações de exibição de Anúncio
PRIMEIRO_ANUNCIO = 20        # Primeiro anúncio após 20 vídeos
PROXIMOS_ANUNCIOS = 50       # Anúncios seguintes a cada 50 vídeos (70, 120, 170...)
TEMPO_ANUNCIO_SEGUNDOS = 10  # Duração da barra de progresso do anúncio

bot = telebot.TeleBot(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

sessoes_usuarios = {}
aguardando_anuncio = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup_remover = telebot.types.ReplyKeyboardRemove()
    msg = bot.send_message(message.chat.id, "👋 Olá! Insira a sua senha de acesso:", reply_markup=markup_remover)
    bot.register_next_step_handler(msg, process_password)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    nova_senha = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    try:
        supabase.table('senhas').insert({'codigo': nova_senha}).execute()
        
        texto_admin = (
            f"🛠️ *PAINEL ADMINISTRATIVO*\n\n"
            f"🎟️ *Nova Senha de Prévia:* `{nova_senha}`\n\n"
            f"📢 *Cadastrar Mídia VIP:*\n"
            f"Envie o comando `/anuncio` e em seguida envie o Vídeo ou Foto da propaganda do VIP."
        )
        bot.reply_to(message, texto_admin, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "⚠️ Erro ao acessar o banco de dados.")

@bot.message_handler(commands=['anuncio'])
def definir_anuncio(message):
    if message.from_user.id != ADMIN_ID:
        return
    aguardando_anuncio[ADMIN_ID] = True
    bot.reply_to(
        message, 
        f"📢 *Modo Anúncio VIP Ativo!*\n\nEnvie agora o **VÍDEO** que será exibido como propaganda para os clientes."
    )

def process_password(message):
    chat_id = message.chat.id
    senha_digitada = message.text.strip()
    cliente_info = f"@{message.from_user.username}" if message.from_user.username else f"ID {message.from_user.id}"
    
    # Montando o teclado com Pausar, Continuar e Comprar VIP
    markup_controles = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup_controles.row("⏸ Pausar", "▶️ Continuar")
    markup_controles.row("⭐ Comprar VIP")
    
    if senha_digitada == 'start123vip':
        bot.send_message(chat_id, "✅ Acesso VIP liberado! Iniciando exibição...", reply_markup=markup_controles)
        bot.send_message(ADMIN_ID, f"🔔 *Acesso VIP:*\nO cliente {cliente_info} acessou com a senha mestra.", parse_mode="Markdown")
        iniciar_sessao_videos(chat_id)
        return

    response = supabase.table('senhas').select('codigo').eq('codigo', senha_digitada).execute()
    if response.data:
        supabase.table('senhas').delete().eq('codigo', senha_digitada).execute()
        bot.send_message(chat_id, "✅ Senha de prévia aceita! Iniciando exibição...", reply_markup=markup_controles)
        bot.send_message(ADMIN_ID, f"🔔 *Senha Única Usada:*\nO cliente {cliente_info} usou a senha `{senha_digitada}`.", parse_mode="Markdown")
        iniciar_sessao_videos(chat_id)
    else:
        bot.send_message(chat_id, "❌ Senha inválida ou já utilizada. Digite /start para tentar novamente.")

def iniciar_sessao_videos(chat_id):
    response = supabase.table('videos').select('file_id').execute()
    videos = response.data

    if not videos:
        bot.send_message(chat_id, "⚠️ Nenhum vídeo cadastrado no momento.")
        return

    sessoes_usuarios[chat_id] = {
        'videos': videos,
        'index': 0,
        'pausado': False,
        'esperando_decisao': False
    }
    threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()

@bot.message_handler(func=lambda message: message.text in ["⏸ Pausar", "▶️ Continuar", "⭐ Comprar VIP"])
def controles_inferiores(message):
    chat_id = message.chat.id
    
    # Se o cliente clicou em comprar VIP no teclado inferior
    if message.text == "⭐ Comprar VIP":
        markup_vip = telebot.types.InlineKeyboardMarkup()
        btn_link = telebot.types.InlineKeyboardButton("📲 Falar com Suporte VIP", url=LINK_ADMIN_PRIVADO)
        markup_vip.add(btn_link)
        bot.send_message(
            chat_id, 
            "🚀 *Ótima decisão!*\nClique no botão abaixo para ser redirecionado(a) e garantir sua vaga no Grupo VIP agora mesmo:", 
            parse_mode="Markdown", 
            reply_markup=markup_vip
        )
        return

    sessao = sessoes_usuarios.get(chat_id)
    
    if not sessao:
        bot.reply_to(message, "Nenhum envio em andamento.", reply_markup=telebot.types.ReplyKeyboardRemove())
        return
        
    if message.text == "⏸ Pausar":
        if not sessao['pausado']:
            sessao['pausado'] = True
            bot.reply_to(message, "⏸ *Envio pausado.* Use os botões abaixo para continuar ou comprar o VIP.", parse_mode="Markdown")
        else:
            bot.reply_to(message, "O envio já está pausado.")
            
    elif message.text == "▶️ Continuar":
        if sessao['esperando_decisao']:
            bot.reply_to(message, "⏳ Aguarde o vídeo do anúncio finalizar ou compre o VIP para continuar.")
            return
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
        if sessao['pausado'] or sessao['esperando_decisao']:
            return

        video = videos[sessao['index']]
        is_cliente = (chat_id != ADMIN_ID)
        
        try:
            bot.send_video(chat_id, video['file_id'], protect_content=is_cliente)
            sessao['index'] += 1
            
            # Checa se chegou ao fim absoluto de todos os vídeos
            if sessao['index'] >= len(videos):
                markup_remover = telebot.types.ReplyKeyboardRemove()
                bot.send_message(chat_id, "🎯 *As prévias acabaram por aqui!*", parse_mode="Markdown", reply_markup=markup_remover)
                
                # Dispara o anúncio final obrigatório focado 100% no VIP
                enviar_anuncio_final_vip(chat_id)
                del sessoes_usuarios[chat_id]
                return

            # Lógica 20/50 para exibição dos anúncios intermediários
            videos_enviados = sessao['index']
            deve_mostrar_anuncio = (videos_enviados == PRIMEIRO_ANUNCIO) or (videos_enviados > PRIMEIRO_ANUNCIO and (videos_enviados - PRIMEIRO_ANUNCIO) % PROXIMOS_ANUNCIOS == 0)
            
            if deve_mostrar_anuncio:
                sessao['esperando_decisao'] = True
                threading.Thread(target=executar_fluxo_anuncio, args=(chat_id,)).start()
                return
            else:
                time.sleep(0.8)
                
        except Exception as e:
            print(f"Erro no envio de vídeo: {e}")
            sessao['index'] += 1

def gerar_barra_progresso(progresso_atual, total=10):
    preenchido = int((progresso_atual / total) * 10)
    vazio = 10 - preenchido
    return f"[{'🟩' * preenchido}{'⬜' * vazio}] {int((progresso_atual / total) * 100)}%"

def executar_fluxo_anuncio(chat_id):
    sessao = sessoes_usuarios.get(chat_id)
    if not sessao:
        return

    res = supabase.table('anuncios').select('*').order('id', desc=True).limit(1).execute()
    
    legenda_anuncio = (
        "⭐ *OFERTA EXCLUSIVA VIP* ⭐\n\n"
        "⚠️ *Aguarde o vídeo acabar* para continuar vendo as prévias, ou você pode pausar, ou melhor ainda: *COMPRAR O GRUPO VIP COMIGO AGORA!*\n\n"
        "🔒 Garanta seu acesso ao grupo completo e ilimitado para não precisar ficar esperando!\n"
        "👇 _Clique no botão abaixo do teclado ou espere o tempo terminar._"
    )
    
    is_cliente = (chat_id != ADMIN_ID)
    
    if res.data:
        anuncio = res.data[0]
        try:
            if anuncio['tipo'] == 'photo':
                bot.send_photo(chat_id, anuncio['file_id'], caption=legenda_anuncio, parse_mode="Markdown", protect_content=is_cliente)
            else:
                bot.send_video(chat_id, anuncio['file_id'], caption=legenda_anuncio, parse_mode="Markdown", protect_content=is_cliente)
        except Exception as e:
            print(f"Erro ao enviar mídia do anúncio: {e}")
            bot.send_message(chat_id, legenda_anuncio, parse_mode="Markdown")
    else:
        bot.send_message(chat_id, legenda_anuncio, parse_mode="Markdown")

    msg_progresso = bot.send_message(
        chat_id, 
        f"⏳ *Exibindo anúncio VIP...*\n`{gerar_barra_progresso(0, TEMPO_ANUNCIO_SEGUNDOS)}`\nRestam {TEMPO_ANUNCIO_SEGUNDOS}s para continuar.", 
        parse_mode="Markdown"
    )

    passo = 2
    for segundos_passados in range(passo, TEMPO_ANUNCIO_SEGUNDOS + 1, passo):
        time.sleep(passo)
        restante = TEMPO_ANUNCIO_SEGUNDOS - segundos_passados
        barra = gerar_barra_progresso(segundos_passados, TEMPO_ANUNCIO_SEGUNDOS)
        texto_atualizado = (
            f"⏳ *Exibindo anúncio VIP...*\n`{barra}`\n"
            f"Restam {restante}s para liberar as prévias." if restante > 0 else "✅ *Pronto para continuar! Compre o VIP para evitar esperas.*"
        )
        try:
            bot.edit_message_text(texto_atualizado, chat_id, msg_progresso.message_id, parse_mode="Markdown")
        except Exception:
            pass

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn_vip = telebot.types.InlineKeyboardButton("⭐ COMPRAR O VIP AGORA", url=LINK_ADMIN_PRIVADO)
    btn_continuar = telebot.types.InlineKeyboardButton("🎬 Continuar Assistindo Prévias", callback_data="continuar_previas")
    markup.add(btn_vip, btn_continuar)

    bot.send_message(
        chat_id,
        "👇 *Escolha o que deseja fazer agora:*",
        reply_markup=markup,
        parse_mode="Markdown"
    )

def enviar_anuncio_final_vip(chat_id):
    """Envia o anúncio final obrigatório quando todas as prévias terminam."""
    res = supabase.table('anuncios').select('*').order('id', desc=True).limit(1).execute()
    
    legenda_final = (
        "🚨 *AS PRÉVIAS ACABARAM POR AQUI!* 🚨\n\n"
        "Você assistiu a todo o nosso conteúdo de demonstração.\n\n"
        "🔥 *Quer continuar assistindo sem limites, com atualizações diárias e acesso liberado ao grupo principal?*\n\n"
        "⭐ Garanta seu acesso VIP agora mesmo clicando no botão abaixo!"
    )
    
    is_cliente = (chat_id != ADMIN_ID)
    
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn_vip = telebot.types.InlineKeyboardButton("⭐ COMPRAR ACESSO VIP COMPLETO", url=LINK_ADMIN_PRIVADO)
    markup.add(btn_vip)
    
    if res.data:
        anuncio = res.data[0]
        try:
            if anuncio['tipo'] == 'photo':
                bot.send_photo(chat_id, anuncio['file_id'], caption=legenda_final, parse_mode="Markdown", reply_markup=markup, protect_content=is_cliente)
            else:
                bot.send_video(chat_id, anuncio['file_id'], caption=legenda_final, parse_mode="Markdown", protect_content=is_cliente)
            return
        except Exception as e:
            print(f"Erro ao enviar mídia final do anúncio: {e}")
            
    bot.send_message(chat_id, legenda_final, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "continuar_previas")
def continuar_previas_callback(call):
    chat_id = call.message.chat.id
    sessao = sessoes_usuarios.get(chat_id)
    
    if not sessao:
        bot.answer_callback_query(call.id, "Sessão finalizada. Digite /start para iniciar novamente.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "Retomando as prévias...")
    sessao['esperando_decisao'] = False
    
    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    except Exception:
        pass
        
    threading.Thread(target=enviar_lote_videos, args=(chat_id,)).start()

@bot.message_handler(content_types=['photo', 'video'])
def handle_media(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    if aguardando_anuncio.get(ADMIN_ID):
        aguardando_anuncio[ADMIN_ID] = False
        
        if message.photo:
            file_id = message.photo[-1].file_id
            tipo = 'photo'
        else:
            file_id = message.video.file_id
            tipo = 'video'
            
        try:
            supabase.table('anuncios').insert({'file_id': file_id, 'tipo': tipo}).execute()
            bot.reply_to(
                message, 
                f"✅ *Mídia do Anúncio VIP cadastrada!*\nEla será exibida após os primeiros {PRIMEIRO_ANUNCIO} vídeos, a cada {PROXIMOS_ANUNCIOS} seguintes, e no encerramento das prévias.", 
                parse_mode="Markdown"
            )
        except Exception:
            bot.reply_to(message, "⚠️ Erro ao salvar anúncio no banco.")
        return

    if message.video:
        file_id = message.video.file_id
        try:
            supabase.table('videos').insert({'file_id': file_id}).execute()
            bot.reply_to(message, "📁 Vídeo cadastrado com sucesso no banco!")
        except Exception:
            bot.reply_to(message, "⚠️ Erro yt ao salvar vídeo.")

print("Bot iniciado...")
bot.infinity_polling()
