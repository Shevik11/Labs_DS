"""Keep the local models loaded for an interactive terminal conversation."""
from datetime import datetime
import json
from rag import RAG, ROOT, read_json

def main():
    print('ЛР7 · RAG для візуалізації енергетичних даних')
    print('Завантаження локальних моделей; перший запуск може тривати близько хвилини...')
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--preset',choices=['baseline','tuned'],default='baseline')
    args = parser.parse_args()
    config = read_json(ROOT / 'results' / 'selected_config.json') if args.preset=='tuned' else None
    rag = RAG(config=config)
    print('Режим:',args.preset)
    log = ROOT / 'results' / ('session_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.jsonl')
    print('Готово. Введіть запит; /exit — завершити.')
    while True:
        try:
            question = input('\nЗапит: ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ['/exit','exit','quit']:
            break
        if not question:
            continue
        if len(question)>2000:
            print('Скоротіть запит до 2000 символів.')
            continue
        result = rag.ask(question)
        print('\n' + result['answer'])
        for p in result['passages']:
            print(f"  [{p['id']}] {p['source']} · {p['locator']} · score={p['score']:.3f}")
        print(f"Пошук {result['retrieval_ms']:.1f} мс; генерація {result['generation_ms']/1000:.2f} с")
        with log.open('a',encoding='utf-8') as f:
            f.write(json.dumps(result,ensure_ascii=False)+'\n')
    print('\nЗавершено.')

if __name__=='__main__':
    main()

