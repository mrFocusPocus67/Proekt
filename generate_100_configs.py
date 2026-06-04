import random
import yaml

errors_configs = []

for i in range(100):
    config = {
        'server': {
            'debug_mode': random.choice([True, True, True, False]),
            'port': random.choice([80, 80, 80, 443, 8080]),
            'workers': random.choice([-1, 0, 1, 2, 4, 8])
        },
        'database': {
            'password': random.choice(['123456', 'password', 'admin', 'qwerty', '${DB_PASS}']),
            'ssl': random.choice([True, False]),
            'timeout': random.choice([-5, 0, 30, 60])
        }
    }
    
    # Добавляем гарантированные ошибки для части файлов
    if i < 70:
        config['server']['debug_mode'] = True
    if i < 60:
        config['server']['port'] = 80
    if i < 80:
        config['database']['password'] = '123456'
    if i < 40:
        config['database']['ssl'] = False
    if i < 30:
        config['server']['workers'] = -1
    
    filename = f'test_error_{i:03d}.yaml'
    with open(filename, 'w') as f:
        yaml.dump(config, f)
    errors_configs.append(filename)

print(f"Создано {len(errors_configs)} тестовых конфигов с ошибками")
