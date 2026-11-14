# 验证记录

这是2026-11-14在本机实际完成的验证快照，不是GitHub CI运行结果。完整运行数据和逐条审查文件存放在本机qa目录，不进入源码仓库。

| 验证范围 | 结果 |
|---|---|
| 修复后的源码全套 | 124项通过，0失败、0异常、0跳过 |
| 正式Windows可执行程序全套 | 61项通过，0失败、0异常、0跳过 |
| 另行编写的实际exe错误目标探测 | 8种路径均在写入前拒绝，目录树和批次状态不变 |
| 错误操作后的A、B、外部批次完整复核 | 各15/15 |
| 新生成的300000份独立逐号实点 | 000至999每号恰好300份，无遗漏、重复编号和文本差异 |

此次目录保护修复的生产代码仅涉及storage/output_paths.py、storage/backup.py和storage/export.py。分组、配额、直选格式和ABC各五遍策略保持原规则。

已覆盖正常备份/导出/恢复、批次内部及其他批次的错误目标、不存在子目录、外部批次、大小写、Windows目录联接和链接路径，以及原有金额、编号、文件损坏、进程异常和中断恢复测试。

本机实测Windows 10 x64、Python 3.13.13、PySide6 6.12.0。Qt源码交互测试已执行；原生目录选择器的全部点击和逐像素布局审阅未重新执行。没有做真实断电、坏盘及所有Windows版本的兼容性测试。

代码中的三个检查器独立解析/计算，每个五遍，每次重新启动spawn进程并读取实际数据。重复次数不能消除算法自身的固定缺陷，因此保留错误注入和实际文件回读验证。

从源码复现检查：

```powershell
& .\.venv\Scripts\python.exe scripts\run_checks.py source
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm packaging\number_tool.spec
& .\.venv\Scripts\python.exe scripts\run_checks.py release --dist-dir .\dist\NumberTool
```

运行器自行建立本轮QA目录，并依据所指定exe的实际SHA256准备回归测试元数据；新克隆不需要下载本机已有的candidate-exes.json或号码数据。必须真实构建后再执行release，缺少exe会明确失败。
