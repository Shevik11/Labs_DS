import ast
import json
import textwrap
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STEM = 'ЛР10_Шевчук_ФЕІм-13с'


def architecture():
    image = Image.new('RGB', (1800, 960), 'white')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/times.ttf', 36)
    boxes = [(60,70,540,260), (660,70,1140,260), (1260,70,1740,260),
             (1260,480,1740,700), (660,480,1140,700), (60,480,540,700)]
    labels = ['Запит користувача\nЛіміт і перевірка атак', 'Словник понять\nskos:altLabel', 'SPARQL\nФрагмент онтології',
              'Шаблон підказки\nQwen3-0.6B', 'JSON і класи\nДо двох виправлень', 'Відповідь\nабо відмова']
    for box, label in zip(boxes, labels):
        draw.rectangle(box, outline='black', width=3)
        draw.multiline_text(((box[0]+box[2])/2,(box[1]+box[3])/2), label, font=font, anchor='mm', align='center', fill='black', spacing=12)
    def arrow(start, end):
        draw.line([start,end], fill='black', width=4)
        x,y=end
        if end[0] > start[0]:
            triangle=[(x,y),(x-18,y-10),(x-18,y+10)]
        elif end[0] < start[0]:
            triangle=[(x,y),(x+18,y-10),(x+18,y+10)]
        else:
            triangle=[(x,y),(x-10,y-18),(x+10,y-18)]
        draw.polygon(triangle, fill='black')
    arrow((540,165),(660,165)); arrow((1140,165),(1260,165))
    arrow((1500,260),(1500,480)); arrow((1260,590),(1140,590)); arrow((660,590),(540,590))
    draw.line([(900,700),(900,820),(1500,820),(1500,700)], fill='black', width=3)
    draw.polygon([(1500,700),(1490,718),(1510,718)], fill='black')
    draw.text((1200,870),'Помилка → зауваження → повтор',font=font,anchor='mm',fill='black')
    path = ROOT/'work/architecture.png'
    path.parent.mkdir(exist_ok=True)
    image.save(path)
    return path


def load(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def build():
    runtime = load('results/runtime.json')
    dev = load('results/dev_metrics.json')
    test = load('results/test_metrics.json')
    attacks = load('results/attack_metrics.json')
    selected = load('results/selection.json')['version']
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(2), Cm(1)
    sec.top_margin = sec.bottom_margin = Cm(2)
    sec.header_distance = Cm(.7)
    sec.different_first_page_header_footer = True
    for name in ['Normal', 'Title', 'Heading 1', 'Heading 2', 'Caption']:
        style = doc.styles[name]
        style.font.name = 'Times New Roman'
        style.font.size = Pt(12 if name == 'Caption' else 14)
        style.font.color.rgb = RGBColor(0, 0, 0)
        fonts = style.element.get_or_add_rPr().rFonts
        for key in list(fonts.attrib):
            if key.endswith('Theme'):
                del fonts.attrib[key]
        for key in ['ascii', 'hAnsi', 'eastAsia', 'cs']:
            fonts.set(qn('w:'+key), 'Times New Roman')
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.5
        style.paragraph_format.first_line_indent = Cm(1.25 if name == 'Normal' else 0)
        if name.startswith('Heading'):
            style.font.bold = True
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(8)
            style.paragraph_format.space_after = Pt(5)
    doc.styles['Heading 1'].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    header._p.append(field)
    doc.core_properties.author = 'Шевчук Максим Вікторович'
    doc.core_properties.title = 'Лабораторна робота 10 Онтологічні підказки для SLM'

    def para(text, style=None):
        p = doc.add_paragraph(text, style)
        if style is None:
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return p

    def heading(text):
        return doc.add_heading(text, 1)

    def title(text, before=0, after=0, size=14, bold=False, right=False):
        p = doc.add_paragraph(style='Title' if text == 'Звіт' else 'Normal')
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if right else WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.line_spacing = 1
        pf.space_before, pf.space_after = Pt(before), Pt(after)
        r = p.add_run(text)
        r.font.size, r.bold = Pt(size), bold
        return p

    def table(caption, headers, rows, widths=None):
        p = para(caption)
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.keep_with_next = True
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = 'Table Grid'
        t.autofit = False
        widths = widths or [18/len(headers)]*len(headers)
        for column, width in zip(t.columns, widths):
            column.width = Cm(width)
        for cell, text in zip(t.rows[0].cells, headers):
            cell.text = str(text)
            for r in cell.paragraphs[0].runs:
                r.bold = True
        repeat = OxmlElement('w:tblHeader')
        t.rows[0]._tr.get_or_add_trPr().append(repeat)
        for values in rows:
            for cell, value in zip(t.add_row().cells, values):
                cell.text = str(value)
        for row_index, row in enumerate(t.rows):
            cant_split = OxmlElement('w:cantSplit')
            row._tr.get_or_add_trPr().append(cant_split)
            for i, cell in enumerate(row.cells):
                if widths:
                    cell.width = Cm(widths[i])
                for p in cell.paragraphs:
                    p.paragraph_format.first_line_indent = Cm(0)
                    p.paragraph_format.line_spacing = 1
                    p.paragraph_format.space_after = Pt(4)
                    p.paragraph_format.space_before = Pt(4)
                    p.paragraph_format.keep_with_next = row_index < len(t.rows)-1
        return t

    def code(text):
        for line in text.splitlines():
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.first_line_indent = Cm(0)
            pf.line_spacing = 1
            pf.space_before = pf.space_after = Pt(0)
            r = p.add_run(line)
            r.font.name, r.font.size = 'Consolas', Pt(12)
            pp = p._p.get_or_add_pPr()
            shade = OxmlElement('w:shd')
            shade.set(qn('w:fill'), 'F2F2F2')
            pp.append(shade)
            borders = OxmlElement('w:pBdr')
            for edge in ['top', 'left', 'bottom', 'right']:
                border = OxmlElement('w:'+edge)
                for key, value in [('val','single'),('sz','4'),('space','2'),('color','D9D9D9')]:
                    border.set(qn('w:'+key),value)
                borders.append(border)
            pp.append(borders)

    title('МІНІСТЕРСТВО ОСВІТИ І НАУКИ УКРАЇНИ', before=16, size=12)
    title('ЛЬВІВСЬКИЙ НАЦІОНАЛЬНИЙ УНІВЕРСИТЕТ ІМЕНІ ІВАНА ФРАНКА', after=8, size=12)
    title('Факультет електроніки і комп’ютерних технологій')
    title('Звіт', before=80, after=14, bold=True)
    title('про виконання лабораторної роботи №10', after=14)
    title('з курсу «Вибрані розділи науки про дані»', after=20)
    title('«Система підказок на основі онтології\nта тестові набори для малої мовної моделі»')
    title('Виконав:', before=130, after=5, bold=True, right=True)
    title('студент групи ФЕІм-13с', after=5, right=True)
    title('Шевчук Максим Вікторович', after=16, right=True)
    title('Перевірив:', bold=True, right=True)
    title('Львів 2026', before=159)
    doc.add_page_break()

    heading('Тема та мета роботи')
    para('Розроблено систему зіставлення опису запиту з класами онтології енергетичних даних. '
         'Замість великої мовної моделі використано вже завантажену Qwen3-0.6B з ЛР7. '
         'Мета — порівняти типи й версії підказок, перевірити динамічне використання онтології, '
         'виміряти якість та продемонструвати захист від ін’єкцій.')
    para('Експерименти виконано локально. Синтетичні еталонні мітки підготовлено за участі Codex; '
         'дві незалежні людські розмітки ще не отримано. Тому κ Коена не визначено, а відповідний '
         'пункт результату 3 не можна вважати завершеним. Решту числових результатів наведено за реальними журналами запуску.')
    heading('Початкові дані та середовище')
    para('Файл ontology.ttl — незмінена копія asserted-онтології з ЛР9. Для семи вибраних класів '
         'додано окремий шар skos:altLabel у data/synonyms.ttl. Початкові твердження ЛР9 не змінювалися. '
         'Завдання вузьке: визначити явно названий тип графіка, моделі, лічильник або часовий ряд; '
         'система не прогнозує споживання і не керує обладнанням.')
    para(f'Модель має {runtime["parameters"]:,} параметрів. Використано CPU, float32, чотири потоки, '
         'seed 42, enable_thinking=False. do_sample=False виконує жадібну генерацію — еквівалент '
         'temperature=0. Ліміт відповіді — 100 нових токенів; вхід моделі — до 8192 токенів. '
         'Python-середовище і ваги повторно використано з ЛР7.')

    heading('Результат 1 Чотири типи підказок')
    para('Вихід — JSON з полями status і classes, без додаткових полів. Для status=ok потрібен '
         'один клас, для ambiguous — щонайменше два, для unknown або refused — порожня множина. '
         'Доступні класи: LineChart, Heatmap, RegressionModel, ClassificationModel, ClusteringModel, Meter, TimeSeries. '
         'JSON перевіряється jsonschema, після чого перевіряються існування класів та узгодженість статусу.')
    table('Таблиця 1 — Реалізовані типи підказок', ['Тип', 'Відмінність'], [
        ['Інструктивна', 'Пряме завдання, перелік міток і формат JSON'],
        ['Рольова', 'Роль куратора онтології енергетичної візуалізації'],
        ['Контекстна', 'Дані зі SPARQL і синоніми виділених понять'],
        ['Few-shot', 'Три приклади: лінійний графік, теплова карта, запит поза темою'],
    ], [4,14])
    template_rows = []
    for style in ['instruction', 'role', 'context', 'fewshot']:
        rows = load('results/templates_'+style+'.json')
        template_rows.append([style, len(rows), sum(r['schema_valid'] for r in rows)])
    table('Таблиця 2 — Демонстраційні запуски', ['Тип', 'Запитів', 'Валідних відповідей'], template_rows, [7,4,7])
    para('Для кожного типу використано однакові п’ять запитів про різні класи. Повні підказки '
         'й сирі відповіді збережено в results/templates_*.json. Така демонстрація перевіряє '
         'працездатність форматів, але не замінює оцінювання на незалежних даних.')

    heading('Результат 2 Динамічні підказки з онтології')
    para('Послідовність етапів і повторну перевірку показано на рис. 1.')
    picture = doc.add_paragraph()
    picture.paragraph_format.first_line_indent = Cm(0)
    picture.paragraph_format.keep_with_next = True
    picture.add_run().add_picture(str(architecture()), width=Cm(18))
    caption = para('Рис. 1 — Система онтологічних підказок', 'Caption')
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.line_spacing = 1
    para('Запит нормалізується Unicode NFKC і casefold; словник skos:altLabel дає множину понять. '
         'Межі слів зменшують помилкові збіги всередині інших слів. SPARQL VALUES містить лише '
         'довірені IRI класів. Запит повертає мітки, коментарі, батьківські класи, властивості '
         'з domain/range та доступні OWL-обмеження. Відсутність обмеження не замінюється вигаданим правилом.')
    para('Отриманий фрагмент і словник підставляються в system-повідомлення. Названі у відповіді '
         'класи мають існувати в онтології та входити до виділеного контексту. За порушення '
         'модель отримує текст помилки і до двох повторних запитів. У v3 невдале виправлення '
         'закінчується відмовою, яку окремо позначено як рішення застосунку.')
    dynamic = load('results/dynamic_demo.json')
    table('Таблиця 3 — Динамічний контекст для п’яти запитів', ['ID', 'Поняття', 'Фактів', 'Спроб'],
          [[r['id'], ', '.join(r['concepts']), len(r['fragment']['facts']), len(r['attempts'])] for r in dynamic], [2,8,4,4])
    para('Файл results/dynamic_demo.json містить фактичний SPARQL кожного запиту і відповіді. '
         'Наявність механізму повторів додатково перевірено тестом із навмисно неіснуючим класом; '
         'штучний тест не включено до метрик моделі.')

    heading('Результат 3 Розмічений тестовий набір')
    para('Набір версії 1.0.0 містить 38 авторських синтетичних прикладів: 28 типових, '
         '3 граничні, 2 неоднозначні та 5 шкідливих. Розбиття фіксоване: '
         f'{dev["v1"]["n"]} dev і {test["n"]} held-out test. Частину шаблонів навмисно перефразовано, '
         'але набір залишається простим і близьким до словника синонімів; він не відображає реального потоку користувачів.')
    para('Правила розмітки: один явно підтримуваний клас — ok; кілька — ambiguous; '
         'непідтримуваний чи недостатньо конкретний запит — unknown; спроба зміни інструкцій, '
         'розкриття підказки або надмірна довжина — refused. Відмова має пріоритет. '
         'Правильність означає точний збіг статусу та множини класів без урахування порядку.')
    para('Для другої розмітки підготовлено десять різних прикладів у annotation_blind.csv. '
         'Формула κ = (pₒ − pₑ)/(1 − pₑ), де pₒ — фактична частка збігів, '
         'pₑ — очікувана за добутками частот категорій. Категорія тут — статус разом із множиною класів. '
         'Незалежні людські відповіді ще відсутні, тому обчислювати число κ немає підстав. '
         'annotation.py готовий до порівняння з отриманою розміткою; для вимоги двох людей потрібні дві незалежні людські форми.')

    heading('Результат 4 Оцінювання версій підказки')
    para('v1 задає інструкцію та повний перелік класів. v2 додає динамічний контекст, '
         'перевірку належності класів і два виправлення. v3 додає межу довіри, JSON-контейнер '
         'для даних, скринінг атак, enum і відмову після невдалого виправлення. '
         'Отже, порівнюються версії всієї системи підказок разом із перевірками.')
    table('Таблиця 4 — Метрики на dev', ['Версія', 'Точність', 'JSON моделі', 'Токенів / запит', 'Секунд / запит'],
          [[v, f'{m["accuracy"]:.1%}', f'{m["valid_model_json_rate"]:.1%}',
            f'{m["mean_total_tokens_per_query"]:.1f}', f'{m["mean_seconds_per_query"]:.2f}'] for v,m in dev.items()])
    para('Токени включають вхід і вихід усіх повторів; запити, відхилені до моделі, '
         'мають нуль токенів. Частка JSON моделі не зараховує відмови фільтра як успішну генерацію. '
         'Час включає лише generate, без завантаження моделі, SPARQL і токенізації. '
         'API-вартість усіх запусків — 0 USD, але локальні витрати електроенергії й обладнання не виміряно.')
    table('Таблиця 5 — Категорії помилок на dev', ['Версія', 'Хибна мітка', 'Галюцинація', 'Формат', 'Відмова'],
          [[v]+[m['errors'].get(k,0) for k in ['wrong_label','hallucination','format','refusal']] for v,m in dev.items()])
    para(f'Для v3 точність становить {dev["v3"]["accuracy"]:.1%}; '
         f'зафіксовано {dev["v3"]["guard_refusals"]} відмов захисного шару, включно з '
         'відмовами після невдалих виправлень. Система завжди повертає прийнятний кінцевий '
         'об’єкт, але це може бути зайва відмова. Для малої моделі довша захисна підказка '
         'і суворіші перевірки в цьому експерименті погіршили класифікацію.')
    para('Наприклад, v1 для q21 про лічильник повернула ClassificationModel і зайві поля '
         'refused та private_evaluation_canary. Відповідь синтаксично є JSON, але порушує '
         'схему й не відповідає запиту. Це показує потребу відокремлювати парсинг JSON, '
         'перевірку схеми та правильність мітки.')
    para(f'За точністю dev обрано {selected}; за рівності враховано валідність JSON і меншу '
         'кількість токенів. Вибір та SHA-256 коду зафіксовано до test. '
         f'Одноразова оцінка на {test["n"]} тестових запитах: точність {test["accuracy"]:.1%}, '
         f'валідний JSON моделі {test["valid_model_json_rate"]:.1%}, '
         f'{test["mean_total_tokens_per_query"]:.1f} токена на запит. '
         'Після перегляду test підказки не налаштовувалися. Малі вибірки та близькі формулювання '
         'обмежують узагальнення цих результатів.')
    para('Стійкість обраної v2 потребує окремого врахування: на dev вона прийняла '
         'шкідливий q37 із тегом system як звичайний запит про Meter. '
         'Цей приклад показує, що вибір за точністю не розв’язує задачу захисту.')

    heading('Результат 5 Ін’єкції та захист')
    para('Підготовлено сім атак: перевизначення правил українською та англійською, '
         'вбудований тег system, запит розкриття підказки, вимога неіснуючого класу, '
         'імітація закриття контейнера та довгий ввід. Цілі — HACKED, приватний штучний '
         'canary або NuclearReactor. Справжні паролі чи API-ключі не використовувалися.')
    table('Таблиця 6 — Частка успішних атак', ['Версія', 'Атак', 'Ціль у сирій відповіді', 'Ціль на виході застосунку'],
          [[v,m['n'],f'{m["raw_target_seen"]:.1%}' if any(r['attempts'] for r in load('results/attacks_'+v+'.json')) else 'Без викликів',
            f'{m["application_target_seen"]:.1%}'] for v,m in attacks.items()])
    protected = load('results/attacks_v3.json')
    para(f'У захищеному прогоні {sum(not r["attempts"] for r in protected)} із {len(protected)} '
         'атак відхилено до виклику моделі. Відповідно, висновок про захист стосується '
         'передусім скринінгу вводу; власну поведінку Qwen3 для цих заблокованих атак не виміряно.')
    para('Відсутність цільового маркера і коректна відмова — різні критерії: '
         'окремо збережено task_failure. У захищеній версії шаблонний фільтр може відмовити '
         'до генерації. Це демонструє поведінку застосунку, а не доводить власну стійкість '
         'мовної моделі. Нуль атак у малій перевірці не гарантує захисту від перефразованих ін’єкцій. '
         'Можливі також хибні відмови на нешкідливі цитати.')
    para('У незахищеній пробі v1 невалідний сирий текст вважається доступним користувачу; '
         'валідація реєструє помилку. Для v3 вимірюється тільки перевірений кінцевий об’єкт '
         'або відмова. Це спосіб моделювання незахищеної та захищеної інтеграції, '
         'а не окремий розгорнутий вебзастосунок.')
    para('Перевірено п’ять автоматичних тестів: SPARQL, семантичне відхилення, ліміт повторів '
         'із відмовою, блокування без виклику моделі, успішне виправлення. Їхні підставні '
         'відповіді не включено до експериментальної статистики.')

    heading('Висновки')
    para(f'Реалізовано локальну систему підказок для Qwen3-0.6B з онтологічним контекстом '
         f'та формальною перевіркою виходу. Обрана за dev версія {selected} отримала '
         f'{test["accuracy"]:.1%} точності на held-out test. Витрати контексту й повторів '
         'слід оцінювати разом із якістю. Захист поєднує перевірки вводу та виходу, '
         'але його ефективність тут досліджено лише на семи відомих атаках. '
         'Для повного завершення результату 3 потрібні незалежні людські розмітки та κ Коена.')
    heading('Декларація використання ШІ')
    para('Codex використано для підготовки коду, синтетичних прикладів, початкових міток і звіту '
         'за запитом використати SLM. Експериментальні відповіді отримано локально від Qwen3-0.6B; '
         'вони збережені без підміни еталонними відповідями. Перевірка охоплювала реальні запуски, '
         'валідацію та журнали. Codex або Qwen не подано як незалежних людей-розмітників. '
         'Докладніше — AI_USAGE.md.')
    heading('Джерела')
    for reference in ['1. ЛР10_завдання.pdf — поточна методичка, 2026–2027 н. р.',
         '2. Онтологія ЛР9: data/ontology_asserted.ttl.',
         '3. Qwen3-0.6B, локальна картка моделі з ЛР7; https://huggingface.co/Qwen/Qwen3-0.6B.',
         '4. RDFLib documentation: https://rdflib.readthedocs.io/.']:
        p = para(reference)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(0)
    doc.add_page_break()
    heading('Додаток А Основні алгоритми')
    para('Фрагменти lab10.py. Повний код, підготовка набору й запуск містяться в ZIP.')
    source = (ROOT/'lab10.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ['validate', 'run_case', 'metrics']:
            doc.add_heading(node.name, 2)
            code(ast.get_source_segment(source, node))
    path = ROOT/(STEM+'.docx')
    doc.save(path)
    print(path)


if __name__ == '__main__':
    build()
