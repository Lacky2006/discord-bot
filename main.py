import discord
from discord.ext import commands
import os
import datetime
import pytz
from flask import Flask
from threading import Thread

# --- KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy!"

def run_flask_app():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():  
    t = Thread(target=run_flask_app)
    t.start()

# --- MÚI GIỜ VIỆT NAM ---
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# --- INTENTS DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True       

bot = commands.Bot(command_prefix='!', intents=intents)
user_sessions = {}

@bot.event
async def on_ready():
    print(f'Bot đã đăng nhập với tên: {bot.user.name}')
    print(f'ID Bot: {bot.user.id}')
    print('--------------------')

@bot.command(name='checkin')
async def check_in(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.display_name

    current_session = None
    if user_id in user_sessions and user_sessions[user_id]:
        last_session = user_sessions[user_id][-1]
        if "check_out" not in last_session:
            current_session = last_session

    if current_session:
        await ctx.send(f'{user_name}, bạn đã chấm công vào rồi. Vui lòng sử dụng `!checkout` khi kết thúc.')
        return

    check_in_time = datetime.datetime.now(vietnam_tz)

    if user_id not in user_sessions:
        user_sessions[user_id] = []

    user_sessions[user_id].append({"check_in": check_in_time})

    await ctx.send(f'{user_name} đã chấm công vào lúc: {check_in_time.strftime("%H:%M:%S ngày %d/%m/%Y")}')
    print(f'{user_name} (ID: {user_id}) đã chấm công vào.')

@bot.command(name='checkout')
async def check_out(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.display_name

    if user_id not in user_sessions or not user_sessions[user_id]:
        await ctx.send(f'{user_name}, bạn chưa chấm công vào. Vui lòng sử dụng `!checkin` trước.')
        return

    last_session = user_sessions[user_id][-1]

    if "check_out" in last_session:
        await ctx.send(f'{user_name}, bạn chưa chấm công vào. Vui lòng sử dụng `!checkin` trước.')
        return

    check_out_time = datetime.datetime.now(vietnam_tz)
    last_session["check_out"] = check_out_time

    check_in_time = last_session["check_in"]
    time_worked = check_out_time - check_in_time
    hours, remainder = divmod(time_worked.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    await ctx.send(
        f'{user_name} đã chấm công ra lúc: {check_out_time.strftime("%H:%M:%S ngày %d/%m/%Y")}\n'
        f'Thời gian làm việc trong phiên này: {int(hours)} giờ {int(minutes)} phút {int(seconds)} giây.'
    )
    print(f'{user_name} (ID: {user_id}) đã chấm công ra.')

@bot.command(name='mytime')
async def my_time(ctx):
    user_id = ctx.author.id
    user_name = ctx.author.display_name

    if user_id not in user_sessions or not user_sessions[user_id]:
        await ctx.send(f'{user_name}, bạn chưa có dữ liệu chấm công nào.')
        return

    total_seconds_worked = 0
    detailed_report = []

    for session in user_sessions[user_id]:
        if "check_in" in session and "check_out" in session:
            check_in = session["check_in"]
            check_out = session["check_out"]
            duration = check_out - check_in
            total_seconds_worked += duration.total_seconds()

            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            detailed_report.append(
                f"- Từ {check_in.strftime('%H:%M')} đến {check_out.strftime('%H:%M')}: "
                f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            )
        elif "check_in" in session and "check_out" not in session:
            check_in = session["check_in"]
            detailed_report.append(
                f"- Đang làm việc từ: {check_in.strftime('%H:%M:%S ngày %d/%m/%Y')} (chưa chấm công ra)"
            )

    total_hours, total_remainder = divmod(total_seconds_worked, 3600)
    total_minutes, total_seconds = divmod(total_remainder, 60)

    response_message = f'**Tổng thời gian làm việc của {user_name}:**\n'
    response_message += f'Tổng cộng: {int(total_hours)} giờ {int(total_minutes)} phút {int(total_seconds)} giây.\n\n'

    if detailed_report:
        response_message += '**Chi tiết các phiên làm việc đã hoàn thành:**\n'
        response_message += '\n'.join(detailed_report)

    if len(response_message) > 2000:
        chunks = [response_message[i:i+1990] for i in range(0, len(response_message), 1990)]
        for i, chunk in enumerate(chunks):
            await ctx.send(chunk + ("\n... (tiếp theo)" if i < len(chunks)-1 else ""))
    else:
        await ctx.send(response_message)

@bot.command(name='report')
async def report(ctx):
    if not user_sessions:
        await ctx.send("Chưa có dữ liệu chấm công nào.")
        return

    report_message = "Báo cáo chấm công tổng hợp:\n"
    for user_id, sessions in user_sessions.items():
        user = bot.get_user(user_id)
        user_name = user.display_name if user else f"Người dùng ID: {user_id}"

        total_user_seconds = 0
        current_status = "Đã chấm công ra"

        for session in sessions:
            if "check_in" in session and "check_out" in session:
                duration = session["check_out"] - session["check_in"]
                total_user_seconds += duration.total_seconds()
            elif "check_in" in session and "check_out" not in session:
                current_status = "Đang làm việc"

        total_hours, total_remainder = divmod(total_user_seconds, 3600)
        total_minutes, total_seconds = divmod(total_remainder, 60)

        report_message += f"\n**{user_name}**:\n"
        report_message += f"- Trạng thái hiện tại: {current_status}\n"
        report_message += f"- Tổng thời gian làm việc đã hoàn thành: {int(total_hours)} giờ {int(total_minutes)} phút {int(total_seconds)} giây.\n"

        if current_status == "Đang làm việc":
            last_session = sessions[-1]
            check_in_time = last_session["check_in"]
            report_message += f"- Phiên đang mở từ: {check_in_time.strftime('%H:%M:%S ngày %d/%m/%Y')}\n"

    if len(report_message) > 2000:
        chunks = [report_message[i:i+1990] for i in range(0, len(report_message), 1990)]
        for i, chunk in enumerate(chunks):
            await ctx.send(chunk + ("\n... (tiếp theo)" if i < len(chunks)-1 else ""))
    else:
        await ctx.send(report_message)

@bot.command(name='alltime')
async def all_time_summary(ctx):
    if not user_sessions:
        await ctx.send("Chưa có dữ liệu chấm công của bất kỳ ai.")
        return

    summary_message = "**Tổng thời gian làm việc của tất cả mọi người:**\n\n"
    user_summaries = []

    for user_id, sessions in user_sessions.items():
        user = bot.get_user(user_id)
        user_name = user.display_name if user else f"Người dùng ID: {user_id}"

        total_user_seconds = 0

        for session in sessions:
            if "check_in" in session and "check_out" in session:
                duration = session["check_out"] - session["check_in"]
                total_user_seconds += duration.total_seconds()

        total_hours, remainder = divmod(total_user_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        user_summaries.append({
            "name": user_name,
            "total_seconds": total_user_seconds,
            "display_time": f"{int(total_hours)}h {int(minutes)}m {int(seconds)}s"
        })

    user_summaries.sort(key=lambda x: x["total_seconds"], reverse=True)

    for summary in user_summaries:
        summary_message += f"**{summary['name']}**: {summary['display_time']}\n"

    if len(summary_message) > 2000:
        chunks = [summary_message[i:i+1990] for i in range(0, len(summary_message), 1990)]
        for i, chunk in enumerate(chunks):
            await ctx.send(chunk + ("\n... (tiếp theo)" if i < len(chunks)-1 else ""))
    else:
        await ctx.send(summary_message)

# ✅ CHỈ CÒN 1 LỆNH CLEAN, AI CŨNG DÙNG ĐƯỢC
@bot.command(name='clean')
async def clean_data(ctx):
    global user_sessions
    user_sessions = {}
    await ctx.send("Đã xoá tất cả dữ liệu chấm công cũ.")
    print(f"Dữ liệu chấm công đã được xoá bởi {ctx.author.display_name} (ID: {ctx.author.id}).")

# --- CHẠY BOT ---
keep_alive()
bot_token = os.environ.get("DISCORD_BOT_TOKEN") 
if bot_token:
    bot.run(bot_token)
else:
    print("Lỗi: Không tìm thấy DISCORD_BOT_TOKEN trong biến môi trường.")
    print("Vui lòng thêm biến môi trường 'DISCORD_BOT_TOKEN' với giá trị là token bot của bạn.")
