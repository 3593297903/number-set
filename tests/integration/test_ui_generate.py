from PySide6.QtCore import Qt
from number_app.ui.app import MainWindow
import pytest

@pytest.mark.parametrize('via_shortcut',[False,True])
def test_actual_desktop_generate(qtbot,tmp_path,via_shortcut):
    w=MainWindow(tmp_path); qtbot.addWidget(w)
    with qtbot.waitExposed(w):
        w.show()
    with qtbot.waitActive(w):
        w.activateWindow()
    if via_shortcut: qtbot.keyClick(w,Qt.Key_Return,Qt.ControlModifier)
    else: qtbot.mouseClick(w.new_page.start,Qt.LeftButton)
    assert not w.new_page.start.isEnabled()
    ticks=[]
    from PySide6.QtCore import QTimer
    timer=QTimer(w); timer.timeout.connect(lambda:ticks.append(1)); timer.start(50)
    qtbot.waitUntil(lambda:w.last_result is not None,timeout=120000)
    qtbot.waitUntil(lambda:not w.worker.isRunning(),timeout=10000)
    assert w.last_result['status']=='COMPLETED' and len(ticks)>5
    assert all(w.current_page.table.item(i,j).text()=='PASS' for i in range(3) for j in range(5))
    w.close()
