from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem
from number_app.checks.a_count import parse_a
from number_app.ui.results import healthy_row

class StatisticsPage(QWidget):
    def __init__(self,catalog):
        super().__init__(); self.catalog=catalog
        layout=QVBoxLayout(self); self.label=QLabel('统计仅显示已固定并通过审查的结果'); layout.addWidget(self.label)
        self.table=QTableWidget(1000,4); self.table.setHorizontalHeaderLabels(['号码','预期份数','实际份数','差值']); layout.addWidget(self.table)
    def load_batch(self,batch_id):
        row=healthy_row(self.catalog,batch_id); total=[0]*1000
        for group in range(1,row['group_count']+1):
            counts,_=parse_a((Path(row['batch_dir'])/f'groups/group_{group:03}.txt').read_bytes(),row['copies'])
            for code,n in enumerate(counts): total[code]+=n
        for i,n in enumerate(total):
            for j,v in enumerate([f'{i:03}',row['copies'],n,n-row['copies']]): self.table.setItem(i,j,QTableWidgetItem(str(v)))
        self.label.setText(batch_id+f" · {sum(total):,}原始份数 · 1000种号码")
