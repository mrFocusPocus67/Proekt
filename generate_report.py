import sqlite3
from datetime import datetime

def generate_full_report():
    conn = sqlite3.connect('scans.db')
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM scans')
    total_scans = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(total_errors) FROM scans')
    total_errors = cursor.fetchone()[0] or 0

    cursor.execute('SELECT SUM(total_warnings) FROM scans')
    total_warnings = cursor.fetchone()[0] or 0

    cursor.execute('SELECT AVG(total_errors) FROM scans')
    avg_errors = cursor.fetchone()[0] or 0

    cursor.execute('''
        SELECT rule_name, COUNT(*) FROM scan_results 
        WHERE severity = 'error' 
        GROUP BY rule_name 
        ORDER BY COUNT(*) DESC 
        LIMIT 5
    ''')
    top_errors = cursor.fetchall()

    cursor.execute('SELECT id, scan_date, total_errors, total_warnings, passed FROM scans ORDER BY id DESC LIMIT 20')
    scans = cursor.fetchall()

    conn.close()

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Сводный отчет по всем проверкам</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .error {{ color: red; font-weight: bold; }}
        .warning {{ color: orange; }}
        .passed {{ color: green; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .summary {{ background-color: #f9f9f9; padding: 10px; margin-top: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Сводный отчет по всем проверкам конфигураций</h1>
    
    <div class="summary">
        <h2>Общая статистика</h2>
        <p><strong>Дата отчета:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Всего проверок:</strong> {total_scans}</p>
        <p><strong>Всего ошибок:</strong> <span class="error">{total_errors}</span></p>
        <p><strong>Всего предупреждений:</strong> <span class="warning">{total_warnings}</span></p>
        <p><strong>Среднее ошибок на проверку:</strong> {avg_errors:.1f}</p>
    </div>

    <h2>Самые частые ошибки</h2>
    <ul>
'''
    for rule, count in top_errors:
        html += f'<li><span class="error">{rule}</span> — {count} раз</li>'
    
    if not top_errors:
        html += '<li>Ошибок не обнаружено</li>'
    
    html += '''    </ul>

    <h2>Последние 20 проверок</h2>
    <table>
        <tr><th>ID</th><th>Дата</th><th>Ошибки</th><th>Предупреждения</th><th>Результат</th></tr>
'''
    for scan_id, date, err, warn, passed in scans:
        result = '✅ Пройдено' if passed else '❌ Ошибки'
        result_class = 'passed' if passed else 'error'
        html += f'''<tr>
            <td>{scan_id}</td>
            <td>{date}</td>
            <td class="error">{err}</td>
            <td class="warning">{warn}</td>
            <td class="{result_class}">{result}</td>
        </tr>'''
    
    html += '''
    </table>
    <p><em>Сгенерировано системой проверки конфигураций</em></p>
</body>
</html>'''
    
    with open('report_full.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Сводный отчет сохранен в report_full.html")
    print(f"Всего проверок: {total_scans}, ошибок: {total_errors}, предупреждений: {total_warnings}")

if __name__ == '__main__':
    generate_full_report()
