import pandas as pd
import numpy as np
import logging
import os

OUTPUT_FILE = 'results.xlsx'


def calculate_stats():
    logging.info("Початок читання та обробки даних у calculate_stats...")

    try:
        # --- 1. Завантаження даних з start_kvk.xlsx (для потужності до КВК) ---
        df_start_kvk = pd.DataFrame()
        if os.path.exists('start_kvk.xlsx'):
            try:
                df_start_kvk = pd.read_excel('start_kvk.xlsx')
                df_start_kvk = df_start_kvk.rename(columns={
                    'Governor ID': 'Governor ID',
                    'Power': 'Power_at_KVK_start'
                })
                # Переконайтеся, що Governor ID є рядковим типом для коректного об'єднання
                df_start_kvk['Governor ID'] = df_start_kvk['Governor ID'].astype(str).str.strip()
                df_start_kvk = df_start_kvk[['Governor ID', 'Power_at_KVK_start']]
                logging.info("start_kvk.xlsx успішно завантажено.")
            except Exception as e:
                logging.exception(f"Помилка при завантаженні start_kvk.xlsx: {e}")
        else:
            logging.warning(
                "Файл 'start_kvk.xlsx' не знайдено. Показники зміни потужності від початку KVK можуть бути відсутні.")

        # --- 2. Завантаження даних з before_pass4.xlsx (статистика до битви) ---
        df_before_pass4 = pd.DataFrame()
        if os.path.exists('before_pass4.xlsx'):
            try:
                df_before_pass4 = pd.read_excel('before_pass4.xlsx')
                df_before_pass4 = df_before_pass4.add_suffix('_before')
                df_before_pass4 = df_before_pass4.rename(columns={'Governor ID_before': 'Governor ID'})
                # Переконайтеся, що Governor ID є рядковим типом для коректного об'єднання
                df_before_pass4['Governor ID'] = df_before_pass4['Governor ID'].astype(str).str.strip()
                logging.info("before_pass4.xlsx успішно завантажено.")
            except Exception as e:
                logging.exception(f"Помилка при завантаженні before_pass4.xlsx: {e}")
        else:
            logging.error(
                "Критична помилка: файл 'before_pass4.xlsx' не знайдено. Без нього неможливий розрахунок змін статистики!")
            return pd.DataFrame()

        # --- 3. Завантаження даних з pass4.xlsx (статистика після битви, основні дані, нікнейми) ---
        df_pass4 = pd.DataFrame()
        if os.path.exists('pass4.xlsx'):
            try:
                df_pass4 = pd.read_excel('pass4.xlsx')
                df_pass4 = df_pass4.add_suffix('_after')
                df_pass4 = df_pass4.rename(columns={
                    'Governor ID_after': 'Governor ID',
                    'Governor Name_after': 'Governor Name'  # Основний нікнейм
                })
                # Переконайтеся, що Governor ID є рядковим типом для коректного об'єднання
                df_pass4['Governor ID'] = df_pass4['Governor ID'].astype(str).str.strip()
                logging.info("pass4.xlsx успішно завантажено.")
            except Exception as e:
                logging.exception(f"Помилка при завантаженні pass4.xlsx: {e}")
        else:
            logging.error(
                "Критична помилка: файл 'pass4.xlsx' не знайдено. Без нього неможливий розрахунок змін статистики!")
            return pd.DataFrame()

        # --- 4. Завантаження даних з required.xlsx (вимоги) ---
        df_requirements = pd.DataFrame()
        if os.path.exists('required.xlsx'):
            try:
                df_requirements = pd.read_excel('required.xlsx')
                # !!! ПЕРЕВІРТЕ НАЗВИ КОЛОНОК У ВАШОМУ 'required.xlsx' !!!
                # Змініть 'Required Kills Col Name' та 'Required Deaths Col Name', якщо вони відрізняються
                df_requirements = df_requirements.rename(columns={
                    'Governor ID': 'Governor ID',  # Ідентифікатор гравця
                    'Required Kills': 'Required Kills',  # Назва стовпця у ВАШОМУ required.xlsx для Kills
                    'Required Deaths': 'Required Deaths'  # Назва стовпця у ВАШОМУ required.xlsx для Deaths
                })
                # Переконайтеся, що Governor ID є рядковим типом для коректного об'єднання
                df_requirements['Governor ID'] = df_requirements['Governor ID'].astype(str).str.strip()
                df_requirements = df_requirements[['Governor ID', 'Required Kills', 'Required Deaths']]
                logging.info("required.xlsx успішно завантажено.")
            except Exception as e:
                logging.exception(f"Помилка при завантаженні required.xlsx: {e}")
        else:
            logging.warning("Файл 'required.xlsx' не знайдено. Вимоги для гравців будуть вважатися нульовими.")

        # --- 5. Об'єднання даних ---
        # *** ЗМІНА ТУТ: Ініціалізуємо final_df з усіма колонками df_pass4 ***
        # df_pass4 вже має суфікс '_after' і перейменовані 'Governor ID' та 'Governor Name'
        final_df = df_pass4.copy()
        logging.debug("final_df ініціалізовано з df_pass4.")

        # 5.1. Об'єднання з df_before_pass4
        # Використовуємо left merge, щоб зберегти всіх гравців з pass4.xlsx
        final_df = pd.merge(final_df, df_before_pass4, on='Governor ID', how='left')
        logging.info(f"Об'єднано з {len(df_before_pass4)} гравців з before_pass4.")

        # 5.2. Об'єднання з df_start_kvk (для Power_at_KVK_start)
        final_df = pd.merge(final_df, df_start_kvk, on='Governor ID', how='left')
        logging.info(f"Об'єднано з {len(df_start_kvk)} гравцями зі start_kvk (потужність до КВК).")

        # 5.3. Об'єднання з df_requirements (для Required Kills/Deaths)
        if not df_requirements.empty:  # Об'єднуємо тільки якщо df_requirements не порожній
            final_df = pd.merge(final_df, df_requirements, on='Governor ID', how='left')
            logging.info(f"Об'єднано з {len(df_requirements)} гравцями з required.xlsx (вимоги).")
        else:
            # Якщо required.xlsx не знайдено або порожній, додаємо стовпці з нулями
            final_df['Required Kills'] = 0
            final_df['Required Deaths'] = 0
            logging.warning("Вимоги не завантажені, стовпці 'Required Kills' та 'Required Deaths' встановлено на 0.")

        # --- 6. Обчислення змін та додаткових метрик ---
        def to_numeric_and_fill(series, fill_value=0):
            """Допоміжна функція для безпечного перетворення в число та заповнення NaN."""
            # Використовуємо .copy() щоб уникнути SettingWithCopyWarning, якщо Series є копією
            return pd.to_numeric(series.copy(), errors='coerce').fillna(fill_value)

        # Потужність: Power_at_KVK_start (з start_kvk) vs Power_after (з pass4)
        # Тепер Power_after має бути у final_df
        final_df['Power_after'] = to_numeric_and_fill(final_df['Power_after'])
        final_df['Power_at_KVK_start'] = to_numeric_and_fill(final_df['Power_at_KVK_start'])
        final_df['Power Change'] = final_df['Power_after'] - final_df['Power_at_KVK_start']

        # Kills Change (використовуємо before_pass4 та pass4)
        final_df['Kill Points_before'] = to_numeric_and_fill(final_df['Kill Points_before'])
        final_df['Kill Points_after'] = to_numeric_and_fill(final_df['Kill Points_after'])
        final_df['Kills Change'] = final_df['Kill Points_after'] - final_df['Kill Points_before']

        # Deaths Change (використовуємо before_pass4 та pass4)
        final_df['Deads_before'] = to_numeric_and_fill(final_df['Deads_before'])
        final_df['Deads_after'] = to_numeric_and_fill(final_df['Deads_after'])
        final_df['Deads Change'] = final_df['Deads_after'] - final_df['Deads_before']

        # Tier 4 Kills Change
        final_df['Tier 4 Kills_before'] = to_numeric_and_fill(final_df['Tier 4 Kills_before'])
        final_df['Tier 4 Kills_after'] = to_numeric_and_fill(final_df['Tier 4 Kills_after'])
        final_df['Tier 4 Kills Change'] = final_df['Tier 4 Kills_after'] - final_df['Tier 4 Kills_before']

        # Tier 5 Kills Change
        final_df['Tier 5 Kills_before'] = to_numeric_and_fill(final_df['Tier 5 Kills_before'])
        final_df['Tier 5 Kills_after'] = to_numeric_and_fill(final_df['Tier 5 Kills_after'])
        final_df['Tier 5 Kills Change'] = final_df['Tier 5 Kills_after'] - final_df['Tier 5 Kills_before']

        # DKP (формула) - обчислюється після всіх змін
        final_df['DKP'] = (
                (final_df['Deads Change'] * 15) +  # Зміна смертей
                (final_df['Tier 5 Kills Change'] * 10) +  # Зміна T5 вбивств
                (final_df['Tier 4 Kills Change'] * 4)  # Зміна T4 вбивств
        )
        final_df['DKP'] = to_numeric_and_fill(final_df['DKP'])  # Заповнюємо NaN нулями після обчислення

        # Required Kills/Deaths (Тепер з required.xlsx, вже об'єднані)
        # Переконайтеся, що вони числові; NaN тут перетворяться на 0, якщо не були заповнені під час merge
        final_df['Required Kills'] = to_numeric_and_fill(final_df['Required Kills'])
        final_df['Required Deaths'] = to_numeric_and_fill(final_df['Required Deaths'])

        # Обчислення Kills/Deaths Completion (%)
        final_df['Kills Completion (%)'] = final_df.apply(
            lambda row: ((row['Tier 4 Kills Change'] + row['Tier 5 Kills Change']) / row['Required Kills']) * 100 if row['Required Kills'] != 0 else 0,
            # 0, якщо вимоги 0
            axis=1
        )
        final_df['Deaths Completion (%)'] = final_df.apply(
            lambda row: (row['Deads Change'] / row['Required Deaths']) * 100 if row['Required Deaths'] != 0 else 0,
            # 0, якщо вимоги 0
            axis=1
        )

        # # Обмежуємо відсотки 100% ТІЛЬКИ ЯКЩО ВИМОГИ НЕ НУЛЬОВІ (закоментовано, щоб дозволити >100%)
        # final_df['Kills Completion (%)'] = final_df.apply(
        #     lambda row: min(row['Kills Completion (%)'], 100) if row['Required Kills'] != 0 else row['Kills Completion (%)'], axis=1
        # )
        # final_df['Deaths Completion (%)'] = final_df.apply(
        #     lambda row: min(row['Deaths Completion (%)'], 100) if row['Required Deaths'] != 0 else row['Deaths Completion (%)'], axis=1
        # )

        # Загальні Kills/Deaths (для player_stats)
        final_df['Total Kills'] = to_numeric_and_fill(final_df['Kill Points_after'])
        final_df['Total Deaths'] = to_numeric_and_fill(final_df['Deads_after'])

        # Ранг DKP
        final_df['Rank'] = final_df['DKP'].rank(ascending=False, method='min')
        final_df['Rank'] = to_numeric_and_fill(final_df['Rank'], fill_value=0).astype(int)  # Ранг має бути цілим

        # --- 7. Фінальна очистка та підготовка ---
        # Залишимо лише необхідні для виводу та розрахунків стовпці в `results.xlsx`
        final_columns = [
            'Governor ID', 'Governor Name', 'DKP', 'Rank',
            'Power_after', 'Power_at_KVK_start', 'Power Change',
            'Kill Points_before', 'Kill Points_after', 'Kills Change',
            'Deads_before', 'Deads_after', 'Deads Change',
            'Tier 4 Kills_before', 'Tier 4 Kills_after', 'Tier 4 Kills Change',
            'Tier 5 Kills_before', 'Tier 5 Kills_after', 'Tier 5 Kills Change',
            'Required Kills', 'Required Deaths',
            'Kills Completion (%)', 'Deaths Completion (%)',
            'Total Kills', 'Total Deaths'
        ]
        # Фільтруємо, щоб уникнути помилок, якщо колонка не існує в певних df
        final_columns = [col for col in final_columns if col in final_df.columns]
        final_df = final_df[final_columns]

        # Перетворення числових колонок на int, якщо вони цілі числа
        for col in final_df.columns:
            if pd.api.types.is_float_dtype(final_df[col]):
                # Перевіряємо, чи всі значення float є цілими числами
                if (final_df[col] == final_df[col].astype(int)).all():
                    final_df.loc[:, col] = final_df[col].astype(int)

        # Додаткова перевірка: перетворення ID на str перед збереженням, щоб уникнути форматування як числа
        final_df['Governor ID'] = final_df['Governor ID'].astype(str)

        final_df.to_excel(OUTPUT_FILE, index=False)
        logging.info(f"Оброблені дані успішно збережено у '{OUTPUT_FILE}'.")
        print(f"Results saved to '{OUTPUT_FILE}'")  # Вивід у консоль
        return final_df

    except Exception as e:
        logging.exception(f"Непередбачена помилка в calculate_stats: {e}")
        return pd.DataFrame()


# --- get_player_stats - ця функція залишається в calculate.py ---
# Вона вже повинна коректно брати дані з result_df, підготовленого calculate_stats
def get_player_stats(result_df, player_id):
    logging.debug(f"Виклик get_player_stats для ID: {player_id}")
    if result_df.empty:
        logging.warning("get_player_stats: result_df порожній.")
        return None

    # Перетворення Governor ID в result_df на str для коректного порівняння
    # Це важливо, якщо в Excel ID були числами, а ви шукаєте їх як рядки
    result_df['Governor ID'] = result_df['Governor ID'].astype(str).str.strip()
    player_id = str(player_id).strip()  # Переконайтеся, що вхідний player_id також рядок

    player_data = result_df[result_df['Governor ID'] == player_id]

    if player_data.empty:
        logging.info(f"get_player_stats: Гравець з ID {player_id} не знайдений.")
        return None

    player = player_data.iloc[0]

    # Використовуємо .get() з значеннями за замовчуванням
    governor_name = player.get('Governor Name', 'N/A')
    matchmaking_power = player.get('Power_at_KVK_start', 0)
    power_change = player.get('Power Change', 0)
    tier4_kills_change = player.get('Tier 4 Kills Change', 0)
    tier5_kills_change = player.get('Tier 5 Kills Change', 0)
    kills_change = player.get('Kills Change', 0)
    deads_change = player.get('Deads Change', 0)

    # Total Kills/Deaths тепер є окремими стовпцями
    total_kills = player.get('Total Kills', 0)
    total_deaths = player.get('Total Deaths', 0)

    required_kills = player.get('Required Kills', 0)
    required_deaths = player.get('Required Deaths', 0)

    # Ці відсотки вже обчислені в calculate_stats
    kills_completion = player.get('Kills Completion (%)', 0)
    deads_completion = player.get('Deaths Completion (%)', 0)

    dkp = player.get('DKP', 0)
    rank = int(player.get('Rank', 0))  # Переконайтеся, що ранг є цілим числом

    return {
        'governor_name': governor_name,
        'matchmaking_power': matchmaking_power,
        'power_change': power_change,
        'tier4_kills_change': tier4_kills_change,
        'tier5_kills_change': tier5_kills_change,
        'kills_change': kills_change,
        'deads_change': deads_change,
        'total_kills': total_kills,
        'total_deaths': total_deaths,
        'required_kills': required_kills,
        'required_deaths': required_deaths,
        'kills_completion': kills_completion,
        'deads_completion': deads_completion,
        'dkp': dkp,
        'rank': rank,
    }