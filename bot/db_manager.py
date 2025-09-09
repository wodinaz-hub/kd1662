import sqlite3
import os
import logging
import pandas as pd

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_manager')

# Путь к файлу базы данных.
# PROJECT_ROOT теперь указывает на директорию 'kd1662'.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_FILE = os.path.join(PROJECT_ROOT, 'data', 'kvk_data.db')

def get_db_connection():
    """Устанавливает соединение с базой данных."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row # Позволяет получать строки как объекты с доступом по имени столбца
        logger.info(f"Успешно подключено к базе данных: {DB_FILE}")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

def create_tables():
    """Создает необходимые таблицы в базе данных, если они не существуют."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Таблица для хранения данных KVK
            # kvk_id теперь TEXT для хранения названий KVK
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kvk_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kvk_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    player_id INTEGER NOT NULL,
                    player_name TEXT NOT NULL,
                    alliance_tag TEXT,
                    kills INTEGER,
                    death INTEGER,
                    resource_gathered INTEGER,
                    alliance_help INTEGER,
                    ruins_captured INTEGER,
                    pass_occupied INTEGER,
                    kill_points INTEGER,
                    UNIQUE(kvk_id, period_key, player_id)
                )
            ''')

            # Таблица для хранения информации о периодах KVK
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kvk_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kvk_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    period_name TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    UNIQUE(kvk_id, period_key)
                )
            ''')

            conn.commit()
            logger.info("Таблицы базы данных успешно проверены/созданы.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
        finally:
            conn.close()

def import_data_from_excel(file_path: str, kvk_name: str, period_key: str):
    """
    Импортирует данные из Excel-файла в базу данных.
    Принимает kvk_name (название KVK) вместо kvk_number.
    """
    conn = get_db_connection()
    if not conn:
        return False

    try:
        df = pd.read_excel(file_path)
        cursor = conn.cursor()

        # Проверяем и добавляем период, если его нет
        period_name = period_key # Можно расширить для более красивых названий периодов
        cursor.execute("INSERT OR IGNORE INTO kvk_periods (kvk_id, period_key, period_name) VALUES (?, ?, ?)",
                       (kvk_name, period_key, period_name))

        # Подготовка данных для вставки
        data_to_insert = []
        for index, row in df.iterrows():
            # Заменяем NaN на None для корректной вставки в БД
            data_to_insert.append((
                kvk_name,
                period_key,
                int(row.get('ID', 0)), # Убедимся, что ID - целое число
                str(row.get('Имя', 'Неизвестно')),
                str(row.get('Тег Альянса', '')),
                int(row.get('Убийства', 0)),
                int(row.get('Смерти', 0)),
                int(row.get('Собранные Ресурсы', 0)),
                int(row.get('Помощь Альянса', 0)),
                int(row.get('Захваченные Руины', 0)),
                int(row.get('Занятые Проходы', 0)),
                int(row.get('Очки Убийств', 0))
            ))

        # Вставляем данные, заменяя существующие при конфликте (по kvk_id, period_key, player_id)
        cursor.executemany('''
            INSERT OR REPLACE INTO kvk_data (
                kvk_id, period_key, player_id, player_name, alliance_tag,
                kills, death, resource_gathered, alliance_help,
                ruins_captured, pass_occupied, kill_points
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)

        conn.commit()
        logger.info(f"Данные для KVK '{kvk_name}' периода '{period_key}' успешно импортированы из {file_path}.")
        return True
    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
        return False
    except KeyError as e:
        logger.error(f"Отсутствует ожидаемый столбец в Excel-файле: {e}. Проверьте правильность заголовков.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при импорте данных из Excel: {e}")
        return False
    finally:
        conn.close()

def get_player_data(kvk_name: str, period_key: str, player_id: int = None):
    """
    Получает данные игрока(ов) для указанного KVK и периода.
    Принимает kvk_name (название KVK).
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        if player_id:
            cursor.execute('''
                SELECT * FROM kvk_data
                WHERE kvk_id = ? AND period_key = ? AND player_id = ?
            ''', (kvk_name, period_key, player_id))
        else:
            cursor.execute('''
                SELECT * FROM kvk_data
                WHERE kvk_id = ? AND period_key = ?
            ''', (kvk_name, period_key))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении данных игрока: {e}")
        return []
    finally:
        conn.close()

def get_top_players(kvk_name: str, period_key: str, metric: str, limit: int = 5):
    """
    Получает топ игроков по указанной метрике для данного KVK и периода.
    Принимает kvk_name (название KVK).
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        # Защита от SQL-инъекций: убедимся, что metric - это допустимый столбец
        allowed_metrics = ['kills', 'death', 'resource_gathered', 'alliance_help',
                           'ruins_captured', 'pass_occupied', 'kill_points']
        if metric not in allowed_metrics:
            logger.warning(f"Попытка запроса по недопустимой метрике: {metric}")
            return []

        query = f'''
            SELECT player_name, alliance_tag, {metric}
            FROM kvk_data
            WHERE kvk_id = ? AND period_key = ?
            ORDER BY {metric} DESC
            LIMIT ?
        '''
        cursor.execute(query, (kvk_name, period_key, limit))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении топ игроков: {e}")
        return []
    finally:
        conn.close()

def get_player_rank(kvk_name: str, period_key: str, player_id: int, metric: str):
    """
    Получает ранг игрока по указанной метрике для данного KVK и периода.
    Принимает kvk_name (название KVK).
    """
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        allowed_metrics = ['kills', 'death', 'resource_gathered', 'alliance_help',
                           'ruins_captured', 'pass_occupied', 'kill_points']
        if metric not in allowed_metrics:
            logger.warning(f"Попытка запроса ранга по недопустимой метрике: {metric}")
            return None

        # Получаем значение метрики для конкретного игрока
        cursor.execute(f'''
            SELECT {metric} FROM kvk_data
            WHERE kvk_id = ? AND period_key = ? AND player_id = ?
        ''', (kvk_name, period_key, player_id))
        player_metric_value = cursor.fetchone()

        if not player_metric_value:
            return None # Игрок не найден или нет данных

        player_metric_value = player_metric_value[metric]

        # Считаем количество игроков с метрикой выше или равной нашей
        cursor.execute(f'''
            SELECT COUNT(*) + 1 FROM kvk_data
            WHERE kvk_id = ? AND period_key = ? AND {metric} > ?
        ''', (kvk_name, period_key, player_metric_value))
        rank = cursor.fetchone()[0]

        return rank
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении ранга игрока: {e}")
        return None
    finally:
        conn.close()

def get_player_stats_for_all_periods(kvk_name: str, player_id: int):
    """
    Получает статистику игрока по всем периодам для указанного KVK.
    Принимает kvk_name (название KVK).
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT period_key, kills, death, resource_gathered, alliance_help,
                   ruins_captured, pass_occupied, kill_points
            FROM kvk_data
            WHERE kvk_id = ? AND player_id = ?
            ORDER BY period_key
        ''', (kvk_name, player_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении статистики игрока по всем периодам: {e}")
        return []
    finally:
        conn.close()

def get_all_kvk_names():
    """
    Получает список всех уникальных названий KVK, присутствующих в базе данных.
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT kvk_id FROM kvk_data ORDER BY kvk_id")
        rows = cursor.fetchall()
        return [row['kvk_id'] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении списка KVK: {e}")
        return []
    finally:
        conn.close()

def get_kvk_periods(kvk_name: str):
    """
    Получает список всех периодов для указанного KVK.
    Принимает kvk_name (название KVK).
    """
    conn = get_db_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT period_key, period_name FROM kvk_periods WHERE kvk_id = ? ORDER BY period_key", (kvk_name,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении периодов для KVK '{kvk_name}': {e}")
        return []
    finally:
        conn.close()

# Вызов создания таблиц при загрузке модуля
create_tables()
