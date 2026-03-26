import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict

class GitHubProjectChecker:
    """Класс для проверки дедлайнов в GitHub Projects"""
    
    def __init__(self, token: str, owner: str, repo: str, project_number: int):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.project_number = project_number
        self.api_url = "https://api.github.com/graphql"
    
    def get_project_items(self) -> List[Dict]:
        """Получает все элементы проекта с их полями"""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                projectV2(number: $number) {
                    items(first: 50) {
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    title
                                    url
                                    state
                                    assignees(first: 5) {
                                        nodes { login }
                                    }
                                }
                                ... on PullRequest {
                                    title
                                    url
                                    state
                                    author { login }
                                }
                            }
                            fieldValues(first: 20) {
                                nodes {
                                    ... on ProjectV2ItemFieldDateValue {
                                        field { name }
                                        date
                                    }
                                    ... on ProjectV2ItemFieldSingleSelectValue {
                                        field { name }
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "owner": self.owner,
            "repo": self.repo,
            "number": self.project_number
        }
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети: {e}", file=sys.stderr)
            return []
        
        data = response.json()
        
        if "errors" in data:
            print(f"Ошибки GraphQL: {data['errors']}", file=sys.stderr)
            return []
        
        try:
            return data["data"]["repository"]["projectV2"]["items"]["nodes"]
        except (KeyError, TypeError) as e:
            print(f"Ошибка парсинга ответа: {e}", file=sys.stderr)
            return []
    
    def check_upcoming_deadlines(self, days_threshold: int = 3) -> List[Dict]:
        """Проверяет дедлайны, приближающиеся в ближайшие N дней"""
        items = self.get_project_items()
        today = datetime.now().date()
        upcoming = []
        
        for item in items:
            deadline = None
            status = None
            title = None
            url = None
            
            # Получаем информацию о содержимом
            content = item.get("content", {})
            if content:
                title = content.get("title", "Неизвестно")
                url = content.get("url", "")
            
            # Извлекаем значения полей
            for field in item.get("fieldValues", {}).get("nodes", []):
                field_name = field.get("field", {}).get("name", "")
                
                if field_name == "Deadline" and field.get("date"):
                    deadline = datetime.fromisoformat(field["date"]).date()
                elif field_name == "Status" and field.get("name"):
                    status = field["name"]
            
            # Пропускаем, если нет дедлайна или задача уже выполнена
            if not deadline:
                continue
            
            if status in ["Done", "Closed", "Completed", "Готово", "Закрыто"]:
                continue
            
            days_left = (deadline - today).days
            
            if 0 <= days_left <= days_threshold:
                upcoming.append({
                    "title": title,
                    "url": url,
                    "deadline": deadline.isoformat(),
                    "days_left": days_left,
                    "status": status,
                    "action": "approaching"
                })
        
        return upcoming
    
    def check_overdue(self) -> List[Dict]:
        """Проверяет просроченные задачи"""
        items = self.get_project_items()
        today = datetime.now().date()
        overdue = []
        
        for item in items:
            deadline = None
            status = None
            title = None
            url = None
            
            content = item.get("content", {})
            if content:
                title = content.get("title", "Неизвестно")
                url = content.get("url", "")
            
            for field in item.get("fieldValues", {}).get("nodes", []):
                field_name = field.get("field", {}).get("name", "")
                
                if field_name == "Deadline" and field.get("date"):
                    deadline = datetime.fromisoformat(field["date"]).date()
                elif field_name == "Status" and field.get("name"):
                    status = field["name"]
            
            if not deadline:
                continue
            
            if status in ["Done", "Closed", "Completed", "Готово", "Закрыто"]:
                continue
            
            if deadline < today:
                overdue.append({
                    "title": title,
                    "url": url,
                    "deadline": deadline.isoformat(),
                    "days_overdue": (today - deadline).days,
                    "status": status,
                    "action": "overdue"
                })
        
        return overdue

def main():
    """Основная функция"""
    # Получаем конфигурацию из переменных окружения
    token = os.environ.get('GITHUB_TOKEN')
    repo_full = os.environ.get('GITHUB_REPOSITORY', '')
    project_number = int(os.environ.get('PROJECT_NUMBER', '1'))
    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not repo_full:
        print("Ошибка: GITHUB_TOKEN и GITHUB_REPOSITORY обязательны", file=sys.stderr)
        sys.exit(1)
    
    if not telegram_token or not telegram_chat_id:
        print("Ошибка: TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID обязательны", file=sys.stderr)
        sys.exit(1)
    
    owner, repo = repo_full.split('/')
    
    checker = GitHubProjectChecker(token, owner, repo, project_number)
    
    # Проверяем приближающиеся дедлайны
    upcoming = checker.check_upcoming_deadlines(days_threshold=3)
    
    # Проверяем просроченные задачи
    overdue = checker.check_overdue()
    
    # Объединяем и отправляем уведомления
    all_deadlines = upcoming + overdue
    
    if all_deadlines:
        # Здесь будет вызов вашей логики отправки
        print(json.dumps({
            "upcoming": len(upcoming),
            "overdue": len(overdue),
            "deadlines": all_deadlines
        }, indent=2, ensure_ascii=False))
    
    print(f"Проверено дедлайнов: {len(upcoming)} приближаются, {len(overdue)} просрочено")

if __name__ == "__main__":
    main()
