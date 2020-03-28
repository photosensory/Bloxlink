from inspect import iscoroutinefunction
from ..exceptions import PermissionError
from .Permissions import Permissions
from .Args import Args
from discord.utils import find
from resources.constants import OWNER
import re


class Command:
	def __init__(self, command):
		self.name = command.__class__.__name__.replace("Command", "").lower()
		self.subcommands = {}
		self.description = command.__doc__ or "N/A"
		self.dm_allowed = getattr(command, "dm_allowed", False)
		self.full_description = getattr(command, "full_description", self.description)
		self.aliases = getattr(command, "aliases", [])
		self.permissions = getattr(command, "permissions", Permissions())
		self.arguments = getattr(command, "arguments", [])
		self.category = getattr(command, "category", "Miscellaneous")
		self.examples = getattr(command, "examples", [])
		self.hidden = getattr(command, "hidden", self.category == "Developer")
		self.free_to_use = getattr(command, "free_to_use", False)
		self.fn = command.__main__
		self.cooldown = getattr(command, "cooldown", 0)

		self.usage = []
		command_args = self.arguments

		if command_args:
			for arg in command_args:
				if arg.get("optional"):
					if arg.get("default"):
						self.usage.append(f'[{arg.get("name")}={arg.get("default")}]')
					else:
						self.usage.append(f'[{arg.get("name")}]')
				else:
					self.usage.append(f'<{arg.get("name")}>')

		self.usage = " | ".join(self.usage) if self.usage else ""

	def __str__(self):
		return self.name

	def __repr__(self):
		return str(self)

	async def check_permissions(self, author, locale, permissions=None):
		permissions = permissions or self.permissions

		if permissions.developer_only or self.category == "Developer":
			if author.id != OWNER:
				raise PermissionError("This command is reserved for the Bloxlink Developer.")

		if permissions.premium:
			pass # TODO

		try:
			for role_exception in permissions.exceptions["roles"]:
				if find(lambda r: r.name == role_exception, author.roles):
					return True

			if permissions.bloxlink_role:
				role_name = permissions.bloxlink_role
				author_perms = author.guild_permissions

				if role_name == "Bloxlink Manager":
					if author_perms.manage_guild or author_perms.administrator:
						pass
					else:
						raise PermissionError("You need the ``Manage Server`` permission to run this command.")

				elif role_name == "Bloxlink Moderator":
					if author_perms.kick_members or author_perms.ban_members or author_perms.administrator:
						pass
					else:
						raise PermissionError("You need the ``Kick`` or ``Ban`` permission to run this command.")

				elif role_name == "Bloxlink Updater":
					if author_perms.manage_guild or author_perms.administrator or author_perms.manage_roles or find(lambda r: r.name == "Bloxlink Updater", author.roles):
						pass
					else:
						raise PermissionError("You either need: a role called ``Bloxlink Updater``, the ``Manage Roles`` "
											  "role permission, or the ``Manage Server`` role permission.")

				elif role_name == "Bloxlink Admin":
					if author_perms.administrator:
						pass
					else:
						raise PermissionError("You need the ``Administrator`` role permission to run this command.")

			if permissions.allowed.get("discord_perms"):
				for perm in permissions.allowed["discord_perms"]:
					if perm == "Manage Server":
						if author_perms.manage_guild or author_perms.administrator:
							pass
						else:
							raise PermissionError("You need the ``Manage Server`` permission to run this command.")
					else:
						if not getattr(author_perms, perm, False) and not perm.administrator:
							raise PermissionError(f"You need the ``{perm}`` permission to run this command.")


			for role in permissions.allowed["roles"]:
				if not find(lambda r: r.name == role, author.roles):
					raise PermissionError(f"Missing role: ``{role}``")

			if permissions.allowed.get("functions"):
				for function in permissions.allowed["functions"]:

					if iscoroutinefunction(function):
						data = [await function(author)]
					else:
						data = [function(author)]

					if not data[0]:
						raise PermissionError

					if isinstance(data[0], tuple):
						if not data[0][0]:
							raise PermissionError(data[0][1])

		except PermissionError as e:
			if e.args:
				raise PermissionError(e)

			raise PermissionError("You do not meet the required permissions for this command.")

	def parse_flags(self, content):
		flags = {m.group(1): m.group(2) or True for m in re.finditer(r"--?(\w+)(?: ([^-]*)|$)", content)}

		if flags:
			try:
				content = content[content.index("--"):]
			except ValueError:
				try:
					content = content[content.index("-"):]
				except ValueError:
					return {}, ""

		return flags, flags and content or ""
