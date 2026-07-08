# Этот файл — вспомогательный патч, применяется один раз вручную или автоматически.
# Добавить в window.py после строки self._build_inwork_tab(tab_inwork):
#
#        from gui.channel_finder_tab import ChannelFinderTab
#        self._channel_finder_tab = ChannelFinderTab(self.root, self.notebook)
#
# Место вставки: между _build_inwork_tab и self.status_label
