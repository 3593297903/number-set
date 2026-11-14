from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QPushButton,QPlainTextEdit

STAGES={'GENERATING':'生成整数配额及完整号码池','WRITING':'写入实际明细和直选文本','AUDITING':'独立审查中','COMMITTING':'提交已审查文件','COMPLETED':'已完成 · 15项全部通过','FAILED':'失败 · 结果不可使用','CANCELLED':'已取消','ERROR':'发生错误'}

class CurrentBatchPage(QWidget):
    def __init__(self,cancel):
        super().__init__(); layout=QVBoxLayout(self)
        self.stage=QLabel('尚未开始'); self.stage.setStyleSheet('font-size:23px;padding:12px;'); layout.addWidget(self.stage)
        self.table=QTableWidget(3,5); self.table.setHorizontalHeaderLabels([f'第{i}遍' for i in range(1,6)]); self.table.setVerticalHeaderLabels(['A 逐号累加','B 展开排序','C 编号与文本重建']); layout.addWidget(self.table)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); layout.addWidget(self.log)
        self.cancel=QPushButton('取消当前任务'); self.cancel.clicked.connect(cancel); self.cancel.setEnabled(False); layout.addWidget(self.cancel)
    def reset(self):
        self.table.clearContents(); self.log.clear(); self.cancel.setEnabled(True); self.stage.setText('任务运行中')
        for i in range(3):
            for j in range(5): self.table.setItem(i,j,QTableWidgetItem('等待'))
    def update_event(self,event):
        self.stage.setText(STAGES.get(event.get('stage'),event.get('stage','')))
        if 'method' in event:
            text=event['status']
            if event.get('accepted') is False: text+=' / 未放行'
            self.table.setItem('ABC'.index(event['method']),event['round']-1,QTableWidgetItem(text))
        self.log.appendPlainText(' · '.join(str(event.get(k,'')) for k in ('stage','method','round','status','batch_id') if k in event))
