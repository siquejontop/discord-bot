import discord
from discord.ext import commands, tasks
import os
import json
from datetime import datetime

BACKUP_FOLDER = "/app/backups"

class BackupSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_backup.start()

    # =====================================================
    # 💾 GUARDAR BACKUP (manual, con permisos)
    # =====================================================
    @commands.command(name="backup")
    @commands.is_owner()
    async def backup(self, ctx):
        guild = ctx.guild
        data = {
            "guild_name": guild.name,
            "guild_description": guild.description,
            "roles": [],
            "categories": [],
            "channels": [],
        }

        # === Roles ===
        for role in guild.roles:
            data["roles"].append({
                "id": role.id,
                "name": role.name,
                "permissions": role.permissions.value,
                "color": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "position": role.position
            })

        # === Categorías ===
        for category in guild.categories:
            data["categories"].append({
                "id": category.id,
                "name": category.name,
                "position": category.position
            })

        # === Canales ===
        for channel in guild.channels:
            overwrites = {}
            for target, perms in channel.overwrites.items():
                overwrites[str(target.id)] = perms._values

            channel_data = {
                "id": channel.id,
                "name": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "category": channel.category.id if channel.category else None,
                "overwrites": overwrites
            }

            if isinstance(channel, discord.TextChannel):
                channel_data.update({
                    "topic": channel.topic,
                    "nsfw": channel.nsfw,
                    "slowmode_delay": channel.slowmode_delay,
                })
            elif isinstance(channel, discord.VoiceChannel):
                channel_data.update({
                    "user_limit": channel.user_limit,
                    "bitrate": channel.bitrate,
                })

            data["channels"].append(channel_data)

        # Guardar en archivo
        os.makedirs(BACKUP_FOLDER, exist_ok=True)  # <-- Asegura la carpeta
        file_name = f"{BACKUP_FOLDER}/backup_{guild.id}_{int(datetime.utcnow().timestamp())}.json"
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        await ctx.send(f"✅ Backup guardado en `{file_name}`")

    # =====================================================
    # ♻️ RESTAURAR BACKUP
    # =====================================================
    @commands.command()
    @commands.is_owner()
    async def restore(self, ctx, backup_file: str):
        """
        Restaura un backup desde un archivo .json
        Puede recibir solo el nombre o la ruta completa.
        """
        # ✅ Si el usuario pasa ruta absoluta (/app/backups/archivo.json), se usa tal cual
        if os.path.isabs(backup_file):
            path = backup_file
        else:
            # ✅ Si solo pasa el nombre, se construye la ruta con BACKUP_FOLDER
            path = os.path.join(BACKUP_FOLDER, backup_file)

        # Verificar si existe
        if not os.path.exists(path):
            return await ctx.send("❌ No encontré ese archivo de backup.")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            guild = ctx.guild  # ✅ Ahora sí obtenemos la guild actual

            # 👇 Ejemplo: si el backup guarda roles
            if "roles" in data:
                for role_data in data["roles"]:
                    await guild.create_role(
                        name=role_data["name"],
                        permissions=discord.Permissions(role_data["permissions"]),
                        colour=discord.Colour(role_data["color"])
                    )

            await ctx.send(f"✅ Backup restaurado desde: `{path}`")

        except Exception as e:
            await ctx.send(f"⚠️ Error restaurando backup: `{e}`")

        # 1. Borrar roles y canales
        for channel in guild.channels:
            try:
                await channel.delete()
            except:
                pass
        for role in guild.roles:
            if not role.is_default():
                try:
                    await role.delete()
                except:
                    pass

        # 2. Restaurar roles
        role_map = {}
        for role_data in sorted(data["roles"], key=lambda r: r["position"]):
            try:
                role = await guild.create_role(
                    name=role_data["name"],
                    permissions=discord.Permissions(role_data["permissions"]),
                    colour=discord.Colour(role_data["color"]),
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"]
                )
                role_map[str(role_data["id"])] = role
            except:
                pass

        # 3. Restaurar categorías
        category_map = {}
        for category_data in data["categories"]:
            try:
                cat = await guild.create_category(
                    name=category_data["name"],
                    position=category_data["position"]
                )
                category_map[str(category_data["id"])] = cat
            except:
                pass

        # 4. Restaurar canales
        for channel_data in data["channels"]:
            try:
                category = category_map.get(str(channel_data["category"]))
                overwrites = {}
                for target_id, perm_values in channel_data["overwrites"].items():
                    target = role_map.get(target_id) or guild.get_member(int(target_id))
                    if target:
                        overwrites[target] = discord.PermissionOverwrite(**perm_values)

                if channel_data["type"] == "text":
                    await guild.create_text_channel(
                        name=channel_data["name"],
                        topic=channel_data.get("topic"),
                        nsfw=channel_data.get("nsfw", False),
                        slowmode_delay=channel_data.get("slowmode_delay", 0),
                        category=category,
                        overwrites=overwrites,
                        position=channel_data["position"]
                    )
                elif channel_data["type"] == "voice":
                    await guild.create_voice_channel(
                        name=channel_data["name"],
                        user_limit=channel_data.get("user_limit", 0),
                        bitrate=channel_data.get("bitrate", 64000),
                        category=category,
                        overwrites=overwrites,
                        position=channel_data["position"]
                    )
            except Exception as e:
                print(f"❌ Error creando canal {channel_data['name']}: {e}")

        await ctx.send("✅ Backup restaurado correctamente.")

    # =====================================================
    # ⏰ Backup automático cada 3 días
    # =====================================================
    @tasks.loop(hours=72)
    async def auto_backup(self):
        for guild in self.bot.guilds:
            data = {
                "guild_name": guild.name,
                "roles": [],
                "categories": [],
                "channels": [],
            }

            for role in guild.roles:
                data["roles"].append({
                    "id": role.id,
                    "name": role.name,
                    "permissions": role.permissions.value,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "position": role.position
                })

            for category in guild.categories:
                data["categories"].append({
                    "id": category.id,
                    "name": category.name,
                    "position": category.position
                })

            for channel in guild.channels:
                overwrites = {}
                for target, perms in channel.overwrites.items():
                    overwrites[str(target.id)] = perms._values

                channel_data = {
                    "id": channel.id,
                    "name": channel.name,
                    "type": str(channel.type),
                    "position": channel.position,
                    "category": channel.category.id if channel.category else None,
                    "overwrites": overwrites
                }
                data["channels"].append(channel_data)

            os.makedirs(BACKUP_FOLDER, exist_ok=True)  # <-- asegura la carpeta
            file_name = f"{BACKUP_FOLDER}/auto_backup_{guild.id}_{int(datetime.utcnow().timestamp())}.json"
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)

            print(f"✅ Auto-backup guardado: {file_name}")

    @auto_backup.before_loop
    async def before_auto_backup(self):
        await self.bot.wait_until_ready()

# =====================================================
# 🔌 Setup obligatorio
# =====================================================
async def setup(bot):
    await bot.add_cog(BackupSystem(bot))
