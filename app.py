import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, render_template, flash, redirect, url_for
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor

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

# Устанавливаем подключение к PostgreSQL
try:
    db_conn = psycopg2.connect(
        dbname="images_db",
        user="postgres",
        password="password",
        host="db",
        port="5432"
    )
    db_conn.autocommit = True
    db_cursor = db_conn.cursor(cursor_factory=RealDictCursor)
    logging.info("Соединение с БД установлено")
except Exception as e:
    logging.error(f"Ошибка подключения к БД: {e}")


def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_metadata(filename, original_name, size, file_type):
    """Сохраняет метаданные изображения в таблицу images"""
    try:
        query = """
        INSERT INTO images (filename, original_name, size, file_type)
        VALUES (%s, %s, %s, %s)
        """
        db_cursor.execute(query, (filename, original_name, size, file_type))
        logging.info(f"Метаданные для файла {filename} сохранены в БД")
    except Exception as e:
        logging.error(f"Ошибка сохранения метаданных: {e}")
        raise


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/upload-error', methods=['POST'])
def handle_upload_error():
    """Обработка ошибок при загрузке файла"""
    data = request.get_data(as_text=True)
    logging.error(data)
    return jsonify({"message": data}), 200    


@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка изображений"""
    logging.info("Начало обработки загрузки файла")
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
            file_size = os.path.getsize(filepath)
            file_ext = unique_filename.rsplit('.', 1)[1].lower()
            if db_cursor:
                save_metadata(unique_filename, filename, file_size, file_ext)
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
    """Страница с формой для загрузки изображения"""
    return render_template('upload.html')


@app.route('/images')
def images_list():
    """Страница с каталогом загруженных изображений с пагинацией"""
    logging.info("Пользователь открыл страницу списка изображений")
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        # Общее количество изображений для расчета пагинации
        db_cursor.execute("SELECT COUNT(*) FROM images")
        total = int(db_cursor.fetchone()['count'])
        # Выборка записей с сортировкой по дате загрузки (от новых к старым)
        db_cursor.execute("SELECT * FROM images ORDER BY upload_time DESC LIMIT %s OFFSET %s", (per_page, offset))
        images = db_cursor.fetchall()
    except Exception as e:
        logging.error(f"Ошибка получения изображений из БД: {e}")
        images = []
        total = 0
    total_pages = (total + per_page - 1) // per_page
    return render_template('images.html', images=images, page=page, total_pages=total_pages)


@app.route('/delete/<int:image_id>', methods=['GET'])
def delete_image(image_id):
    """Удаление изображения по id"""
    try:
        db_cursor.execute("SELECT * FROM images WHERE id = %s", (image_id,))
        image = db_cursor.fetchone()
        if image:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Файл {file_path} удалён с диска")
            else:
                logging.error(f"Файл {file_path} не найден на диске")
            db_cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
            logging.info(f"Запись с id {image_id} удалена из БД")
            flash(("Изображение успешно удалено.",), "success")
        else:
            flash(("Изображение не найдено.",), "error")
            logging.error(f"Изображение с id {image_id} не найдено в БД")
    except Exception as e:
        logging.error(f"Ошибка при удалении изображения: {e}")
        flash(("Произошла ошибка при удалении изображения.",), "error")
    return redirect(url_for('images_list'))
    

@app.route('/images/<filename>')
def uploaded_file(filename):
    """Доступ к изображению"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
