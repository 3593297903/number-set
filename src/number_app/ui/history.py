from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QTableWidget,QTableWidgetItem,QPushButton,QAbstractItemView

class HistoryPage(QWidget):
    def __init__(self,catalog,open_batch,verify,recover,export):
        super().__init__(); self.catalog=catalog; self.rows=[]
        layout=QVBoxLayout(self); self.filter=QLineEdit(); self.filter.setPlaceholderText('按日期、批次编号或状态查找，例如 2026-11-14'); self.filter.textChanged.connect(self.refresh); layout.addWidget(self.filter)
        self.table=QTableWidget(0,6); self.table.setHorizontalHeaderLabels(['日期','批次','套数','组数','状态','最近审查']); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); layout.addWidget(self.table)
        buttons=QHBoxLayout()
        for label,callback in [('刷新',self.refresh),('查看固定结果',lambda:open_batch(self.selected())),('完整复核15次',lambda:verify(self.selected())),('恢复中断批次',lambda:recover(self.selected())),('再次导出',lambda:export(self.selected()))]:
            b=QPushButton(label); b.clicked.connect(callback); buttons.addWidget(b)
        layout.addLayout(buttons); self.refresh()
    def selected(self):
        i=self.table.currentRow()
        return self.rows[i]['batch_id'] if 0<=i<len(self.rows) else None
    def refresh(self,*args):
        text=self.filter.text().strip().lower(); self.rows=[r for r in self.catalog.list() if text in (r['created_at']+' '+r['batch_id']+' '+r['status']).lower()]
        self.table.setRowCount(len(self.rows))
        for i,r in enumerate(self.rows):
            for j,key in enumerate(['created_at','batch_id','copies','group_count','status','last_audit_id']): self.table.setItem(i,j,QTableWidgetItem(str(r[key] or '')))
        self.table.resizeColumnsToContents()
