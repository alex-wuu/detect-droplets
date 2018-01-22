import os
import sys
import droplets
from PyQt5 import QtWidgets


os.environ["PATH"] = ''
os.environ["OUT"] = ''


class SettingsMenu(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'Detect Droplets - Settings'
        self.grid = QtWidgets.QGridLayout()
        self.calibBox = QtWidgets.QLineEdit(self)  # For calibration value
        self.curRow = 1  # Keeps track of current row for adding rows
        self.headerNames = ['Min Radius (pix)', 'Max Radius (pix)', 'Canny Edge Threshold', 'Accumulator Threshold']
        self.settingsValues = []  # Used to access typed values
        self.delButtons = []  # Stores delete row buttons
        self.rowIndices = {}  # Keep track of row indices after deleting rows
        self.initUI()

    def addRow(self):
        self.curRow += 1
        row = self.curRow
        settingsRow = []
        positions = [(self.curRow, i) for i in range(len(self.headerNames))]

        # Add text boxes for new row
        for position in positions:
            textBox = QtWidgets.QLineEdit(self)
            settingsRow.append(textBox)  # Build the row of text boxes
            self.grid.addWidget(textBox, *position)

        # Add delete row button
        delRowButton = QtWidgets.QPushButton('Delete row')
        delRowButton.clicked.connect(lambda: self.delRow(row))
        self.delButtons.append(delRowButton)
        self.grid.addWidget(delRowButton, self.curRow, len(self.headerNames))

        self.rowIndices[self.curRow] = self.curRow  # Set new row indices
        self.settingsValues.append(settingsRow)  # Add new row of text boxes to settingsValues

    def delRow(self, row):
        # Hide delete button
        self.delButtons[self.rowIndices[row] - 2].hide()
        self.delButtons.pop(self.rowIndices[row] - 2)

        # Hide text fields
        for box in self.settingsValues.pop(self.rowIndices[row] - 2):
            box.hide()

        # Adjust indices and current row
        for index in self.rowIndices:
            if index >= row:
                self.rowIndices[index] += -1
        self.curRow += -1

    def runAction(self):
        scriptSettings = []  # Stores settings entered by user
        errorFlag = False

        # First check that all settings fields are valid, and build settings list
        try:
            float(self.calibBox.text())
        except ValueError:
            errorFlag = True
            QtWidgets.QMessageBox.about(self, 'Error', 'Invalid calibration value detected.')
        if len(self.settingsValues) == 0:
            QtWidgets.QMessageBox.about(self, 'Error', 'No settings detected.')
        for row in self.settingsValues:
            rowSettings = []  # Store settings from each column on the row
            if errorFlag is True:
                break
            for textBox in row:
                try:
                    rowSettings.append(int(textBox.text()))
                except ValueError:
                    errorFlag = True
                    QtWidgets.QMessageBox.about(self, 'Error', 'Invalid settings value detected.')
                    break
            scriptSettings.append(rowSettings)  # Store settings from the entire row

        # Run script if no errors detected and paths are selected
        if errorFlag is True:
            pass
        elif os.environ["PATH"] != '' and os.environ["OUT"] != '':
            droplets.main(scriptSettings, float(self.calibBox.text()))
            QtWidgets.QMessageBox.about(self, "Detect Droplets", "Processing done. Output is at {}".format(os.environ["OUT"]))
        else:
            QtWidgets.QMessageBox.about(self, 'Error', 'Missing selected path.')

    def initUI(self):
        self.setLayout(self.grid)
        positions = [(self.curRow, i) for i in range(len(self.headerNames))]

        addRowButton = QtWidgets.QPushButton('Add Row')
        addRowButton.clicked.connect(self.addRow)
        self.grid.addWidget(addRowButton, 0, 0)

        calibLabel = QtWidgets.QLabel('Calibration (microns/pix):')
        self.grid.addWidget(calibLabel, 0, 1)
        self.grid.addWidget(self.calibBox, 0, 2)

        runButton = QtWidgets.QPushButton('Run')
        runButton.clicked.connect(self.runAction)
        self.grid.addWidget(runButton, 0, len(self.headerNames) - 1)

        # Create header row
        for position, name in zip(positions, self.headerNames):
            label = QtWidgets.QLabel(name, self)
            self.grid.addWidget(label, *position)

        self.addRow()

        self.setWindowTitle(self.title)


class SettingsButton(QtWidgets.QPushButton):

    def __init__(self, title, parent):
        super().__init__(title, parent)
        self.dialog = SettingsMenu()
        self.clicked.connect(self.onClick)

    def onClick(self):
        self.dialog.show()


class PathWidgets(QtWidgets.QWidget):

    def __init__(self, title, envVar, parent):
        super().__init__(parent)
        self.dirLabel = QtWidgets.QLineEdit(self)  # Text box for directory
        self.dirButton = QtWidgets.QPushButton(title)
        self.envVar = envVar
        self.selectedDir = ''
        self.initUI()

    def onClick(self):
        # On click, ask to choose directory then edit text box with the selected path
        self.selectedDir = str(QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory'))
        if self.selectedDir != '':
            self.dirLabel.setText(self.selectedDir)
            os.environ[self.envVar] = self.selectedDir

    def initUI(self):
        self.dirButton.clicked.connect(self.onClick)
        self.dirLabel.setReadOnly(True)

        # Put text box and button side by side horizontally
        hBox = QtWidgets.QHBoxLayout()
        hBox.addWidget(self.dirLabel)
        hBox.addWidget(self.dirButton)

        self.setLayout(hBox)


class AddButtons(QtWidgets.QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.photoPath = PathWidgets('Choose Path with Photos', 'PATH', self)
        self.outPath = PathWidgets('Choose Output Directory', 'OUT', self)
        self.setButton = SettingsButton('Settings/Run', self)

        # Format with box layout methods to stack the above widgets vertically
        hBox = QtWidgets.QHBoxLayout()
        hBox.addStretch()
        hBox.addWidget(self.setButton)
        hBox.addStretch()

        vBox = QtWidgets.QVBoxLayout()
        vBox.addStretch()
        vBox.addWidget(self.photoPath)
        vBox.addWidget(self.outPath)
        vBox.addLayout(hBox)
        vBox.addStretch()

        self.setLayout(vBox)


class App(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'Detect Droplets'
        self.left = 300
        self.top = 300
        self.width = 450
        self.height = 150
        self.initUI()

    def tipsWindow(self):
        message = ('Make sure your ranges of radii do not overlap with each other.\n\n'
                   'The Canny Edge Threshold is the upper threshold for the Canny edge detector.\n\n'
                   'Accumulator Threshold is the threshold for center detection. Smaller values can return false circles')
        QtWidgets.QMessageBox.about(self, 'Settings Tips', message)

    def aboutWindow(self):
        message = ('Detect Droplets by Alex Wu')
        QtWidgets.QMessageBox.about(self, 'About', message)

    def initUI(self):
        exitAct = QtWidgets.QAction('Exit', self)
        exitAct.setShortcut('Ctrl+Q')
        exitAct.triggered.connect(self.close)

        tipsAct = QtWidgets.QAction('Settings Tips', self)
        tipsAct.triggered.connect(self.tipsWindow)
        aboutAct = QtWidgets.QAction('About', self)
        aboutAct.triggered.connect(self.aboutWindow)

        menu = self.menuBar()
        fileMenu = menu.addMenu('File')
        fileMenu.addAction(exitAct)

        helpMenu = menu.addMenu('Help')
        helpMenu.addAction(tipsAct)
        helpMenu.addAction(aboutAct)

        self.buttons = AddButtons(self)
        self.setCentralWidget(self.buttons)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setWindowTitle(self.title)
        self.show()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
