import pandas as pd
from collections import defaultdict

# Пример данных
data = {
    'date': ['2024-01-01 06:55:11', '2024-01-02 07:00:00', '2024-01-03 08:00:00', 
             '2024-01-01 09:00:00', '2024-01-02 10:00:00'],
    'tlf_call': ['1234567890', '1234567890', '1234567890', '0987654321', '0987654321'],
    'tlf_to': ['0987654321', '1234567890', '1111111111', '1234567890', '2222222222'],
    'fio_call': ['Иванов И.И.', 'Иванов И.И.', 'Иванов И.И.', 'Петров П.П.', 'Петров П.П.'],
    'fio_to': ['Петров П.П.', 'Иванов И.И.', 'Сидоров С.С.', 'Иванов И.И.', 'Сидоров С.С.'],
    'group_call': [None, None, None, 'Group A', 'Group B'],
    'group_to': ['Group A', None, 'Group C', None, 'Group C']
}

# Создаем DataFrame
df = pd.DataFrame(data)

# Преобразуем столбец с датами в формат datetime
df['date'] = pd.to_datetime(df['date'])

# Фильтруем абонентов с неизвестной группой
unknown_group_calls = df[df['group_call'].isnull() | df['group_to'].isnull()]

# Словари для агрегации
result = defaultdict(lambda: {
    'fio_abonents_agg': defaultdict(int),
    'group_abonents_agg': defaultdict(int),
    'connect_dates': defaultdict(lambda: {'date_first_connect': None, 'date_last_connect': None})
})

# Обрабатываем данные
for _, row in unknown_group_calls.iterrows():
    tlf_new = row['tlf_call']
    date = row['date']
    
    # Если у tlf_call есть группа, используем tlf_to как известный номер
    if row['group_call'] is not None:
        tlf_know = row['tlf_to']
        fio_to = row['fio_to']
        group_to = row['group_to']
        
        # Обновляем агрегацию ФИО
        result[tlf_new]['fio_abonents_agg'][fio_to] += 1
        
        # Обновляем агрегацию групп
        if group_to:
            result[tlf_new]['group_abonents_agg'][group_to] += 1
        
        # Обновляем даты соединений для каждой пары
        pair_key = (tlf_new, tlf_know)
        if result[tlf_new]['connect_dates'][pair_key]['date_first_connect'] is None or date < result[tlf_new]['connect_dates'][pair_key]['date_first_connect']:
            result[tlf_new]['connect_dates'][pair_key]['date_first_connect'] = date
        if result[tlf_new]['connect_dates'][pair_key]['date_last_connect'] is None or date > result[tlf_new]['connect_dates'][pair_key]['date_last_connect']:
            result[tlf_new]['connect_dates'][pair_key]['date_last_connect'] = date

    # Если у tlf_to есть группа, используем tlf_call как известный номер
    elif row['group_to'] is not None:
        tlf_know = row['tlf_call']
        fio_to = row['fio_call']
        group_call = row['group_call']
        
        # Обновляем агрегацию ФИО
        result[tlf_new]['fio_abonents_agg'][fio_to] += 1
        
        # Обновляем агрегацию групп
        if group_call:
            result[tlf_new]['group_abonents_agg'][group_call] += 1
        
        # Обновляем даты соединений для каждой пары
        pair_key = (tlf_know, tlf_new)
        if result[tlf_new]['connect_dates'][pair_key]['date_first_connect'] is None or date < result[tlf_new]['connect_dates'][pair_key]['date_first_connect']:
            result[tlf_new]['connect_dates'][pair_key]['date_first_connect'] = date
        if result[tlf_new]['connect_dates'][pair_key]['date_last_connect'] is None or date > result[tlf_new]['connect_dates'][pair_key]['date_last_connect']:
            result[tlf_new]['connect_dates'][pair_key]['date_last_connect'] = date

# Форматируем результат
formatted_result = []
for tlf_new, agg_data in result.items():
    fio_abonents_agg = ', '.join([f"{fio}: {count}" for fio, count in agg_data['fio_abonents_agg'].items()])
    group_abonents_agg = ', '.join([f"{group}: {count}" for group, count in agg_data['group_abonents_agg'].items()])
    
    # Собираем даты соединений для каждой пары
    connect_dates = []
    for (caller, receiver), dates in agg_data['connect_dates'].items():
        connect_dates.append({
            'pair': f"{caller} - {receiver}",
            'date_first_connect': dates['date_first_connect'],
            'date_last_connect': dates['date_last_connect']
        })
    
    formatted_result.append({
        'tlf_new': tlf_new,
        'fio_abonents_agg': fio_abonents_agg,
        'group_abonents_agg': group_abonents_agg,
        'connect_dates': connect_dates
    })

# Преобразуем в DataFrame для удобного отображения
result_df = pd.DataFrame(formatted_result)

# Выводим результат
for entry in result_df.itertuples(index=False):
    print(f"Телефон: {entry.tlf_new}")
    print(f"ФИО абонентов: {entry.fio_abonents_agg}")
    print(f"Группы абонентов: {entry.group_abonents_agg}")
    for connect in entry.connect_dates:
        print(f"Связь: {connect['pair']}, Дата первого соединения: {connect['date_first_connect']}, Дата последнего соединения: {connect['date_last_connect']}")
    print()

