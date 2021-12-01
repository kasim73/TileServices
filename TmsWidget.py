import os
from PySide2.QtWidgets import QWidget, QVBoxLayout, QTextBrowser, QSplitter, QToolBar, QAction, QMessageBox, QSizePolicy
from PySide2.QtCore import Qt, QSize, QUrl
from PySide2.QtGui import QIcon, QDesktopServices

from .TmsTreeWidget import TmsTreeWidget
from axipy.app import Notifications
from axipy import view_manager

from .TmsUtils import doc_index_filename, json_filename


class ToolBar(QToolBar):

    def __init__(self) -> None:
        super().__init__()
        self.setContentsMargins(0,0,0,0)
        self.setAllowedAreas(Qt.NoToolBarArea)
        self.setIconSize(QSize(16,16))


class TmsWidget(QWidget):

    def __init__(self, plugin) -> None:
        super().__init__()
        self.__plugin = plugin
        self.tr = plugin.tr
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)

        splitter = QSplitter(Qt.Vertical)

        tb_main = ToolBar()

        self.action_open = QAction(QIcon(plugin.local_file('open.png')), self.tr('Открыть'))
        self.action_open.triggered.connect(self.__open_triggered)
        self.action_open.setToolTip(self.tr('Открыть в окне карты'))
        tb_main.addAction(self.action_open)

        self.action_save = QAction(QIcon(plugin.local_file('save.png')), self.tr('Сохранить'))
        self.action_save.triggered.connect(self.__save_triggered)
        self.action_save.setToolTip(self.tr('Сохранить подключение как TAB-файл'))
        tb_main.addAction(self.action_save)

        tb_main.addSeparator()

        self.action_expand = QAction(QIcon(plugin.local_file('expand.png')), self.tr('Развернуть все/Свернуть все'))
        self.action_expand.setCheckable(True)
        self.action_expand.setChecked(True)
        tb_main.addAction(self.action_expand)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tb_main.addWidget(spacer)

        self.action_refresh = QAction(QIcon(plugin.local_file('refresh.png')), self.tr('Обновить'))
        self.action_refresh.triggered.connect(self.__refresh_triggered)
        self.action_refresh.setToolTip(self.tr('Обновить список с сервера'))
        tb_main.addAction(self.action_refresh)

        self.action_help = QAction(QIcon(plugin.local_file('help.png')), self.tr('Справка'))
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

        self.action_open_current_map = QAction(QIcon(plugin.local_file('open.png')), self.tr('Открыть в текущем окне'))
        self.action_open_current_map.triggered.connect(self.__tree.open_current_map)

        self.action_open_new_map = QAction(QIcon(plugin.local_file('open.png')), self.tr('Открыть в новом окне'))
        self.action_open_new_map.triggered.connect(self.__tree.open_new_map)

        self.__tree.popup_menu.addAction(self.action_open_current_map)
        self.__tree.popup_menu.addAction(self.action_open_new_map)
        self.__tree.popup_menu.addAction(self.action_save)

        self.__tree.itemCollapsed.connect(self.__treeItemCollapsed)

        self.__has_mapview = len(view_manager.mapviews)

        view_manager.count_changed.connect(self.__mapview_changed)

        self.__enable_actions(False)

    def __mapview_changed(self):
        self.__has_mapview = len(view_manager.mapviews)
        current_item = self.__tree.currentItem()
        enable = False
        if current_item is not None:
            enable = current_item.data(0, Qt.UserRole) is not None and self.__has_mapview
        self.action_open_current_map.setEnabled(enable)

    @property
    def __update_url(self):
        return  f'https://raw.githubusercontent.com/kasim73/TileServices/main/{json_filename(self.__plugin.language)}'

    def __url_clicked(self, url):
        QDesktopServices.openUrl (url.toString() )

    def __enable_actions(self, enable):
        self.action_save.setEnabled(enable)
        self.action_open.setEnabled(enable)
        self.action_open_current_map.setEnabled(enable and self.__has_mapview)
        self.action_open_new_map.setEnabled(enable)

    def __item_changed(self, current, previons):
        data = current.data(0, Qt.UserRole)
        has_data = data is not None
        self.__enable_actions(has_data)
        if has_data and 'description' in data:
            self.__textBrowser.setHtml(data['description'])
        else:
            self.__textBrowser.clear()

    def __open_triggered(self):
        self.__tree.open_interactive()

    def __save_triggered(self):
        self.__tree.save_current()

    def __expand_toogled(self, checked):
        if checked:
            self.__tree.expandAll()
        else:
            self.__tree.collapseAll()

    def __refresh_triggered(self):
        from urllib.request import Request, urlopen
        if QMessageBox.question(self.__plugin.window(), self.tr('Подтверждение'), 
                self.tr('Обновить данные?')) != QMessageBox.Yes:
            return
        file_name  = self.__tree.json_file
        try:
            req = Request(self.__update_url, headers={'User-Agent': 'Mozilla/5.0'})
            data = urlopen(req).read()
            if os.path.isfile(file_name) and data is not None:
                bak_file_name = file_name + '.BAK'
                if os.path.exists(bak_file_name):
                    os.remove(bak_file_name)
                os.rename(file_name, bak_file_name)
            f = open(file_name, "wb")
            f.write(data)
            f.close()
            self.__tree.refresh_tree()
            self.__plugin.notifications.push('', self.tr('Список обновлен'), Notifications.Information)
        except Exception as error:
            QMessageBox.critical(self.__plugin.window(), self.tr('Ошибка'), str(error))

    def __help_triggered(self):
        file_name = self.__plugin.local_file(doc_index_filename(self.__plugin.language))
        url = QUrl.fromLocalFile(file_name)
        QDesktopServices.openUrl( url.toString() )

    def __treeItemCollapsed(self, item):
        self.action_expand.blockSignals(True)
        self.action_expand.setChecked(False)
        if item.indexOfChild(self.__tree.currentItem()) != -1:
            self.__tree.setCurrentItem(item)
        self.action_expand.blockSignals(False)
