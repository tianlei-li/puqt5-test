# main.py
from PyQt5 import QtGui, QtWidgets

from login import LoginDialog, show_main_window

main_window = None
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    font = QtGui.QFont("Microsoft YaHei", 9)
    app.setFont(font)

    login_window = LoginDialog()




    login_window.login_success_signal.connect(show_main_window)

    login_window.show()
    sys.exit(app.exec_())