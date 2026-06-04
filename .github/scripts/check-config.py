import yaml
import sys
import json
from pathlib import Path
import configparser
from datetime import datetime
import sqlite3
import os

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
    else:
        return None, content

def check_config(file_path, rules):
    errors = []
    try:
        _, content = parse_file(file_path)
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
            'message': str(e),
            'severity': 'error'
        })
    return errors

def init_db():
    conn = sqlite3.connect('scans.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT,
            total_errors INTEGER,
            total_warnings INTEGER,
            passed BOOLEAN
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            file_path TEXT,
            rule_name TEXT,
            message TEXT,
            severity TEXT
        )
    ''')
    conn.close()

def save_to_db(all_results, errors_count, warnings_count, passed):
    conn = sqlite3.connect('scans.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO scans (scan_date, total_errors, total_warnings, passed) VALUES (?,?,?,?)',
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), errors_count, warnings_count, passed))
    scan_id = cur.lastrowid
    for item in all_results:
        cur.execute('INSERT INTO scan_results (scan_id, file_path, rule_name, message, severity) VALUES (?,?,?,?,?)',
                    (scan_id, item['file'], item['rule'], item['message'], item['severity']))
    conn.commit()
    conn.close()

def show_stats():
    if not os.path.exists('scans.db'):
        print("\nСтатистика пока отсутствует")
        return
    
    conn = sqlite3.connect('scans.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM scans')
    total_scans = cur.fetchone()[0]
    cur.execute('SELECT SUM(total_errors) FROM scans')
    total_errors = cur.fetchone()[0] or 0
    cur.execute('SELECT SUM(total_warnings) FROM scans')
    total_warnings = cur.fetchone()[0] or 0
    cur.execute('SELECT AVG(total_errors) FROM scans')
    avg_errors = cur.fetchone()[0] or 0
    cur.execute('''
        SELECT rule_name, COUNT(*) FROM scan_results 
        WHERE severity = 'error' 
        GROUP BY rule_name 
        ORDER BY COUNT(*) DESC 
        LIMIT 5
    ''')
    top_rules = cur.fetchall()
    conn.close()
    
    print("\nСТАТИСТИКА ПО ВСЕМ ПРОВЕРКАМ")
    print(f"Всего проверок: {total_scans}")
    print(f"Всего ошибок: {total_errors}")
    print(f"Всего предупреждений: {total_warnings}")
    print(f"Среднее ошибок на проверку: {avg_errors:.1f}")
    if top_rules:
        print("\nСамые частые ошибки:")
        for rule, count in top_rules:
            print(f"   • {rule}: {count} раз")

def generate_html_report(all_results, errors_count, warnings_count):
    rows = ''
    for item in all_results:
        rows += f'''<tr>
            <td>{item['file']}</td>
            <td>{item['rule']}</td>
            <td>{item['message']}</td>
            <td>{item['severity']}</td>
        </tr>'''
    
    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Отчет проверки конфигураций</title>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .error {{ color: red; }}
    .warning {{ color: orange; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
    <h1>Отчет проверки конфигураций</h1>
    <p><strong>Дата:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <p><strong>Ошибок:</strong> <span class="error">{errors_count}</span></p>
    <p><strong>Предупреждений:</strong> <span class="warning">{warnings_count}</span></p>
    <table>
        <tr><th>Файл</th><th>Правило</th><th>Сообщение</th><th>Severity</th></tr>
        {rows}
    </table>
</body>
</html>'''
    
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("\nHTML отчет сохранен в report.html")

def main():
    init_db()
    rules = load_rules()
    print("Запускаю проверку конфигураций...")
    
    all_results = []
    extensions = ['*.yaml', '*.yml', '*.json']
    
    for ext in extensions:
        for file_path in Path('.').rglob(ext):
            if '.github' in str(file_path) or 'rules.json' in str(file_path):
                continue
            print(f"Проверяю: {file_path}")
            errors = check_config(file_path, rules)
            for error in errors:
                all_results.append({'file': str(file_path), **error})
    
    if all_results:
        print("\nНАЙДЕНЫ ПРОБЛЕМЫ В КОНФИГАХ")
        errors_only = [r for r in all_results if r['severity'] == 'error']
        warnings_only = [r for r in all_results if r['severity'] == 'warning']
        
        save_to_db(all_results, len(errors_only), len(warnings_only), len(errors_only)==0)
        generate_html_report(all_results, len(errors_only), len(warnings_only))
        show_stats()
        
        if errors_only:
            print("\nКРИТИЧНЫЕ ОШИБКИ:")
            for r in errors_only:
                print(f"   • {r['file']}: {r['message']}")
        if warnings_only:
            print("\nПРЕДУПРЕЖДЕНИЯ:")
            for r in warnings_only:
                print(f"   • {r['file']}: {r['message']}")
        
        print(f"\nИТОГО: {len(errors_only)} ошибок, {len(warnings_only)} предупреждений")
        sys.exit(1 if errors_only else 0)
    else:
        print("\nВсе конфиги в порядке!")
        sys.exit(0)

if __name__ == "__main__":
    main()
