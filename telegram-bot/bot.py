#!/usr/bin/env python3
"""
Телеграм бот для отображения задач из системы "Мои дела"
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes


class TodoBot:
    def __init__(self, token: str):
        self.token = token
        self.base_path = Path(__file__).parent.parent
        self.todos_path = self.base_path / "todos"
        try:
            print("Bot paths - Base: {}, Todos: {}, Exists: {}".format(
                str(self.base_path.resolve()), 
                str(self.todos_path.resolve()), 
                self.todos_path.exists()
            ))
            if self.todos_path.exists():
                files = list(self.todos_path.glob('current/*.md'))
                print("Current files found: {}".format(len(files)))
            else:
                print("Todos path does not exist!")
        except Exception as e:
            print("Debug error:", str(e))
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Приветственное сообщение"""
        keyboard = [
            [InlineKeyboardButton("📋 Текущие задачи", callback_data="current")],
            [InlineKeyboardButton("✅ Выполненные", callback_data="completed")],
            [InlineKeyboardButton("📁 Проекты", callback_data="projects")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Привет! Я помогу управлять вашими задачами.\n"
            "Выберите категорию:",
            reply_markup=reply_markup
        )
    
    async def list_todos(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать текущие задачи"""
        todos = self._get_todos("current")
        
        if not todos:
            await update.message.reply_text("📭 Нет текущих задач")
            return
            
        message = "📋 *Текущие задачи:*\n\n"
        for i, todo in enumerate(todos, 1):
            message += f"{i}. {todo['title']}\n"
            if todo.get('status'):
                message += f"   Статус: {todo['status']}\n"
            if todo.get('priority'):
                message += f"   Приоритет: {todo['priority']}\n"
            message += "\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать статистику"""
        current = len(self._get_todos("current"))
        completed = len(self._get_todos("completed"))
        projects = len(self._get_todos("projects"))
        
        message = (
            "📊 *Статистика:*\n\n"
            f"📋 Текущих задач: {current}\n"
            f"✅ Выполнено: {completed}\n"
            f"📁 Проектов: {projects}\n"
            f"\n📅 Дата: {datetime.now().strftime('%Y-%m-%d')}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        category = query.data
        print(f"Button clicked: {category}")
        todos = self._get_todos(category)
        print(f"Found {len(todos)} todos in category {category}")
        
        if not todos:
            await query.edit_message_text(f"📭 Нет задач в категории '{category}'")
            return
        
        titles = {
            "current": "📋 Текущие задачи",
            "completed": "✅ Выполненные задачи",
            "projects": "📁 Проекты"
        }
        
        message = f"*{titles.get(category, category)}:*\n\n"
        for i, todo in enumerate(todos, 1):
            message += f"{i}. {todo['title']}\n"
            if todo.get('description'):
                message += f"   {todo['description'][:50]}...\n"
            message += "\n"
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    def _get_todos(self, category: str) -> List[Dict]:
        """Получить список задач из файлов"""
        todos = []
        category_path = self.todos_path / category
        
        print(f"Looking for todos in: {category_path}")
        print(f"Path exists: {category_path.exists()}")
        
        if not category_path.exists():
            print(f"Category path {category_path} does not exist!")
            return todos
        
        md_files = list(category_path.glob("*.md"))
        print(f"Found {len(md_files)} .md files: {md_files}")
        
        for file_path in md_files:
            print(f"Parsing file: {file_path}")
            todo = self._parse_todo_file(file_path)
            if todo:
                print(f"Parsed todo: {todo.get('title', 'No title')}")
                todos.append(todo)
            else:
                print(f"Failed to parse: {file_path}")
        
        print(f"Total todos in {category}: {len(todos)}")
        return todos
    
    def _parse_todo_file(self, file_path: Path) -> Dict:
        """Парсинг markdown файла с задачей"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            todo = {
                'filename': file_path.name,
                'title': lines[0].strip('# ') if lines else 'Без названия'
            }
            
            # Простой парсер для извлечения метаданных
            for line in lines:
                if line.startswith('**Статус:**'):
                    todo['status'] = line.split('**Статус:**')[1].strip()
                elif line.startswith('**Приоритет:**'):
                    todo['priority'] = line.split('**Приоритет:**')[1].strip()
                elif line.startswith('**Дедлайн:**'):
                    todo['deadline'] = line.split('**Дедлайн:**')[1].strip()
            
            # Извлечь описание
            if '## Описание' in content:
                desc_start = content.find('## Описание') + len('## Описание')
                desc_end = content.find('##', desc_start)
                if desc_end == -1:
                    desc_end = len(content)
                todo['description'] = content[desc_start:desc_end].strip()
            
            return todo
        except Exception as e:
            print(f"Ошибка при чтении {file_path}: {e}")
            return None
    
    def run(self):
        """Запуск бота"""
        app = Application.builder().token(self.token).build()
        
        # Команды
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("list", self.list_todos))
        app.add_handler(CommandHandler("stats", self.stats))
        
        # Кнопки
        app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Запуск
        app.run_polling()


if __name__ == "__main__":
    # Загрузка токена из переменной окружения или файла
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                TOKEN = config.get("token")
    
    if not TOKEN:
        print("❌ Токен не найден! Создайте config.json или установите TELEGRAM_BOT_TOKEN")
        print("Пример config.json:")
        print(json.dumps({"token": "YOUR_BOT_TOKEN"}, indent=2))
        exit(1)
    
    bot = TodoBot(TOKEN)
    print("Bot zapuschen...")
    bot.run()