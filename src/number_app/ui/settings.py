from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton,QFileDialog
from number_app.storage.backup import create_backup,restore_backup
from number_app.jobs.service import verify_batch

class SettingsPage(QWidget):
    def __init__(self,window):
        super().__init__(); self.window=window; c=window.catalog; layout=QVBoxLayout(self)
        label=QLabel('设置与独立复核'); label.setStyleSheet('font-size:24px;'); layout.addWidget(label)
        self.info=QLabel(f'软件 2.0.0 · 数据格式1 · direct_amount_v1\n数据目录：{window.data_dir}\n审查固定为 A/B/C 各5遍，独立新进程。'); self.info.setWordWrap(True); layout.addWidget(self.info)
        self.backup_label=QLabel('备份目录：'+c.setting('backup_root',str(window.data_dir.parent/(window.data_dir.name+'_backups')))); layout.addWidget(self.backup_label)
        for text,handler in [('选择数据目录（重启生效）',self.choose_data),('选择备份目录',self.choose_backup),('立即完整备份',self.backup),('验证备份并恢复到空目录',self.restore),('导入完整批次 · 独立复核15次',self.verify_import),('检查中断任务与历史损坏',self.scan)]:
            b=QPushButton(text); b.clicked.connect(handler); layout.addWidget(b)
        layout.addWidget(QLabel('恢复保留现有数据，仅接受空目标目录。导入复核会注明参数来自包内声明。')); layout.addStretch()
    def choose_data(self):
        folder=QFileDialog.getExistingDirectory(self,'选择日常数据目录',str(self.window.data_dir))
        if folder:
            self.window.catalog.set_setting('preferred_data_dir',folder)
            self.info.setText(self.info.text()+'\n下次启动使用：'+folder+'（现有数据保留）')
    def choose_backup(self):
        folder=QFileDialog.getExistingDirectory(self,'选择备份目录',str(self.window.data_dir.parent))
        if folder:
            self.window.catalog.set_setting('backup_root',folder); self.backup_label.setText('备份目录：'+folder)
    def backup(self):
        root=self.window.catalog.setting('backup_root',str(self.window.data_dir.parent/(self.window.data_dir.name+'_backups')))
        self.window.start_operation(lambda p,c:create_backup(self.window.data_dir,root))
    def restore(self):
        source=QFileDialog.getExistingDirectory(self,'选择含BACKUP_COMPLETE.json的备份目录')
        if not source: return
        target=QFileDialog.getExistingDirectory(self,'选择空的恢复目标目录')
        if target: self.window.start_operation(lambda p,c:restore_backup(source,target,progress=p,cancel=c))
    def verify_import(self):
        folder=QFileDialog.getExistingDirectory(self,'选择包含manifest.json的完整批次目录')
        if folder: self.window.start_operation(lambda p,c:verify_batch(folder,self.window.data_dir,progress=p,cancel=c))
    def scan(self):
        from number_app.storage.recovery import inspect_recovery
        self.window.start_operation(lambda p,c:dict(status='RECOVERY_READY',pending=inspect_recovery(self.window.data_dir)))
