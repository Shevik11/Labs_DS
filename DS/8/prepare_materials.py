import hashlib
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def main():
    build=json.loads((ROOT/'results/build_validation.json').read_text(encoding='utf-8'))
    verified=[]
    for candidate in (ROOT/'results').glob('local_*/validation.json'):
        value=json.loads(candidate.read_text(encoding='utf-8'))
        if value.get('status')=='passed':
            verified.append((candidate,value))
    path,validation=sorted(verified)[-1]
    folder=path.parent
    benchmark=json.loads((folder/'benchmark_comparison.json').read_text(encoding='utf-8'))
    answers=json.loads((folder/'query_results.json').read_text(encoding='utf-8'))
    rows=[]
    for key,value in benchmark.items():
        a,b=value['before'],value['after']
        rows.append(f"| {key} | {a['median_wall_ms']:.3f} | {b['median_wall_ms']:.3f} | {a['db_hits_sum']} | {b['db_hits_sum']} | {value['median_ratio_before_over_after']:.2f} |")
    daily=answers['07_daily_energy']['rows'][0]
    mae=answers['11_all_test_mae']['rows'][0]
    material=f'''# Матеріали для майбутнього звіту №8

Оформлений звіт №8 створено у DOCX і PDF. Нижче — карта джерел, фактичних результатів та їх перевірки.

## Предметна область

Індустрія: **Енергетика**. Домен: **Програмне забезпечення**. Задача: **Візуалізація**.
Тема з №1: програмний модуль візуалізації та аналізу електроспоживання.
У №8 збережено знання семантичної онтології №6 у property graph Neo4j.

## Джерела

- `inputs/lab6.owl`: 993 RDF-трійки, 37 класів, 31 object property, 34 datatype property, 26 індивідів.
- `inputs/lab6_inferred.owl`: попередньо отримані висновки HermiT №6, матеріалізовані під час проєкції.
- `inputs/hourly_clean.csv`: усі 34 085 повних годин №1.
- `inputs/test_predictions.csv`: усі 9 530 збережених тестових прогнозів №1.
- `inputs/metrics.json`: контрольні результати №1. Дані UCI одного домогосподарства Франції, CC BY 4.0.
- `inputs/ds_lab_8.pdf`: поточна умова.
- SHA-256 усіх вхідних файлів: `results/build_validation.json`.

## Фактично виконано

1. Визначено відображення класів, індивідів, властивостей, типів та успадкування: `MODEL_MAPPING.md`.
2. Побудовано JSON/CSV: **43 746 вузлів**, **199 287 зв’язків**.
3. Реально імпортовано граф у **Neo4j Community 5.26.32**, окремий портативний локальний сервер.
4. Перевірено повторний MERGE: **0** нових вузлів і **0** нових зв’язків.
5. Виконано 11 запитів; відповіді збережено у `{folder.relative_to(ROOT).as_posix()}/query_results.json`.
6. Перевірено індекси ONLINE; порівняно три складні сценарії до/після індексації.
7. Перевірено збіг відповідей до/після та відповідність контрольним обчисленням Python.
8. Виконано обидва браузерні імпорти у транзакціях із відкатом на локальному графі.
   Це перевірка виконуваності Cypher; новий порожній веб-Sandbox цим не перевірено.
9. Повні RDF-трійки відновлено в RDF-граф; ізоморфність вихідному OWL підтверджена.

Локальний запуск: **`{folder.relative_to(ROOT).as_posix()}`**.
Початок UTC: `{validation['started_at_utc']}`. Завершення UTC: `{validation['finished_at_utc']}`.
Для Києва у дату запуску застосовується UTC+3; назви папок навмисно мають UTC-час.
Python {validation['python']}; офіційний драйвер Neo4j {validation['driver']}.
Локальний сервер після перевірки зупинено; Sandbox не потребує його запуску.

## Контрольні значення

- Вузлів: **43 746**; зв’язків: **199 287**.
- Повний ряд має **{build['missing_hours_full_series']}** відсутніх годин у часовій сітці.
  Наявні спостереження представляють лише повні години, без заповнення пропусків.
- MAE на 9 530 прогнозах: **{mae['mae_kwh']:.15f} kWh**.
- MAE базового прогнозу незмінного навантаження: **{mae['persistence_mae_kwh']:.15f} kWh**.
- 09.09.2009: **{daily['hours']}** наявні години, сума **{daily['energy_kwh']:.6f} kWh**.
- Перший Random Forest прогноз: **1,9519405504171758 kWh**, факт **2,12 kWh**.
- Семантичний поріг: **1,5613 kWh**. Прогноз має тип HighConsumptionForecast;
  пов’язане подання — AttentionVisualization. Logistic Regression для прикладу має мітку **0**.

## Продуктивність: лише локальний запуск

Той самий повний граф і ті самі параметризовані запити. Для кожного сценарію —
3 прогріви та 10 звичайних повторів в обох умовах. Порядок сценаріїв чергується.
PROFILE виконувався окремо. Унікальний індекс ID існував в обох умовах;
порівнюється додавання пошукових range-індексів.

| Запит | Медіана до, ms | Медіана після, ms | DB Hits до | DB Hits після | Відношення медіан |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Для всіх трьох сценаріїв план змінився з NodeByLabelScan на NodeIndexSeek /
NodeIndexSeekByRange. Кожен повертає один агрегований рядок; різниця в роботі рушія
видима в DB Hits. Обсяг поверненої відповіді — у `*_samples.csv` як `json_utf8_bytes`.
Це розмір серіалізації, а не точні мережеві байти чи дисковий I/O.

Результат залежить від локального CPU, прогрітого кешу, обсягу даних і селективності відбору.
Порівнюються запити одного добового інтервалу на повному графі. Це не загальна гарантія
прискорення будь-якого запиту. Часи не можна видавати за вимірювання Sandbox.

## Карта доказів

| Вимога умови | Доказ |
|---|---|
| Структурування онтології | `MODEL_MAPPING.md`, `data/nodes.json`, `relationships.json` |
| Формати JSON/CSV | `data/*.json`, `data/*.csv` |
| Опис Cypher й автоматичний імпорт | `build_lab8.py`, `run_neo4j.py`, `cypher/`, `browser/` |
| Фактичний імпорт і кількості | папка локального запуску, `validation.json` |
| Базові та складні запити | `queries/*.cypher`, `queries/catalog.json`, `query_results.json` |
| Індекси | `cypher/10_indexes.cypher`, `indexes.json` |
| Ефективність | `before_samples.csv`, `after_samples.csv`, `benchmark_comparison.json` |
| Плани й обсяг роботи | `before_profiles.json`, `after_profiles.json` |
| Ідемпотентність | `validation.json` → `repeat_import` |
| Контроль результатів №1 | `validation.json` → `checks` |
| Перевірка браузерного Cypher / RDF | `results/browser_validation.json`, `browser_verify.log` |
| Схема моделі | `figures/property_graph.svg`, `.png`; пояснювальна схема, не скриншот |
| Вебпідключення й візуалізація | **Ще потрібні дії користувача: `SANDBOX_STEPS.md`** |

## Ще потрібно підтвердити у твоєму Sandbox

- Створення власного Blank Sandbox і успішне підключення.
- Запуск `Запустити_Sandbox.cmd` і нова папка `results/sandbox_.../` зі статусом passed.
- Реальні зображення графа, результатів, індексів та PROFILE у вебінтерфейсі.
- Скриншоти за переліком у `SANDBOX_STEPS.md`, папка `results/screenshots/`.

Ці GUI-дії локальним запуском не підтверджені. Готовий матеріал не містить вигаданих
скриншотів чи вимірювань Sandbox. Для браузерного компактного маршруту інші кількості:
159 вузлів, 404 зв’язки, 24 години та 4 прогнози. Їх не можна змішувати з повним імпортом.
'''
    review_file=ROOT/'SANDBOX_REVIEW.md'
    if review_file.exists():
        material=material.split('## Ще потрібно підтвердити у твоєму Sandbox')[0]
        material=material.replace('| Вебпідключення й візуалізація | **Ще потрібні дії користувача: `SANDBOX_STEPS.md`** |', '| Вебпідключення й візуалізація | **Підтверджено: `SANDBOX_REVIEW.md`, `results/screenshots/`** |')
        material+='## Виконання у Sandbox підтверджено\n\nНаступний розділ містить фактичні віддалені результати; таблиця вище стосується лише локального запуску.\n\n'+review_file.read_text(encoding='utf-8')
    (ROOT/'REPORT_MATERIALS.md').write_text(material,encoding='utf-8')
    boxes=[('Dataset',70,130,'Набір годинних даних'),('TimeSeries',440,130,'Часовий ряд'),
           ('ConsumptionObject',840,130,'Домогосподарство'),('ForecastResult',70,360,'Прогноз із ЛР1'),
           ('Measurement',440,360,'Енергія, kWh'),('Meter',840,360,'Канал обліку'),
           ('AnalyticalModel',70,580,'Random Forest'),('Unit',840,580,'Кіловат-година')]
    links=[(290,175,440,175,'CONTAINS_SERIES',365,155),
           (660,175,840,175,'SERIES_OF',750,155),
           (550,220,550,360,'HAS_MEASUREMENT',430,295),
           (290,405,440,405,'COMPARED_WITH',365,387),
           (660,405,840,405,'RECORDED_BY',750,387),
           (180,450,180,580,'GENERATED_BY',260,520),
           (660,450,840,580,'HAS_UNIT',780,513),
           (660,360,840,220,'MEASUREMENT_OF',780,290)]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">',
         '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#334155"/></marker></defs>',
         '<rect width="1200" height="800" fill="white"/>',
         '<g font-family="Arial" fill="#000000">',
         '<text x="50" y="48" font-size="27" font-weight="bold">Модель збереження енергетичних знань</text>',
         '<text x="50" y="80" font-size="17">Пояснювальна схема структури. Джерела: ЛР1 та семантична онтологія ЛР6.</text>']
    for x1,y1,x2,y2,label,lx,ly in links:
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#334155" stroke-width="2"/>')
        ux,uy=x2-x1,y2-y1
        norm=math.hypot(ux,uy)
        ux,uy=ux/norm,uy/norm
        points=[(x2,y2),(x2-12*ux-5*uy,y2-12*uy+5*ux),(x2-12*ux+5*uy,y2-12*uy-5*ux)]
        vertices=' '.join(str(x)+','+str(y) for x,y in points)
        svg.append('<polygon points="'+vertices+'" fill="#334155"/>')
        width=len(label)*8+14
        svg.append(f'<rect x="{lx-width/2}" y="{ly-16}" width="{width}" height="24" fill="white"/>')
        svg.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-size="13">{label}</text>')
    for title,x,y,description in boxes:
        svg.append(f'<rect x="{x}" y="{y}" width="220" height="90" rx="9" fill="#f1f5f9" stroke="#475569" stroke-width="1.5"/>')
        svg.append(f'<text x="{x+110}" y="{y+33}" text-anchor="middle" font-size="18" font-weight="bold">{html.escape(title)}</text>')
        svg.append(f'<text x="{x+110}" y="{y+62}" text-anchor="middle" font-size="15">{html.escape(description)}</text>')
    svg.extend(['<text x="50" y="735" font-size="18">Повний граф: 43 746 вузлів, 199 287 зв’язків. Час зберігається як localdatetime.</text>',
                '<text x="50" y="767" font-size="16">Класи, TYPE_OF та обмеження схеми показано окремо в Neo4j. Це не скриншот інтерфейсу.</text>',
                '</g></svg>'])
    (ROOT/'figures/property_graph.svg').write_text('\n'.join(svg),encoding='utf-8')
    print('Prepared REPORT_MATERIALS.md and figures/property_graph.svg')

if __name__=='__main__':
    main()
