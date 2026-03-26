import os
import sys
import json
import requests
from datetime import datetime

def send_telegram_message(token, chat_id, text, parse_mode='HTML'):
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}", file=sys.stderr)
        return False

def format_branch_created_notification(repo, actor, branch_name):
    """Форматирует уведомление о создании ветки"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
🌿 <b>Новая ветка создана</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
👤 <b>Автор:</b> {actor}
🌿 <b>Ветка:</b> {branch_name}
"""

def format_push_notification(repo, actor, message, url):
    """Формат Push уведомления"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
🔵 <b>Новый Push</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
👤 <b>Автор:</b> {actor}
📝 <b>Описание:</b> {message[:200] if message else 'Нет описания'}
🔗 <b>Ссылка:</b> <a href="{url if url else '#'}">Проверить Commit</a>
"""

def format_pr_opened_notification(repo, actor, title, url):
    """Формат Pull Request уведомления"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
🟢 <b>Pull Request открыт</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
👤 <b>Автор:</b> {actor}
📝 <b>Название:</b> {title}
🔗 <b>Ссылка:</b> <a href="{url if url else '#'}">Проверить Pull Request</a>
"""

def format_pr_merged_notification(repo, actor, title, url):
    """Формат Merdge уведомления"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return f"""
✅ <b>Merdge выполнен</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
👤 <b>Автор:</b> {actor}
📝 <b>Название:</b> {title}
🔗 <b>Ссылка:</b> <a href="{url if url else '#'}">Проверить Merdge</a>
"""

def format_issue_notification(repo, actor, title, url, action='opened'):
    """Формат Issue уведомления"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    action_map = {
        'opened': ('🟡', 'Открыт'),
        'closed': ('🔴', 'Закрыт'),
        'reopened': ('🔄', 'Переоткрыт')
    }
    emoji, action_text = action_map.get(action, ('📝', action.capitalize()))
    
    return f"""
{emoji} <b>Задача {action_text}</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
👤 <b>Автор:</b> {actor}
📝 <b>Название:</b> {title}
🔗 <b>Ссылка:</b> <a href="{url if url else '#'}">Открыть Issue</a>
"""

def format_deadline_notification(repo, deadline_info):
    """Формат дедлайн уведомления"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        if isinstance(deadline_info, str):
            info = json.loads(deadline_info)
        else:
            info = deadline_info
        
        title = info.get('title', 'Неизвестно')
        url = info.get('url', '#')
        deadline_date = info.get('deadline', 'Неизвестно')
        days_left = info.get('days_left', info.get('days_overdue', '?'))
        action = info.get('action', 'approaching')
        
        if action == 'approaching':
            if days_left == 0:
                urgency = "🚨 <b>Дедлайн сегодня</b> 🚨"
            elif days_left == 1:
                urgency = "⚠️ <b>Завтра дедлайн</b> ⚠️"
            elif days_left <= 7:
                urgency = f"⏰ <b>Дедлайн меньше чем через неделю</b>"
        elif action == 'overdue':
            urgency = f"💀 <b>Дедлайн проёбан на {days_left} дней</b> 💀"
        elif action == 'changed':
            urgency = "📅 <b>Дедлайн смещён</b>"
        elif action == 'added':
            urgency = "➕ <b>Дедлайн добавлен</b>"
        else:
            urgency = "📅 <b>Напоминмние о дедлайне</b>"
        
        return f"""
{urgency} @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
📌 <b>Задача:</b> {title}
🗓️ <b>Дата:</b> {deadline_date}
🔗 <b>Ссылка:</b> <a href="{url}">Чекнуть задачу</a>
"""
    except Exception as e:
        return f"""
📅 <b>Уведомление о дедлайне</b> @ {timestamp}

📦 <b>Репозиторий:</b> {repo}
ℹ️ <b>Детали:</b> {deadline_info}
"""

def main():
    # Получаем переменные
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    event_type = os.environ.get('EVENT_TYPE', 'unknown')
    repo_name = os.environ.get('REPO_NAME', 'Unknown')
    actor = os.environ.get('ACTOR', 'Unknown')
    commit_message = os.environ.get('COMMIT_MESSAGE', '')
    commit_url = os.environ.get('COMMIT_URL', '')
    deadline_info = os.environ.get('DEADLINE_INFO', '')
    
    # Проверяем обязательные параметры
    if not token or not chat_id:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required", file=sys.stderr)
        sys.exit(1)
    
    # Форматируем сообщение в зависимости от типа события
    if event_type == 'push':
        message = format_push_notification(repo_name, actor, commit_message, commit_url)
    elif event_type == 'pr_opened':
        message = format_pr_opened_notification(repo_name, actor, commit_message, commit_url)
    elif event_type == 'pr_merged':
        message = format_pr_merged_notification(repo_name, actor, commit_message, commit_url)
    elif event_type == 'issue':
        # Парсим действие из commit_message (формат: "action|title")
        parts = commit_message.split('|', 1)
        action = parts[0] if len(parts) > 0 else 'opened'
        title = parts[1] if len(parts) > 1 else 'Issue'
        message = format_issue_notification(repo_name, actor, title, commit_url, action)
    elif event_type == 'deadline':
        message = format_deadline_notification(repo_name, deadline_info)
    elif event_type == 'branch_created':
        message = format_branch_created_notification(repo_name, actor, commit_message)
    else:
        # Общее уведомление
        message = f"""
📢 <b>GitHub Event: {event_type}</b>

📦 <b>Repository:</b> {repo_name}
👤 <b>Author:</b> {actor}
📝 <b>Details:</b> {commit_message if commit_message else 'No details'}
"""
    
    # Отправляем сообщение
    success = send_telegram_message(token, chat_id, message)
    
    if success:
        print(f"Notification sent successfully for {event_type} in {repo_name}")
    else:
        print(f"Failed to send notification for {event_type}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
