import yaml
import sys
import json
from pathlib import Path

def load_rules():
    with open('rules.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [r for r in data['rules'] if r.get('enabled', True)]

def check_config(file_path, rules):
    errors = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            config = yaml.safe_load(content)
        
        for rule in rules:
            pattern = rule['pattern']
            if pattern in content:
                item = {
                    'rule': rule['name'],
                    'message': rule['message'],
                    'severity': rule['severity']
                }
                errors.append(item)
        
    except yaml.YAMLError as e:
        errors.append({
            'rule': 'yaml_syntax',
            'message': f'Ошибка в YAML синтаксисе: {e}',
            'severity': 'error'
        })
    except Exception as e:
        errors.append({
            'rule': 'file_read',
            'message': f'Не могу прочитать файл: {e}',
            'severity': 'error'
        })
    
    return errors

def main():
    rules = load_rules()
    print("Запускаю проверку конфигураций...")
    print("-" * 50)
    
    all_results = []
    
    for ext in ['*.yaml', '*.yml']:
        for file_path in Path('.').rglob(ext):
            if '.github' in str(file_path):
                continue
                
            print(f"Проверяю: {file_path}")
            errors = check_config(file_path, rules)
            
            for error in errors:
                all_results.append({
                    'file': str(file_path),
                    **error
                })
    
    if all_results:
        print("\n" + "=" * 60)
        print("НАЙДЕНЫ ПРОБЛЕМЫ В КОНФИГАХ")
        print("=" * 60)
        
        errors_only = [r for r in all_results if r['severity'] == 'error']
        warnings_only = [r for r in all_results if r['severity'] == 'warning']
        
        if errors_only:
            print("\nКРИТИЧНЫЕ ОШИБКИ (надо исправить обязательно):")
            for result in errors_only:
                print(f"   • {result['file']}: {result['message']}")
        
        if warnings_only:
            print("\nПРЕДУПРЕЖДЕНИЯ (стоит проверить):")
            for result in warnings_only:
                print(f"   • {result['file']}: {result['message']}")
        
        print("\n" + "=" * 60)
        print(f"ИТОГО: {len(errors_only)} ошибок, {len(warnings_only)} предупреждений")
        print("=" * 60)
        
        if errors_only:
            print("\nДеплой остановлен из-за критичных ошибок в конфигах")
            sys.exit(1)
        else:
            print("\nЕсть предупреждения, но деплой разрешен")
            sys.exit(0)
    else:
        print("\nВсе конфиги в порядке! Можно деплоить")
        sys.exit(0)

if __name__ == "__main__":
    main()
