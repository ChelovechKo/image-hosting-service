import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename

# Настройка логирования
logging.basicConfig(
    filename='/logs/app.log',                         # Лог файл в Docker volume /logs
    level=logging.INFO,                               # Уровень логирования
    format='%(asctime)s [%(levelname)s]: %(message)s' # Формат записи
)
app = Flask(__name__)
app.secret_key = 'VhEnGT@lklcsShySWN%yAXKk}|Y3p?8~'

# Параметры
UPLOAD_FOLDER = '/images/'
ALLOWED_EXTENSIONS = {'jpg', 'png', 'gif'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


@app.route('/')
def index():
    '''Главная страница'''
    return render_template('index.html')


def allowed_file(filename):
    '''Проверка расширения файла'''
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           

@app.route('/upload-error', methods=['POST'])
def handle_upload_error():
    """Обработка ошибок при загрузке файла"""
    data = request.get_data(as_text=True)
    logging.error(data)
    return jsonify({"message": data}), 200    


@app.route('/upload', methods=['POST'])
def upload_file():
    '''Загрузка изображений'''
    if 'file' not in request.files:
        flash(("Ошибка: файл не выбран!",), "error")
        logging.error("Ошибка: файл не выбран!")
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash(("Ошибка: файл не выбран!",), "error")
        logging.error("Ошибка: файл не выбран!")
        return redirect(url_for('upload_page'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Генерация уникального имени файла
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Логируем путь к файлу, который будет сохранён
        logging.info(f"Сохраняем файл: {filepath}")
        
        try:
            file.save(filepath)
            logging.info(f"Успех: изображение {unique_filename} загружено.")
            flash(
                ("Изображение успешно загружено!", f"<a href='/images/{unique_filename}' target='_blank'>/images/{unique_filename}</a>"), 
                "success"
            )
            return redirect(url_for('upload_page'))
        except Exception as e:
            logging.error(f"Ошибка при сохранении файла: {e}")
            flash(("В ходе загрузки возникла ошибка, попробуйте загрузить изображение ещё раз", ), "error")
            return redirect(url_for('upload_page'))
        
    else:
        logging.error(f"Ошибка: неподдерживаемый формат файла {file.filename}.")
        flash(("Ошибка: неподдерживаемый формат файла", ), "error")
        return redirect(url_for('upload_page'))



@app.route('/upload', methods=['GET'])
def upload_page():
    '''Страница с формой для загрузки изображения'''
    return render_template('upload.html')


@app.route('/images')
def images_list():
    '''Страница с каталогом загруженных изображений'''
    # Получаем список файлов в папке /images
    image_files = os.listdir(app.config['UPLOAD_FOLDER'])
    image_urls = [f"/images/{filename}" for filename in image_files if allowed_file(filename)]

    # Передаем список изображений в шаблон
    return render_template('images.html', image_urls=image_urls)


@app.route('/images/<filename>')
def uploaded_file(filename):
    '''Доступ к изображению'''
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
