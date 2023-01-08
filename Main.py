import sys
import re
from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWidgets import QPushButton, QFileDialog, QLabel, QLineEdit, QStylePainter


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        QtWidgets.QApplication.instance().focusChanged.connect(self.on_focusChanged)

        self.button = QPushButton("Open", self)
        self.button.resize(self.button.sizeHint())
        self.button.move(10,10)
        self.button.clicked.connect(self.buttonPress)

        self.fileDiag = QFileDialog(self)
        self.fileDiag.setNameFilters(["Gcode File (*.gcode)", "All Files (*)"])
        self.fileDiag.selectNameFilter("Gcode File (*.gcode)")

        self.file_label_box = QLabel("", self)
        self.file_label_box.move(10, 30)
        self.file_label_box.resize(380, 60)
        self.file_label_box.setAlignment(QtCore.Qt.AlignCenter)
        self.file_label_box.setWordWrap(True)
        self.file_label_box.show()

        label_box = QLabel("Layer Changes:", self)
        label_box.move(130, 80)
        label_box.resize(150, 20)
        label_box.alignment = QtCore.Qt.AlignLeft
        label_box.show()

        self.layer_box = []
        self.label_box = []

        for i in range(0,5):
            if i < 4:
                layer_box = QLineEdit(self)
                layer_box.move(100, (110 + (30*i)))
                layer_box.setEnabled(False)
                layer_box.show()
                layer_box.i = i
                layer_box.textChanged.connect(partial(self.text_change,i))
                self.layer_box.append(layer_box)

            label_box = QLabel("",self)
            label_box.move(250, (110 + (30*i)))
            label_box.resize(250,20)
            label_box.alignment = QtCore.Qt.AlignLeft
            label_box.show()
            self.label_box.append(label_box)

        self.gcode = GCodeFile()

    def on_focusChanged(self, old, now):
        for i in range(0, len(self.label_box)):
            if i < len(self.label_box) - 1:
                self.text_change(i, self.layer_box[i].text())
            else:
                self.text_change(i, "999")
        #    if layer == now or layer == old:
        #        self.text_change(layer.i,layer.text())

    def buttonPress(self):
        if self.fileDiag.exec():
            if self.gcode.openGcodeFile(self.fileDiag.selectedFiles()[0]):
                file_name = self.fileDiag.selectedFiles()[0]
                self.file_label_box.setText(file_name[int(file_name.rfind("/"))+1:len(file_name)])
                self.file_label_box.setToolTip(file_name[int(file_name.rfind("/"))+1:len(file_name)])
                for layer_box in self.layer_box:
                    layer_box.setEnabled(True)
                for i in range(0, len(self.label_box)):
                    if i < len(self.label_box) - 1:
                        self.text_change(i, self.layer_box[i].text())
                    else:
                        self.text_change(i, "999")
        else:
            print("no file selected")

    def text_change(self, slot, new_text):
        if(new_text == ""):
            self.label_box[slot].setText("")
        else:
            try:
                layer = int(new_text)
            except ValueError:
                print("not an int")
                self.layer_box[slot].setText("")
                self.label_box[slot].setText("")
                return 0

            if slot == 0:
                first_layer = 0
            else:
                first_layer = -1
                i = 1

                while first_layer == -1 and slot-i >=0:
                    if(self.layer_box[slot-i].text() != ""):
                        first_layer = int(self.layer_box[slot-i].text())
                    else:
                        i = i+1

                if first_layer == -1:
                    first_layer = 0

            if layer > len(self.gcode.filament_length):
                layer = len(self.gcode.filament_length)

            #if slot < len(self.layer_box) and layer <= first_layer:
                #print("cannot by same or lower than last line")
                #self.layer_box[slot].setText("")
                #self.label_box[slot].setText("")
                #return 0

            filament_count = 0

            for i in range(first_layer, layer):
                filament_count += self.gcode.filament_length[i]

            filament_count = round(filament_count,5)

            if (slot < len(self.layer_box)):
                self.layer_box[slot].setText(str(layer))
            self.label_box[slot].setText(str(filament_count))




class GCodeFile():
    def __init__(self, file_name=""):
        self.filament_length = []

        if file_name != "":
            self.openGcodeFile(file_name)

    def openGcodeFile(self, file_name=""):
        self.filament_length.clear()

        if str.endswith(file_name, "gcode"):
            print("GCode file selected: " + file_name)

            file = open(file_name, 'r')
            lines = file.readlines()

            print(str(len(lines)) + " lines")
            count = 0

            extruded_num_last_layer = 0.0

            extruded_last_line = 0.0
            layer_filament_length = 0.0
            is_absolute = False

            for line in lines:
                if re.search("^G90", line, re.IGNORECASE):
                    is_absolute = True
                elif re.search("^G91", line, re.IGNORECASE):
                    is_absolute = False
                if re.search("^;layer:", line, re.IGNORECASE):
                    layer_filament_length += round(extruded_last_line - extruded_num_last_layer,1)
                    self.filament_length.append(layer_filament_length)

                    extruded_num_last_layer = extruded_last_line
                    extruded_last_line = 0.0
                    layer_filament_length = 0.0

                if re.search("^G92 E0", line, re.IGNORECASE):
                    layer_filament_length += round(extruded_last_line - extruded_num_last_layer,1)
                    extruded_last_line = 0.0
                    extruded_num_last_layer = 0.0
                elif re.search("E-?[0-9]+(\.[0-9])*", line, re.IGNORECASE):
                    if(is_absolute):
                        extruded_last_line = float(re.search("E(-?[0-9]+(\.[0-9]+)*)", line, re.IGNORECASE)[1])
                    else:
                        layer_filament_length += round(extruded_last_line - extruded_num_last_layer, 1)
                        extruded_last_line = 0.0
                        extruded_num_last_layer = 0.0

                        layer_filament_length += float(re.search("E(-?[0-9]+(\.[0-9]+)*)", line, re.IGNORECASE)[1])
                count += 1
            if (is_absolute):
                layer_filament_length += round(extruded_last_line - extruded_num_last_layer, 1)

            self.filament_length.append(layer_filament_length)
            print(str(len(self.filament_length)) + " layers")

            print(self.filament_length)
            print(round(sum(self.filament_length),5))

            return True
        else:
            print("not a GCode file")

            return False


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    gcode_file = GCodeFile()

    widget.resize(400, 280)
    widget.setWindowTitle("Layer color change calculator")
    widget.show()

    sys.exit(app.exec())
