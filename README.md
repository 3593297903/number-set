# 随机号码分组工具 2.0

Windows本地桌面工具：Python 3.13、PySide6、SQLite及spawn独立审查进程。

## 功能

- 原始套数可选100至300套，每套完整包含000至999。
- 随机分成40至300组，每组占总原始份数的0.2%至3%。
- 同组按号码份数合并为“直选N元”，同金额号码放在同一行，三位号码保留前导零。
- A逐号计数、B独立展开排序、C唯一编号检查及文本重建，各执行五遍；15项全部通过才完成。
- 历史记录、固定结果再次导出、中断恢复、备份及独立复核。
- 备份/导出在写入前检查目标路径，保护已有批次和暂存区域。

```text
905.040直选1元
007.482直选2元
128.356直选3元
```

源码仓库：[3593297903/number-set](https://github.com/3593297903/number-set)。本仓库只发布程序源码、测试、固定格式样例、构建配置和公开文档；实际号码数据、数据库、备份、QA证据、本机交接资料及exe构建产物不入Git。

## 新设备快速运行

当前程序面向Windows 10/11 x64。新设备需要安装Python 3.13 x64（包含Python launcher），首次安装依赖需要联网访问PyPI。

```powershell
git clone https://github.com/3593297903/number-set.git
cd number-set
.\setup.cmd
.\start.cmd
```

也可在GitHub下载源码ZIP后解压，双击setup.cmd安装，再双击start.cmd启动。数据写入当前项目目录的data子目录，不要求新设备存在E盘。数据与虚拟环境只在新设备本地建立，不随源码公开上传。

安装脚本只建立项目自己的.venv并安装锁定依赖；可重复运行更新安装，不会删除data。源码模式会保留命令窗口用于显示启动错误，构建后的exe为窗口版。

## 手动安装与源码启动

在项目根目录使用Windows和Python 3.13：

```powershell
py -3.13 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
& .\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
$numberData = Join-Path (Get-Location).Path 'data'
& .\.venv\Scripts\python.exe -m number_app gui --data-dir $numberData
```

版本约束在pyproject.toml，验证过的精确依赖在requirements-dev.lock。程序默认数据目录是`E:/number/data`；其他位置可像上面一样显式传入`--data-dir`。

## 测试与构建

```powershell
& .\.venv\Scripts\python.exe scripts\run_checks.py source
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm packaging\number_tool.spec
& .\.venv\Scripts\python.exe scripts\run_checks.py release --dist-dir .\dist\NumberTool
```

运行器在本项目的qa/checks创建独立收据和临时批次，按指定exe的实际SHA256准备测试元数据，不依赖本机未发布的QA文件。没有构建exe时release会明确失败。可追加pytest参数，例如`--collect-only`或`-k formatting`。

release测试会生成真实QA批次，并对其生成/审查进程做故障测试；日常历史不作为故障注入对象。

构建后保留dist/NumberTool完整目录，按[使用说明](docs/USAGE.md)显式指定数据目录启动exe。也可运行创建桌面快捷方式.ps1，通过指向本项目data目录的快捷方式启动。NumberVerify.exe可独立复核，验证范围见[验证记录](docs/VERIFICATION.md)。

## 数据与审查约束

0.2%至3%按合并前原始份数计算。金额恢复后的各组份数必须等于配额，全部结果中每个号码恰好有原始套数份；唯一编号恰好各使用一次。

三个审查主体各自读取固定文件、独立计算；不调用生成器或彼此的金额解析、统计和格式函数。五轮分别启动新进程，必须准确15个组合全部通过、进程正常退出且文件与报告未变。

正式入口没有随机种子、减少审查或跳过审查开关。没有可信历史快照的导入包会标注imported_declaration_only，表示相对包内声明的自洽性。重复五遍不能消除算法自身的固定缺陷。
