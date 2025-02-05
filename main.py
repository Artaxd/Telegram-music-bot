import os
import telebot
import yt_dlp
from telebot.types import InputFile, InlineKeyboardButton, InlineKeyboardMarkup
import requests 
from mutagen.mp4 import MP4, MP4Cover


#downloader configuration
ydl_opts = {
    'format': 'm4a/bestaudio/best',
    # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
    'postprocessors': [{  # Extract audio using ffmpeg
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a',
    }],
    'geo_bypass_country' : 'us',
    'noplaylist': True,
    'dump_single_json': True,
    'embedthumbnail': True,  # Встраивание обложки в файл
    'embed-metadata': True,  # Встраивание метаданных
    'extractor-args': 'youtube:player_skip=config'  # Обход возрастных ограничений
}

#поиск видео на ютуб по запросу(query)
def search_youtube(query, max_results):
    search_query = f"ytsearch{max_results}:{query}"  # Поисковый запрос в формате ytsearch
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False) #извлекаем метаданные страницы

    # Извлечение ссылок на видео
    video_urls = []
    for entry in info.get("entries", []):
        category = entry.get('categories', [])
        if 'music' in category or 'Music' in category: #фильтруем только музыку по категориям
            video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
    return video_urls

#добавляет информацию об обложке внутрь м4а файла с помощью тегов
def add_cover_to_audio(audio_file, cover_image):
    # Загружаем аудиофайл
    audio = MP4(audio_file)

    try:
        audio.add_tags()
    except:
        pass

    # Добавляем обложку в виде APIC (Attached Picture)
    audio.tags["covr"] = [
        MP4Cover(
            cover_image,
            imageformat=MP4Cover.FORMAT_JPEG  # Используем JPEG. Если PNG, замените на FORMAT_PNG
        )
    ]

    audio.save(audio_file)

#отправляет музыку аудио файлом в телеграм
def send_music(url, chat_id):
    file_path = ""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False) #извлекаем метаданные самого видео
            file_path = ydl.prepare_filename(info)
            ydl.download(url) 

            thumbnails_list = info.get("thumbnails", []) #получаем превью видео из метаданных
            thumbnail_url = [x["url"] for x in thumbnails_list if x["url"][-13:] == "hqdefault.jpg"][-1] #среднее качество формат jpg
            thumbnail_data = requests.get(thumbnail_url).content #поучаем данные картинкук с помощью request по ссылке

            add_cover_to_audio(file_path, thumbnail_data) #добавяем обложку внутрь файла с музыкой
            
            #отрпавляем сообщение
            bot.send_audio(chat_id, InputFile(file_path), performer=info.get("uploader"), title=info.get("title"), thumb=thumbnail_data, thumbnail=thumbnail_data)

            #удаляем файл после отправки
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Файл {file_path} успешно удалён.")
            else:
                print(f"Файл {file_path} не найден.")

        except:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Файл {file_path} успешно удалён.")
            else:
                print(f"Файл {file_path} не найден.")

#удаляет лишние сообщения кроме текущего меню выбора музыки
def clear_messages(chat_id, ids):
    for id in ids:
        bot.delete_message(chat_id, id)
    
    ids.clear()

#ключ для бота
bot = telebot.TeleBot("")

#список с id отосланных сообщений вида "id чата" : [id сообщений]
sent_messages_ids = {}

@bot.message_handler()
def main(message):
    #добавляем сообщения пользователя в существующий список или создем новый если он отсутствует
    try:
        sent_messages_ids[message.chat.id].append(message.message_id)
    except:
        sent_messages_ids[message.chat.id] = [message.message_id]
    #счетчик сообщений начиная с текущего т.к. id сообщений нумеруются по порядку (т.е. слуд. сообщение будет иметь id +1 от текущего и т.д.)
    message_count = 1

    #проверка на различные команды
    if message.text.lower() in ['/start', 'start', 'hello', 'привет']:
        bot.send_message(message.chat.id, "Привет! Напиши название музыки, и я найду её!")
        sent_messages_ids[message.chat.id].append(message.message_id + message_count)
        message_count+=1
    else:
        #если не какая-то команда то начинаем искать музыку
        bot.send_message(message.chat.id, "Уже ищу!")
        #все отосланые сообщения добавляем в список чтобы потом удалить
        sent_messages_ids[message.chat.id].append(message.message_id + message_count)
        message_count+=1
        
        #массив полученных ссылок на музыку
        URLS = search_youtube(message.text.lower().replace(" ", "+"), max_results=10)

        #высылаем меню с найдеными треками на выбор
        markup = InlineKeyboardMarkup()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in URLS:
                info = ydl.extract_info(url, download=False)
                markup.add(InlineKeyboardButton(info.get("title"), callback_data=url))
        #удаляем все предыдущие сообщения 
        clear_messages(message.chat.id, sent_messages_ids[message.chat.id])
        #вывидом меню
        bot.send_message(message.chat.id, f'Вот что нашел по запросу "{message.text}"', reply_markup=markup)
        sent_messages_ids[message.chat.id].append(message.message_id + message_count)


#обработка нажатий на кнопку
@bot.callback_query_handler(func=lambda callback: True)
def callback_handler(callback):
    if callback.data == "like":
        #добавялем трек в понравившиеся/удаляем если трек уже в лайкнутых
        pass
    elif callback.data == "delete":
        #удаляем сообщение с треком
        pass
    else: 
        #высылаем выбранный трек
        url = callback.data
        send_music(url, callback.message.chat.id)
        

bot.polling(non_stop=True)
