from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QPlainTextEdit,QApplication,QTableWidget,QTableWidgetItem
from number_app.storage.files import check_snapshot,load_json
from number_app.storage.access import healthy_row

class ResultsPage(QWidget):
    def __init__(self,catalog):
        super().__init__(); self.catalog=catalog; self.batch_id=None; self.raw=None
        layout=QVBoxLayout(self); self.label=QLabel('请选择一个已完成批次'); layout.addWidget(self.label)
        bar=QHBoxLayout(); self.group=QComboBox(); self.group.setObjectName('resultGroup'); bar.addWidget(self.group)
        self.copy=QPushButton('复制本组'); self.copy.setObjectName('copyGroup'); self.copy.clicked.connect(self.copy_current); bar.addWidget(self.copy); layout.addLayout(bar)
        self.text=QPlainTextEdit(); self.text.setReadOnly(True); self.text.setObjectName('resultText'); layout.addWidget(self.text,3)
        self.quotas=QTableWidget(0,3); self.quotas.setHorizontalHeaderLabels(['原组号','原始份数','显示比例']); layout.addWidget(self.quotas,2)
        self.group.currentIndexChanged.connect(self.show_group); self.copy.setEnabled(False)
    def load_batch(self,batch_id):
        row=healthy_row(self.catalog,batch_id); self.batch_id=batch_id
        self.label.setText(batch_id+' · 固定结果 · '+row['batch_dir'])
        q=load_json(Path(row['batch_dir'])/'quotas.json')['groups']
        self.group.blockSignals(True); self.group.clear(); self.group.addItems([f"第{g['group']}组 · {g['raw_count']}份" for g in q]); self.group.blockSignals(False)
        self.quotas.setRowCount(len(q))
        for i,g in enumerate(q):
            u=g['display_percent_units']; values=[g['group'],g['raw_count'],f'{u//1000000}.{u%1000000:06}%']
            for j,v in enumerate(values): self.quotas.setItem(i,j,QTableWidgetItem(str(v)))
        self.show_group(0)
    def show_group(self,index):
        if not self.batch_id or index<0: return
        try:
            row=healthy_row(self.catalog,self.batch_id)
            self.raw=(Path(row['batch_dir'])/f'groups/group_{index+1:03}.txt').read_bytes()
            self.text.setPlainText(self.raw.decode('utf-8')); self.copy.setEnabled(True)
        except Exception as e:
            self.raw=None; self.copy.setEnabled(False); self.text.setPlainText(str(e))
    def copy_current(self):
        self.show_group(self.group.currentIndex())
        if self.raw: QApplication.clipboard().setText(self.raw.decode('utf-8'))
