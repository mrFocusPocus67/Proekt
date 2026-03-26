#!/usr/bin/env python3
# Скрипт для проверки конфигов перед деплоем
# Запускается автоматически в GitHub Actions при Pull Request

import yaml
import sys
import json
from pathlib import Path

def check_config(file_path):
    """
    Проверяет один конфиг-файл на типичные ошибки
    Возвращает список найденных проблем
    """
    errors = []
    warnings = []
    
    try:
        # Пробуем прочитать файл как YAML
        with open(file_path, 'r') as f:
            content = f.read()
            config = yaml.safe_load(content)
        
        # Правило 1: Не должно быть включенного debug режима
        # В проде debug_mode: true может выдать чувствительные данные или тормозить
        if 'debug' in str(config).lower() or 'debug_mode' in str(config).lower():
            errors.append({
                'rule': 'debug_mode',
                'message': 'Найден debug режим — в проде должно быть выключено',
                'severity': 'warning'  # Пока предупреждение, но может стать ошибкой
            })
        
        # Правило 2: Проверяем на тупые пароли
        # Люди часто забывают сменить дефолтные пароли
        if '123456' in str(config) or 'password' in str(config).lower():
            errors.append({
                'rule': 'simple_password',
                'message': 'Найден простой пароль — используйте сложные или переменные окружения',
                'severity': 'error'
            })
        
        # Правило 3: Порты
        # Порт 80 без HTTPS
        if 'port: 80' in content:
            errors.append({
                'rule': 'port_80',
                'message': 'Используется порт 80 (лучше 443 с HTTPS или другой нестандартный порт)',
                'severity': 'warning'
            })
        
        # Правило 4: Запуск от рута
        if 'user: root' in content:
            errors.append({
                'rule': 'root_user',
                'message': 'Запуск от root - опасно! Создайте отдельного пользователя',
                'severity': 'error'
            })
        
        # Правило 5: Проверяем на пустые значения
        # Частая ошибка: забыли заполнить обязательное поле
        if '""' in content or "''" in content:
            errors.append({
                'rule': 'empty_values',
                'message': 'Найдены пустые строки — возможно, забыли заполнить параметр',
                'severity': 'warning'
            })
        
        # Правило 6: Смотрим на отрицательные числа
        # В конфигах обычно не бывает отрицательных значений
        if ':-' in content or '= -' in content:
            errors.append({
                'rule': 'negative_values',
                'message': 'Найдены отрицательные числа — уверены, что так надо?',
                'severity': 'warning'
            })
        
    except yaml.YAMLError as e:
        # Файл кривой — даже не распарсился
        errors.append({
            'rule': 'yaml_syntax',
            'message': f'Ошибка в YAML синтаксисе: {e}',
            'severity': 'error'  # Синтаксис сломан — чинить обязательно
        })
    except Exception as e:
        # Всякие другие ошибки (доступ к файлу, кодировка и т.д.)
        errors.append({
            'rule': 'file_read',
            'message': f'Не могу прочитать файл: {e}',
            'severity': 'error'
        })
    
    return errors

def main():
    """Главная функция — ищем файлы и проверяем их"""
    print("🔍 Запускаю проверку конфигураций...")
    print("-" * 50)
    
    all_results = []
    
    # Ищем все YAML файлы в проекте (самые частые конфиги)
    for ext in ['*.yaml', '*.yml']:
        for file_path in Path('.').rglob(ext):
            # Пропускаем служебные папки GitHub
            if '.github' in str(file_path):
                continue
                
            print(f"📄 Проверяю: {file_path}")
            errors = check_config(file_path)
            
            for error in errors:
                all_results.append({
                    'file': str(file_path),
                    **error
                })
    
    if all_results:
        print("\n" + "=" * 60)
        print("❌  НАЙДЕНЫ ПРОБЛЕМЫ В КОНФИГАХ")
        print("=" * 60)
        
        # Разделяем ошибки и предупреждения
        errors_only = [r for r in all_results if r['severity'] == 'error']
        warnings_only = [r for r in all_results if r['severity'] == 'warning']
        
        # Сначала показываем критичные ошибки (красные)
        if errors_only:
            print("\n🔴 КРИТИЧНЫЕ ОШИБКИ (надо исправить обязательно):")
            for result in errors_only:
                print(f"   • {result['file']}: {result['message']}")
        
        # Потом предупреждения (желтые)
        if warnings_only:
            print("\n🟡 ПРЕДУПРЕЖДЕНИЯ (стоит проверить):")
            for result in warnings_only:
                print(f"   • {result['file']}: {result['message']}")
        
        print("\n" + "=" * 60)
        print(f"📊 ИТОГО: {len(errors_only)} ошибок, {len(warnings_only)} предупреждений")
        print("=" * 60)
        
        # Если есть критичные ошибки — останавливаем CI/CD
        if errors_only:
            print("\n❌ Деплой остановлен из-за критичных ошибок в конфигах")
            sys.exit(1)
        else:
            print("\n⚠️  Есть предупреждения, но деплой разрешен")
            sys.exit(0)
    else:
        print("\n✅ Все конфиги в порядке! Можно деплоить")
        sys.exit(0)

if __name__ == "__main__":
    main()
