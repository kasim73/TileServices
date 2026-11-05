import axipy
import os
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QIcon, QDesktopServices, QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QSplitter, QToolBar, QMessageBox, QSizePolicy
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen
from .tms_tree_widget import TmsTreeWidget
from .tms_utils import doc_index_filename, json_filename

if TYPE_CHECKING:
    from .plugin import TileServicesPlugin


class ToolBar(QToolBar):

    def __init__(self) -> None:
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.setAllowedAreas(Qt.ToolBarArea.NoToolBarArea)
        self.setIconSize(QSize(16, 16))


class TmsWidget(QWidget):

    def __init__(self, plugin: "TileServicesPlugin") -> None:
        super().__init__()
        self.__plugin = plugin
        self._tr = plugin.tr
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        tb_main = ToolBar()

        self.action_open = QAction(QIcon(str(plugin.plugin_dir / "open.png")), self._tr("Открыть"))
        self.action_open.triggered.connect(self.__open_triggered)
        self.action_open.setToolTip(self._tr("Открыть в окне карты"))
        tb_main.addAction(self.action_open)

        self.action_save = QAction(QIcon(str(plugin.plugin_dir / "save.png")), self._tr("Сохранить"))
        self.action_save.triggered.connect(self.__save_triggered)
        self.action_save.setToolTip(self._tr("Сохранить подключение как TAB-файл"))
        tb_main.addAction(self.action_save)

        tb_main.addSeparator()

        self.action_expand = QAction(
            QIcon(str(plugin.plugin_dir / "expand.png")), self._tr("Развернуть все/Свернуть все")
        )
        self.action_expand.setCheckable(True)
        self.action_expand.setChecked(True)
        tb_main.addAction(self.action_expand)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tb_main.addWidget(spacer)

        self.action_refresh = QAction(QIcon(str(plugin.plugin_dir / "refresh.png")), self._tr("Обновить"))
        self.action_refresh.triggered.connect(self.__refresh_triggered)
        self.action_refresh.setToolTip(self._tr("Обновить список с сервера"))
        tb_main.addAction(self.action_refresh)

        self.action_help = QAction(QIcon(str(plugin.plugin_dir / "help.png")), self._tr("Справка"))
        self.action_help.triggered.connect(self.__help_triggered)
        tb_main.addAction(self.action_help)
        tb_main.setMovable(False)

        layout.addWidget(tb_main)

        self.__tree = TmsTreeWidget(plugin)
        self.__tree.currentItemChanged.connect(self.__item_changed)
        splitter.addWidget(self.__tree)

        self.action_expand.toggled.connect(self.__expand_toogled)

        self.__textBrowser = QTextBrowser()
        splitter.addWidget(self.__textBrowser)

        splitter.setCollapsible(0, False)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        self.setLayout(layout)

        self.__textBrowser.setReadOnly(True)
        self.__textBrowser.setOpenLinks(False)
        self.__textBrowser.anchorClicked.connect(self.__url_clicked)

        self.action_open_current_map = QAction(
            QIcon(str(plugin.plugin_dir / "open.png")), self._tr("Открыть в текущем окне")
        )
        self.action_open_current_map.triggered.connect(self.__tree.open_current_map)

        self.action_open_new_map = QAction(QIcon(str(plugin.plugin_dir / "open.png")), self._tr("Открыть в новом окне"))
        self.action_open_new_map.triggered.connect(self.__tree.open_new_map)

        self.__tree.popup_menu.addAction(self.action_open_current_map)
        self.__tree.popup_menu.addAction(self.action_open_new_map)
        self.__tree.popup_menu.addAction(self.action_save)

        self.__tree.itemCollapsed.connect(self.__treeItemCollapsed)

        self.__has_mapview = len(axipy.view_manager.mapviews) > 0

        axipy.view_manager.count_changed.connect(self.__mapview_changed)

        self.__enable_actions(False)

    def __mapview_changed(self) -> None:
        self.__has_mapview = len(axipy.view_manager.mapviews) > 0
        current_item = self.__tree.currentItem()
        enable = False
        if current_item is not None:
            enable = current_item.data(0, Qt.ItemDataRole.UserRole) is not None and self.__has_mapview
        self.action_open_current_map.setEnabled(enable)

    @property
    def __update_url(self):
        return f"https://raw.githubusercontent.com/kasim73/TileServices/main/com_github_kasim73_tile_services/{json_filename(axipy.CurrentSettings.Language)}"

    def __url_clicked(self, url):
        QDesktopServices.openUrl(url.toString())

    def __enable_actions(self, enable):
        self.action_save.setEnabled(enable)
        self.action_open.setEnabled(enable)
        self.action_open_current_map.setEnabled(enable and self.__has_mapview)
        self.action_open_new_map.setEnabled(enable)

    def __item_changed(self, current, previons):
        data = current.data(0, Qt.ItemDataRole.UserRole)
        has_data = data is not None
        self.__enable_actions(has_data)
        if has_data and "description" in data:
            self.__textBrowser.setHtml(data["description"])
        else:
            self.__textBrowser.clear()

    def __open_triggered(self) -> None:
        self.__tree.open_interactive()

    def __save_triggered(self) -> None:
        self.__tree.save_current()

    def __expand_toogled(self, checked):
        if checked:
            self.__tree.expandAll()
        else:
            self.__tree.collapseAll()

    def __update_file(self, file_name, data):
        if os.path.isfile(file_name) and data is not None:
            bak_file_name = file_name + ".BAK"
            if os.path.exists(bak_file_name):
                os.remove(bak_file_name)
            os.rename(file_name, bak_file_name)
        f = open(file_name, "wb")
        f.write(data)
        f.close()

    def __refresh_triggered(self) -> None:
        if (
            QMessageBox.question(axipy.mainwindow.widget, self.windowTitle(), self._tr("Обновить данные?"))
            != QMessageBox.StandardButton.Yes
        ):
            return
        file_name = self.__tree.json_file
        try:
            print("Url:", self.__update_url)
            req = Request(self.__update_url, headers={"User-Agent": "Mozilla/5.0"})
            data = urlopen(req).read()
            try:
                self.__update_file(file_name, data)
            except PermissionError:
                if axipy.Version.segments()[0] >= 4:
                    self.__plugin.get_plugin_data_dir().mkdir(parents=True, exist_ok=True)
                    file_name = str(self.__plugin.get_plugin_data_dir() / json_filename(axipy.CurrentSettings.Language))
                    self.__update_file(file_name, data)
                else:
                    raise
            self.__tree.refresh_tree()
            axipy.Notifications.push(
                "",
                self._tr(f"Список '{file_name}' обновлен"),
                axipy.Notifications.Information,
            )
        except Exception as error:
            QMessageBox.critical(axipy.mainwindow.widget, self._tr("Ошибка"), str(error))

    def __help_triggered(self) -> None:
        file_name = str(self.__plugin.plugin_dir / "documentation" / doc_index_filename(axipy.CurrentSettings.Language))
        url = QUrl.fromLocalFile(file_name)
        if axipy.Version.number() >= ((4 << 16) + (3 << 8)):
            axipy.mainwindow.show_html_url(url, self.windowTitle())
        else:
            QDesktopServices.openUrl(url.toString())

    def __treeItemCollapsed(self, item):
        self.action_expand.blockSignals(True)
        self.action_expand.setChecked(False)
        if item.indexOfChild(self.__tree.currentItem()) != -1:
            self.__tree.setCurrentItem(item)
        self.action_expand.blockSignals(False)
