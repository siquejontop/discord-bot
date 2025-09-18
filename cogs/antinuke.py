# cogs/antinuke.py
import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime, timedelta

CONFIG_FILE = "antinuke_config.json"
DEFAULT_CONFIG = {
    # por guild_id:
    # "guilds": {
    #   "<guild_id>": {
    #       "log_channel": 1234567890,
    #       "whitelist_users": [111,222],
    #       "whitelist_roles": [333,444],
    #       "thresholds": {...}
    #   }
    # }
    "guilds": {}
}

# valores por defecto de thresholds (puedes editarlos por guild con comando)
DEFAULT_THRESHOLDS = {
    "mass_ban_count": 3,           # N bans en timeframe -> sancionar
    "mass_ban_window_seconds": 10,
    "mass_kick_count": 5,
    "mass_kick_window_seconds": 10,
    "mass_channel_delete_count": 4,
    "mass_channel_window_seconds": 8,
    "mass_channel_create_count": 6,
    "mass_channel_create_window_seconds": 8,
    "mass_role_delete_count": 6,
    "mass_role_window_seconds": 8,
    "mass_role_create_count": 8,
    "mass_role_create_window_seconds": 8,
    "webhook_create_count": 5,
    "webhook_window_seconds": 10,
    "emoji_create_count": 10,
    "emoji_window_seconds": 20,
    "strikes_to_ban": 3,
    "strike_expire_hours": 24
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

class AntiNuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = load_config()
        self.actions = {}  # {guild_id: {executor_id: {action: [timestamps]}}}
        self.strikes = {}  # {guild_id: {user_id: [{"when": ts, "reason": str}]}}
        self.cleanup_task.start()

    def cog_unload(self):
        self.cleanup_task.cancel()

    # -------------------------
    # Helpers
    # -------------------------
    def get_gcfg(self, guild: discord.Guild):
        gid = str(guild.id)
        if gid not in self.cfg["guilds"]:
            self.cfg["guilds"][gid] = {
                "log_channel": None,
                "whitelist_users": [],
                "whitelist_roles": [],
                "thresholds": DEFAULT_THRESHOLDS.copy()
            }
            save_config(self.cfg)
        # ensure thresholds exist
        gcfg = self.cfg["guilds"][gid]
        if "thresholds" not in gcfg:
            gcfg["thresholds"] = DEFAULT_THRESHOLDS.copy()
        return gcfg

    def is_bot_owner_or_guild_owner(self, ctx):
        # allow if bot owner or guild owner
        return self.bot.is_owner(ctx.author) or (ctx.guild and ctx.guild.owner_id == ctx.author.id)

    async def is_allowed_executor(self, guild: discord.Guild, member: discord.Member):
        # allowed if bot owner, guild owner, in whitelist users, or has any whitelist role
        gcfg = self.get_gcfg(guild)
        if await self.bot.is_owner(member):
            return True
        if guild.owner_id == member.id:
            return True
        if member.id in gcfg.get("whitelist_users", []):
            return True
        for r in member.roles:
            if r.id in gcfg.get("whitelist_roles", []):
                return True
        return False

    def log_channel_obj(self, guild: discord.Guild):
        gcfg = self.get_gcfg(guild)
        cid = gcfg.get("log_channel")
        if not cid:
            return None
        return guild.get_channel(cid)

    async def log_embed(self, guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.red(), fields: list = None):
        ch = self.log_channel_obj(guild)
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.utcnow())
        if fields:
            for n, v, inline in fields:
                embed.add_field(name=n, value=v, inline=inline)
        if ch:
            try:
                await ch.send(embed=embed)
            except Exception:
                # fallback to default system channel if exists
                if guild.system_channel:
                    try:
                        await guild.system_channel.send(embed=embed)
                    except:
                        pass

    def record_action(self, guild_id: int, executor_id: int, action: str):
        gid = str(guild_id)
        self.actions.setdefault(gid, {})
        self.actions[gid].setdefault(str(executor_id), {})
        self.actions[gid][str(executor_id)].setdefault(action, [])
        self.actions[gid][str(executor_id)][action].append(datetime.utcnow())

    def recent_count(self, guild_id: int, executor_id: int, action: str, window_seconds: int):
        gid = str(guild_id)
        now = datetime.utcnow()
        arr = self.actions.get(gid, {}).get(str(executor_id), {}).get(action, [])
        # keep only within window
        cutoff = now - timedelta(seconds=window_seconds)
        arr = [t for t in arr if t >= cutoff]
        # replace with filtered
        if gid in self.actions and str(executor_id) in self.actions[gid]:
            self.actions[gid][str(executor_id)][action] = arr
        return len(arr)

    async def punish_executor(self, guild: discord.Guild, executor: discord.Member, reason: str):
        # If executor allowed (whitelist/owner) skip
        if await self.is_allowed_executor(guild, executor):
            await self.log_embed(guild, "Acción detectada, pero ejecutor whitelisted", f"{executor} ({executor.id}) realizó la acción pero está en whitelist. Se ignoró.", discord.Color.orange())
            return False

        # Try to ban; fallback: kick; fallback: strip roles
        try:
            await guild.ban(executor, reason=f"AntiNuke - {reason}")
            await self.log_embed(guild, "Usuario baneado (AntiNuke)", f"{executor} ({executor.id}) fue baneado por: {reason}", discord.Color.red())
            return True
        except Exception:
            try:
                await guild.kick(executor, reason=f"AntiNuke - {reason}")
                await self.log_embed(guild, "Usuario expulsado (AntiNuke)", f"{executor} ({executor.id}) fue expulsado por: {reason}", discord.Color.red())
                return True
            except Exception:
                # try to remove all roles (except @everyone) if bot has perms
                try:
                    roles_to_remove = [r for r in executor.roles if r != guild.default_role]
                    await executor.remove_roles(*roles_to_remove, reason=f"AntiNuke - {reason}")
                    await self.log_embed(guild, "Roles removidos (AntiNuke)", f"Se removieron roles de {executor} ({executor.id}) por: {reason}", discord.Color.red())
                    return True
                except Exception as e:
                    await self.log_embed(guild, "Fallo al sancionar", f"No pude sancionar a {executor} ({executor.id}). Error: {e}", discord.Color.dark_red())
                    return False

    def add_strike(self, guild: discord.Guild, user_id: int, reason: str):
        gid = str(guild.id)
        self.strikes.setdefault(gid, {})
        self.strikes[gid].setdefault(str(user_id), [])
        self.strikes[gid][str(user_id)].append({"when": datetime.utcnow().isoformat(), "reason": reason})

    def strikes_count(self, guild: discord.Guild, user_id: int, expire_hours: int):
        gid = str(guild.id)
        arr = self.strikes.get(gid, {}).get(str(user_id), [])
        if not arr:
            return 0
        cutoff = datetime.utcnow() - timedelta(hours=expire_hours)
        arr = [s for s in arr if datetime.fromisoformat(s["when"]) >= cutoff]
        # replace with filtered
        if gid in self.strikes and str(user_id) in self.strikes[gid]:
            self.strikes[gid][str(user_id)] = arr
        return len(arr)

    # -------------------------
    # Audit helpers
    # -------------------------
    async def get_audit_executor(self, guild: discord.Guild, action: discord.AuditLogAction):
        # return the user who last did this action (most recent)
        try:
            async for entry in guild.audit_logs(limit=1, action=action):
                return entry
        except Exception:
            return None

    # -------------------------
    # EVENTS: channels/roles/webhooks/emoji/member join/ban/kick
    # -------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        entry = await self.get_audit_executor(guild, discord.AuditLogAction.channel_delete)
        if not entry:
            return
        executor = entry.user
        # record
        self.record_action(guild.id, executor.id, "channel_delete")
        gcfg = self.get_gcfg(guild)
        count = self.recent_count(guild.id, executor.id, "channel_delete", gcfg["thresholds"].get("mass_channel_window_seconds", 8))
        if count >= gcfg["thresholds"].get("mass_channel_delete_count", 4):
            reason = f"Mass channel delete ({count} in window)"
            await self.log_embed(guild, "Mass channel delete detectado", f"{executor} eliminó {count} canales en poco tiempo.", fields=[
                ("Executor", f"{executor} ({executor.id})", False),
                ("Canal eliminado", f"{channel.name} ({channel.id})", False)
            ])
            # punish
            await self.punish_executor(guild, executor, reason)
            self.add_strike(guild, executor.id, reason)
            strikes = self.strikes_count(guild, executor.id, gcfg["thresholds"].get("strike_expire_hours", 24))
            if strikes >= gcfg["thresholds"].get("strikes_to_ban", 3):
                await self.punish_executor(guild, executor, f"Exceeded strikes ({strikes})")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        guild = channel.guild
        entry = await self.get_audit_executor(guild, discord.AuditLogAction.channel_create)
        if not entry:
            return
        executor = entry.user
        self.record_action(guild.id, executor.id, "channel_create")
        gcfg = self.get_gcfg(guild)
        count = self.recent_count(guild.id, executor.id, "channel_create", gcfg["thresholds"].get("mass_channel_create_window_seconds", 8))
        if count >= gcfg["thresholds"].get("mass_channel_create_count", 6):
            reason = f"Mass channel create ({count})"
            await self.log_embed(guild, "Mass channel create detectado", f"{executor} creó {count} canales en poco tiempo.", fields=[
                ("Executor", f"{executor} ({executor.id})", False),
                ("Channel example", f"{channel.name} ({channel.id})", False)
            ])
            await self.punish_executor(guild, executor, reason)
            self.add_strike(guild, executor.id, reason)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        entry = await self.get_audit_executor(guild, discord.AuditLogAction.role_delete)
        if not entry:
            return
        executor = entry.user
        self.record_action(guild.id, executor.id, "role_delete")
        gcfg = self.get_gcfg(guild)
        count = self.recent_count(guild.id, executor.id, "role_delete", gcfg["thresholds"].get("mass_role_window_seconds", 8))
        if count >= gcfg["thresholds"].get("mass_role_delete_count", 6):
            reason = f"Mass role delete ({count})"
            await self.log_embed(guild, "Mass role delete detectado", f"{executor} eliminó {count} roles en poco tiempo.", fields=[
                ("Executor", f"{executor} ({executor.id})", False),
                ("Role example", f"{role.name} ({role.id})", False)
            ])
            await self.punish_executor(guild, executor, reason)
            self.add_strike(guild, executor.id, reason)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        guild = role.guild
        entry = await self.get_audit_executor(guild, discord.AuditLogAction.role_create)
        if not entry:
            return
        executor = entry.user
        self.record_action(guild.id, executor.id, "role_create")
        gcfg = self.get_gcfg(guild)
        count = self.recent_count(guild.id, executor.id, "role_create", gcfg["thresholds"].get("mass_role_create_window_seconds", 8))
        if count >= gcfg["thresholds"].get("mass_role_create_count", 8):
            reason = f"Mass role create ({count})"
            await self.log_embed(guild, "Mass role create detectado", f"{executor} creó {count} roles en poco tiempo.", fields=[
                ("Executor", f"{executor} ({executor.id})", False),
                ("Role example", f"{role.name} ({role.id})", False)
            ])
            await self.punish_executor(guild, executor, reason)
            self.add_strike(guild, executor.id, reason)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        # audit log to find who banned
        entry = await self.get_audit_executor(guild, discord.AuditLogAction.ban)
        if not entry:
            return
        executor = entry.user
        self.record_action(guild.id, executor.id, "ban")
        gcfg = self.get_gcfg(guild)
        count = self.recent_count(guild.id, executor.id, "ban", gcfg["thresholds"].get("mass_ban_window_seconds", 10))
        if count >= gcfg["thresholds"].get("mass_ban_count", 3):
            reason = f"Mass ban ({count})"
            await self.log_embed(guild, "Mass ban detectado", f"{executor} baneó {count} usuarios en poco tiempo.", fields=[
                ("Executor", f"{executor} ({executor.id})", False)
            ])
            await self.punish_executor(guild, executor, reason)
            self.add_strike(guild, executor.id, reason)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # cannot know if kick or left; detect kicks via audit_logs if possible
        guild = member.guild
        # check latest kick audit
        try:
            async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.kick):
                # entry.target is the member
                if entry.target.id == member.id:
                    executor = entry.user
                    self.record_action(guild.id, executor.id, "kick")
                    gcfg = self.get_gcfg(guild)
                    count = self.recent_count(guild.id, executor.id, "kick", gcfg["thresholds"].get("mass_kick_window_seconds", 10))
                    if count >= gcfg["thresholds"].get("mass_kick_count", 5):
                        reason = f"Mass kick ({count})"
                        await self.log_embed(guild, "Mass kick detectado", f"{executor} expulsó {count} miembros en poco tiempo.", fields=[
                            ("Executor", f"{executor} ({executor.id})", False),
                        ])
                        await self.punish_executor(guild, executor, reason)
                        self.add_strike(guild, executor.id, reason)
                    break
        except Exception:
            return

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        guild = channel.guild
        # can't get creator in event, check audit logs for webhook create
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.webhook_create):
                executor = entry.user
                self.record_action(guild.id, executor.id, "webhook_create")
                gcfg = self.get_gcfg(guild)
                count = self.recent_count(guild.id, executor.id, "webhook_create", gcfg["thresholds"].get("webhook_window_seconds", 10))
                if count >= gcfg["thresholds"].get("webhook_create_count", 5):
                    reason = f"Mass webhook create ({count})"
                    await self.log_embed(guild, "Mass webhook create detectado", f"{executor} creó {count} webhooks en poco tiempo.", fields=[
                        ("Executor", f"{executor} ({executor.id})", False),
                        ("Channel", f"{channel.name} ({channel.id})", False)
                    ])
                    await self.punish_executor(guild, executor, reason)
                    self.add_strike(guild, executor.id, reason)
                break
        except Exception:
            return

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        # compare additions
        added = [e for e in after if e.id not in [b.id for b in before]]
        removed = [b for b in before if b.id not in [a.id for a in after]]
        # check audit logs for emoji create/delete
        if added:
            try:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.emoji_create):
                    executor = entry.user
                    self.record_action(guild.id, executor.id, "emoji_create")
                    gcfg = self.get_gcfg(guild)
                    count = self.recent_count(guild.id, executor.id, "emoji_create", gcfg["thresholds"].get("emoji_window_seconds", 20))
                    if count >= gcfg["thresholds"].get("emoji_create_count", 10):
                        reason = f"Mass emoji create ({count})"
                        await self.log_embed(guild, "Mass emoji create detectado", f"{executor} creó {count} emojis en poco tiempo.", fields=[
                            ("Executor", f"{executor} ({executor.id})", False),
                            ("Ejemplo", f"{added[0].name} ({added[0].id})", False)
                        ])
                        await self.punish_executor(guild, executor, reason)
                        self.add_strike(guild, executor.id, reason)
                    break
            except Exception:
                pass
        if removed:
            try:
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.emoji_delete):
                    executor = entry.user
                    self.record_action(guild.id, executor.id, "emoji_delete")
                    # can handle thresholds similarly if desired
                    break
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # if a bot joins and is not whitelisted -> ban it
        if not member.bot:
            return
        guild = member.guild
        gcfg = self.get_gcfg(guild)
        # if bot in whitelist roles/users, skip
        wh_users = gcfg.get("whitelist_users", [])
        wh_roles = gcfg.get("whitelist_roles", [])
        if member.id in wh_users:
            return
        # check bot whitelist by ID via guild config users
        # if not allowed -> ban bot
        try:
            if not await self.is_allowed_executor(guild, member):  # member is bot but isn't whitelisted
                try:
                    await guild.ban(member, reason="AntiNuke - bot not whitelisted")
                    await self.log_embed(guild, "Bot no autorizado baneado", f"Se detectó un bot no whitelisted: {member} ({member.id})", discord.Color.red())
                except Exception:
                    await self.log_embed(guild, "No pude banear al bot no autorizado", f"{member} ({member.id})", discord.Color.orange())
        except Exception:
            return

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        # detect dangerous permission escalation
        guild = before.guild
        # if permissions changed to add dangerous perms like administrator or manage_guild, check executor
        if before.permissions == after.permissions:
            return
        added_perms_value = after.permissions.value & (~before.permissions.value)
        added = discord.Permissions(added_perms_value)
        dangerous = any([
            added.administrator,
            added.manage_guild,
            added.ban_members,
            added.kick_members,
            added.manage_roles,
            added.manage_channels,
            added.manage_webhooks,
            added.manage_emojis
        ])
        if dangerous:
            entry = await self.get_audit_executor(guild, discord.AuditLogAction.role_update)
            if not entry:
                return
            executor = entry.user
            # if executor is whitelisted skip
            if await self.is_allowed_executor(guild, executor):
                await self.log_embed(guild, "Role editado con permisos peligrosos por whitelisted", f"{executor} ({executor.id}) editó {after.name} agregando permisos peligrosos, pero está whitelisted.", discord.Color.orange())
                return
            # revert permissions
            try:
                await after.edit(permissions=before.permissions, reason="AntiNuke - revert dangerous permission escalation")
                await self.log_embed(guild, "Permisos revertidos (AntiNuke)", f"Se revirtieron permisos del rol {after.name} porque {executor} agregó permisos peligrosos.", discord.Color.red(), fields=[
                    ("Executor", f"{executor} ({executor.id})", False),
                    ("Rol", f"{after.name} ({after.id})", False)
                ])
            except Exception as e:
                await self.log_embed(guild, "Fallo al revertir permisos", f"No pude revertir el rol {after.name}. Error: {e}", discord.Color.dark_red())
            # give strike & punish
            reason = "Dangerous permission escalation"
            self.add_strike(guild, executor.id, reason)
            gcfg = self.get_gcfg(guild)
            strikes = self.strikes_count(guild, executor.id, gcfg["thresholds"].get("strike_expire_hours", 24))
            if strikes >= gcfg["thresholds"].get("strikes_to_ban", 3):
                await self.punish_executor(guild, executor, f"Exceeded strikes ({strikes})")
            else:
                await self.punish_executor(guild, executor, reason)

    # -------------------------
    # COMMANDS: whitelist manage, set log channel, show config
    # Only bot owner or guild owner can manage via checks inside command
    # -------------------------
    def check_guild_owner_or_bot_owner(self, ctx):
        return (self.bot.is_owner(ctx.author) or ctx.guild and ctx.guild.owner_id == ctx.author.id)

    @commands.command(name="antinuke_setlog")
    async def antinuke_setlog(self, ctx, channel_id: int = None):
        if not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("❌ Solo el owner del bot o el owner del servidor pueden ejecutar esto.")
        if channel_id is None:
            return await ctx.send("❌ Indica la ID del canal para logs: `$antinuke_setlog 123456789012345678`")
        gcfg = self.get_gcfg(ctx.guild)
        gcfg["log_channel"] = channel_id
        save_config(self.cfg)
        await ctx.send(f"✅ Canal de logs guardado: {channel_id}")

    @commands.command(name="antinuke_whitelist_user")
    async def antinuke_whitelist_user(self, ctx, user_id: int = None):
        if not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("❌ Solo el owner del bot o el owner del servidor pueden ejecutar esto.")
        if not user_id:
            return await ctx.send("❌ Indica la ID del usuario a whitelistear.")
        gcfg = self.get_gcfg(ctx.guild)
        if user_id in gcfg.get("whitelist_users", []):
            return await ctx.send("⚠️ Ese usuario ya está en whitelist.")
        gcfg.setdefault("whitelist_users", []).append(user_id)
        save_config(self.cfg)
        await ctx.send(f"✅ Usuario {user_id} añadido a whitelist.")

    @commands.command(name="antinuke_unwhitelist_user")
    async def antinuke_unwhitelist_user(self, ctx, user_id: int = None):
        if not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("❌ Solo el owner del bot o el owner del servidor pueden ejecutar esto.")
        if not user_id:
            return await ctx.send("❌ Indica la ID del usuario a remover de whitelist.")
        gcfg = self.get_gcfg(ctx.guild)
        if user_id not in gcfg.get("whitelist_users", []):
            return await ctx.send("⚠️ Ese usuario no está en whitelist.")
        gcfg["whitelist_users"].remove(user_id)
        save_config(self.cfg)
        await ctx.send(f"✅ Usuario {user_id} removido de whitelist.")

    @commands.command(name="antinuke_whitelist_role")
    async def antinuke_whitelist_role(self, ctx, role_id: int = None):
        if not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("❌ Solo el owner del bot o el owner del servidor pueden ejecutar esto.")
        if not role_id:
            return await ctx.send("❌ Indica la ID del rol a whitelistear.")
        gcfg = self.get_gcfg(ctx.guild)
        if role_id in gcfg.get("whitelist_roles", []):
            return await ctx.send("⚠️ Ese rol ya está en whitelist.")
        gcfg.setdefault("whitelist_roles", []).append(role_id)
        save_config(self.cfg)
        await ctx.send(f"✅ Rol {role_id} añadido a whitelist.")

    @commands.command(name="antinuke_unwhitelist_role")
    async def antinuke_unwhitelist_role(self, ctx, role_id: int = None):
        if not (await self.bot.is_owner(ctx.author) or ctx.guild.owner_id == ctx.author.id):
            return await ctx.send("❌ Solo el owner del bot o el owner del servidor pueden ejecutar esto.")
        if not role_id:
            return await ctx.send("❌ Indica la ID del rol a remover de whitelist.")
        gcfg = self.get_gcfg(ctx.guild)
        if role_id not in gcfg.get("whitelist_roles", []):
            return await ctx.send("⚠️ Ese rol no está en whitelist.")
        gcfg["whitelist_roles"].remove(role_id)
        save_config(self.cfg)
        await ctx.send(f"✅ Rol {role_id} removido de whitelist.")

    @commands.command(name="antinuke_show")
    async def antinuke_show(self, ctx):
        gcfg = self.get_gcfg(ctx.guild)
        embed = discord.Embed(title="AntiNuke - Configuración del servidor", color=discord.Color.blue(), timestamp=datetime.utcnow())
        embed.add_field(name="Log channel ID", value=str(gcfg.get("log_channel")), inline=False)
        embed.add_field(name="Whitelist users", value=", ".join([str(x) for x in gcfg.get("whitelist_users", [])]) or "Ninguno", inline=False)
        embed.add_field(name="Whitelist roles", value=", ".join([str(x) for x in gcfg.get("whitelist_roles", [])]) or "Ninguno", inline=False)
        await ctx.send(embed=embed)

    # -------------------------
    # background cleanup of old actions/strikes
    # -------------------------
    @tasks.loop(minutes=10)
    async def cleanup_task(self):
        # clean actions older than largest window (just keep last 1 hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        for gid, execs in list(self.actions.items()):
            for eid, acts in list(execs.items()):
                for action, arr in list(acts.items()):
                    arr_filtered = [t for t in arr if t >= cutoff]
                    self.actions[gid][eid][action] = arr_filtered

        # expire strikes that are older than threshold (per guild)
        for gid, users in list(self.strikes.items()):
            g = None
            try:
                g = self.bot.get_guild(int(gid))
            except:
                g = None
            for uid, arr in list(users.items()):
                # get guild threshold or default
                if g:
                    gcfg = self.get_gcfg(g)
                    expire_hours = gcfg["thresholds"].get("strike_expire_hours", 24)
                else:
                    expire_hours = DEFAULT_THRESHOLDS["strike_expire_hours"]
                cutoff = datetime.utcnow() - timedelta(hours=expire_hours)
                new_arr = [s for s in arr if datetime.fromisoformat(s["when"]) >= cutoff]
                self.strikes[gid][uid] = new_arr

    @cleanup_task.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

# setup
async def setup(bot):
    await bot.add_cog(AntiNuke(bot))
