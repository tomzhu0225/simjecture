# Simjecture 课题组安装与开发指南

这份指南面向第一次接触 Simjecture、Git 和 GitHub 的同学。先把程序跑起来，再用一个真实的小修改走完开发和提交 PR 的流程。只使用软件的同学可以读到第 4 节；准备参与开发的同学继续往下读。

Simjecture 有两种主要用法：**交互模式**让你和智能体一起写代码、运行仿真、看图和排查问题；**自主研究模式**从你给出的假设、研究范围和时间预算出发，让智能体设计实验、寻找反例，并把证据提交给独立审阅者。仿真成功退出和科学结论成立，是两件需要分别检查的事。

项目仓库：[github.com/tomzhu0225/simjecture](https://github.com/tomzhu0225/simjecture) · 在线试用：[simjecture.com](https://simjecture.com) · 完整文档：[drawingsword.com/simjecture](https://drawingsword.com/simjecture/)

## 1. 先选适合自己的路径

| 你的目标 | 建议从哪里开始 | 是否需要 GitHub 账号 |
| --- | --- | --- |
| 先看看软件能做什么 | 打开在线试用网站 | 访客可以试用；登录后可以保留项目、上传文件 |
| 在自己的电脑或组内服务器上做研究 | 安装发布版 | 下载和安装公开发布版不需要账号 |
| 修改 Simjecture、修问题或贡献新功能 | Fork 仓库，再安装源码开发环境 | 需要自己的 GitHub 账号 |
| 接入自己的求解器或诊断程序 | 先跑通程序，再提供接口、示例和验证 | 提交公开贡献时需要账号 |

**第一次使用，建议先完成一个普通 Python 小任务。** 不必先装 FLASH、WarpX，也不必先配置 GPU。

发布版和开发版可以同时存在，但要分清两个目录：发布版一般在 `~/simjecture`，自己 Fork 的源码建议放在 `~/src/simjecture`。修改源码后，要从源码目录启动，才能看到修改。

## 2. 安装发布版

### 2.1 确认命令在哪里运行

本指南的完整安装与实验环境使用 **Linux 或 Windows 的 WSL2**。下面标为 `bash` 的代码块，要在 Linux / Ubuntu 终端执行。只有安装 WSL 的代码块在 Windows PowerShell 执行。

| 你的电脑 | 操作方式 |
| --- | --- |
| Ubuntu / Debian / 其他 Linux | 打开终端，直接继续安装 |
| Windows | 先准备 WSL2 Ubuntu，再在 Ubuntu 终端里安装 |
| macOS | 可以用浏览器试用，或通过 SSH 连接 Linux 服务器运行完整实验环境 |

Windows 尚未安装 WSL 的同学，在**管理员 PowerShell**中执行：

```powershell
wsl --install -d Ubuntu
```

按提示重启，打开 Ubuntu，设置一个 Linux 用户名和密码。输入 Linux 密码时，终端通常不显示字符，直接输入后回车即可。然后在 PowerShell 检查：

```powershell
wsl -l -v
```

Ubuntu 对应的 `VERSION` 应为 `2`。安装遇到系统版本、虚拟化或发行版问题时，按 [微软的 WSL 安装说明](https://learn.microsoft.com/zh-cn/windows/wsl/install) 排查。

### 2.2 安装并打开 Simjecture

在 Linux / Ubuntu 终端执行：

```bash
curl -fsSL https://github.com/tomzhu0225/simjecture/releases/latest/download/install.sh | bash
```

这条命令安装**最新稳定发布版**，准备 Python、依赖和本地界面，并校验下载的程序包。首次安装需要联网，终端会显示进度；如果提示输入 `sudo` 密码，输入当前 Linux 用户的密码。

如果提示 `curl: command not found`，Ubuntu / Debian 用户先执行：

```bash
sudo apt update
sudo apt install -y curl
```

安装成功后，按终端给出的地址打开浏览器。默认是：

```text
http://127.0.0.1:8765
```

以后重新启动，不需要重新安装：

```bash
~/simjecture/start-workspace
```

终端会保持运行，用来提供网页服务。浏览器关掉后，可以重新打开同一个地址。需要关闭研究任务时，先在界面中暂停或停止；仅关闭浏览器，并不等于停止仿真。

如果 8765 端口被占用，改用一个空闲端口：

```bash
~/simjecture/start-workspace --port 8766
```

然后打开 `http://127.0.0.1:8766`。

### 2.3 安装在组内服务器上

先按平常的方式 SSH 登录服务器，再在服务器终端执行上面的安装命令。程序和计算任务会运行在服务器上。

要在自己的电脑看界面，在**自己电脑的另一个终端**执行端口转发。下面的用户名、服务器地址和 SSH 端口都要换成自己的：

```bash
ssh -p 22 -N -L 8766:127.0.0.1:8765 YOUR_USER@YOUR_SERVER
```

服务器上的 Simjecture 使用 8765，本地浏览器打开 `http://127.0.0.1:8766`。两个终端都要保持连接。安装器也会打印转发命令；实际使用哪一个 SSH 地址和端口登录，就用哪一个转发。

服务器的安装位置可能因管理员部署方式而不同。以安装完成后打印的启动路径为准。不要为了打开网页而把本地操作界面直接绑定到公网。

### 2.4 数据放在哪里，怎样升级

默认发布版目录的含义如下：

| 位置 | 内容 |
| --- | --- |
| `~/simjecture/app/` | 按版本保存的程序和 Python 环境 |
| `~/simjecture/.runtime/` | 安装的科研工具和运行环境 |
| `~/simjecture/artifacts/projects/` | 会话、输入、实验输出和研究记录 |
| `~/simjecture/start-workspace` | 日常启动入口 |

升级稳定版时，可以重新运行第 2.2 节的安装命令。安装器保留项目、工具和旧程序版本，切换启动入口。组内正式计算仍应保存重要数据的备份，并记录所用版本。

复现论文或组内统一环境时，从 [Releases 页面](https://github.com/tomzhu0225/simjecture/releases) 选择**已发布**的指定版本，使用该版本的安装地址。`rc` 是候选版；它不会由 `latest` 自动选中。未发布的 Draft 也没有普通用户可用的公开下载地址。源码 `main` 则可能比稳定版更新。

更详细的部署说明见 [安装文档](https://drawingsword.com/simjecture/getting-started/installation.html)。

## 3. 连接模型，完成第一次小任务

安装 Simjecture 和获得模型访问权限是两件事。本地版需要接入你有权限使用的模型；在线试用站提供的模型和算力则受该站的使用额度限制。

### 3.1 本地版怎么选择智能体

如果使用兼容 API，在本地界面的账户 / 工作区菜单里打开 **Connections（连接设置）**，填入模型服务商提供的 Base URL 和 API key。然后回到会话，选择连接和模型。没有模型列表时，按界面提示输入准确的模型 ID。

如果机器上已经装好并登录了支持的原生 CLI 智能体，可以直接在会话中选择它。CLI 的登录应在**运行 Simjecture 的那台机器、同一个系统用户**下完成。自己的 Windows 浏览器里登录过模型网站，不代表 Linux 服务器上的 CLI 已经登录。

密钥放在连接设置里，不要写进聊天、源代码或 GitHub 提交。组内共享服务器最好使用各自的系统账号和模型账号。具体界面步骤见 [研究工作区说明](https://drawingsword.com/simjecture/getting-started/research-workspace.html)。

### 3.2 先做一个可以检查的小任务

在交互会话中，可以直接输入：

> 用 Python 模拟一个单摆。摆长 1 m，重力加速度 9.81 m/s²，初始角度 30°，初始角速度为零，计算 20 秒。画出角度和总能量随时间的变化，再提高积分精度检查结果。保留脚本、参数和图。

检查四件事：有没有真实运行记录，脚本和输入是否保存，图是否来自实际输出，智能体是否解释了数值误差。如果模型连接失败，先解决连接问题；如果命令执行失败，先读该命令的日志。

### 3.3 再试自主研究

在同一会话准备研究简报。例如：

> 检验假设：摆长 1 m、重力加速度 9.81 m/s² 时，对于 10° 到 80° 的释放角，非线性单摆周期与小角度近似的相对差异都不超过 1%。寻找反例，并通过积分精度或时间步检查确认。先给 10 分钟计算预算；若独立审阅接受了反例，可以结束并报告。使用普通 Python 即可。

在 **Autonomous study（自主研究）**中由智能体准备简报，检查假设、范围、完成策略和预算，再启动。新研究使用 minimal 模式；不同完成策略决定接受反例后直接结束，还是继续提出并验证修正假设。

研究结束时，先读证据和审阅意见。时间耗尽、证据不足和假设被反驳，分别说明不同情况，不应混在一起。具体操作见 [第一次研究](https://drawingsword.com/simjecture/getting-started/first-run.html)。

## 4. 什么时候需要 FLASH、WarpX 或其他工具

普通 Python 计算、拟合、画图和分析已有数据，可以先用默认环境。专业求解器是另行安装和验证的工具，不会因为装好了 Simjecture 就全部出现。

| 任务 | 通常需要准备什么 |
| --- | --- |
| 常微分方程、参数扫描、一般数据分析 | 默认 Python 数值环境 |
| MHD、辐射流体等 FLASH 计算 | 自行取得 FLASH 源码，选择物理配置并构建对应应用 |
| PIC / Hybrid-PIC 等 WarpX 计算 | 对应维度、物理模块和 CPU / CUDA 运行环境 |
| EOS、opacity、合成诊断等 | 对应工具及其需要的数据、材料和接口 |
| 课题组自己的程序 | 一个能运行的例子、输入输出说明和数值验证 |

在 **Research tools（科研工具）**中查看安装和就绪状态。可以让智能体协助构建、接入和检查。FLASH 不随 Simjecture 分发；需要按上游渠道取得源码并按其许可使用。编译好的 FLASH 程序对应特定应用和物理配置，需要其他初值或模块时可能要重新构建。

没有 GPU 的电脑也能参与多数文档、界面、证据服务和普通 Python 开发。真正使用 GPU 的测试，再放到组内已配置的机器上做。加入 SSH 计算机器后，先通过相同的实验启动路径跑一个已知例子。

工具“已安装”、例子“运行成功”和方法“足以支持科学结论”，是三个层次。接入时分别给出证据。可继续读 [工具部署](https://drawingsword.com/simjecture/how-to/deploy-runtimes.html)、[添加工具接口](https://drawingsword.com/simjecture/how-to/add-a-capability.html) 和 [实际启动路径的 commissioning](https://drawingsword.com/simjecture/how-to/guided-commissioning.html)。

## 5. 开发前，先认识这几个词

| 名称 | 在这个项目里是什么意思 |
| --- | --- |
| Git | 你电脑上记录代码版本的工具 |
| GitHub | 网上保存仓库、讨论问题和审阅代码的平台 |
| Repository / Repo（仓库） | 程序文件及其版本历史 |
| Fork | 在自己的 GitHub 账号下建立原仓库的副本 |
| Clone | 把网上的仓库下载到自己的电脑 |
| Branch（分支） | 为某个修改单独开一条工作线，例如 `fix/tool-status` |
| Commit（提交） | 在本地保存一次有说明的修改记录；此时还没有上传 |
| Push（推送） | 把本地提交上传到你的网上仓库 |
| PR / Pull request | 请求维护者审阅并把你的分支合入原仓库 |
| `origin` / `upstream` | 本指南中，前者是你的 Fork，后者是原始 Simjecture 仓库 |

可以按这个顺序理解开发：**在分支上修改 → 本地 Commit → Push 到自己的 Fork → 提交 PR → 维护者审阅与合并**。Push 之后仍然需要 PR，原仓库才会收到你的合并请求。

## 6. Fork，并安装源码开发环境

下面演示 Ubuntu / Debian / WSL Ubuntu 的流程。无需申请原仓库的写权限，也不需要先配置 SSH key。

### 6.1 在 GitHub 上 Fork

登录自己的 GitHub 账号，打开 [Simjecture 仓库](https://github.com/tomzhu0225/simjecture)，点击右上角 **Fork**，选择自己的账号，保持仓库名 `simjecture`，点击 **Create fork**。初次开发复制默认 `main` 分支即可。

完成后，你会有一个地址类似 `https://github.com/YOUR_GITHUB_NAME/simjecture` 的仓库。`YOUR_GITHUB_NAME` 要换成你的真实 GitHub 用户名，不是显示昵称。可参考 [GitHub 的 Fork 说明](https://docs.github.com/en/pull-requests/how-tos/work-with-forks/fork-a-repo)。

### 6.2 准备 Git、GitHub 登录工具和 uv

在 Linux / Ubuntu 终端执行：

```bash
sudo apt update
sudo apt install -y git curl gh
```

检查安装：

```bash
git --version
gh --version
```

`gh` 是 GitHub 的命令行工具，用它完成一次网页登录，可以避免初学者手动处理 Git 推送凭据。若发行版没有 `gh` 包，或其版本不能完成登录，改用 [GitHub CLI 官方安装步骤](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)。

安装 Python 环境工具 uv：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安装器打印路径设置提示后，重新打开 Ubuntu 终端，再检查：

```bash
uv --version
```

uv 会按项目需求准备 Python 和依赖，开发阶段不必另建 Conda 环境。其他安装方式见 [uv 官方说明](https://docs.astral.sh/uv/getting-started/installation/)。

### 6.3 登录 GitHub，让终端可以推送

```bash
gh auth login
```

按提示选择 **GitHub.com**、**HTTPS**、通过浏览器登录，并允许为 Git 配置认证。把终端给出的验证码填到它指定的网页中。完成后执行：

```bash
gh auth setup-git
gh auth status
```

这一步登录的是 GitHub，用于上传代码。它不是 Simjecture 的模型登录，也不是在公共试用站登录账号。

Git 的 HTTPS 推送不能直接使用 GitHub 网页登录密码；本流程由 `gh` 管理认证。登录细节见 [GitHub CLI 的认证说明](https://cli.github.com/manual/gh_auth_login)。

### 6.4 Clone 自己的 Fork

先把下面地址中的 `YOUR_GITHUB_NAME` 换成自己的用户名：

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/YOUR_GITHUB_NAME/simjecture.git
cd simjecture
git remote add upstream https://github.com/tomzhu0225/simjecture.git
git remote -v
```

最后一条命令的输出应该满足：`origin` 指向你自己的仓库，`upstream` 指向 `tomzhu0225/simjecture`。如果 `origin` 是原仓库，你 Clone 的不是自己的 Fork；先确认路径，再继续。

为**当前仓库**设置提交署名。下面的姓名和邮箱要换成自己的：

```bash
git config user.name "Li Ming"
git config user.email "YOUR_GITHUB_EMAIL"
```

邮箱使用 GitHub 账号已验证的地址，或 GitHub 提供的 `noreply` 隐私邮箱。提交邮箱会进入版本记录；不希望公开个人邮箱时，在 GitHub 账户邮箱设置里查看隐私邮箱。见 [提交邮箱设置](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address)。

### 6.5 安装依赖并启动开发版

确认现在在 `~/src/simjecture` 目录，然后执行：

```bash
uv sync --frozen --extra workspace
uv run --extra workspace simjecture doctor --profile core
uv run --extra workspace simjecture web
```

第一条命令准备项目的 `.venv`；第二条检查核心运行环境；第三条启动本地界面。如果 doctor 提示实验沙箱不可用，先读诊断并请管理员参考 [受限容器说明](https://drawingsword.com/simjecture/how-to/restricted-containers.html)。没有安装的可选求解器，不需要为一次文档或界面修改全部补齐。

以后从这个源码目录启动，也可以用：

```bash
bash scripts/launch-workspace.sh
```

如果浏览器里看不到代码修改，重新启动开发服务，并确认打开的是开发版打印的地址。运行 `~/simjecture/start-workspace` 打开的仍是另一份发布版。

### 6.6 用编辑器打开代码

Windows 用户可以在 Windows 上安装 VS Code 和 **WSL** 扩展，然后在 Ubuntu 的源码目录执行 `code .`。窗口应显示连接到 WSL。项目放在 Linux 的 `~/src` 下，避免在 Windows 文件夹和 WSL 文件夹之间来回复制。具体步骤见 [VS Code 的 WSL 开发说明](https://code.visualstudio.com/docs/remote/wsl)。

Linux 用户直接用自己熟悉的编辑器打开源码目录即可。下面的 Git 命令仍在该目录的终端执行。

## 7. 完成第一个真实的小修改

第一次贡献可以是：补充一个安装步骤，修正一个容易误解的字段说明，修复一个能复现的界面问题，或给课题组的诊断程序补一个验证例子。新功能较大时，先开 Issue 讨论范围。

### 7.1 每个问题开一个分支

下面用文档修改举例。开始前，`git status` 应显示没有未提交的修改：

```bash
git status
git switch main
git fetch upstream
git merge --ff-only upstream/main
git push origin main
git switch -c docs/clarify-installation
```

这几步先更新你的 `main`，再建立工作分支。`--ff-only` 不会替你处理分叉的历史；若它拒绝更新，保留现场，请熟悉 Git 的同学检查。不要为了继续执行而直接运行 `reset --hard`。

用编辑器修改你准备改善的文档，例如 `docs/getting-started/installation.md`。如果是修程序，可用 `fix/具体问题` 这样的分支名；新功能可用 `feat/具体功能`。分支名建议使用英文、数字和短横线。

### 7.2 看懂自己的修改

```bash
git status
git diff
```

`git status` 告诉你改了哪些文件；`git diff` 显示实际改动。确认没有混入仿真输出、临时脚本、凭据或与你这次修改无关的内容。

项目主要目录如下：

| 目录 | 开发时常用于什么 |
| --- | --- |
| `src/conjecture_solver/` | 研究服务、智能体接入、实验执行等 Python 代码 |
| `src/conjecture_solver/web/static/` | 本地与共享网页界面的 JavaScript、CSS 和 HTML |
| `src/conjecture_solver/public/` | 公共站点的账户、队列和执行服务 |
| `skills/` | 给智能体看的工具使用说明和稳定注意事项 |
| `capabilities/` | 求解器或工具的运行接口与身份描述 |
| `tests/` | 用于检查程序行为的测试 |
| `docs/` | 用户和开发者文档 |

不要直接修改自己安装目录里的 `site-packages` 来提交贡献。应修改 Fork 中的源文件，测试后提交对应的源文件。

## 8. 修改后，怎样检查

不需要为了修一个文字问题重新做一场长时间科研计算。检查应与修改相关，并保留实际结果。

| 修改类型 | 至少应该检查什么 |
| --- | --- |
| 文档 | 命令、文件路径和链接是否正确，文档能否构建 |
| Python 行为 | 相关测试、失败路径，以及代码格式检查 |
| 网页界面 | 实际点击、宽屏和窄屏、相关浏览器测试 |
| 求解器接口 | 从实际实验启动器跑通例子，确认输出、单位、身份和日志 |
| 证据或研究规则 | 与维护者先讨论，验证原有约束和恢复流程 |

第一次可以运行这个很小的测试模块：

```bash
uv run --extra workspace pytest tests/test_models.py -q
```

它检查模型约束，不需要模型 API，也不需要 GPU。修其他模块时，换成与你修改相关的测试文件。修改 Python 后再检查：

```bash
uv run --extra workspace ruff check .
git diff --check
```

修改文档时，增加文档依赖并构建到一个新的输出目录：

```bash
uv sync --frozen --extra workspace --group docs
uv run --extra workspace --group docs sphinx-build -W --keep-going -b html docs docs/_build/check
uv run --extra workspace --group docs python scripts/check_docs_links.py docs/_build/check
```

最后的链接检查会指出缺失的本地页面或文件。若复用过不同主题的旧输出目录，可换一个新的构建目录，避免旧文件影响结果。

浏览器测试需要额外的 `browser` 依赖组和 Chromium；完整命令、公共服务和 MCP 等专项检查见 [CONTRIBUTING.md](https://github.com/tomzhu0225/simjecture/blob/main/CONTRIBUTING.md)。普通回归测试不应使用真实密钥或消耗付费模型额度。

测试失败时，先区分代码错误、缺依赖和机器不支持的执行环境。把未运行的检查写清楚，不要把“没有测试”写成“通过”，也不要删除检查来掩盖失败。

## 9. Commit、Push，然后提交 PR

### 9.1 保存到本地 Git 历史

以第 7 节的文档修改为例：

```bash
git add docs/getting-started/installation.md
git diff --cached
git commit -m "Clarify the Linux installation steps"
```

`git add` 选择这次要提交的文件，`git diff --cached` 检查这些已选择的改动，`git commit` 将它们写入本地历史。初学时逐个选择文件，比直接 `git add .` 更容易发现误提交。

### 9.2 推送到自己的 Fork

```bash
git push -u origin docs/clarify-installation
```

这里上传到的是你自己的 GitHub 仓库。如果提示权限不足，检查 `git remote -v` 和 `gh auth status`，确认推送目标与登录账号相符。

### 9.3 在浏览器中打开 PR

打开自己的 Fork，点击 **Compare & pull request**。若没有这个按钮，在原仓库的 **Pull requests → New pull request** 中选择 **compare across forks**。

确认合并方向：

| 字段 | 应当选择 |
| --- | --- |
| Base repository（接收方） | `tomzhu0225/simjecture` |
| Base（目标分支） | `main` |
| Head repository（你的改动所在仓库） | `YOUR_GITHUB_NAME/simjecture` |
| Compare（你的工作分支） | `docs/clarify-installation` |

写清标题和说明，再点击 **Create pull request**。还没完成但希望先讨论时，可以建 **Draft PR**。页面操作见 [GitHub 的 Fork PR 说明](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork)。

PR 描述不必很长，但要让别人知道问题、改动和验证。可以按下面的结构填写，删掉不适用的部分：

```text
原来的问题
Windows 新用户容易把 Linux 安装命令输入到 PowerShell。

这次改动
补充执行环境说明，把 WSL 和 Ubuntu 终端的命令分开。

怎样检查
文档构建和本地链接检查通过；Ubuntu 安装步骤已核对。
没有改动程序行为，没有重新运行付费科研任务。

相关 Issue
如果有，对应 #问题编号。
```

这里的检查结果必须换成自己真正做过的结果，不要直接复制示例中的“通过”。

### 9.4 收到意见后怎么改

继续修改**同一个工作分支**，重新检查、Commit，然后执行 `git push`。新提交会自动出现在原 PR 里，不必每次重新建 PR。

PR 的红叉通常表示自动检查失败。点击对应检查，看具体报错。首次贡献者的 CI 有时需要维护者批准才能运行；等待批准不等于代码有问题。一个绿色检查也不等于 PR 已经合并，仍需审阅。

合并后，可以在 GitHub 上删除已合并的远程工作分支；历史提交和 PR 讨论仍然保留。本地切回 `main`，按第 7.1 节的更新步骤同步。再使用 `git branch -d 分支名` 删除已合并的本地分支。如果因 squash 合并提示“未完全合并”，先保留，请同学核对，不必强制删除。

## 10. 课题组的求解器、脚本和研究经验怎样贡献

### 10.1 已有程序先整理成一个可复现的小包

对于组内的场数据读取器、后处理、诊断程序或求解器接口，先准备：

1. **运行命令**：别人用什么命令启动，需要什么软件和硬件。
2. **输入说明**：参数、单位、坐标系、边界条件以及数据格式。
3. **输出说明**：输出文件在哪里，哪些量能作为诊断，怎样读出结果。
4. **已知例子**：给定输入应该得到什么，误差允许多少。
5. **适用范围与来源**：哪些物理可以做，哪些不可以；代码和数据来自哪里、是否可以分发。

先把这些说明和例子做好，再讨论是否增加 `skills/`、`capabilities/`、安装入口或 GUI 控件。接入工具的说明应写稳定接口和数值注意事项，具体研究问题交给每场研究设计。

带来源限制的求解器可以贡献构建与运行接口，原始源码和二进制留在各自的合法安装环境中。大规模输出、检查点和组内未公开资料也不要直接放入公开 Fork。可先用小型公开或合成数据验证接口。

### 10.2 不修改核心代码，也能贡献

一个可靠的诊断、一套能发现错误的数值控制、一个准确的问题复现，或者一份有输入输出和限制说明的研究记录，都能帮助项目。

用科学算例提交结果时，保留人提出的问题、模型和程序版本、输入、实际运行、数值控制、失败尝试与审阅意见。已有输出的重绘或重放，应明确标注；它不等于新做了一场仿真。

普通代码贡献按项目的 Apache-2.0 许可处理，保留必要来源和上游署名。论文署名则应按实际科研贡献，与该研究的合作者另行讨论。

## 11. 常见问题

| 遇到的情况 | 先检查什么 |
| --- | --- |
| PowerShell 提示不认识 `bash` 或 Linux 命令 | 是否应该切到 WSL 的 Ubuntu 终端 |
| `uv: command not found` | uv 是否安装成功；按安装器提示重新打开终端 |
| `not a git repository` | 先 `pwd`、`ls`，确认在源码仓库目录，再执行 Git 命令 |
| `Author identity unknown` | 在仓库中设置第 6.4 节的姓名和邮箱 |
| Push 时提示 `Permission denied` / 403 | `origin` 是否指向自己的 Fork；`gh auth status` 是否登录自己的账号 |
| 无法在原仓库直接 Push | 使用自己的 Fork，推送工作分支，再提交 PR |
| 网页中的模型不可用 | 登录 / API 配置是否在运行 Simjecture 的机器上，模型 ID 是否正确 |
| 改代码后界面没变 | 是否仍启动着发布版或旧服务，浏览器是否打开了正确端口 |
| 沙箱或 Linux namespace 报错 | 保存 doctor 诊断，按受限主机文档由管理员确定执行后端 |
| Shell 脚本提示 `bash\r` 不存在 | 检查编辑器是否保存成 CRLF；Shell 脚本应使用 LF |
| 一个 PR 里出现很多无关文件 | 用 `git diff --cached` 检查选择的文件，只提交与本问题相关的改动 |
| CI 红叉 | 点击失败检查，看具体错误；缺硬件和实际测试失败分开报告 |

向组内同学或维护者求助时，发出**执行的命令、完整报错、系统、运行目录和版本**，比只发“跑不了”更容易定位问题。先去掉密钥、密码和不宜公开的数据。

源码目录中记录版本可以使用：

```bash
git rev-parse --short HEAD
uv run --extra workspace python -c "from importlib.metadata import version; print(version('simjecture'))"
```

## 12. 日常操作速查

| 想做什么 | 命令或操作 |
| --- | --- |
| 启动安装好的发布版 | `~/simjecture/start-workspace` |
| 启动当前源码开发版 | 在仓库里运行 `bash scripts/launch-workspace.sh` |
| 查看文件改动 | `git status`、`git diff` |
| 查看这次选中的提交内容 | `git diff --cached` |
| 新开一个修复分支 | `git switch -c fix/具体问题` |
| 选择本次要提交的文件 | `git add 具体文件路径` |
| 保存一次本地提交 | `git commit -m "说明这次改了什么"` |
| 首次推送当前分支 | `git push -u origin 当前分支名` |
| 在同一个 PR 里继续更新 | 修改、检查、Commit，再 `git push` |
| 向原项目提交改动 | 在 GitHub 上开 PR，接收方选原仓库的 `main` |
| 更新主线 | 干净工作区中切到 `main`，`git fetch upstream`，再 `git merge --ff-only upstream/main` |

组内第一次练习可以这样安排：每个人独立装好环境，完成一个可检查的小任务；再各自选一个真实的小问题，走完一个 PR。后续再分工做求解器接入、诊断验证或核心开发。
