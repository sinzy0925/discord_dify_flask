import os
import asyncio
import requests
from discord.ext import commands
import discord
import uuid
from dotenv import load_dotenv
from flask import Flask
import threading

# .env ファイルから環境変数を読み込む
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
# 修正：sys.query ではなく chat-messages エンドポイントを設定する
DIFY_CHAT_MESSAGES_ENDPOINT = os.getenv("DIFY_API_ENDPOINT")  # 例: https://api.dify.ai/v1/chat-messages

# Flaskアプリケーションの初期化
app = Flask(__name__)

@app.route('/')
def home():
    return "OK!", 200

# Discord ボットの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="@", intents=intents)
# ユーザーIDとconversation_idを紐付ける辞書
user_conversations = {}

async def send_chat_message(query: str, user: str, conversation_id: str = "", is_first_request: bool = False) -> dict:
    conversationId = "" 
    """
    Dify API の chat-messages エンドポイントへ問い合わせを送信する。
    - Authorization ヘッダーに Dify API キーを付与する。
    - payload 内には curl の例と同様のパラメータを設定する。
    """
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": user,
        "conversation_id":conversation_id,  # 初回なら空文字列
        "files": [
            {
                "type": "image",
                "transfer_method": "remote_url",
                "url": "https://cloud.dify.ai/logo/logo-site.png"
            }
        ]
    }
    try:
        print('')
        print('payload')  # リクエスト内容を出力
        print(payload)  # リクエスト内容を出力
        # requests.post は同期関数のため asyncio.to_thread() で呼び出す
        response = await asyncio.to_thread(
            requests.post,
            DIFY_CHAT_MESSAGES_ENDPOINT,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")

@bot.command(name="@")##動く
async def chat_message_command(ctx: commands.Context, *, query: str):
    user_id = str(ctx.author.id)  # ユーザーIDを取得
    conversation_id = "" # 初回は空文字列

    # ユーザーのconversation_idを取得 (なければ新規作成)
    if user_id not in user_conversations:
        is_first_request = True # 初回リクエストのフラグ
        conversation_id = "" # 初回は空文字列
        print('a  conversation_id ' + conversation_id)
    else:
        is_first_request = False
        conversation_id = user_conversations[user_id]
        print('b  conversation_id ' + conversation_id)


    print('')
    print('-----')
    print(f"Discordの入力: {query}")  # ここで入力値をログ出力して確認
    """
    Discord コマンド "!chat" で受け取ったクエリを Dify API へ送信し、結果を返す。
    """
    async with ctx.typing():
        result = await send_chat_message(query, str(ctx.author),conversation_id, is_first_request)
        user_conversations[user_id] = result['conversation_id']
        print('')
        print('result')
        print(result)
        print('')
        print('user_conversations[user_id]')
        print(user_conversations[user_id])
        if "error" in result:
            await ctx.send(f"Error: {result['error']}")
        else:
            answer = result.get("answer")
            # API の返答が "Text message was sent successfully" の場合は返信しない
            if answer and answer != "Text message was sent successfully":
                print('')
                print('-----')
                print(f"Difyの結果 : {answer}")
                await ctx.send(f"{answer}")
            # それ以外の場合や想定外のフォーマットの場合は、必要に応じてログ出力する
            else:
                print('')
                print('-----')
                print("Dify API 結果 : ")
                print(result)

# Flaskを別スレッドで実行する関数
def run_flask():
    app.run(host='0.0.0.0', port=3000)

# ボットの起動
def run_discord_bot():
    bot.run(DISCORD_TOKEN)

if __name__ == '__main__':
    # FlaskとDiscord Botを別スレッドで実行
    flask_thread = threading.Thread(target=run_flask)
    discord_thread = threading.Thread(target=run_discord_bot)

    flask_thread.start()
    discord_thread.start()

    flask_thread.join()
    discord_thread.join()