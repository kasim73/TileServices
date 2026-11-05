import axipy
import json
import os
import os.path
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QImage, QPixmap, QCursor, QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QMessageBox, QMenu
from typing import TYPE_CHECKING
from .tms_utils import json_filename, generate_tile_tab_file

if TYPE_CHECKING:
    from .plugin import TileServicesPlugin


class TmsTreeWidget(QTreeWidget):

    def __init__(self, plugin: "TileServicesPlugin") -> None:
        super().__init__()
        self.__plugin = plugin
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setHeaderHidden(True)
        header = self.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.itemDoubleClicked.connect(self.__itemDoubleClicked)
        self.__load_from_json(self.json_file)
        self.__popup_menu = QMenu(self)

    @property
    def popup_menu(self) -> QMenu:
        return self.__popup_menu

    def refresh_tree(self) -> None:
        self.clear()
        self.__load_from_json(self.json_file)

    @property
    def json_file(self):
        fn = json_filename(axipy.CurrentSettings.Language)
        # Check in the user catalog
        if axipy.Version.segments()[0] >= 4:
            file_name = str(self.__plugin.get_plugin_data_dir() / fn)
            if os.path.isfile(file_name):
                return file_name
        # Check in the current catalog
        file_name = str(self.__plugin.plugin_dir / fn)
        if os.path.isfile(file_name):
            return file_name
        return str(self.__plugin.plugin_dir / "ListTileServices_ru.json")

    def __open_tms(self, data):
        if axipy.Version.compare(6, 2) == -1:
            web_data = axipy.WebOpenData()
            if "header" in data:
                web_data.header = data["header"]
            return axipy.provider_manager.tms.open(
                templateUrl=data["url"],
                type_address=data["typeAddress"],
                minLevel=data["min"] if "min" in data else 0,
                maxLevel=data["max"] if "max" in data else 19,
                size=data["tileSize"] if "tileSize" in data else (256, 256),
                prj=data["prj"] if "prj" in data else None,
                live_time=data["liveTime"] if "liveTime" in data else 0,
                alias=data["title"] if "title" in data else None,
                extra_data=web_data,
            )
        else:
            return axipy.provider_manager.tms.open(
                templateUrl=data["url"],
                type_address=data["typeAddress"],
                minLevel=data["min"] if "min" in data else 0,
                maxLevel=data["max"] if "max" in data else 19,
                size=data["tileSize"] if "tileSize" in data else (256, 256),
                prj=data["prj"] if "prj" in data else None,
                live_time=data["liveTime"] if "liveTime" in data else 0,
                alias=data["title"] if "title" in data else None,
            )

    def __open_interactive(self, layer):
        axipy.mainwindow.add_layer_interactive(layer)

    def __open_current_map(self, layer):
        axipy.mainwindow.add_layer_current_map(layer)

    def __open_new_map(self, layer):
        axipy.mainwindow.add_layer_new_map(layer)

    def __open_url(self, data, func_open):
        raster = None
        if "typeService" in data:
            tp = data["typeService"]
            if tp == "tms":
                raster = self.__open_tms(data)
        else:
            print("typeService is not detected")
        if raster is not None:
            raster.name = data["name"]
            layer = axipy.Layer.create(raster)
            func_open(layer)

    def __itemDoubleClicked(self, item, column):
        data = item.data(column, Qt.ItemDataRole.UserRole)
        if data is not None and "url" in data:
            self.__open_url(data, self.__open_interactive)

    def __add_category(self, cat: dict, imgs):
        item = QTreeWidgetItem(self)
        item.setText(0, cat["name"])
        if "image" in cat:
            px = self.__get_image(cat["image"], imgs)
            if not px.isNull():
                item.setIcon(0, px)
        return item

    def open_interactive(self) -> None:
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.ItemDataRole.UserRole), self.__open_interactive)

    def open_current_map(self) -> None:
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.ItemDataRole.UserRole), self.__open_current_map)

    def open_new_map(self) -> None:
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.ItemDataRole.UserRole), self.__open_new_map)

    def save_current(self) -> None:
        item = self.currentItem()
        if item is not None:
            d = item.data(0, Qt.ItemDataRole.UserRole)
            filename = "{}_{}.tab".format(d["name"], item.parent().text(0)).lower()
            fn, _ = QFileDialog.getSaveFileName(
                axipy.mainwindow.widget, self.tr("Сохранение файла"), filename, "MapInfo (*.tab)"
            )
            if fn:
                generate_tile_tab_file(fn, item.data(0, Qt.ItemDataRole.UserRole))
                raster = axipy.provider_manager.openfile(fn)
                layer = axipy.Layer.create(raster)
                axipy.mainwindow.add_layer_interactive(layer)

    def __get_image(self, name, imgs) -> QPixmap:
        if name in imgs:
            im = imgs[name]
            by = QByteArray.fromBase64(im["data"].encode("ascii"))
            image = QImage.fromData(by, im["format"])
            return QPixmap.fromImage(image)
        return QPixmap()

    def __add_service(self, name: str, base_item, data: dict, imgs):
        item = QTreeWidgetItem(base_item)
        item.setText(0, data.get("title", data["name"]))

        if "image" in data:
            px = self.__get_image(data["image"], imgs)
            if not px.isNull():
                item.setIcon(0, px)

        item.setData(0, Qt.ItemDataRole.UserRole, data)

    def __load_from_json(self, fn):
        try:
            file = open(fn, "r", encoding="UTF-8")
            json_string = file.read()
            file.close()
            data = json.loads(json_string)
            self.__parse_dict_data(data)
            self.expandAll()
        except Exception as error:
            QMessageBox.critical(axipy.mainwindow.widget, self.tr("Ошибка"), str(error))

    def __parse_dict_data_tms(self, tms):
        data = {"name": tms["name"], "url": tms["url"]}
        data["typeAddress"] = tms["type"] if "type" in tms else "xyz"
        if "title" in tms:
            data["title"] = tms["title"]
        if "description" in tms:
            data["description"] = tms["description"]
        if "image" in tms:
            data["image"] = tms["image"]
        if "size" in tms:
            s = tms["size"]
            data["size"] = (s["width"], s["height"])
        if "level" in tms:
            l = tms["level"]
            data["min"] = l["min"]
            data["max"] = l["max"]
        if "cs" in tms:
            data["prj"] = tms["cs"]
        if "liveTime" in tms:
            data["liveTime"] = tms["liveTime"]
        if "header" in tms:
            data["header"] = tms["header"]
        return data

    def __parse_dict_data(self, data):
        if "services" in data and "category" in data["services"]:
            cats = data["services"]["category"]
            imgs = {}
            if "images" in data:
                imgs = data["images"]
            for cat in cats:
                cat_item = self.__add_category(cat, imgs)
                for tms in cat["tms"]:
                    data = self.__parse_dict_data_tms(tms)
                    data["typeService"] = "tms"
                    self.__add_service(tms["name"], cat_item, data, imgs)

    def __show_popup(self) -> None:
        self.popup_menu.exec(QCursor.pos())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.__show_popup()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        if Qt.Key.Key_Menu == event.key():
            self.__show_popup()
