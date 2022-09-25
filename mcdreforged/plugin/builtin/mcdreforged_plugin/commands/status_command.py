import threading

import psutil

from mcdreforged.command.builder.nodes.basic import Literal
from mcdreforged.command.command_source import CommandSource
from mcdreforged.constants import core_constant
from mcdreforged.minecraft.rtext import RText, RColor, RAction, RStyle
from mcdreforged.permission.permission_level import PermissionLevel
from mcdreforged.plugin.builtin.mcdreforged_plugin.commands.sub_command import SubCommand
from mcdreforged.utils import tree_printer


class StatusCommand(SubCommand):
	def get_command_node(self) -> Literal:
		return (
			self.public_command_root('status').runs(self.print_mcdr_status)
		)

	def print_mcdr_status(self, source: CommandSource):
		def bool_formatter(bl: bool) -> RText:
			return RText(bl, RColor.green if bl else RColor.red)
		rcon_status_dict = {
			True: self.tr('mcdr_command.print_mcdr_status.online'),
			False: self.tr('mcdr_command.print_mcdr_status.offline')
		}

		source.reply(
			RText(self.tr('mcdr_command.print_mcdr_status.line1', core_constant.NAME, core_constant.VERSION)).
			c(RAction.open_url, core_constant.GITHUB_URL).
			h(RText(core_constant.GITHUB_URL, styles=RStyle.underlined, color=RColor.blue))
		)

		if not source.has_permission(PermissionLevel.MCDR_CONTROL_LEVEL):
			return
		source.reply(RText.join('\n', [
			RText(self.tr('mcdr_command.print_mcdr_status.line2', self.tr(self.mcdr_server.mcdr_state.value))),
			RText(self.tr('mcdr_command.print_mcdr_status.line3', self.tr(self.mcdr_server.server_state.value))),
			RText(self.tr('mcdr_command.print_mcdr_status.line4', bool_formatter(self.mcdr_server.is_server_startup()))),
			RText(self.tr('mcdr_command.print_mcdr_status.line5', bool_formatter(self.mcdr_server.should_exit_after_stop()))),
			RText(self.tr('mcdr_command.print_mcdr_status.line6', rcon_status_dict[self.server_interface.is_rcon_running()])),
			RText(self.tr('mcdr_command.print_mcdr_status.line7', self.mcdr_server.plugin_manager.get_plugin_amount())).c(RAction.suggest_command, '!!MCDR plugin list')
		]))

		# ------------ Physical server secrets ------------
		if not source.has_permission(PermissionLevel.PHYSICAL_SERVER_CONTROL_LEVEL):
			return

		process = self.mcdr_server.process
		source.reply(self.tr('mcdr_command.print_mcdr_status.extra.pid', process.pid if process is not None else '§rN/A§r'))
		if process is not None:
			def make_tree(proc: psutil.Process) -> tree_printer.Node:
				node = tree_printer.Node('{}: {}'.format(proc.name(), proc.pid))
				for child_proc in proc.children():
					node.add_child(make_tree(child_proc))
				return node
			try:
				tree = make_tree(psutil.Process(process.pid))
			except psutil.NoSuchProcess:
				self.mcdr_server.logger.exception('Fail to fetch process tree from pid {}', process.pid)
			else:
				tree_printer.print_tree(tree, lambda line: source.reply('  ' + line))

		source.reply(self.tr('mcdr_command.print_mcdr_status.extra.queue', self.mcdr_server.task_executor.task_queue.qsize(), core_constant.MAX_TASK_QUEUE_SIZE))

		source.reply(self.tr('mcdr_command.print_mcdr_status.extra.thread', threading.active_count()))
		thread_pool_counts = 0
		for thread in threading.enumerate():
			name = thread.name
			if not name.startswith('ThreadPoolExecutor-'):
				source.reply('  §7-§r {}'.format(name))
			else:
				thread_pool_counts += 1
		if thread_pool_counts > 0:
			source.reply('  §7-§r ThreadPoolExecutor thread x{}'.format(thread_pool_counts))
