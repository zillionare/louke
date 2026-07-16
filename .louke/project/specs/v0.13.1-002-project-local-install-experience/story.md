# v0.13.1 Project-Local Install Experience + Release Identity Sync

## 1. 目标

完成 v0.13.0 之后识别出的两个紧耦合缺口，使得用户可以通过本地运行时、全局运行时来运行 louke。此外，还有一个小目标，即通过 louke 工作流发布的产品，始终有正确的版本号。

## 2. 用户故事

1. 作为 linux/mac 新用户（最终用户），我希望能从 git clone 目录开始，在 5 分钟内，通过 curl | sh 命令，在当前目录下，创建 .venv 虚拟环境（使用 louke 兼容的最高 python 版本），并安装 louke python 包。

2. 作为 windows 新用户（最终用户），我希望能从 github 下载一个 bat/ps 文件到git clone 目录，双击后，在当前目录下，创建 .venv 虚拟环境（使用 louke 兼容的最高 python 版本），并安装 louke python 包。

> 在上述两种安装中，构建的运行环境（.venv 及 louke 包）被称为本地运行时。通过本地运行时执行`lk`命令的方式，被称为本地运行。

3. 在前面两步安装中，安装器还将在用户环境下的可执行路径中，安装一个全局的 lk 命令，从而可以通过 `lk install`，在任何 git clone 目录创建 .venv 环境并安装最新的 louke python 包。

> 通过上述方式构建的运行环境（.venv 和 louke 包）被称为全局运行时。通过全局运行时执行`lk`命令的方式，被称为全局运行。

4. 当运行`lk --version`命令时，根据使用的是本地运行时，还是全局运行时，显示各自的版本，不要混淆。如果是本地运行时，则在输出版本后，拼接上`(local)`；如果是全局运行时，则在输出版本后，拼接上`(global)`

5. 在执行 `lk {command}`时，优先在当前目录下查找运行时。如果存在，则把`{command}`及参数传递给`{python-runtime} -m louke`作为参数。举例： `lk models list` -> `{python-runtime} -m louke models list`。

6. 在执行 `lk {command}`时，如果当前目录下不存在本地运行时，则使用全局运行时来运行命令。

7. 作为老用户，我希望在本地运行时下更新版本时，除更新.venv 和 louke python 包，还将根据当前项目已配置的 harness，自动执行 `board`命令以更新相关资源。

8. 作为老用户（最终用户），我希望在本地运行时下执行升级命令时，能够有选项可以同时更新全局的安装。当然，此时不会去为每一个项目执行`board`命令。

9. 作为最终用户，希望在执行更新时，可以指定 pypi index url，以及 louke 包的版本号。

10. 作为最终用户，我希望 louke 提供一种机制，确保在 release 时，构建物的版本号与 git tag 所暗示的版本号一致。
