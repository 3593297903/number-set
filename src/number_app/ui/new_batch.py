from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QSpinBox,QPushButton

class NewBatchPage(QWidget):
    def __init__(self,catalog,start):
        super().__init__(); layout=QVBoxLayout(self); layout.setContentsMargins(30,25,30,25)
        title=QLabel('新建随机分组'); title.setStyleSheet('font-size:26px;font-weight:600'); layout.addWidget(title)
        layout.addWidget(QLabel('完整号码池 000～999 · 系统随机源 · 每份仅分配一次'))
        form=QFormLayout(); self.copies=QSpinBox(); self.copies.setRange(100,300); self.copies.setObjectName('copies')
        self.groups=QSpinBox(); self.groups.setRange(40,300); self.groups.setObjectName('groups')
        self.copies.setValue(int(catalog.setting('copies','100'))); self.groups.setValue(int(catalog.setting('groups','40')))
        form.addRow('原始套数',self.copies); form.addRow('最终分组数',self.groups); layout.addLayout(form)
        self.preview=QLabel(); self.preview.setStyleSheet('padding:25px;background:#e8f0f7;font-size:18px;'); layout.addWidget(self.preview)
        self.start=QPushButton('开始生成并审查'); self.start.setObjectName('startButton'); self.start.clicked.connect(start); layout.addWidget(self.start)
        layout.addWidget(QLabel('每组按原始份数的0.2%～3%分配。审查全部通过后才能取用结果。'))
        layout.addStretch()
        self.copies.valueChanged.connect(self.update_preview); self.groups.valueChanged.connect(self.update_preview); self.update_preview()
    def update_preview(self):
        s=self.copies.value()
        self.preview.setText(f'总份数  {s*1000:,}    |    每号 {s} 份\n单组范围  {2*s:,} ～ {30*s:,} 份    |    {self.groups.value()} 组')
