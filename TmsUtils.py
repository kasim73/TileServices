import os
from pathlib import Path
import xml.etree.cElementTree as tree
import xml.dom.minidom


def generate_tile_tab_file(fn, data):
    path = Path(fn)
    xml_fn = '{}.xml'.format(path.stem)
    # write tab file
    tab = open(fn, 'w') 
    tab.writelines('!table\n')
    tab.write('!version 1050\n')
    tab.write('!charset WindowsLatin1\n\n')
    tab.write('Definition Table\n')
    tab.write('  File "{}"\n'.format(xml_fn))
    tab.write('  Type "TILESERVER"\n')
    prj = data.get('prj',  'CoordSys Earth Projection 10, 104, "m"')
    tab.write(' {}\n'.format(prj))
    tab.write('ReadOnly\n')
    tab.close()
    # write xml file
    root = tree.Element("TileServerInfo", Type = 'QuadKey' if data['typeAddress'] == 'quadkey' else 'LevelRowColumn')
    tree.SubElement(root, "Url").text = data['url']
    tree.SubElement(root, "MinLevel").text = str(data.get('min', 0))
    tree.SubElement(root, "MaxLevel").text = str(data.get('max', 19))
    size = data.get('size', (256,256))
    tree.SubElement(root, "TileSize", Height=str(size[0]), Width=str(size[1]))
    dom = xml.dom.minidom.parseString(tree.tostring(root))
    fxml = open(os.path.join(path.parent, xml_fn), 'w')
    fxml.write(dom.toprettyxml())
    fxml.close()


def json_filename(language):
    return f'ListTileServices_{language}.json'

def doc_index_filename(language):
    return f'documentation/index_{language}.html'
