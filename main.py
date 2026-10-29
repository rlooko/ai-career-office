import json
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'office.db'
MODEL = 'qwen2.5:3b'

def ask_ai(system, user):
    import time

    payload = json.dumps({
        'model': MODEL,
        'stream': False,
        'think': False,
        'keep_alive': '5m',
        'options': {
            'num_predict': 800,
            'temperature': 0.2
        },
        'messages': [
            {
                'role': 'system',
                'content': system + (
                    '\n최종 답변만 작성하라. '
                    '영어 사고 과정이나 내부 추론을 출력하지 마라.'
                )
            },
            {
                'role': 'user',
                'content': user
            }
        ]
    }, ensure_ascii=False).encode('utf-8')

    request = urllib.request.Request(
        'http://127.0.0.1:11434/api/chat',
        data=payload,
        headers={'Content-Type': 'application/json'}
    )

    print('\n[AI] 응답 생성 중...', flush=True)
    start = time.monotonic()

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)

        elapsed = time.monotonic() - start
        print(f'[AI] 응답 완료: {elapsed:.1f}초', flush=True)

        content = result['message']['content'].strip()

        if not content:
            raise ValueError('AI가 빈 응답을 반환했습니다.')

        return content

    except Exception as error:
        elapsed = time.monotonic() - start
        print(f'[AI] 요청 실패: {elapsed:.1f}초', flush=True)
        raise

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        con.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT "pending", created_at TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)')


def recent_tasks():
    with sqlite3.connect(DB) as con:
        return con.execute('SELECT id,title,status FROM tasks ORDER BY id DESC LIMIT 20').fetchall()


def save_report(kind, content):
    now = datetime.now().isoformat(timespec='seconds')
    with sqlite3.connect(DB) as con:
        con.execute('INSERT INTO reports(kind,content,created_at) VALUES (?,?,?)', (kind, content, now))
    folder = ROOT / 'reports'
    folder.mkdir(exist_ok=True)
    path = folder / f'{datetime.now():%Y-%m-%d_%H-%M-%S}_{kind}.md'
    path.write_text(content, encoding='utf-8')
    return path


def briefing():
    profile = json.loads((ROOT / 'data' / 'profile.json').read_text(encoding='utf-8'))
    tasks = recent_tasks()
    schedule = (
        '기본 일정(실제 캘린더 확인 전): '
        '01:00~08:00 수면, '
        '09:00~13:00 오전 방송, '
        '13:00~14:00 점심, '
        '14:00~16:00 SQL/Python 공부 120분, '
        '21:00~23:00 저녁 방송. '
        '방송과 수면 시간에는 공부를 배정하지 마라. '
        '요일별 일정은 달라질 수 있으므로 확정 일정이라고 주장하지 마라.'
    )
    study = ask_ai(
        '너는 SQL/Python/BI 학습 코치다. 한국어로 답하라. 프로필만으로 실력이나 완료 여부를 추정하지 마라. 하루 120분의 구체적이고 검증 가능한 학습 계획을 제시하라.',
        f'오늘 날짜: {datetime.now():%Y-%m-%d}\n기본 일정: {schedule}\n프로필: {json.dumps(profile, ensure_ascii=False)}\n최근 작업: {tasks}\n시간표나 시각을 작성하지 마라. 14:00~16:00의 120분 안에서 실행할 SQL/Python 학습 과제만 추천하라. 각 과제의 소요 시간(분)을 적고 합계가 정확히 120분이 되도록 하라. 각 과제마다 완료 기준을 제시하라.')
    manager = ask_ai(
        '너는 AI 회사의 총괄 비서다. 한국어로 답하라. 직원 보고서를 검토해 오늘 우선순위와 시간표를 제안하라. 캘린더가 연동되지 않았으므로 모든 일정은 가정이라고 명시하라. 실제 채용공고를 조회하지 않았으므로 회사명이나 채용 마감일을 만들어내지 마라. 외부 게시, 지원서 제출, 캘린더 변경을 실행했다고 주장하지 마라. 공부 시간은 120분이며 방송과 겹치지 않아야 한다.',
        f'오늘 날짜: {datetime.now():%Y-%m-%d}\n기본 일정: {schedule}\n프로필: {json.dumps(profile, ensure_ascii=False)}\n최근 작업: {tasks}\n학습 코치 보고:\n{study}\n시간표나 시각을 작성하지 마라. 기본 시간표는 Python이 별도로 출력한다. 학습 코치의 과제를 중복 배정하지 마라. 다음 세 항목만 작성하라: 오늘의 우선순위 3개, 취업 준비 과제 1개, 사용자 확인 필요 사항.')
    fixed_schedule = (
        '# 기본 시간표 (캘린더 미연동, 요일별 조정 필요)\n\n'
        '| 시간 | 활동 |\n'
        '|---|---|\n'
        '| 01:00~08:00 | 수면 |\n'
        '| 09:00~13:00 | 오전 방송 |\n'
        '| 13:00~14:00 | 점심 |\n'
        '| 14:00~16:00 | SQL/Python 공부 120분 |\n'
        '| 21:00~23:00 | 저녁 방송 |\n\n'
    )
    result = (
        fixed_schedule
        + '# AI 총괄 비서 참고 의견\n\n'
        + manager
        + '\n\n---\n\n# AI 학습 코치 추천\n\n'
        + study
    )
    path = save_report('morning', result)
    print(result)
    print(f'\n저장: {path}')


def add_task(title):
    with sqlite3.connect(DB) as con:
        con.execute('INSERT INTO tasks(title,created_at) VALUES (?,?)', (title, datetime.now().isoformat(timespec='seconds')))
    print('업무 등록:', title)


def complete_task(task_id):
    with sqlite3.connect(DB) as con:
        cur = con.execute('UPDATE tasks SET status="done" WHERE id=?', (task_id,))
    print('완료 처리' if cur.rowcount else '해당 ID가 없습니다.')


def main():
    init_db()
    print('My AI Career Office | 로컬 MVP')
    print('1: 아침 브리핑  2: 업무 추가  3: 업무 목록  4: 완료 처리  0: 종료')
    while True:
        choice = input('\n선택: ').strip()
        try:
            if choice == '1': briefing()
            elif choice == '2':
                title = input('업무 내용: ').strip()
                if title: add_task(title)
            elif choice == '3':
                for row in recent_tasks(): print(f'{row[0]}. [{row[2]}] {row[1]}')
            elif choice == '4': complete_task(int(input('업무 ID: ')))
            elif choice == '0': break
            else: print('메뉴 번호를 입력하세요.')
        except (OSError, ValueError, KeyError) as error:
            print('오류:', error)
            print('Ollama 실행 상태, 모델 설치, 입력값을 확인하세요.')


if __name__ == '__main__':
    main()
