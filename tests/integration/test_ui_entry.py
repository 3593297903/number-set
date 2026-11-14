import sys
from number_app.ui.app import MainWindow

def test_window(qtbot,tmp_path):
    window=MainWindow(tmp_path); qtbot.addWidget(window); window.show()
    assert window.isVisible()
    assert '2.0' in window.windowTitle()
    window.close()
