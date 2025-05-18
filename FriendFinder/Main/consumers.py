import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_name = f"chat_{min(self.user.id, int(self.other_user_id))}_{max(self.user.id, int(self.other_user_id))}"
        self.room_group_name = f"chat_{self.room_name}"

        self.match = await self.get_match()
        if not self.match:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '').strip()

        if message:
            saved_message = await self.save_message(message)
            print(f"Saved message: {saved_message.content} by {saved_message.sender.username} at {saved_message.created_at}")

            # Обновляем кэш после сохранения
            from django.core.cache import cache
            cache_key = f"chat_messages:{self.room_name}"
            messages = cache.get(cache_key, [])
            messages.append({
                'message': message,
                'sender': self.user.username,
                'created_at': saved_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
            cache.set(cache_key, messages, timeout=3600)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': self.user.username,
                    'created_at': saved_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def get_match(self):
        from .models import Match, User
        other_user = User.objects.get(id=self.other_user_id)
        return Match.objects.filter(user1=self.user, user2=other_user).first() or \
               Match.objects.filter(user1=other_user, user2=self.user).first()

    @database_sync_to_async
    def save_message(self, message):
        from .models import Message
        msg = Message.objects.create(
            match=self.match,
            sender=self.user,
            content=message
        )
        print(f"Message created in DB: {msg.id}, {msg.content}")
        return msg