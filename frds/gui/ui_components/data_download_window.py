from PyQt5 import QtWidgets, Qt, QtGui, QtCore
from .generated_py_files.Ui_DataDownloadWindow import Ui_DataDownloadWindow
from frds.data.wrds import Connection
from frds.utils.settings import read_data_source_credentials
from frds.gui.works import get_worker_list_wrds_tables


class StandardItem(Qt.QStandardItem):
    def __init__(
        self,
        item_type,
        txt="",
        font_size=12,
        set_bold=False,
        color=QtGui.QColor(0, 0, 0),
        checkable=True,
    ):
        super().__init__()

        self.type = item_type
        fnt = QtGui.QFont()
        fnt.setBold(set_bold)

        self.setEditable(False)
        self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)
        self.setCheckable(checkable)


class DataDownloadWindow(QtWidgets.QMainWindow, Ui_DataDownloadWindow):
    def __init__(self, thread_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().setupUi(self)

        self.thread_manager = thread_manager
        self.treeModel = Qt.QStandardItemModel()
        self.treeView.header().hide()

        self.initOtherComponents()
        self.connect_signals()

    def initOtherComponents(self):
        pass

    def display_libraries(self, libraries):
        rootNode = self.treeModel.invisibleRootItem()
        wrds = StandardItem("data_source", "WRDS", 16, set_bold=True, checkable=False)
        for lib in libraries:
            libItem = StandardItem("library", lib, 15, checkable=False)
            wrds.appendRow(libItem)
        wrds.sortChildren(QtCore.Qt.AscendingOrder)
        rootNode.appendRow(wrds)
        self.treeView.setModel(self.treeModel)
        self.treeView.expandAll()
        self.treeView.doubleClicked.connect(self.view_double_cliced)

    def view_double_cliced(self, val: QtCore.QModelIndex):
        item: StandardItem = self.treeModel.itemFromIndex(val)
        if item.type == "library" and not item.hasChildren():
            worker = get_worker_list_wrds_tables(val.data())
            worker.signals.result.connect(self.add_tables_to_library)
            self.thread_manager.enqueue(worker)
        if item.type == "table":
            if item.checkState() == QtCore.Qt.Checked:
                item.setCheckState(QtCore.Qt.Unchecked)
            else:
                item.setCheckState(QtCore.Qt.Checked)

    def add_tables_to_library(self, library, tables):
        root: QtGui.QStandardItem = self.treeModel.invisibleRootItem()
        wrds: StandardItem = root.child(0, 0)
        for row in range(wrds.rowCount()):
            item = wrds.child(row, 0)
            if item.text() == library:
                break
        for table in tables:
            table_item = StandardItem("table", table, checkable=True)
            item.appendRow(table_item)
        self.treeModel.layoutChanged.emit()

    def connect_signals(self):
        self.treeModel.itemChanged.connect(self.on_dataset_selection)

    def on_dataset_selection(self, item: Qt.QStandardItem):
        lib = item.parent()
        src = lib.parent()
        full_name = f"{src.text()}.{lib.text()}.{item.text()}".lower()
        if item.checkState() == QtCore.Qt.Checked:
            self.listWidget.addItem(full_name)
        else:
            # remove it from the list of datasets to download
            for dataset in self.listWidget.findItems(full_name, QtCore.Qt.MatchExactly):
                self.listWidget.takeItem(self.listWidget.row(dataset))
                del dataset