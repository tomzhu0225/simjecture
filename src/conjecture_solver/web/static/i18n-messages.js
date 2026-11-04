/* Phase-one explanatory UI copy. Keep identifiers and research content unchanged. */
"use strict";

window.SimjectureMessages = {
  "workspace.spacesHelp": {
    "en": "Separate places for your research. Switching leaves running work in progress.",
    "zh-CN": "为不同研究设置独立工作区。切换工作区不会中断正在运行的任务。"
  },
  "workspace.collectionHelp": {
    "en": "Conversations can have their own questions. Existing study records stay unchanged.",
    "zh-CN": "每个对话可以研究不同的问题。已有研究记录保持不变。"
  },
  "workspace.projectEmpty": {
    "en": "Your work will appear here.",
    "zh-CN": "你的研究工作将显示在这里。"
  },
  "workspace.knowledgeIntro": {
    "en": "Find the work behind your next idea.",
    "zh-CN": "查找能为下一个研究想法提供依据的资料。"
  },
  "workspace.knowledgePreviewHelp": {
    "en": "Select a result to read the passage, check its version, and bring it into a conversation.",
    "zh-CN": "选择一条结果，阅读相关段落、核对版本，并将其引入对话。"
  },
  "workspace.knowledgeRefreshHelp": {
    "en": "Folders refresh every minute while Simjecture is running. Conversations appear after a turn finishes.",
    "zh-CN": "Simjecture 运行期间，文件夹索引每分钟刷新一次。对话在一轮交互结束后加入索引。"
  },
  "workspace.knowledgeIndexHelp": {
    "en": "Indexes text, code, PDF, PPTX, DOCX and notebooks. Hidden folders, dependencies, build caches and large binary outputs are skipped. Scanned PDFs need a text layer; figures are available in the original file.",
    "zh-CN": "支持索引文本、代码、PDF、PPTX、DOCX 和笔记本。跳过隐藏文件夹、依赖、构建缓存和大型二进制输出。扫描版 PDF 需要文本层；图表请查看原始文件。"
  },
  "workspace.knowledgeAgentHelp": {
    "en": "Connect an external agent to this workspace's enabled sources. These tools can search and read; they cannot change your files or start research.",
    "zh-CN": "将外部智能体连接到此工作区已启用的资料源。这些工具可搜索和读取资料，无法修改文件或启动研究。"
  },
  "workspace.knowledgeTerminalHelp": {
    "en": "Run these commands on the machine that owns the folders. The browser server refreshes the index; when it is closed, refresh with:",
    "zh-CN": "请在存放这些文件夹的机器上运行命令。Web 服务会刷新索引；服务关闭后，可使用以下命令刷新："
  },
  "workspace.sharedContextHelp": {
    "en": "Available to conversations in this project. Each agent turn and study keeps its own snapshot.",
    "zh-CN": "供此项目中的对话使用。每轮智能体交互和每项研究都会保留各自的快照。"
  },
  "workspace.readonlyHelp": {
    "en": "This session is read-only. You can inspect projects and results.",
    "zh-CN": "当前会话为只读模式，可查看项目和结果。"
  },
  "workspace.homeIntro": {
    "en": "What are we investigating?",
    "zh-CN": "我们要研究什么？"
  },
  "workspace.interactiveIntro": {
    "en": "Explore with your agent",
    "zh-CN": "与智能体一起探索"
  },
  "workspace.interactiveSummary": {
    "en": "Chat, run code and simulations, look at plots and decide the next step together. You stay in the loop.",
    "zh-CN": "通过对话、运行代码与仿真、查看图表，共同决定下一步。整个过程由你参与。"
  },
  "workspace.interactiveBest": {
    "en": "getting started, debugging, and working out what to ask.",
    "zh-CN": "入门探索、调试，以及梳理研究问题。"
  },
  "workspace.autonomousIntro": {
    "en": "Let a study run on its own",
    "zh-CN": "让研究自主运行"
  },
  "workspace.autonomousSummary": {
    "en": "Give it a claim and a time budget. It runs experiments and looks for counterexamples; an independent review checks the evidence before anything counts.",
    "zh-CN": "给出待检验的论断和时间预算。研究会运行实验并寻找反例；证据须经独立评审后才能被采纳。"
  },
  "workspace.autonomousBest": {
    "en": "“is this true?” questions you can state precisely.",
    "zh-CN": "能够精确表述的“这个论断成立吗？”类问题。"
  },
  "workspace.autonomousNote": {
    "en": "Start in Interactive; when your claim is clear, switch to Autonomous study inside the conversation.",
    "zh-CN": "先在 Interactive 中探索；论断明确后，在对话中切换到 Autonomous study。"
  },
  "workspace.machinesIntro": {
    "en": "Connect your machines. Run experiments in parallel.",
    "zh-CN": "连接你的计算设备，并行运行实验。"
  },
  "workspace.machinesFootnote": {
    "en": "The research agent stays here. Connected machines run your experiments.",
    "zh-CN": "研究智能体仍在本机运行，已连接的机器负责执行实验。"
  },
  "workspace.machineConnectHelp": {
    "en": "Connect with an SSH address and your SSH key, agent, or password. We’ll detect the hardware and prepare the worker.",
    "zh-CN": "使用 SSH 地址及 SSH 密钥、SSH agent 或密码连接。系统将检测硬件并准备执行节点。"
  },
  "workspace.machineAddressHelp": {
    "en": "Also accepts user@host:port or an address from your SSH config.",
    "zh-CN": "也支持 user@host:port 或 SSH 配置中的主机地址。"
  },
  "workspace.machineSecretHelp": {
    "en": "Stored privately on this computer.",
    "zh-CN": "仅在本机私密保存。"
  },
  "workspace.machineCooperativeHelp": {
    "en": "Restricted containers use a dedicated unprivileged worker with cooperative execution.",
    "zh-CN": "受限容器通过专用的非特权执行节点进行协作执行。"
  },
  "workspace.settingsIntro": {
    "en": "Choose your agent and model inside each conversation. Installed CLI agents need no API setup here.",
    "zh-CN": "在各个对话中选择智能体和模型。已安装的 CLI 智能体无需在此配置 API。"
  },
  "workspace.settingsSecretHelp": {
    "en": "Stored in a private file on the execution machine. Never returned to the browser or included in project exports.",
    "zh-CN": "保存在执行机器的私密文件中，不会返回浏览器，也不会包含在项目导出文件中。"
  },
  "workspace.settingsHostHelp": {
    "en": "Files, installations, and experiments stay on the machine serving this page.",
    "zh-CN": "文件、软件安装和实验均保留在提供此页面的机器上。"
  },
  "workspace.settingsCliHelp": {
    "en": "Installed agents are detected automatically. They keep their existing login and native tools.",
    "zh-CN": "系统自动检测已安装的智能体，并沿用其登录状态和原生工具。"
  },
  "workspace.benchmarkIntro": {
    "en": "Measured scientific coding tasks. Compare completion, time and API-equivalent cost.",
    "zh-CN": "基于实测的科研编程任务，比较完成情况、耗时和 API 等效费用。"
  },
  "workspace.timeBarsHelp": {
    "en": "Median verified finish time · shorter bars are better",
    "zh-CN": "经验证的完成时间中位数；条形越短越好。"
  },
  "workspace.costBarsHelp": {
    "en": "API-equivalent cost per attempt · shorter bars are better",
    "zh-CN": "每次尝试的 API 等效费用；条形越短越好。"
  },
  "workspace.unfinishedBarsHelp": {
    "en": "Red marks unfinished runs. They have no verified finish-time rank; cost bars still show recorded spending, including labelled lower bounds. Configurations without inference are omitted.",
    "zh-CN": "红色标记表示未完成的运行，不参与经验证的完成时间排名；费用条形仍显示已记录的支出，并标明其中的下限值。未进行推理的配置不显示。"
  },
  "workspace.benchmarkCommunityHelp": {
    "en": "Test any supported model with your installed agent or API connection. Local and imported runs appear in Community & local. Official results are maintained by Simjecture.",
    "zh-CN": "可通过已安装的智能体或 API 连接测试支持的模型。本地和导入的运行显示在 Community & local 中，官方结果由 Simjecture 维护。"
  },
  "workspace.toolsIntro": {
    "en": "Find the right tool for your next investigation. Open a card to learn more.",
    "zh-CN": "为下一项研究寻找合适的工具，打开卡片了解详情。"
  },
  "workspace.toolsSetupHelp": {
    "en": "Live installs, readiness checks and setups that need attention",
    "zh-CN": "查看正在进行的安装、就绪检查，以及需要处理的配置。"
  },
  "workspace.installedToolsHelp": {
    "en": "Installed tools and detected local builds",
    "zh-CN": "已安装的工具及检测到的本地构建版本。"
  },
  "workspace.managedToolsHelp": {
    "en": "Provided and maintained by your administrator",
    "zh-CN": "由管理员提供并维护。"
  },
  "workspace.availableToolsHelp": {
    "en": "Open a tool to explore setup options",
    "zh-CN": "打开工具，查看可用的配置方式。"
  },
  "workspace.toolSearchHelp": {
    "en": "Try a different keyword or category.",
    "zh-CN": "请尝试其他关键词或类别。"
  },
  "workspace.toolsQualificationHelp": {
    "en": "Installation and readiness checks tell you a tool can run. Each investigation still validates its scientific method.",
    "zh-CN": "安装和就绪检查仅说明工具可以运行。每项研究仍需验证其科学方法。"
  },
  "workspace.toolsMachinesHelp": {
    "en": "For tools on SSH workers, use",
    "zh-CN": "如需管理 SSH 执行节点上的工具，请前往"
  },
  "workspace.customToolHelp": {
    "en": "Connect an existing capability directory on this computer. Your agent can help prepare the software and its descriptor.",
    "zh-CN": "连接本机已有的 capability 目录。智能体可协助准备软件及其描述文件。"
  },
  "workspace.continuationHelp": {
    "en": "Talk through the next step in chat; your agent then drafts its brief.",
    "zh-CN": "在对话中讨论下一步，再由智能体起草研究简报。"
  },
  "workspace.agentSwitchHelp": {
    "en": "Changing CLI or model starts a fresh agent session. It may lose tool context and cache reuse, making the next reply slower or less consistent. Your conversation and files are kept. Any running turn continues with its original agent.",
    "zh-CN": "更换 CLI 或模型会开启新的智能体会话，可能丢失工具上下文和可复用缓存，使下一次回复变慢或一致性降低。对话和文件会保留；正在进行的交互仍由原智能体完成。"
  },
  "workspace.studyIntro": {
    "en": "How an autonomous study works",
    "zh-CN": "自主研究如何进行"
  },
  "workspace.studyBackgroundHelp": {
    "en": "It runs on its own after you approve a plan. Closing this page does not stop it.",
    "zh-CN": "你批准计划后，研究将自主运行。关闭此页面不会中断研究。"
  },
  "workspace.studyDiscussHelp": {
    "en": "Talk the question through in Interactive, or let Grill me interview you.",
    "zh-CN": "在 Interactive 中讨论研究问题，或通过 Grill me 逐项梳理。"
  },
  "workspace.studyBriefHelp": {
    "en": "Your agent writes the claim, the evidence needed and a time budget. Edit anything.",
    "zh-CN": "智能体起草待检验的论断、所需证据和时间预算。你可以修改任何内容。"
  },
  "workspace.studyLaunchHelp": {
    "en": "Experiments run within the budget and look for counterexamples.",
    "zh-CN": "实验在预算内运行，并寻找反例。"
  },
  "workspace.studyReportHelp": {
    "en": "An independent reviewer checks the evidence; your agent explains the result in the chat.",
    "zh-CN": "独立评审者核查证据，智能体在对话中解释结果。"
  },
  "workspace.preparationIntro": {
    "en": "Plan the study with your agent",
    "zh-CN": "与智能体共同制定研究计划"
  },
  "workspace.preparationHelp": {
    "en": "Your agent uses this conversation and its files to write a study brief. Nothing runs until you review and start it.",
    "zh-CN": "智能体根据当前对话及其文件撰写研究简报。你审阅并启动后，研究才会运行。"
  },
  "workspace.grillHelp": {
    "en": "Your agent interviews you one question at a time, pushes back on vague points, then writes the study brief.",
    "zh-CN": "智能体逐个提问，澄清模糊之处，然后撰写研究简报。"
  },
  "workspace.draftHelp": {
    "en": "Use what we already discussed. Ask only when something important is missing.",
    "zh-CN": "使用已有的讨论内容，仅在缺少关键信息时提问。"
  },
  "workspace.briefAfterHelp": {
    "en": "When the study finishes, your agent explains the report here in the conversation. Each study keeps its own results.",
    "zh-CN": "研究结束后，智能体将在此对话中解释报告。每项研究分别保留自己的结果。"
  },
  "workspace.solverHelp": {
    "en": "The agent may change its own copy of a solver. Your installed solvers are never modified, and results from a changed solver are checked before they count as evidence.",
    "zh-CN": "智能体可以修改自己的求解器副本，不会改动你已安装的求解器。修改后求解器的结果须经核查后才能作为证据。"
  },
  "workspace.solverHostedHelp": {
    "en": "Hosted policy: use supplied solver implementations. Experiment and analysis scripting remains available within host permissions.",
    "zh-CN": "托管策略要求使用提供的求解器实现。在主机权限范围内，仍可编写实验和分析脚本。"
  },
  "workspace.installedToolsGuide": {
    "en": "The agent can use all available installed tools and choose which ones each experiment needs.",
    "zh-CN": "智能体可使用所有可用的已安装工具，并按各项实验的需要进行选择。"
  },
  "workspace.studyMachinesHelp": {
    "en": "Select several machines to run experiments in parallel. Add machines on the Machines page.",
    "zh-CN": "选择多台机器可并行运行实验。请在 Machines 页面添加机器。"
  },
  "workspace.directorHelp": {
    "en": "Watches the strategy while experiments run. Data from a stopped experiment is kept. This is separate from the independent review of the final evidence.",
    "zh-CN": "在实验运行期间检查研究策略，被停止实验的数据会保留。该过程与最终证据的独立评审分别进行。"
  },
  "workspace.reviewAgentHelp": {
    "en": "Use another installed CLI or the API in Connections. Each review starts in a separate context.",
    "zh-CN": "可使用其他已安装的 CLI，或 Connections 中配置的 API。每次评审均在独立上下文中开始。"
  },
  "workspace.reviewHostedHelp": {
    "en": "The review agent is managed by the host.",
    "zh-CN": "评审智能体由托管方管理。"
  },
  "workspace.executionHelp": {
    "en": "Cooperative execution is for a dedicated unprivileged account and does not isolate host networking.",
    "zh-CN": "协作执行适用于专用的非特权账户，不隔离主机网络。"
  },
  "workspace.studyLifetimeHelp": {
    "en": "The study keeps running if you close this page. It stops at the time budget or once the review accepts an answer, and you can pause or stop it at any time.",
    "zh-CN": "关闭页面后，研究仍会运行。达到时间预算或评审接受答案后，研究停止；你也可以随时暂停或停止研究。"
  },
  "workspace.simulationIntro": {
    "en": "Your experiments, in view.",
    "zh-CN": "在这里查看你的实验。"
  },
  "workspace.simulationHelp": {
    "en": "Ask your agent to run a simulation. Its live console and saved outputs appear here, beside the conversation.",
    "zh-CN": "请让智能体运行仿真。实时控制台和保存的输出将显示在对话旁。"
  },
  "workspace.commandHelp": {
    "en": "Agent commands and their output appear here.",
    "zh-CN": "智能体执行的命令及其输出将显示在这里。"
  },
  "workspace.conversationFilesHelp": {
    "en": "Inputs, reports and results shared by this conversation. Each simulation's own outputs are in Simulations.",
    "zh-CN": "此对话共享的输入、报告和结果。各次仿真的输出位于 Simulations 中。"
  },
  "workspace.uploadHelp": {
    "en": "Copy large datasets here directly. Browser uploads support files up to 64 MB.",
    "zh-CN": "大型数据集可直接复制到此目录。浏览器上传支持最大 64 MB 的文件。"
  },
  "workspace.emptyBrief": {
    "en": "No study planned yet. Open Autonomous study when your question is clear.",
    "zh-CN": "尚未规划研究。问题明确后，可打开 Autonomous study。"
  },
  "workspace.deleteWarning": {
    "en": "This permanently deletes the conversation, uploaded files, simulation outputs, and autonomous studies inside this folder:",
    "zh-CN": "这将永久删除以下文件夹中的对话、上传文件、仿真输出和自主研究："
  },
  "workspace.deleteIrreversible": {
    "en": "Shared tools and API connections are kept. This cannot be undone.",
    "zh-CN": "共享工具和 API 连接会保留。此操作无法撤销。"
  },
  "workspace.knowledgeFolderHelp": {
    "en": "Choose a folder on the machine running Simjecture. Its supported files will be searchable in this workspace.",
    "zh-CN": "选择运行 Simjecture 的机器上的文件夹。此工作区将能够搜索其中支持的文件。"
  },
  "workspace.knowledgeScopeHelp": {
    "en": "Choose where this conversation's agent can search.",
    "zh-CN": "选择此对话中的智能体可以搜索的资料源。"
  },
  "workspace.fileEmpty": {
    "en": "Files you upload and files your agent creates appear here.",
    "zh-CN": "你上传的文件和智能体创建的文件将显示在这里。"
  },
  "workspace.findingsHelp": {
    "en": "Experiment outputs are recorded results. Scientific acceptance comes from independent review; completing a run alone does not establish a claim.",
    "zh-CN": "实验输出是已记录的结果。科学结论须经独立评审认可；仅完成一次运行不能证明论断成立。"
  },
  "workspace.noCommandSelected": {
    "en": "No command selected.",
    "zh-CN": "尚未选择命令。"
  },
  "workspace.noSimulationSelected": {
    "en": "No simulation selected.",
    "zh-CN": "尚未选择仿真。"
  },
  "workspace.requestPlaceholder": {
    "en": "Ask a question or describe your research…",
    "zh-CN": "提出问题或描述你的研究……"
  },
  "workspace.chatPlaceholder": {
    "en": "Ask your research agent…",
    "zh-CN": "向研究智能体提问……"
  },
  "monitor.emptyIntro": {
    "en": "Begin with a falsifiable hypothesis.",
    "zh-CN": "从一个可证伪的假设开始。"
  },
  "monitor.emptyHelp": {
    "en": "Simjecture tests hypotheses, searches for counterexamples, and preserves every scientific branch as durable evidence.",
    "zh-CN": "Simjecture 检验假设、寻找反例，并将每条研究分支作为证据持久保存。"
  },
  "monitor.evidenceHelp": {
    "en": "Recorded experiments and independent assessments. An output or completed run alone is not an accepted scientific finding.",
    "zh-CN": "查看已记录的实验和独立评估。仅有输出或完成运行，并不代表已获得被认可的科学结论。"
  },
  "monitor.graphHelp": {
    "en": "Scientific arrows show hypothesis refinement; prerequisite arrows flow from validation claims through commissioning into the scientific target. Drag nodes or empty canvas, zoom at the cursor, or fit the complete graph.",
    "zh-CN": "科学关系箭头表示假设的细化；前置条件箭头从验证论断出发，经调试验证阶段指向科学目标。可拖动节点或空白画布，在光标处缩放，或将完整关系图适配到视图。"
  },
  "monitor.graphControlsHelp": {
    "en": "Drag empty canvas to pan; drag nodes to arrange them; scroll to zoom at the cursor",
    "zh-CN": "拖动空白画布以平移，拖动节点以调整位置，滚动以在光标处缩放。"
  },
  "monitor.noClaims": {
    "en": "No claims have been registered.",
    "zh-CN": "尚未登记论断。"
  },
  "monitor.selectRecord": {
    "en": "Select a claim or workflow stage to inspect it.",
    "zh-CN": "选择一个论断或工作流阶段以查看详情。"
  },
  "monitor.selectClaim": {
    "en": "Select a claim or stage to inspect it.",
    "zh-CN": "选择一个论断或阶段以查看详情。"
  },
  "monitor.noClaimDetails": {
    "en": "Claim details are not available yet.",
    "zh-CN": "暂时没有可用的论断详情。"
  },
  "monitor.executionHelp": {
    "en": "Select one run to inspect its live heartbeat and console record.",
    "zh-CN": "选择一次运行，查看实时心跳和控制台记录。"
  },
  "monitor.noSimulation": {
    "en": "No simulation or calculation has been recorded.",
    "zh-CN": "尚未记录仿真或计算。"
  },
  "monitor.traceHelp": {
    "en": "Typed decisions, laboratory notes, tool outcomes, and provider usage—not private hidden chain-of-thought.",
    "zh-CN": "记录结构化决策、实验笔记、工具结果和服务用量，不展示模型内部的隐式思维链。"
  },
  "monitor.backendHelp": {
    "en": "Uses your existing backend login",
    "zh-CN": "沿用已有的后端登录状态"
  },
  "monitor.cooperativeHelp": {
    "en": "The cooperative backend shares host networking and is not a security sandbox.",
    "zh-CN": "协作后端共享主机网络，不属于安全沙箱。"
  },
  "monitor.routeHelp": {
    "en": "Minimal keeps native tools available and records experiments and independent reviews.",
    "zh-CN": "Minimal 保留原生工具，并记录实验及独立评审。"
  },
  "monitor.solverHelp": {
    "en": "Minimal mode: protect reference installations and qualify changed methods independently.",
    "zh-CN": "Minimal 模式保护参考安装，并对修改后的方法进行独立验证。"
  },
  "monitor.registryHelp": {
    "en": "Leave blank to use available tools, enter a registry to restrict access, or none for Python only.",
    "zh-CN": "留空以使用可用工具，填写注册表以限制访问，或填写 none 以仅使用 Python。"
  },
  "monitor.noEvidenceContract": {
    "en": "No evidence contract is recorded for this claim.",
    "zh-CN": "此论断尚未记录证据约定。"
  },
  "monitor.noEvidence": {
    "en": "No evidence is linked to this claim yet.",
    "zh-CN": "此论断尚未关联证据。"
  },
  "monitor.noExecution": {
    "en": "No numerical execution has been recorded.",
    "zh-CN": "尚未记录数值计算运行。"
  },
  "monitor.firstExecutionHelp": {
    "en": "The first simulation or calculation will appear here with its real state and heartbeat.",
    "zh-CN": "首次仿真或计算将在此显示实际状态和心跳。"
  },
  "monitor.workerWaitHelp": {
    "en": "Worker inference is parked. Experiments and host supervision continue; the original campaign deadline remains in force. New review results or operator guidance wake the worker.",
    "zh-CN": "执行智能体暂停推理，实验和主机监督继续运行；原定研究截止时间仍然有效。新的评审结果或操作指导会唤醒智能体。"
  },
  "monitor.reportReviewHelp": {
    "en": "Reports can be reviewed while the investigation runs, including inconclusive findings. Report acceptance does not approve the hypothesis or promote exploratory evidence.",
    "zh-CN": "研究运行期间即可评审报告，包括尚无定论的结果。接受报告不代表认可假设，也不会提升探索性证据的等级。"
  },
  "monitor.directorHelp": {
    "en": "Stops individual experiments and requests replans. Scientific claim acceptance remains separate.",
    "zh-CN": "可停止单项实验并要求重新规划。科学论断的认可仍需单独评审。"
  },
  "monitor.methodApprovalHelp": {
    "en": "Method approval applies to its reviewed source and scope. Instrument readiness is separate from production-method approval and scientific claim acceptance.",
    "zh-CN": "方法批准仅适用于已评审的源代码及适用范围。工具就绪、正式计算方法的批准和科学论断的认可分别判定。"
  },
  "monitor.telemetryHelp": {
    "en": "Live timing is operational telemetry. Recorded metrics have researcher-declared targets and units. Claim approval remains separate.",
    "zh-CN": "实时计时属于运行遥测。记录指标的目标和单位由研究者声明。论断是否获认可仍单独判定。"
  },
  "monitor.coverageHelp": {
    "en": "Execution wall time excludes provider calls, preflight checks and artifact transfers. Targets and forecasts remain advisory.",
    "zh-CN": "执行实际耗时不含模型服务调用、预检和产物传输。目标与预测仅供参考。"
  },
  "monitor.noActions": {
    "en": "No model or tool actions have been recorded yet.",
    "zh-CN": "尚未记录模型或工具操作。"
  },
  "monitor.noArtifacts": {
    "en": "No browser-visible artifacts have been recorded yet.",
    "zh-CN": "尚未记录可在浏览器中查看的产物。"
  },
  "monitor.noConclusion": {
    "en": "The campaign has not written a terminal conclusion.",
    "zh-CN": "此项研究尚未写入最终结论。"
  },
  "workspace.hostedToolsIntro": {
    "en": "Verified tools provided for this hosted workspace.",
    "zh-CN": "此托管工作区提供的已验证工具。"
  }
};
