import axipy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtWidgets import QDockWidget
from .tms_utils import doc_index_filename
from .tms_widget import TmsWidget


class DockWidget(QDockWidget):

    closeWidget = Signal()

    def __init__(self, name: str) -> None:
        super().__init__(name)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closeWidget.emit()
        super().closeEvent(event)


class TileServicesPlugin(axipy.Plugin):

    __dock: DockWidget | None

    def load(self) -> None:
        self.__icon = QIcon(str(self.plugin_dir / "tms_icon.svg"))
        self.__button = self.create_action(
            self.tr("Карты из Интернета"),
            icon=self.__icon,
            on_click=self.show_widget,
            tooltip=self.tr("Добавление слоя из каталога Интернет-карт"),
            doc_file=doc_index_filename(axipy.CurrentSettings.Language),
        )
        self.__button.action.setCheckable(True)
        position = axipy.Position(self.tr("Основные"), self.tr("Команды"))
        position.add(self.__button)
        self.__dock = None

    def __remove_dock(self) -> None:
        if self.__dock is not None:
            self.__dock.close()
            self.__dock = None

    def unload(self) -> None:
        self.__remove_dock()
        self.__button.remove()

    def __close_dock(self) -> None:
        self.__button.action.setChecked(False)
        self.__remove_dock()

    def show_widget(self) -> None:
        if self.__dock is None:
            title = self.tr("Карты из Интернета")
            self.__dock = DockWidget(title)
            self.__dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            w = TmsWidget(self)
            w.setWindowTitle(title)
            self.__dock.setWidget(w)
            self.__dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            axipy.mainwindow.add_dock_widget(self.__dock, axipy.DockWidgetArea.Right, self.__icon)
            self.__dock.closeWidget.connect(self.__close_dock)
        else:
            self.__remove_dock()
