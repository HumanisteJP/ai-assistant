from discord.ext import commands

class EchoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("EchoCog が初期化されました")

    @commands.Cog.listener()
    async def on_message(self, message):
        # 自分のメッセージには反応しない
        if message.author == self.bot.user:
            return
        
        # DMには反応しない
        if message.guild is None:
            return
            
        # ボットがメンションされているか確認
        if self.bot.user.mentioned_in(message):
            # @everyoneや@hereの特殊メンションがある場合は反応しない
            if message.mention_everyone:
                return
                
            # メンションを除去したメッセージ内容を取得
            content = message.content
            
            # 全てのメンションを削除
            for mention in message.mentions:
                content = content.replace(f'<@{mention.id}>', '')
                content = content.replace(f'<@!{mention.id}>', '')
            
            # 空白を整理
            content = content.strip()
            
            # 内容が空でなければ返信
            if content:
                await message.reply(f"{content}", mention_author=False)
            else:
                await message.reply("何かお手伝いできることはありますか？", mention_author=False)

def setup(bot):
    bot.add_cog(EchoCog(bot)) 