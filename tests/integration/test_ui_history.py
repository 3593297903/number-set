from pathlib import Path
from number_app.ui.app import MainWindow
from number_app.jobs.service import generate_batch
from number_app.spec import BatchSpec
from PySide6.QtWidgets import QApplication

def test_reopen_copy_reverify(qtbot,tmp_path):
    result=generate_batch(BatchSpec(100,40),tmp_path)
    w=MainWindow(tmp_path); qtbot.addWidget(w); w.show(); w.open_batch(result['batch_id'])
    raw=(Path(result['batch_dir'])/'groups/group_001.txt').read_bytes()
    assert w.results_page.raw==raw
    w.results_page.copy_current(); assert QApplication.clipboard().text().encode()==raw
    assert w.stats_page.table.item(0,0).text()=='000' and w.stats_page.table.item(999,2).text()=='100'
    w.close()
    again=MainWindow(tmp_path); qtbot.addWidget(again); again.show(); again.verify_selected(result['batch_id'])
    qtbot.waitUntil(lambda:again.last_result is not None,timeout=120000); qtbot.waitUntil(lambda:not again.worker.isRunning(),timeout=10000)
    assert again.last_result['status']=='PASS'
    assert (Path(result['batch_dir'])/'groups/group_001.txt').read_bytes()==raw
    again.close()
