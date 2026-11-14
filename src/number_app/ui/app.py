import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QTabWidget,QLabel,QMessageBox,QFileDialog
from PySide6.QtGui import QFont,QAction,QKeySequence
from number_app.storage.catalog import Catalog
from number_app.ui.new_batch import NewBatchPage
from number_app.ui.current_batch import CurrentBatchPage
from number_app.ui.worker import Worker
from number_app.jobs.service import generate_batch
from number_app.spec import BatchSpec
from number_app.ui.results import ResultsPage
from number_app.ui.history import HistoryPage
from number_app.ui.statistics import StatisticsPage
from number_app.ui.settings import SettingsPage

STYLE='''
QMainWindow,QWidget {background:#f5f7fb;color:#192d43;font-size:14px;}
QTabWidget::pane {border:1px solid #dae1ec;border-radius:6px;background:white;}
QTabBar::tab {padding:12px 20px;background:#e7edf5;}
QTabBar::tab:selected {background:#183e66;color:white;}
QPushButton {background:#1a608f;color:white;border:0;border-radius:5px;padding:9px 16px;}
QPushButton:disabled {background:#a8b4c3;}
QPushButton:hover {background:#2278af;}
QSpinBox,QLineEdit,QComboBox,QPlainTextEdit,QTableWidget {background:white;border:1px solid #ccd6e2;padding:5px;}
QHeaderView::section {background:#e8eef5;padding:6px;border:0;}
'''

class MainWindow(QMainWindow):
    def __init__(self,data_dir):
        super().__init__()
        self.data_dir=Path(data_dir).resolve(); self.catalog=Catalog(self.data_dir)
        self.setWindowTitle('随机号码分组工具 2.0'); self.resize(1180,820)
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs)
        self.worker=None; self.last_result=None
        self.new_page=NewBatchPage(self.catalog,self.start_generate)
        self.current_page=CurrentBatchPage(self.cancel_task)
        self.tabs.addTab(self.new_page,'新建分组'); self.tabs.addTab(self.current_page,'运行进度')
        self.results_page=ResultsPage(self.catalog); self.stats_page=StatisticsPage(self.catalog)
        self.history_page=HistoryPage(self.catalog,self.open_batch,self.verify_selected,self.recover_selected,self.export_selected)
        self.tabs.addTab(self.results_page,'直选结果'); self.tabs.addTab(self.stats_page,'逐号统计'); self.tabs.addTab(self.history_page,'历史记录')
        self.settings_page=SettingsPage(self); self.tabs.addTab(self.settings_page,'设置与备份')
        menu=self.menuBar().addMenu('操作')
        for title,key,handler in [
            ('开始生成并审查','Ctrl+Return',self.start_generate),
            ('打开最近完成结果','Ctrl+L',self.open_latest),
            ('历史记录','Ctrl+H',self.show_history),
            ('完整复核当前批次','Ctrl+R',lambda:self.verify_selected(self.selected_batch())),
            ('再次导出当前批次','Ctrl+E',lambda:self.export_selected(self.selected_batch())),
            ('立即完整备份','Ctrl+B',self.settings_page.backup)]:
            action=QAction(title,self); action.setShortcut(QKeySequence(key)); action.triggered.connect(handler); menu.addAction(action)
        self.statusBar().showMessage('数据目录：'+str(self.data_dir))
        if any(r['status'] in {'CREATED','GENERATING','WRITING','AUDITING','COMMITTING'} for r in self.catalog.list()):
            from number_app.storage.recovery import inspect_recovery
            self.start_operation(lambda p,c:dict(status='RECOVERY_READY',pending=inspect_recovery(self.data_dir)))

    def start_generate(self):
        if self.worker and self.worker.isRunning(): return
        s=self.new_page.copies.value(); k=self.new_page.groups.value()
        self.catalog.set_setting('copies',s); self.catalog.set_setting('groups',k)
        self.start_operation(lambda progress,cancel:generate_batch(BatchSpec(s,k),self.data_dir,progress=progress,cancel=cancel))

    def start_operation(self,operation):
        if self.worker and self.worker.isRunning(): return False
        self.last_result=None; self.new_page.start.setEnabled(False); self.current_page.reset(); self.tabs.setCurrentWidget(self.current_page)
        self.worker=Worker(operation,self)
        self.worker.progress.connect(self.current_page.update_event)
        self.worker.result.connect(self.on_result); self.worker.failed.connect(self.on_error); self.worker.finished.connect(self.on_finished)
        self.worker.start(); return True

    def on_result(self,result):
        self.last_result=result
        if 'checks_passed' in result:
            self.current_page.stage.setText('完成 · '+result['status']+' · '+str(result['checks_passed'])+'/15')
        else:
            self.current_page.stage.setText({'BACKUP_COMPLETE':'备份完成','EXPORTED':'复制导出完成','RESTORED':'备份恢复及复核完成','RECOVERY_READY':'恢复检查完成'}.get(result['status'],result['status']))
        self.current_page.log.appendPlainText(str(result))
        self.statusBar().showMessage(result.get('batch_dir',str(self.data_dir)))
        if result.get('backup_status'): self.current_page.log.appendPlainText('备份状态：'+result['backup_status']+' '+result.get('backup_error',result.get('backup_note','')))
        self.history_page.refresh()
        if result['status'] in {'COMPLETED','PASS'} and self.catalog.get(result.get('batch_id')):
            self.open_batch(result['batch_id'],switch=False)

    def on_error(self,message):
        self.current_page.stage.setText('失败 · 结果不可使用'); self.current_page.log.appendPlainText(message)

    def on_finished(self):
        self.new_page.start.setEnabled(True); self.current_page.cancel.setEnabled(False)

    def cancel_task(self):
        if self.worker: self.worker.cancel.set()

    def open_batch(self,batch_id,switch=True):
        if not batch_id: return
        try:
            self.results_page.load_batch(batch_id); self.stats_page.load_batch(batch_id)
            if switch: self.tabs.setCurrentWidget(self.results_page)
        except Exception as e: self.on_error(str(e)); self.history_page.refresh()

    def selected_batch(self):
        return self.history_page.selected() if self.tabs.currentWidget()==self.history_page else self.results_page.batch_id

    def open_latest(self):
        row=next((r for r in self.catalog.list() if r['status']=='COMPLETED'),None)
        if row: self.open_batch(row['batch_id'])

    def show_history(self):
        self.history_page.refresh(); self.tabs.setCurrentWidget(self.history_page)
        if self.history_page.rows: self.history_page.table.selectRow(0)

    def verify_selected(self,batch_id):
        if not batch_id: return
        from number_app.jobs.service import verify_batch
        row=self.catalog.get(batch_id)
        self.start_operation(lambda p,c:verify_batch(row['batch_dir'],self.data_dir,progress=p,cancel=c))

    def recover_selected(self,batch_id):
        if not batch_id: return
        from number_app.storage.recovery import recover_batch
        self.start_operation(lambda p,c:recover_batch(batch_id,self.data_dir,progress=p,cancel=c))

    def export_selected(self,batch_id):
        if not batch_id: return
        destination=QFileDialog.getExistingDirectory(self,'选择导出目录')
        if destination:
            from number_app.storage.export import export_batch
            self.start_operation(lambda p,c:export_batch(batch_id,self.data_dir,destination))

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel_task(); self.statusBar().showMessage('正在停止任务，请稍后关闭窗口'); event.ignore()
        else: event.accept()

def run_gui(data_dir):
    app=QApplication.instance() or QApplication(sys.argv[:1])
    app.setFont(QFont('Microsoft YaHei UI',10)); app.setStyleSheet(STYLE)
    visited=set()
    for _ in range(8):
        root=Path(data_dir).resolve()
        if root in visited: break
        visited.add(root); preferred=Catalog(root).setting('preferred_data_dir')
        if not preferred or Path(preferred).resolve()==root: break
        data_dir=preferred
    window=MainWindow(data_dir); window.show()
    return app.exec()
