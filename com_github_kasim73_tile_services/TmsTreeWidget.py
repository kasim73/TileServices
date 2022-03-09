from PySide2.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QMessageBox, QMenu
from PySide2.QtGui import QImage, QPixmap, QCursor
from PySide2.QtCore import Qt, QByteArray

from .TmsUtils import json_filename, generate_tile_tab_file
from axipy.app import mainwindow

import os
import os.path
import json

from axipy import provider_manager, Layer


class TmsTreeWidget(QTreeWidget):

    def __init__(self, plugin) -> None:
        super().__init__()
        self.__plugin = plugin
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setHeaderHidden(True)
        header = self.header()
        header.setSectionResizeMode(QHeaderView.Fixed);
        self.itemDoubleClicked.connect(self.__itemDoubleClicked)
        self.__load_from_json(self.json_file)
        self.__popup_menu = QMenu(self)

    @property
    def popup_menu(self):
        return self.__popup_menu

    def refresh_tree(self):
        self.clear()
        self.__load_from_json(self.json_file)

    @property
    def json_file(self):
        file_name = self.__plugin.local_file(json_filename(self.__plugin.language))
        if os.path.isfile(file_name):
            return file_name
        return self.__plugin.local_file('ListTileServices_ru.json')

    def __open_tms(self, data):
        return provider_manager.tms.open(templateUrl = data['url'],
                                           type_address = data['typeAddress'],
                                           minLevel = data['min'] if 'min' in data else 0,
                                           maxLevel = data['max'] if 'max' in data else 19,
                                           size = data['tileSize'] if 'tileSize' in data else (256, 256),
                                           prj = data['prj'] if 'prj' in data else None,
                                           live_time = data['liveTime'] if 'liveTime' in data else 0
                                           )

    def __open_interactive(self, layer):
        mainwindow.add_layer_interactive(layer)

    def __open_current_map(self, layer):
        mainwindow.add_layer_current_map(layer)

    def __open_new_map(self, layer):
        mainwindow.add_layer_new_map(layer)

    def __open_url(self, data, func_open):
        raster = None
        if 'typeService' in data:
            tp = data['typeService']
            if tp == 'tms':
                raster = self.__open_tms(data)
        else:
            print('typeService is not detected')
        if raster is not None:
            raster.name = data['name']
            layer = Layer.create(raster)
            func_open(layer)

    def __itemDoubleClicked(self, item, column):
        data = item.data(column, Qt.UserRole)
        if data is not None and 'url' in data:
            self.__open_url(data, self.__open_interactive)
    
    def __add_category(self, cat: dict, imgs):
        item = QTreeWidgetItem(self)
        item.setText(0, cat['name'])
        if 'image' in cat:
            px  = self.__get_image(cat['image'], imgs)
            if not px.isNull():
                item.setIcon(0, px)
        return item

    def open_interactive(self):
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.UserRole), self.__open_interactive)

    def open_current_map(self):
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.UserRole), self.__open_current_map)

    def open_new_map(self):
        item = self.currentItem()
        if item is not None:
            self.__open_url(item.data(0, Qt.UserRole), self.__open_new_map)

    def save_current(self):
        item = self.currentItem()
        if item is not None:
            d = item.data(0, Qt.UserRole)
            filename = '{}_{}.tab'.format(d['name'], item.parent().text(0)).lower()
            fn , _ =  QFileDialog.getSaveFileName(self.__plugin.window(), self.tr('Сохранение файла'), filename, 'MapInfo (*.tab)')
            if fn:
                generate_tile_tab_file(fn, item.data(0, Qt.UserRole))
                raster = provider_manager.openfile(fn)
                layer = Layer.create(raster)
                mainwindow.add_layer_interactive(layer)

    def __get_image(self, name, imgs) -> QPixmap:
        if name in imgs:
            im = imgs[name]
            by = QByteArray.fromBase64(im['data'].encode('ascii'))
            image = QImage.fromData(by, im['format'])
            return QPixmap.fromImage(image)
        return QPixmap()

    def __add_service(self, name: str, base_item, data: dict, imgs):
        item = QTreeWidgetItem(base_item)
        item.setText(0, data.get('title', data['name']))

        if 'image' in data:
            px  = self.__get_image(data['image'], imgs)
            if not px.isNull():
                item.setIcon(0, px)

        item.setData(0, Qt.UserRole, data)

    def __load_from_json(self, fn):
        try:
            file = open(fn, 'r', encoding="UTF-8") 
            json_string = file.read()
            file.close()
            data = json.loads(json_string)
            self.__parse_dict_data(data)
            self.expandAll()
        except Exception as error:
            QMessageBox.critical(self.__plugin.window(), self.tr('Ошибка'), str(error))

    def __parse_dict_data_tms(self, tms):
        data = {
            'name': tms['name'],
            'url': tms['url']
        }
        data['typeAddress'] = tms['type'] if 'type' in tms else 'xyz'
        if 'title' in tms:
            data['title'] = tms['title']
        if 'description' in tms:
            data['description'] = tms['description']
        if 'image' in tms:
            data['image'] = tms['image']
        if 'size' in tms:
            s = tms['size']
            data['size'] = (s['width'], s['height'])
        if 'level' in tms:
            l = tms['level']
            data['min'] = l['min']
            data['max'] = l['max']
        if 'cs' in tms:
            data['prj'] = tms['cs']
        if 'liveTime' in tms:
            data['liveTime'] = tms['liveTime']
        return data

    def __parse_dict_data(self, data):
        if 'services' in data and 'category' in data['services']:
            cats = data['services']['category']
            imgs = {}
            if 'images' in data:
                imgs = data['images']
            for cat in cats:
                cat_item = self.__add_category(cat, imgs)
                for tms in cat['tms']:
                    data = self.__parse_dict_data_tms(tms)
                    data['typeService'] = 'tms'
                    self.__add_service(tms['name'], cat_item, data, imgs)
    
    def __show_popup(self):
        self.popup_menu.exec_(QCursor.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self.__show_popup()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if Qt.Key_Menu == event.key():
            self.__show_popup()

