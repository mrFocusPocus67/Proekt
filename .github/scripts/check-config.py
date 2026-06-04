import yaml
import sys
import json
import tomllib
from pathlib import Path
import configparser

def load_rules():
    with open('rules.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [r for r in data['rules'] if r.get('enabled', True)]

def parse_file(file_path):
    ext = file_path.suffix.lower()
    with open(file_path, 'r') as f:
        content = f.read()
    
    if ext in ['.yaml', '.yml']:
        return yaml.safe_load(content), content
    elif ext == '.json':
        return json.loads(content), content
    elif ext == '.toml':
        return tomllib.loads(content), content
    elif ext in ['.conf', '.ini']:
        config = configparser.ConfigParser()
        config.read_string(content)
        return config, content
    else:
        return None, content

def check_config(file_path, rules):
    errors = []
    
    try:
        config, content = parse_file(file_path)
        if config is None and file_path.suffix.lower() not in ['.yaml', '.yml', '.json', '.toml', '.conf', '.ini']:
            return errors
        
        for rule in rules:
            if rule['pattern'] in content:
                errors.append({
                    'rule': rule['name'],
                    'message': rule['message'],
                    'severity': rule['severity']
                })
        
    except Exception as e:
        errors.append({
            'rule': 'parse_error',
            'message': f'Ошибка парсинга файла: {e}',
            'severity': 'error'
        })
    
    return errors

def main():
    rules = load_rules()
    print("Запускаю проверку конфигураций...")
    print("-" * 50)
    
    all_results = []
    extensions = ['*.yaml', '*.yml', '*.json', '*.toml', '*.conf', '*.ini']
    
    for ext in extensions:
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
