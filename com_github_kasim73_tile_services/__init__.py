from axipy import AxiomaPlugin, Position
from axipy.app import mainwindow, Version

from PySide2.QtWidgets import QDockWidget
from PySide2.QtGui import QIcon
from PySide2.QtCore import Qt, Signal, QObject

from .TmsWidget import TmsWidget
from .TmsUtils import doc_index_filename


class DockWidget(QDockWidget):

    closeWidget = Signal()

    def __init__(self, name) -> None:
        super().__init__(name)

    def closeEvent(self, event):
        self.closeWidget.emit()
        super().closeEvent(event)


class Plugin(AxiomaPlugin):
    def load(self):
        self.__icon = QIcon(self.local_file('tms_icon.svg'))
        self.__button = self.create_action(
            self.tr('Карты из Интернета'),
            icon = self.__icon,
            on_click = self.show_widget,
            tooltip = self.tr('Добавление слоя из каталога Интернет-карт'),
            doc_file = doc_index_filename(self.language))
        self.__button.action.setCheckable(True)
        position = Position(self.tr('Основные'), self.tr('Команды'))
        position.add(self.__button)
        self.__dock = None

    def __remove_dock(self):
        if self.__dock is not None:
            mainwindow.remove_dock_widget(self.__dock)
            self.__dock = None

    def unload(self):
        self.__remove_dock()
        self.__button.remove()

    def __close_dock(self):
        self.__button.action.setChecked(False)
        self.__remove_dock()

    def show_widget(self):
        if self.__dock is None:
            title = self.tr('Карты из Интернета')
            self.__dock = DockWidget(title)
            w = TmsWidget(self)
            w.setWindowTitle(title)
            self.__dock.setWidget(w)
            self.__dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            if (Version.segments()[0] >= 4):
                mainwindow.add_dock_widget(self.__dock, Qt.RightDockWidgetArea, self.__icon)
            else:
                mainwindow.add_dock_widget(self.__dock, Qt.RightDockWidgetArea)
            self.__dock.closeWidget.connect(self.__close_dock)
        else:
            self.__remove_dock()
