import os
import time
import uuid
import logging
from datetime import datetime
from mattermostdriver import Driver
from mattermostdriver.exceptions import NoAccessTokenProvided
from tarantool import Connection


MM_CONFIG = {
    'url': 'mattermost',
    'port': 8065,
    'token': os.getenv('MM_TOKEN'),
    'scheme': 'http',
    'verify': False,

}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voting_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('VotingBot')

class VotingBot:
    def __init__(self):
        self.mm = Driver(MM_CONFIG)
        self.tarantool = Connection('tarantool', 3301)
        self.user_id = None
        self.team_id = None
    
    def start(self):
        logger.info("Starting Mattermost Voting Bot...")
        
        try:
            self.mm.login()
            user = self.mm.users.get_user(user_id='me')
            self.user_id = user['id']
            logger.info(f"Bot is running as: {user['username']} (ID: {self.user_id})")

            team_name = 'vk'
            team = self.mm.teams.get_team_by_name(team_name)
            self.team_id = team['id']
            
            channels = self.mm.channels.get_channels_for_user(self.user_id, self.team_id)
            
            self.message_loop(channels)
            
        except NoAccessTokenProvided:
            print("Error: No access token provided. Please check your bot token.")
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            print("Bot stopped")
    
    def message_loop(self, channels):
        last_post_times = {}
        logger.info("Starting message processing loop")

        while True:
            try:
                for channel in channels:
                    channel_id = channel['id']
                    
                    posts = self.mm.posts.get_posts_for_channel(channel_id)
                    
                    if 'posts' in posts:
                        latest_post = max(posts['posts'].values(), key=lambda x: x['create_at'])
                        
                        if channel_id not in last_post_times or \
                           latest_post['create_at'] > last_post_times[channel_id]:
                            
                            last_post_times[channel_id] = latest_post['create_at']
                            
                            if latest_post['user_id'] != self.user_id:
                                self.handle_message(
                                    latest_post['message'],
                                    channel_id,
                                    latest_post['user_id']
                                )
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(5)
    
    def handle_message(self, message, channel_id, user_id):        
        if not message.startswith('!vote'):
            return
        
        parts = message.split()
        if len(parts) < 2:
            self.show_help(channel_id)
            return
        
        command = parts[1].lower()
        args = parts[2:]
        
        if command == 'create':
            logger.info(f"Create voting command by user {user_id}")
            self.handle_create(args, channel_id, user_id)
        elif command == 'vote':
            logger.info(f"Vote command by user {user_id}")
            self.handle_vote(args, channel_id, user_id)
        elif command == 'results':
            logger.info(f"Results command by user {user_id}")
            self.handle_results(args, channel_id, user_id)
        elif command == 'end':
            logger.info(f"End voting command by user {user_id}")
            self.handle_end(args, channel_id, user_id)
        elif command == 'delete':
            logger.info(f"Delete voting command by user {user_id}")
            self.handle_delete(args, channel_id, user_id)
        else:
            logger.info(f"Help command by user {user_id}")
            self.show_help(channel_id)
    
    def handle_create(self, args, channel_id, user_id):
        try:
            if not args:
                raise ValueError("Не указаны аргументы")
            logger.debug(f"Create voting args: {args}") 
            parsed_args = self.parse_arguments(args)
            logger.debug(f"Parsed args: {parsed_args}")
            
            if not parsed_args.get('q'):
                raise ValueError("Не указан вопрос (-q)")
                
            if not parsed_args.get('c'):
                raise ValueError("Не указаны варианты (-c)")
            
            question = parsed_args['q']
            choices = self.split_choices(parsed_args['c'])
            logger.debug(f"Parsed choices: {choices}")
            
            if len(choices) < 2:
                raise ValueError("Нужно указать как минимум 2 варианта")
                
            voting_id = str(uuid.uuid4())[:8]
            options = {str(i): {'text': choice, 'count': 0} 
                  for i, choice in enumerate(choices, 1)}

            logger.info(f"Creating new voting by user {user_id}. ID: {voting_id}, Question: {question}")

            choices_text = "\n".join(f"{i+1}. {choice}" for i, choice in enumerate(choices))
            response = (
                f"✅ **Голосование создано!** (ID: `{voting_id}`)\n\n"
                f"**Вопрос:** {question}\n\n"
                f"**Варианты:**\n{choices_text}\n\n"
                f"Чтобы проголосовать: `!vote vote {voting_id} номер_варианта`"
            )
            
            self.send_message(channel_id, response)

            self.tarantool.insert('votings', (
                voting_id,
                user_id,
                question,
                options,
                {},
                True,
                channel_id
            ))
            return voting_id

            logger.info(f"Voting {voting_id} created successfully")
            
        except Exception as e:
            logger.error(f"Error creating voting: {str(e)}", exc_info=True)

            error_message = (
                "❌ Ошибка создания голосования:\n"
                f"{str(e)}\n\n"
                "**Правильный формат:**\n"
                "`!vote create -q=\"Ваш вопрос\" -c=\"Вариант 1, Вариант 2, Вариант 3\"`\n\n"
                "**Пример:**\n"
                "`!vote create -q=\"Какой язык лучше?\" -c=\"Python, Go, C++, JavaScript\"`"
            )
            self.send_message(channel_id, error_message)

    def split_choices(self, choices_str):
        """Разделяет строку вариантов, учитывая кавычки"""
        choices = []
        current = []
        in_quotes = False
        
        i = 0
        n = len(choices_str)
        while i < n:
            c = choices_str[i]
            
            if c == '"':
                in_quotes = not in_quotes
                i += 1
            elif c == ',' and not in_quotes:
                choices.append(''.join(current).strip())
                current = []
                i += 1
                # Пропускаем пробелы после запятой
                while i < n and choices_str[i].isspace():
                    i += 1
            else:
                current.append(c)
                i += 1
        
        if current:
            choices.append(''.join(current).strip())
        
        return choices

    def parse_arguments(self, args):
        """Парсит аргументы в формате -key=value с поддержкой значений в кавычках"""
        parsed = {}
        current_key = None
        current_value = []
        in_quotes = False
        
        for arg in args:
            if arg.startswith('-') and '=' in arg:
                if current_key:
                    parsed[current_key] = ' '.join(current_value).strip('"')
                    current_value = []
                
                key_part, value_part = arg.split('=', 1)
                current_key = key_part[1:].lower()
                
                if value_part.startswith('"'):
                    in_quotes = True
                    value_part = value_part[1:]
                
                current_value.append(value_part)
                
                if value_part.endswith('"') and in_quotes:
                    in_quotes = False
                    current_value[-1] = current_value[-1][:-1]
            elif in_quotes:
                current_value.append(arg)
                
                if arg.endswith('"'):
                    in_quotes = False
                    current_value[-1] = current_value[-1][:-1]
            elif current_key:
                current_value.append(arg)
        
        if current_key:
            parsed[current_key] = ' '.join(current_value).strip('"')
        
        return parsed
    
    def handle_vote(self, args, channel_id, user_id):
        logger.debug(f"Vote args: {args}")

        if len(args) != 2:
            self.send_message(channel_id, "Формат: !vote vote ID номер")
            return
        
        voting_id, option = args
        try:
            logger.info(f"User {user_id} trying to vote in {voting_id} for option {option}")
            result = self.add_vote(voting_id, option, user_id)
        
            if result is True:
                logger.info(f"User {user_id} voted successfully in {voting_id}")
                self.send_message(channel_id, "✅ Ваш голос успешно учтен!")
            elif result == "inactive":
                logger.warning(f"User {user_id} tried to vote in inactive voting {voting_id}")
                self.send_message(channel_id, "❌ Это голосование уже завершено")
            elif result == "alr_voted":
                logger.warning(f"User {user_id} tried to vote twice in {voting_id}")
                voting = self.get_voting(voting_id)
                question = voting[0][2] if voting else "unknown"
                self.send_message(
                    channel_id,
                    f"❌ Вы уже голосовали в этом опросе!\n"
                    f"Голосование: *{question}*\n"
                    f"ID: `{voting_id}`"
                )
            elif result == "invalid_option":
                logger.warning(f"Invalid option {option} in voting {voting_id} by user {user_id}")
                voting = self.get_voting(voting_id)
                if voting:
                    options = voting[0][3]
                    valid_options = "\n".join([f"{num}. {opt['text']}" for num, opt in options.items()])
                    self.send_message(
                        channel_id,
                        f"❌ Неправильный вариант!\n"
                        f"Доступные варианты:\n{valid_options}"
                    )
                else:
                    self.send_message(channel_id, "❌ Голосование не найдено")
            else:
                logger.warning(f"User {user_id} tried to vote in non-existant voting {voting_id}")
                self.send_message(channel_id, "❌ Голосование не найдено")

        except Exception as e:
            logger.error(f"Error processing vote: {str(e)}", exc_info=True)
            self.send_message(channel_id, f"⚠️ Произошла ошибка: {str(e)}")
    
    def handle_results(self, args, channel_id, user_id):
        if len(args) != 1:
            self.send_message(
                channel_id,
                "Использование: !vote results <ID_голосования>"
            )
            return
        
        voting_id = args[0]

        logger.info(f"User {user_id} trying to get results for voting {voting_id}")

        voting = self.get_voting(voting_id)
        if not voting:
            logger.warning(f"User {user_id} tried to get results for a non-existant voting {voting_id}")
            self.send_message(channel_id, "❌ Голосование не найдено")
            return
        voting_data = voting[0]
        question = voting_data[2]
        options = voting_data[3]
        is_active = voting_data[5]
        
        total_votes = sum(opt['count'] for opt in options.values())
        
        sorted_options = sorted(
            options.items(),
            key=lambda item: item[1]['count'],
            reverse=True
        )
        
        result_lines = []
        for opt_num, opt_data in sorted_options:
            count = opt_data['count']
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            bar_length = int(percentage / 5)
            bar = '█' * bar_length
            result_lines.append(
                f"{opt_num}. **{opt_data['text']}**\n"
                f"    {bar} {count} ({percentage:.1f}%)"
            )
        
        status = "🟢 Активно" if is_active else "🔴 Завершено"
        response = (
            f"📊 **Результаты голосования**\n"
            f"**ID:** `{voting_id}` {status}\n"
            f"**Вопрос:** {question}\n"
            f"**Всего голосов:** {total_votes}\n\n"
            + "\n\n".join(result_lines)
        )
        logger.info(f"Results for voting {voting_id} sent successfully")
        self.send_message(channel_id, response)
    
    def handle_end(self, args, channel_id, user_id):
        if len(args) != 1:
            self.send_message(
                channel_id,
                "Использование: !vote end <ID_голосования>"
            )
            return
        
        voting_id = args[0]

        logger.info(f"User {user_id} trying to end voting {voting_id}")
        
        try:
            voting = self.get_voting(voting_id)
            if not voting:
                logger.warning(f"User {user_id} tried to end a non-existant voting {voting_id}")
                self.send_message(channel_id, "❌ Голосование не найдено")
                return
            
            if voting[0][1] != user_id:
                logger.warning(f"User {user_id} is not a creator of voting {voting_id}, end process stopped")
                self.send_message(
                    channel_id,
                    "❌ Только создатель может завершить голосование"
                )
                return
            
            self.tarantool.update('votings', voting_id, [('=', 5, False)])
            
            self.handle_results([voting_id], channel_id, user_id)
            logger.info(f"Voting {voting_id} ended successfully")
            self.send_message(
                channel_id,
                f"Голосование `{voting_id}` завершено. Новые голоса не принимаются."
            )
            
        except Exception as e:
            logger.error(f"Error during ending voting {voting_id}")
            self.send_message(
                channel_id,
                f"❌ Ошибка при завершении голосования: {str(e)}"
            )
    
    def handle_delete(self, args, channel_id, user_id):
        if len(args) != 1:
            self.send_message(
                channel_id,
                "Использование: !vote delete <ID_голосования>"
            )
            return
        
        voting_id = args[0]

        logger.info(f"User {user_id} trying to delete voting {voting_id}")
        
        try:
            voting = self.get_voting(voting_id)
            if not voting:
                logger.warning(f"User {user_id} tried to delete a non-existant voting {voting_id}")
                self.send_message(channel_id, "❌ Голосование не найдено")
                return
            
            if voting[0][1] != user_id:
                logger.warning(f"User {user_id} is not a creator of voting {voting_id}, delete process stopped")
                self.send_message(
                    channel_id,
                    "❌ Только создатель может удалить голосование"
                )
                return
            
            self.tarantool.delete('votings', voting_id)
            
            self.tarantool.delete('voted_users', (voting_id, user_id))

            logger.info(f"Voting {voting_id} deleted successfully")
            self.send_message(
                channel_id,
                f"Голосование `{voting_id}` удалено. Все данные очищены."
            )
            
        except Exception as e:
            logger.error(f"Error during deleting voting {voting_id}")
            self.send_message(
                channel_id,
                f"❌ Ошибка при удалении голосования: {str(e)}"
            )
    
    def get_voting(self, voting_id):
        return self.tarantool.select('votings', voting_id)
    
    def add_vote(self, voting_id, option_num, user_id):
        voting = self.get_voting(voting_id)
        if not voting:
            return False

        if not voting[0][5]:
            return "inactive"
        
        options = voting[0][3]
        if str(option_num) not in options:
            return "invalid_option"

        if self.tarantool.select('voted_users', (voting_id, user_id)):
            return "alr_voted"
        
        options[str(option_num)]['count'] += 1
        self.tarantool.update('votings', voting_id, [('=', 3, options)])
        
        self.tarantool.insert('voted_users', (voting_id, user_id))
        return True

    
    def show_help(self, channel_id):
        help_text = """
**Доступные команды голосования:**
- `!vote create -q="Вопрос" -c="Вариант1, Вариант2"` - Создать новое голосование
- `!vote vote <ID> <номер>` - Проголосовать за вариант
- `!vote results <ID>` - Показать результаты
- `!vote end <ID>` - Завершить голосование (только создатель)
- `!vote delete <ID>` - Удалить голосование (только создатель)
"""
        self.send_message(channel_id, help_text)
    
    def send_message(self, channel_id, message):
        self.mm.posts.create_post({
            'channel_id': channel_id,
            'message': message
        })

if __name__ == '__main__':
    bot = VotingBot()
    bot.start()
