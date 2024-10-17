import pandas as pd

# Допустим, у нас есть DataFrame с данными
data = {
    'абонент1': [1, 2, 3, 4],
    'абонент2': [5, 6, 7, 8],
    'группа_абонента1': ['А', 'Б', None, 'В'],
    'группа_абонента2': [None, 'А', 'Б', 'В'],
    'фио_абонента1': ['Иванов', 'Петров', None, 'Сидоров'],
    'фио_абонента2': [None, 'Козлов', 'Смирнов', 'Иванова']
}

df = pd.DataFrame(data)

# Известные группы
known_groups = ['А', 'Б', 'В']

# Шаг 1: Выделить абонентов с неизвестной группой
unknown_group_contacts = df[(df['группа_абонента1'].isna() | df['группа_абонента2'].isna())]

# Шаг 2: Подсчитать соединения по группам для абонентов с неизвестной группой
unknown_stats = {}

for index, row in unknown_group_contacts.iterrows():
    if pd.isna(row['группа_абонента1']):
        unknown_abonent = row['абонент1']
        known_group = row['группа_абонента2']
    else:
        unknown_abonent = row['абонент2']
        known_group = row['группа_абонента1']
    
    if known_group in known_groups:
        if unknown_abonent not in unknown_stats:
            unknown_stats[unknown_abonent] = {group: 0 for group in known_groups}
        unknown_stats[unknown_abonent][known_group] += 1

# Шаг 3: Собрать список ФИО абонентов, с которыми связывались неизвестные абоненты, по группам
fio_by_group = {}

for index, row in unknown_group_contacts.iterrows():
    if pd.isna(row['группа_абонента1']):
        unknown_abonent = row['абонент1']
        known_group = row['группа_абонента2']
        known_fio = row['фио_абонента2']
    else:
        unknown_abonent = row['абонент2']
        known_group = row['группа_абонента1']
        known_fio = row['фио_абонента1']
    
    if known_group in known_groups:
        if unknown_abonent not in fio_by_group:
            fio_by_group[unknown_abonent] = {group: [] for group in known_groups}
        fio_by_group[unknown_abonent][known_group].append(known_fio)

# Вывод результатов
print("Статистика соединений неизвестных абонентов по группам:")
for abonent, stats in unknown_stats.items():
    print(f"Абонент {abonent}: {stats}")

print("\nСписок ФИО абонентов, с которыми связывались неизвестные абоненты по группам:")
for abonent, fio_lists in fio_by_group.items():
    print(f"Абонент {abonent}:")
    for group, fio_list in fio_lists.items():
        print(f"  Группа {group}: {fio_list}")
