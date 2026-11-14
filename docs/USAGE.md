# 使用说明

## 启动

新设备使用Windows 10/11 x64并先安装Python 3.13 x64及Python launcher。克隆或解压仓库后，运行setup.cmd；安装完成后运行start.cmd。首次需要联网下载锁定依赖。start.cmd会显式将数据放到此份项目下的data目录，因此不依赖原电脑的E盘路径。

如需exe，按README安装依赖并构建，保留`dist/NumberTool`的完整目录。在项目根目录显式指定数据目录启动：

```powershell
$numberData = Join-Path (Get-Location).Path 'data'
& .\dist\NumberTool\NumberTool.exe gui --data-dir $numberData
```

程序默认路径为`E:/number/data`；克隆到其他位置时可用`--data-dir`指定。数据目录与程序分开保存。

## 生成与结果

选择100至300套原始号码，以及40至300个结果组。每套完整包含000至999，总原始份数为套数乘1000。每组分配总原始份数的0.2%至3%。

同一个原分组里，相同号码的份数转为直选金额；金额相同的号码合并一行：

```text
905.040直选1元
007.482直选2元
128.356直选3元
```

行尾金额分别适用于行内每个号码。号码始终保留三位，金额全部使用阿拉伯数字。原分组之间不合并；金额行递增，同金额号码保持原组首次出现顺序。

生成后A、B、C各执行五遍，每次新进程读取实际文件。15项全部通过，文件固定保存后才显示完成。查看、复制和再次导出使用已保存文本。

## 导出和备份

选择独立输出目录。程序会拒绝写入已有批次、暂存保留区域、可识别外部批次及其内部，避免污染已经审查的文件集合。文件夹版升级时保留数据目录。

恢复使用完整备份和空的目标目录；恢复后重新执行完整审查。中断批次在历史记录中检查，已有完整固定数据时可以重新复核。

## 命令行

在源码项目根目录运行：

```powershell
$numberQA = Join-Path (Get-Location).Path 'qa\manual'
& .\.venv\Scripts\python.exe -m number_app generate --copies 300 --groups 300 --data-dir $numberQA --result-json "$numberQA\generation.json"
$numberRun = Get-Content -LiteralPath "$numberQA\generation.json" -Raw -Encoding UTF8 | ConvertFrom-Json
& .\.venv\Scripts\python.exe -m number_app verify --batch-dir $numberRun.batch_dir --data-dir $numberQA --result-json "$numberQA\verify.json"
```

打包后的NumberTool.exe支持相同子命令；NumberVerify.exe可独立接收`--batch-dir`、`--data-dir`、`--result-json`执行完整复核。窗口版自动化请读取result-json并等待进程退出。

退出码：0成功、2输入不合法、3数据或审查不通过、4环境/IO/内部异常、5取消或中断。请把result-json保存到独立收据位置。
