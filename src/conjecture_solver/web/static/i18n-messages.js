/* Central UI copy. Research data, identifiers and console output stay verbatim. */
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
    "zh-CN": "先在交互探索中梳理问题；论断明确后，在对话中切换到自主研究。"
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
    "zh-CN": "可通过已安装的智能体或 API 连接测试支持的模型。本地和导入的运行显示在“社区与本地”中，官方结果由 Simjecture 维护。"
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
    "zh-CN": "在交互探索中讨论研究问题，或通过“逐项提问”梳理。"
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
    "zh-CN": "尚未规划研究。问题明确后，可打开自主研究。"
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
  },
  "ui.add-project-files": {
    "en": "Add project files",
    "zh-CN": "添加项目文件"
  },
  "ui.sign-in-to-add-files": {
    "en": "Sign in to add files",
    "zh-CN": "登录后添加文件"
  },
  "ui.sign-in": {
    "en": "Sign in",
    "zh-CN": "登录"
  },
  "ui.workspace-menu": {
    "en": "Workspace menu",
    "zh-CN": "工作区菜单"
  },
  "ui.account": {
    "en": "Account: {p0}",
    "zh-CN": "账户：{p0}"
  },
  "ui.sign-in-and-account": {
    "en": "Sign in and account",
    "zh-CN": "登录与账户"
  },
  "ui.account-2": {
    "en": "ACCOUNT",
    "zh-CN": "账户"
  },
  "ui.guest-workspace": {
    "en": "Guest workspace",
    "zh-CN": "访客工作区"
  },
  "ui.local-workspace": {
    "en": "Local workspace",
    "zh-CN": "本地工作区"
  },
  "ui.owner-workspace": {
    "en": "Owner workspace",
    "zh-CN": "所有者工作区"
  },
  "ui.unlimited": {
    "en": "Unlimited {p0}",
    "zh-CN": "{p0}不限次数"
  },
  "ui.no-hosted-wall-time-limit-shared-queue": {
    "en": "No hosted wall-time limit · shared queue",
    "zh-CN": "托管运行不限时 · 使用共享队列"
  },
  "ui.allowance-renews-over-24-hours-one-task-at-a-time": {
    "en": "Allowance renews over 24 hours · one task at a time",
    "zh-CN": "配额按 24 小时周期恢复 · 同时运行一项任务"
  },
  "ui.temporary-workspace-sign-in-to-keep-your-files-and-results": {
    "en": "Temporary workspace. Sign in to keep your files and results.",
    "zh-CN": "临时工作区。登录以保留文件和结果。"
  },
  "ui.sign-out": {
    "en": "Sign out",
    "zh-CN": "退出登录"
  },
  "ui.sign-in-with-github": {
    "en": "Sign in with GitHub",
    "zh-CN": "使用 GitHub 登录"
  },
  "ui.github-sign-in-being-configured": {
    "en": "GitHub sign-in · being configured",
    "zh-CN": "GitHub 登录 · 配置中"
  },
  "ui.connections": {
    "en": "Connections",
    "zh-CN": "连接设置"
  },
  "ui.take-the-tour": {
    "en": "Take the tour",
    "zh-CN": "查看使用导览"
  },
  "ui.workspace-details": {
    "en": "Workspace details",
    "zh-CN": "工作区详情"
  },
  "ui.github": {
    "en": "GitHub ↗",
    "zh-CN": "GitHub ↗"
  },
  "ui.selected-study": {
    "en": "Selected study",
    "zh-CN": "已选研究"
  },
  "ui.select-study": {
    "en": "Select study",
    "zh-CN": "选择研究"
  },
  "ui.saved-leave-blank-to-keep-this-key": {
    "en": "Saved · leave blank to keep this key",
    "zh-CN": "已保存 · 留空以保留此密钥"
  },
  "ui.api-key-optional-for-a-local-server": {
    "en": "API key (optional for a local server)",
    "zh-CN": "API 密钥（本地服务可不填）"
  },
  "ui.configure-api-connections": {
    "en": "Configure API connections",
    "zh-CN": "配置 API 连接"
  },
  "ui.cli-agents-detected": {
    "en": "{p0} CLI agents detected",
    "zh-CN": "检测到 {p0} 个 CLI 智能体"
  },
  "ui.api-endpoint-saved": {
    "en": "API endpoint saved",
    "zh-CN": "已保存 API 端点"
  },
  "ui.choose-an-agent-in-your-project": {
    "en": "Choose an agent in your project",
    "zh-CN": "在项目中选择智能体"
  },
  "ui.this-machine": {
    "en": "This machine",
    "zh-CN": "本机"
  },
  "ui.local-execution": {
    "en": "{p0} · local execution",
    "zh-CN": "{p0} · 本地执行"
  },
  "ui.no-supported-cli-agents-found-you-can-use-the-built-in-api-agent": {
    "en": "No supported CLI agents found. You can use the built-in API agent.",
    "zh-CN": "未找到受支持的 CLI 智能体。可以使用内置 API 智能体。"
  },
  "ui.built-in-agent-powered-by-hugging-face-smolagents-your-existing-simj": {
    "en": "Built-in agent powered by Hugging Face smolagents. Your existing Simjecture experiment and review services govern autonomous studies.",
    "zh-CN": "内置智能体基于 Hugging Face smolagents，自主研究由现有的 Simjecture 实验与评审服务管理。"
  },
  "ui.to-enable-the-built-in-api-agent-run-once-uv-sync-extra-workspace-in": {
    "en": "To enable the built-in API agent, run once: uv sync --extra workspace. Installed CLI agents work without this extra.",
    "zh-CN": "启用内置 API 智能体前，请运行一次 uv sync --extra workspace。已安装的 CLI 智能体不需要此扩展依赖。"
  },
  "ui.api-endpoint-saved-select-its-model-in-your-conversation": {
    "en": "API endpoint saved. Select its model in your conversation.",
    "zh-CN": "已保存 API 端点。请在对话中选择对应模型。"
  },
  "ui.optional-you-can-use-an-installed-cli-without-adding-an-api-key": {
    "en": "Optional. You can use an installed CLI without adding an API key.",
    "zh-CN": "可选。使用已安装的 CLI 无需添加 API 密钥。"
  },
  "ui.agent-for-a-new-conversation": {
    "en": "Agent for a new conversation",
    "zh-CN": "新对话使用的智能体"
  },
  "ui.local-cli": {
    "en": "{p0} · local CLI",
    "zh-CN": "{p0} · 本地 CLI"
  },
  "ui.compatible-api": {
    "en": "Compatible API",
    "zh-CN": "兼容 API"
  },
  "ui.compatible-api-add-endpoint": {
    "en": "Compatible API · add endpoint",
    "zh-CN": "兼容 API · 添加端点"
  },
  "ui.unavailable": {
    "en": "{p0} · unavailable",
    "zh-CN": "{p0} · 不可用"
  },
  "ui.loading-model-choices": {
    "en": "Loading model choices…",
    "zh-CN": "正在加载模型选项……"
  },
  "ui.reading-model-choices": {
    "en": "Reading model choices…",
    "zh-CN": "正在读取模型选项……"
  },
  "ui.other-model": {
    "en": "Other model…",
    "zh-CN": "其他模型……"
  },
  "ui.delete-conversation-and-files": {
    "en": "Delete conversation and files",
    "zh-CN": "删除对话及文件"
  },
  "ui.delete-conversation": {
    "en": "Delete conversation: {p0}",
    "zh-CN": "删除对话：{p0}"
  },
  "ui.choose-model": {
    "en": "choose model",
    "zh-CN": "选择模型"
  },
  "ui.choose-an-agent": {
    "en": "Choose an agent",
    "zh-CN": "选择智能体"
  },
  "ui.your-agent-is-working-its-questions-and-proposed-brief-appear-in-the": {
    "en": "Your agent is working. Its questions and proposed brief appear in the conversation.",
    "zh-CN": "智能体正在工作。提问和拟定的简报会显示在对话中。"
  },
  "ui.either-way-your-agent-asks-about-anything-missing-and-fills-in-the-b": {
    "en": "Either way, your agent asks about anything missing and fills in the brief.",
    "zh-CN": "无论选择哪种方式，智能体都会询问缺失信息并完善简报。"
  },
  "ui.proposal-ready-review-the-brief-below-then-start-the-study": {
    "en": "Proposal ready — review the brief below, then start the study.",
    "zh-CN": "方案已就绪，请审阅下方简报后启动研究。"
  },
  "ui.preparing-with-your-agent-continue-the-conversation-to-answer-its-qu": {
    "en": "Preparing with your agent. Continue the conversation to answer its questions.",
    "zh-CN": "正在与智能体准备研究，请继续对话以回答相关问题。"
  },
  "ui.plan-a-study-with-your-agent-you-review-the-brief-before-anything-ru": {
    "en": "Plan a study with your agent. You review the brief before anything runs.",
    "zh-CN": "与智能体共同制定研究计划。运行前由你审阅简报。"
  },
  "ui.your-studies-are-below-when-one-finishes-your-agent-explains-its-rep": {
    "en": "Your studies are below. When one finishes, your agent explains its report in the conversation.",
    "zh-CN": "下方列出你的研究。研究结束后，智能体会在对话中解释报告。"
  },
  "ui.continuation-proposal": {
    "en": "CONTINUATION PROPOSAL",
    "zh-CN": "后续研究方案"
  },
  "ui.step-2-of-2-review-and-start": {
    "en": "STEP 2 OF 2 · REVIEW AND START",
    "zh-CN": "第 2 步，共 2 步 · 审阅并启动"
  },
  "ui.continuation-phase-selected-files-parent-study": {
    "en": "Continuation phase · {p0} selected files · parent study ↗",
    "zh-CN": "后续阶段 · 已选 {p0} 个文件 · 原研究 ↗"
  },
  "ui.choose-agent": {
    "en": "choose agent",
    "zh-CN": "选择智能体"
  },
  "ui.agent": {
    "en": "Agent: {p0} / {p1}",
    "zh-CN": "智能体：{p0} / {p1}"
  },
  "ui.change-agent-model": {
    "en": "Change agent / model",
    "zh-CN": "更换智能体 / 模型"
  },
  "ui.let-s-work-through-your-question": {
    "en": "Let’s work through your question.",
    "zh-CN": "一起梳理你的研究问题。"
  },
  "ui.describe-your-task-or-attach-a-file-you-can-investigate-together-the": {
    "en": "Describe your task or attach a file. You can investigate together, then prepare an autonomous study when the question is clear.",
    "zh-CN": "描述任务或附加文件。先共同探索，问题明确后再准备自主研究。"
  },
  "ui.you": {
    "en": "You",
    "zh-CN": "你"
  },
  "ui.study-report-received": {
    "en": "Study report received",
    "zh-CN": "已收到研究报告"
  },
  "ui.actions-view-activity": {
    "en": "{p0} actions · view activity",
    "zh-CN": "{p0} 次操作 · 查看活动"
  },
  "ui.simulation": {
    "en": "SIMULATION",
    "zh-CN": "仿真"
  },
  "ui.autonomous-study": {
    "en": "AUTONOMOUS STUDY",
    "zh-CN": "自主研究"
  },
  "ui.open": {
    "en": "Open ↗",
    "zh-CN": "打开 ↗"
  },
  "ui.agent-active": {
    "en": "Agent active",
    "zh-CN": "智能体正在工作"
  },
  "ui.waiting-for-agent": {
    "en": "Waiting for agent",
    "zh-CN": "等待智能体"
  },
  "ui.recent-agent-activity": {
    "en": "Recent agent activity",
    "zh-CN": "近期智能体活动"
  },
  "ui.repair": {
    "en": "Repair",
    "zh-CN": "修正"
  },
  "ui.setup": {
    "en": "Setup",
    "zh-CN": "配置"
  },
  "ui.conversation-ready-review-the-request-choose-your-agent-then-send": {
    "en": "{p0} conversation ready. Review the request, choose your agent, then send.",
    "zh-CN": "{p0}对话已就绪。审阅请求、选择智能体后再发送。"
  },
  "ui.study-conversation-ready-describe-your-problem-and-send-the-request": {
    "en": "Study conversation ready. Describe your problem and send the request.",
    "zh-CN": "研究对话已就绪。请描述问题并发送请求。"
  },
  "ui.machine-settings": {
    "en": "Machine settings",
    "zh-CN": "计算设备设置"
  },
  "ui.add-a-machine": {
    "en": "Add a machine",
    "zh-CN": "添加计算设备"
  },
  "ui.leave-empty-to-keep-the-saved-password": {
    "en": "Leave empty to keep the saved password",
    "zh-CN": "留空以保留已保存的密码"
  },
  "ui.leave-empty-to-use-your-ssh-key-or-agent": {
    "en": "Leave empty to use your SSH key or agent",
    "zh-CN": "留空以使用 SSH 密钥或 SSH agent"
  },
  "ui.save-settings": {
    "en": "Save settings",
    "zh-CN": "保存设置"
  },
  "ui.connect-prepare": {
    "en": "Connect & prepare",
    "zh-CN": "连接并准备"
  },
  "ui.this-host-existing-local-launcher": {
    "en": "This host · existing local launcher",
    "zh-CN": "本机 · 使用现有本地启动器"
  },
  "ui.setup-conversation-ready-choose-your-agent-and-send-the-request": {
    "en": "Setup conversation ready. Choose your agent and send the request.",
    "zh-CN": "配置对话已就绪。选择智能体后发送请求。"
  },
  "ui.jobs": {
    "en": "{p0} · jobs",
    "zh-CN": "{p0} · 任务"
  },
  "ui.stopping": {
    "en": "Stopping…",
    "zh-CN": "正在停止……"
  },
  "ui.cancel": {
    "en": "Cancel",
    "zh-CN": "取消"
  },
  "ui.no-experiments-on-this-worker-yet": {
    "en": "No experiments on this worker yet.",
    "zh-CN": "此执行节点尚无实验。"
  },
  "ui.your-agent-can-prepare-scientific-tools": {
    "en": "Your agent can prepare scientific tools.",
    "zh-CN": "智能体可帮助准备科研工具。"
  },
  "ui.jobs-2": {
    "en": "{p0} · {p1}/{p2} jobs",
    "zh-CN": "{p0} · {p1}/{p2} 项任务"
  },
  "ui.just-checked": {
    "en": "just checked",
    "zh-CN": "刚刚检查"
  },
  "ui.awaiting-first-check": {
    "en": "Awaiting first check",
    "zh-CN": "等待首次检查"
  },
  "ui.last-checked-ms": {
    "en": "Last checked {p0} · {p1} ms",
    "zh-CN": "上次检查 {p0} · {p1} 毫秒"
  },
  "ui.detecting-hardware-and-preparing-the-worker": {
    "en": "Detecting hardware and preparing the worker…",
    "zh-CN": "正在检测硬件并准备执行节点……"
  },
  "ui.connection-unavailable-details": {
    "en": "Connection unavailable · details",
    "zh-CN": "连接不可用 · 查看详情"
  },
  "ui.setup-needs-attention-details": {
    "en": "Setup needs attention · details",
    "zh-CN": "配置需要处理 · 查看详情"
  },
  "ui.jobs-3": {
    "en": "Jobs",
    "zh-CN": "任务"
  },
  "ui.prepare-worker": {
    "en": "Prepare worker",
    "zh-CN": "准备执行节点"
  },
  "ui.prepare-with-agent": {
    "en": "Prepare with agent",
    "zh-CN": "与智能体共同准备"
  },
  "ui.settings": {
    "en": "Settings",
    "zh-CN": "设置"
  },
  "ui.setup-log": {
    "en": "Setup log",
    "zh-CN": "配置日志"
  },
  "ui.your-first-machine-is-one-connection-away": {
    "en": "Your first machine is one connection away.",
    "zh-CN": "连接第一台计算设备即可开始。"
  },
  "ui.add-an-ssh-address-or-use-this-computer-to-get-started": {
    "en": "Add an SSH address, or use this computer to get started.",
    "zh-CN": "添加 SSH 地址，或使用本机开始。"
  },
  "ui.connected-preparing-the-worker-in-the-background": {
    "en": "Connected. Preparing the worker in the background…",
    "zh-CN": "已连接，正在后台准备执行节点……"
  },
  "ui.machine-settings-saved": {
    "en": "Machine settings saved.",
    "zh-CN": "已保存计算设备设置。"
  },
  "ui.task-pack-finite-diagnostic-coding-contracts": {
    "en": "Task pack {p0} · finite diagnostic coding contracts",
    "zh-CN": "任务包 {p0} · 有限范围的诊断编程约定"
  },
  "ui.prepare-conversation": {
    "en": "Prepare conversation",
    "zh-CN": "准备对话"
  },
  "ui.hdf5-fields-and-csv-diagnostics": {
    "en": "HDF5 fields and CSV diagnostics.",
    "zh-CN": "HDF5 场数据与 CSV 诊断。"
  },
  "ui.minute-suggested-budget": {
    "en": "{p0} minute suggested budget. {p1}",
    "zh-CN": "建议预算 {p0} 分钟。{p1}"
  },
  "ui.run-your-own-benchmarks-in-a-self-hosted-simjecture-workspace": {
    "en": "Run your own benchmarks in a self-hosted Simjecture workspace.",
    "zh-CN": "可在自行托管的 Simjecture 工作区中运行基准测试。"
  },
  "ui.task-prepared-choose-your-agent-and-send-the-request": {
    "en": "Task prepared. Choose your agent and send the request.",
    "zh-CN": "任务已准备。选择智能体后发送请求。"
  },
  "ui.passed-the-finite-numerical-contract": {
    "en": "Passed the finite numerical contract",
    "zh-CN": "通过指定范围的数值验收"
  },
  "ui.incomplete-or-failed-numerical-contract": {
    "en": "Incomplete or failed numerical contract",
    "zh-CN": "数值验收未完成或未通过"
  },
  "ui.not-graded": {
    "en": "Not graded",
    "zh-CN": "尚未评分"
  },
  "ui.grade-delivered-results": {
    "en": "Grade delivered results",
    "zh-CN": "对交付结果评分"
  },
  "ui.grading": {
    "en": "Grading…",
    "zh-CN": "正在评分……"
  },
  "ui.prepare-a-task-to-begin": {
    "en": "Prepare a task to begin.",
    "zh-CN": "请先准备一项任务。"
  },
  "ui.just-now": {
    "en": "just now",
    "zh-CN": "刚刚"
  },
  "ui.min-ago": {
    "en": "{p0} min ago",
    "zh-CN": "{p0} 分钟前"
  },
  "ui.h-ago": {
    "en": "{p0} h ago",
    "zh-CN": "{p0} 小时前"
  },
  "ui.d-ago": {
    "en": "{p0} d ago",
    "zh-CN": "{p0} 天前"
  },
  "ui.setup-progress": {
    "en": "{p0} setup progress",
    "zh-CN": "{p0} 配置进度"
  },
  "ui.of-output": {
    "en": "{p0} · {p1} of output",
    "zh-CN": "{p0} · 输出 {p1}"
  },
  "ui.waiting-for-output": {
    "en": "Waiting for output…",
    "zh-CN": "等待输出……"
  },
  "ui.the-readiness-check-failed": {
    "en": "The readiness check failed",
    "zh-CN": "就绪检查失败"
  },
  "ui.setup-did-not-finish": {
    "en": "Setup did not finish",
    "zh-CN": "配置未完成"
  },
  "ui.the-last-attempt-reported-a-failed-readiness-check": {
    "en": "The last attempt reported a failed readiness check.",
    "zh-CN": "上次尝试的就绪检查未通过。"
  },
  "ui.diagnose-with-agent-prepares-a-conversation-with-this-error-and-the-": {
    "en": "Diagnose with agent prepares a conversation with this error and the saved output. You review it and choose the agent before anything runs.",
    "zh-CN": "“请智能体诊断”会创建包含错误和已保存输出的对话。运行前由你审阅并选择智能体。"
  },
  "ui.readiness-checks": {
    "en": "Readiness checks",
    "zh-CN": "就绪检查"
  },
  "ui.live-output": {
    "en": "Live output",
    "zh-CN": "实时输出"
  },
  "ui.output-from-the-last-run": {
    "en": "Output from the last run",
    "zh-CN": "上次运行的输出"
  },
  "ui.updates-automatically": {
    "en": "Updates automatically",
    "zh-CN": "自动更新"
  },
  "ui.finished": {
    "en": "Finished {p0}",
    "zh-CN": "完成于 {p0}"
  },
  "ui.copy-output": {
    "en": "Copy output",
    "zh-CN": "复制输出"
  },
  "ui.output-copied": {
    "en": "Output copied",
    "zh-CN": "已复制输出"
  },
  "ui.copying-is-unavailable-in-this-browser-select-the-text-instead": {
    "en": "Copying is unavailable in this browser; select the text instead.",
    "zh-CN": "此浏览器不支持复制，请手动选择文本。"
  },
  "ui.stopping-setup": {
    "en": "Stopping {p0} setup…",
    "zh-CN": "正在停止 {p0} 的配置……"
  },
  "ui.setup-continues-in-the-background-follow-it-in-research-tools": {
    "en": "Setup continues in the background. Follow it in Research tools.",
    "zh-CN": "配置继续在后台运行，可在科研工具中查看进度。"
  },
  "ui.optional-attention-tool": {
    "en": "Optional attention tool",
    "zh-CN": "可选注意力分析工具"
  },
  "ui.guided-setup": {
    "en": "Guided setup",
    "zh-CN": "引导配置"
  },
  "ui.flash-is-licensed-software-so-you-supply-the-source-install-with-age": {
    "en": "FLASH is licensed software, so you supply the source. Install with agent opens a conversation that asks for it, along with the application and physics you need, then builds and registers the runtime.",
    "zh-CN": "FLASH 需要授权源代码。选择“请智能体安装”后，将在对话中询问源码位置、应用和物理模型需求，再构建并注册运行环境。"
  },
  "ui.this-tool-needs-choices-that-only-you-can-make-install-with-agent-op": {
    "en": "This tool needs choices that only you can make. Install with agent opens a conversation with setup instructions for your agent. You review the request and choose the agent before anything runs.",
    "zh-CN": "此工具需要你决定部分配置。“请智能体安装”会打开包含配置指导的对话，由你审阅请求并选择智能体后再运行。"
  },
  "ui.connected-tool": {
    "en": "Connected tool",
    "zh-CN": "已连接的工具"
  },
  "ui.check-readiness-runs-the-probe-defined-by-its-capability-descriptor": {
    "en": "Check readiness runs the probe defined by its capability descriptor.",
    "zh-CN": "就绪检查运行 capability 描述文件中定义的探测程序。"
  },
  "ui.one-click-install": {
    "en": "One-click install",
    "zh-CN": "一键安装"
  },
  "ui.local-builds-are-present-connect-a-capability-directory-to-use-one-i": {
    "en": "Local builds are present. Connect a capability directory to use one in recorded studies. A managed-profile check does not test these detected builds.",
    "zh-CN": "已检测到本地构建。连接其 capability 目录后可用于有记录的研究。托管配置的检查不会检验这些本地构建。"
  },
  "ui.ready-to-use": {
    "en": "Ready to use",
    "zh-CN": "可以使用"
  },
  "ui.readiness-check-passed-each-investigation-still-validates-its-own-sc": {
    "en": "Readiness check passed{p0}. Each investigation still validates its own scientific method.",
    "zh-CN": "就绪检查已通过{p0}。各项研究仍需验证自己的科学方法。"
  },
  "ui.the-last-setup-was-stopped-before-it-finished-its-output-is-kept-bel": {
    "en": "The last setup was stopped before it finished. Its output is kept below.",
    "zh-CN": "上次配置在完成前被停止，输出保留在下方。"
  },
  "ui.about-this-tool": {
    "en": "About this tool",
    "zh-CN": "关于此工具"
  },
  "ui.contributed-by": {
    "en": "Contributed by {p0}",
    "zh-CN": "贡献者：{p0}"
  },
  "ui.connected-capability-directory": {
    "en": "Connected capability directory",
    "zh-CN": "已连接的 capability 目录"
  },
  "ui.starter-preset": {
    "en": "starter preset",
    "zh-CN": "入门预设"
  },
  "ui.installed-application": {
    "en": "installed application",
    "zh-CN": "已安装的应用"
  },
  "ui.local-build": {
    "en": "Local build",
    "zh-CN": "本地构建"
  },
  "ui.managed-profile-setup-diagnostics": {
    "en": "Managed profile · setup diagnostics",
    "zh-CN": "托管配置 · 配置诊断"
  },
  "ui.this-collection-is-managed-by-your-administrator": {
    "en": "This collection is managed by your administrator.",
    "zh-CN": "此工具集合由管理员管理。"
  },
  "ui.read-only-workspace-tool-setup-is-disabled": {
    "en": "Read-only workspace · tool setup is disabled.",
    "zh-CN": "只读工作区 · 工具配置已禁用。"
  },
  "ui.included-with-simjecture-no-installation-needed": {
    "en": "Included with Simjecture. No installation needed.",
    "zh-CN": "Simjecture 内置，无需安装。"
  },
  "ui.optional-per-study-shadow-by-default-model-service-managed-separatel": {
    "en": "Optional per study · shadow by default · model service managed separately.",
    "zh-CN": "各项研究按需启用 · 默认影子模式 · 模型服务单独管理。"
  },
  "ui.your-agent-receives-the-saved-error-and-output-you-choose-the-agent-": {
    "en": "Your agent receives the saved error and output. You choose the agent and send the request.",
    "zh-CN": "智能体将收到已保存的错误和输出，由你选择智能体后发送请求。"
  },
  "ui.installation-is-separate-from-scientific-validation": {
    "en": "Installation is separate from scientific validation.",
    "zh-CN": "软件安装与科学验证分别进行。"
  },
  "ui.optional-research-tool-install-when-you-need-it": {
    "en": "Optional research tool · install when you need it",
    "zh-CN": "可选科研工具 · 按需安装"
  },
  "ui.view-progress": {
    "en": "View progress →",
    "zh-CN": "查看进度 →"
  },
  "ui.diagnose-setup": {
    "en": "Diagnose setup →",
    "zh-CN": "诊断配置 →"
  },
  "ui.explore-tool": {
    "en": "Explore tool →",
    "zh-CN": "了解工具 →"
  },
  "ui.view-details": {
    "en": "View {p0} details",
    "zh-CN": "查看 {p0} 详情"
  },
  "ui.stop-setup": {
    "en": "Stop setup",
    "zh-CN": "停止配置"
  },
  "ui.retry-readiness-check": {
    "en": "Retry readiness check",
    "zh-CN": "重试就绪检查"
  },
  "ui.retry-installation": {
    "en": "Retry installation",
    "zh-CN": "重试安装"
  },
  "ui.study-setup": {
    "en": "{p0} study setup",
    "zh-CN": "{p0} 研究配置"
  },
  "ui.custom-study-prepare-with-agent": {
    "en": "Custom study · prepare with agent",
    "zh-CN": "自定义研究 · 与智能体共同准备"
  },
  "ui.prepare-in-chat": {
    "en": "Prepare in chat",
    "zh-CN": "在对话中准备"
  },
  "ui.run-preset": {
    "en": "Run preset",
    "zh-CN": "运行预设"
  },
  "ui.starter-preset-queued-follow-its-run-in-simulations": {
    "en": "Starter preset queued. Follow its run in Simulations.",
    "zh-CN": "入门预设已加入队列，可在仿真中查看运行情况。"
  },
  "ui.check-existing-install": {
    "en": "Check existing install",
    "zh-CN": "检查已有安装"
  },
  "ui.already-installed-this-tool-yourself-run-its-readiness-check": {
    "en": "Already installed this tool yourself? Run its readiness check.",
    "zh-CN": "已自行安装此工具？可运行就绪检查。"
  },
  "ui.run-cylinder-wake": {
    "en": "Run cylinder wake",
    "zh-CN": "运行圆柱尾流"
  },
  "ui.run-demo": {
    "en": "Run demo",
    "zh-CN": "运行示例"
  },
  "ui.simulation-started-its-plots-and-results-will-appear-in-simulations": {
    "en": "Simulation started. Its plots and results will appear in Simulations.",
    "zh-CN": "仿真已启动，图表和结果将显示在仿真面板中。"
  },
  "ui.prepare-benchmark": {
    "en": "Prepare benchmark",
    "zh-CN": "准备基准测试"
  },
  "ui.benchmark-task-prepared-choose-your-agent-and-send-the-request": {
    "en": "Benchmark task prepared. Choose your agent and send the request.",
    "zh-CN": "基准测试任务已准备。选择智能体后发送请求。"
  },
  "ui.of-tools": {
    "en": "{p0} of {p1} tools",
    "zh-CN": "{p1} 个工具中显示 {p0} 个"
  },
  "ui.managed-collection-your-administrator-chooses-and-maintains-the-tool": {
    "en": "Managed collection · Your administrator chooses and maintains the tools available on this server. Explore a tool to see how you can use it.",
    "zh-CN": "托管工具集合 · 管理员选择并维护此服务器上的可用工具。打开工具可了解使用方法。"
  },
  "ui.read-only-workspace-you-can-explore-tools-and-their-details-installa": {
    "en": "Read-only workspace · You can explore tools and their details. Installation and setup changes are disabled.",
    "zh-CN": "只读工作区 · 可查看工具及详情，安装和配置修改已禁用。"
  },
  "ui.available-in-this-workspace": {
    "en": "Available in this workspace",
    "zh-CN": "此工作区可用"
  },
  "ui.on-your-workbench": {
    "en": "On your workbench",
    "zh-CN": "工作台上的工具"
  },
  "ui.all-categories": {
    "en": "All categories",
    "zh-CN": "所有类别"
  },
  "ui.explore-reconnecting-magnetic-islands": {
    "en": "Explore reconnecting magnetic islands",
    "zh-CN": "探索磁岛重联"
  },
  "ui.watch-chaos-appear": {
    "en": "Watch chaos appear",
    "zh-CN": "观察混沌的出现"
  },
  "ui.all-available-tools-default": {
    "en": "All available tools (default)",
    "zh-CN": "所有可用工具（默认）"
  },
  "ui.python-only-no-external-solver": {
    "en": "Python only · no external solver",
    "zh-CN": "仅 Python · 不使用外部求解器"
  },
  "ui.saved-tool-restriction-check-availability": {
    "en": "Saved tool restriction · check availability",
    "zh-CN": "已保存工具访问限制 · 请检查可用状态"
  },
  "ui.all-verified-hosted-tools": {
    "en": "All verified hosted tools",
    "zh-CN": "所有已验证的托管工具"
  },
  "ui.setup-stopped-its-output-is-kept": {
    "en": "{p0}: setup stopped. Its output is kept.",
    "zh-CN": "{p0}：配置已停止，输出已保留。"
  },
  "ui.needs-attention-open-it-in-research-tools-to-see-why-and-diagnose-wi": {
    "en": "{p0} needs attention. Open it in Research tools to see why and diagnose with an agent.",
    "zh-CN": "{p0} 需要处理。请在科研工具中查看原因，并请智能体诊断。"
  },
  "ui.passed-its-readiness-check": {
    "en": "passed its readiness check",
    "zh-CN": "已通过就绪检查"
  },
  "ui.is-installed-and-ready": {
    "en": "is installed and ready",
    "zh-CN": "已安装并就绪"
  },
  "ui.readiness-check": {
    "en": "readiness check",
    "zh-CN": "就绪检查"
  },
  "ui.finished-2": {
    "en": "{p0}: {p1} finished.",
    "zh-CN": "{p0}：{p1}已完成。"
  },
  "ui.study-finished-review-its-findings-and-independent-assessment-below": {
    "en": "Study finished. Review its findings and independent assessment below.",
    "zh-CN": "研究已结束，请查看下方结果与独立评估。"
  },
  "ui.study-stopped-before-an-accepted-outcome-the-report-records-the-part": {
    "en": "Study stopped before an accepted outcome. The report records the partial findings.",
    "zh-CN": "研究在结果获认可前停止，报告中记录了阶段性发现。"
  },
  "ui.read-the-agent-s-explanation-in-conversation": {
    "en": "Read the agent’s explanation in conversation ↗",
    "zh-CN": "在对话中阅读智能体的解释 ↗"
  },
  "ui.return-to-the-conversation": {
    "en": "Return to the conversation ↗",
    "zh-CN": "返回对话 ↗"
  },
  "ui.explain-in-conversation": {
    "en": "Explain in conversation",
    "zh-CN": "在对话中解释"
  },
  "ui.report-queued-for-your-interactive-agent": {
    "en": "Report queued for your interactive agent.",
    "zh-CN": "报告已提交给交互智能体处理。"
  },
  "ui.the-report-has-been-handed-to-your-interactive-agent-its-explanation": {
    "en": "The report has been handed to your interactive agent. Its explanation appears in the conversation.",
    "zh-CN": "报告已交给交互智能体，解释会显示在对话中。"
  },
  "ui.ask-your-interactive-agent-to-explain-this-report-when-you-are-ready": {
    "en": "Ask your interactive agent to explain this report when you are ready.",
    "zh-CN": "准备好后，可请交互智能体解释这份报告。"
  },
  "ui.run-settings-saved-new-worker-and-review-calls-will-use-them": {
    "en": "Run settings saved. New worker and review calls will use them.",
    "zh-CN": "运行设置已保存，后续执行与评审调用将使用新设置。"
  },
  "ui.study-time-extended-the-director-will-update-its-plan": {
    "en": "Study time extended. The director will update its plan.",
    "zh-CN": "研究时间已延长，研究主管将更新计划。"
  },
  "ui.director-reviewing-alongside-the-worker": {
    "en": "Director reviewing alongside the worker",
    "zh-CN": "研究主管正在与执行智能体并行评审"
  },
  "ui.not-fully-reported": {
    "en": "not fully reported",
    "zh-CN": "报告不完整"
  },
  "ui.available": {
    "en": "Available",
    "zh-CN": "可用"
  },
  "ui.not-available": {
    "en": "Not available",
    "zh-CN": "不可用"
  },
  "ui.evidence-review": {
    "en": "Evidence & review ↗",
    "zh-CN": "证据与评审 ↗"
  },
  "ui.continues-an-earlier-study": {
    "en": "Continues an earlier study ↗",
    "zh-CN": "延续先前的研究 ↗"
  },
  "ui.operator-guidance-queued": {
    "en": "Operator guidance ({p0} queued)",
    "zh-CN": "操作指导（{p0} 条待处理）"
  },
  "ui.included-at-agent-checkpoint": {
    "en": "Included at agent checkpoint",
    "zh-CN": "已在智能体检查点送达"
  },
  "ui.queued": {
    "en": "Queued",
    "zh-CN": "排队中"
  },
  "ui.accepted": {
    "en": "Accepted",
    "zh-CN": "已接受"
  },
  "ui.more-evidence-needed": {
    "en": "More evidence needed",
    "zh-CN": "需要更多证据"
  },
  "ui.scientific-results": {
    "en": "Scientific results",
    "zh-CN": "科研结果"
  },
  "ui.results-reports-and-simulation-files": {
    "en": "Results, reports, and simulation files",
    "zh-CN": "结果、报告与仿真文件"
  },
  "ui.simulation-2": {
    "en": "Simulation",
    "zh-CN": "仿真"
  },
  "ui.machine": {
    "en": "Machine: {p0} · {p1}",
    "zh-CN": "设备：{p0} · {p1}"
  },
  "ui.remote-artifact-to-retrieve": {
    "en": "Remote artifact to retrieve",
    "zh-CN": "待取回的远程产物"
  },
  "ui.retrieve-from-worker": {
    "en": "Retrieve from worker",
    "zh-CN": "从执行节点取回"
  },
  "ui.artifact-retrieved-and-sha256-verified": {
    "en": "Artifact retrieved and SHA256 verified.",
    "zh-CN": "已取回产物并验证 SHA256。"
  },
  "ui.all-recorded-files": {
    "en": "All recorded files",
    "zh-CN": "所有已记录文件"
  },
  "ui.the-hosted-agent-and-compute-are-ready": {
    "en": "The hosted agent and compute are ready.",
    "zh-CN": "托管智能体和计算资源已就绪。"
  },
  "ui.managed-experiments": {
    "en": "Managed experiments",
    "zh-CN": "托管实验"
  },
  "ui.assigned-by-the-host": {
    "en": "Assigned by the host",
    "zh-CN": "由托管方分配"
  },
  "ui.compatible-api-connections": {
    "en": "Compatible API · Connections",
    "zh-CN": "兼容 API · 连接设置"
  },
  "ui.model-id-for-the-selected-agent": {
    "en": "Model ID for the selected agent",
    "zh-CN": "所选智能体的模型 ID"
  },
  "ui.default-conversation-agent-model": {
    "en": "Default: conversation agent model",
    "zh-CN": "默认使用对话智能体模型"
  },
  "ui.limited-isolation": {
    "en": "Limited isolation",
    "zh-CN": "隔离能力有限"
  },
  "ui.execution-needs-setup": {
    "en": "Execution needs setup",
    "zh-CN": "执行环境需要配置"
  },
  "ui.saving-api-connection": {
    "en": "Saving API connection…",
    "zh-CN": "正在保存 API 连接……"
  },
  "ui.connection-not-saved": {
    "en": "Connection not saved: {p0}",
    "zh-CN": "连接未保存：{p0}"
  },
  "ui.api-connection-saved-choose-its-model-in-a-conversation": {
    "en": "API connection saved. Choose its model in a conversation.",
    "zh-CN": "API 连接已保存。请在对话中选择对应模型。"
  },
  "ui.checking-linux-experiment-execution": {
    "en": "Checking Linux experiment execution…",
    "zh-CN": "正在检查 Linux 实验执行环境……"
  },
  "ui.ready-recorded-experiments-can-run-in-the-linux-sandbox": {
    "en": "Ready. Recorded experiments can run in the Linux sandbox.",
    "zh-CN": "已就绪，可在 Linux 沙箱中运行有记录的实验。"
  },
  "ui.your-agent-will-ask-focused-questions-in-the-conversation": {
    "en": "Your agent will ask focused questions in the conversation.",
    "zh-CN": "智能体将在对话中逐项提问。"
  },
  "ui.your-agent-is-drafting-the-study-from-this-conversation": {
    "en": "Your agent is drafting the study from this conversation.",
    "zh-CN": "智能体正在根据当前对话起草研究计划。"
  },
  "ui.study-brief-saved": {
    "en": "Study brief saved",
    "zh-CN": "研究简报已保存"
  },
  "ui.saved": {
    "en": "Saved {p0}",
    "zh-CN": "已保存 {p0}"
  },
  "ui.research-tool-registered": {
    "en": "Research tool registered",
    "zh-CN": "科研工具已注册"
  },
  "ui.conversation-and-saved-folders-deleted": {
    "en": "Conversation and saved folders deleted",
    "zh-CN": "已删除对话及其保存目录"
  },
  "ui.light-mode": {
    "en": "☀ Light mode",
    "zh-CN": "☀ 浅色模式"
  },
  "ui.dark-mode": {
    "en": "☾ Dark mode",
    "zh-CN": "☾ 深色模式"
  },
  "ui.continue-investigation": {
    "en": "Continue investigation",
    "zh-CN": "继续研究"
  },
  "ui.send-guidance": {
    "en": "Send guidance",
    "zh-CN": "发送指导"
  },
  "ui.guidance-queued-for-the-next-agent-checkpoint": {
    "en": "Guidance queued for the next agent checkpoint.",
    "zh-CN": "指导已排队，将在下一个智能体检查点送达。"
  },
  "ui.agent-and-model-settings": {
    "en": "Agent and model settings",
    "zh-CN": "智能体与模型设置"
  },
  "ui.expand-message-editor": {
    "en": "Expand message editor",
    "zh-CN": "展开消息编辑器"
  },
  "ui.collapse-message-editor": {
    "en": "Collapse message editor",
    "zh-CN": "收起消息编辑器"
  },
  "ui.loading-agent": {
    "en": "Loading agent…",
    "zh-CN": "正在加载智能体……"
  },
  "ui.choose-agent-2": {
    "en": "Choose agent",
    "zh-CN": "选择智能体"
  },
  "ui.choose-model-2": {
    "en": "Choose model",
    "zh-CN": "选择模型"
  },
  "ui.agent-2": {
    "en": "Agent",
    "zh-CN": "智能体"
  },
  "ui.project-settings": {
    "en": "Project settings",
    "zh-CN": "项目设置"
  },
  "ui.new-project": {
    "en": "New project",
    "zh-CN": "新建项目"
  },
  "ui.personal": {
    "en": "Personal",
    "zh-CN": "个人工作区"
  },
  "ui.unknown": {
    "en": "Unknown",
    "zh-CN": "未知"
  },
  "ui.default-effort": {
    "en": " · default effort",
    "zh-CN": " · 默认推理强度"
  },
  "ui.no-inference": {
    "en": "No inference",
    "zh-CN": "无推理调用"
  },
  "ui.variable-tariff": {
    "en": "Variable tariff",
    "zh-CN": "浮动费率"
  },
  "ui.usage-missing": {
    "en": "Usage missing",
    "zh-CN": "缺少用量记录"
  },
  "ui.verified-completions": {
    "en": " verified completions",
    "zh-CN": " 次验证通过"
  },
  "ui.recorded-cost-lower-bound-unranked": {
    "en": " · recorded cost lower bound, unranked",
    "zh-CN": " · 记录成本为下限，不参与排名"
  },
  "ui.no-measurements-match-this-filter": {
    "en": "No measurements match this filter",
    "zh-CN": "没有符合筛选条件的测量结果"
  },
  "ui.clear-the-model-or-effort-filter-to-see-the-published-results": {
    "en": "Clear the model or effort filter to see the published results.",
    "zh-CN": "清除模型或推理强度筛选，即可查看已发布结果。"
  },
  "ui.verified-finish-time-minutes-faster-at-top": {
    "en": "Verified finish time · minutes · faster at top",
    "zh-CN": "验证完成时间 · 分钟 · 越靠上越快"
  },
  "ui.api-equivalent-cost-per-attempt-usd-log-scale-cheaper-to-the-left": {
    "en": "API-equivalent cost per attempt · USD · log scale · cheaper to the left",
    "zh-CN": "每次尝试的 API 等效成本 · 美元 · 对数坐标 · 越靠左越便宜"
  },
  "ui.better-less-cost-less-time": {
    "en": "↖ BETTER · LESS COST + LESS TIME",
    "zh-CN": "↖ 更优 · 成本更低、耗时更短"
  },
  "ui.completed": {
    "en": " completed · ",
    "zh-CN": " 次完成 · "
  },
  "ui.per-attempt": {
    "en": " per attempt · ",
    "zh-CN": " 每次尝试 · "
  },
  "ui.observed-pareto-frontier": {
    "en": " · observed Pareto frontier",
    "zh-CN": " · 观测到的 Pareto 前沿"
  },
  "ui.agy-counter-estimate": {
    "en": " · AGY counter estimate",
    "zh-CN": " · AGY 计数器估计"
  },
  "ui.pareto-frontier": {
    "en": " · Pareto frontier",
    "zh-CN": " · Pareto 前沿"
  },
  "ui.cost-time-pareto-plot": {
    "en": "Cost–time Pareto plot",
    "zh-CN": "成本—耗时 Pareto 图"
  },
  "ui.upper-left-is-better-cheaper-to-the-left-faster-at-the-top-outlined-": {
    "en": "Upper left is better: cheaper to the left, faster at the top. Outlined points mark the observed Pareto frontier. Colour identifies the model. Dashed lines connect reasoning efforts for the same model. Unfinished and partial cost receipts are excluded.",
    "zh-CN": "越靠左上越好：向左成本更低，向上速度更快。描边点表示观测到的 Pareto 前沿，颜色区分模型，虚线连接同一模型的不同推理强度。未完成及成本回执不完整的尝试不参与比较。"
  },
  "ui.version-unavailable": {
    "en": "Version unavailable",
    "zh-CN": "版本不可用"
  },
  "ui.view": {
    "en": "View ",
    "zh-CN": "查看 "
  },
  "ui.elapsed": {
    "en": "Elapsed",
    "zh-CN": "耗时"
  },
  "ui.input-incl-cache": {
    "en": "Input incl. cache",
    "zh-CN": "输入（含缓存）"
  },
  "ui.cached-input": {
    "en": "Cached input",
    "zh-CN": "缓存输入"
  },
  "ui.output": {
    "en": "Output",
    "zh-CN": "输出"
  },
  "ui.cost": {
    "en": "Cost",
    "zh-CN": "成本"
  },
  "ui.result": {
    "en": "Result",
    "zh-CN": "结果"
  },
  "ui.unavailable-2": {
    "en": "Unavailable",
    "zh-CN": "不可用"
  },
  "ui.no-successful-inference": {
    "en": "No successful inference",
    "zh-CN": "无成功的推理调用"
  },
  "ui.numerical-passes": {
    "en": " numerical passes",
    "zh-CN": " 次数值检查通过"
  },
  "ui.agy-estimate": {
    "en": "AGY estimate",
    "zh-CN": "AGY 估计"
  },
  "ui.partial-receipt-unranked-by-cost": {
    "en": "Partial receipt · unranked by cost",
    "zh-CN": "回执不完整 · 不参与成本排名"
  },
  "ui.groq-tariff-reference": {
    "en": "Groq tariff reference",
    "zh-CN": "Groq 费率参考"
  },
  "ui.api-equivalent": {
    "en": "API equivalent",
    "zh-CN": "API 等效"
  },
  "ui.variable-routing": {
    "en": "Variable routing",
    "zh-CN": "动态路由"
  },
  "ui.reference-source": {
    "en": "Reference source",
    "zh-CN": "参考来源"
  },
  "ui.vendor-tariff": {
    "en": "Vendor tariff",
    "zh-CN": "服务商费率"
  },
  "ui.rank": {
    "en": "Rank",
    "zh-CN": "排名"
  },
  "ui.model-coding-agent": {
    "en": "Model / coding agent",
    "zh-CN": "模型 / 编程智能体"
  },
  "ui.effort": {
    "en": "Effort",
    "zh-CN": "推理强度"
  },
  "ui.completion": {
    "en": "Completion",
    "zh-CN": "完成率"
  },
  "ui.numerical-checks": {
    "en": "Numerical checks",
    "zh-CN": "数值检查"
  },
  "ui.completion-time": {
    "en": "Completion time",
    "zh-CN": "完成时间"
  },
  "ui.cost-attempt-usd": {
    "en": "Cost / attempt · USD",
    "zh-CN": "成本 / 次尝试 · 美元"
  },
  "ui.token-tariff-in-out-per-1m": {
    "en": "Token tariff · in / out per 1M",
    "zh-CN": "token 费率 · 每百万输入 / 输出"
  },
  "ui.tradeoffs-need-measured-usage-and-timing": {
    "en": "Tradeoffs need measured usage and timing",
    "zh-CN": "权衡比较需要实测用量和耗时"
  },
  "ui.missing-cost-stays-unknown-complete-timed-trial-metadata-will-place-": {
    "en": "Missing cost stays unknown. Complete timed trial metadata will place configurations here.",
    "zh-CN": "缺失的成本保留为未知。补齐计时试验元数据后，配置会显示在这里。"
  },
  "ui.estimated-token-cost-and-elapsed-time-per-verified-success-includes-": {
    "en": "Estimated token cost and elapsed time per verified success. Includes failed attempts; upper left is cheaper and faster. Pass rate is a third Pareto objective.",
    "zh-CN": "每次验证成功的估计 token 成本和耗时，包含失败尝试。左上方表示成本更低、速度更快；通过率为第三个 Pareto 优化目标。"
  },
  "ui.token-estimate-verified-success": {
    "en": "Token $ estimate / verified success",
    "zh-CN": "估计 token 成本 / 次验证成功"
  },
  "ui.elapsed-time-verified-success": {
    "en": "Elapsed time / verified success",
    "zh-CN": "耗时 / 次验证成功"
  },
  "ui.provisional": {
    "en": ", provisional",
    "zh-CN": "，暂定"
  },
  "ui.pass-rate-per-success": {
    "en": "{p0}: {p1} pass rate, {p2}, {p3} per success{p4}",
    "zh-CN": "{p0}：通过率 {p1}，{p2}，每次成功 {p3}{p4}"
  },
  "ui.provisional-fewer-than-five-trials": {
    "en": "\nProvisional: fewer than five trials",
    "zh-CN": "\n暂定：试验次数不足五次"
  },
  "ui.each-comparison-holds-the-task-prompt-hardware-deadline-harness-and-": {
    "en": "Each comparison holds the task, prompt, hardware, deadline, harness and continuation policy fixed.",
    "zh-CN": "每组比较均固定任务、提示词、硬件、截止时间、测试框架和续跑规则。"
  },
  "ui.build-the-first-comparison": {
    "en": "Build the first comparison",
    "zh-CN": "建立首次比较"
  },
  "ui.prepare-a-task-below-or-import-final-host-grades-from-fresh-timed-tr": {
    "en": "Prepare a task below, or import final host grades from fresh timed trials. Exploratory results remain visible separately.",
    "zh-CN": "在下方准备任务，或导入新计时试验的最终评分。探索性结果单独保留。"
  },
  "ui.execution-unknown": {
    "en": "execution unknown",
    "zh-CN": "执行方式未知"
  },
  "ui.pack-s-budget-harness-runner": {
    "en": "{p0} · pack {p1} · {p2} · {p3}s budget · {p4} · harness {p5} · runner {p6}",
    "zh-CN": "{p0} · 任务包 {p1} · {p2} · {p3} 秒预算 · {p4} · 测试框架 {p5} · 执行器 {p6}"
  },
  "ui.effort-2": {
    "en": "{p0} {p1} · {p2} effort",
    "zh-CN": "{p0} {p1} · {p2} 推理强度"
  },
  "ui.trial-measurements": {
    "en": "Trial measurements",
    "zh-CN": "试验测量值"
  },
  "ui.input-tokens": {
    "en": "Input tokens",
    "zh-CN": "输入 token"
  },
  "ui.output-tokens": {
    "en": "Output tokens",
    "zh-CN": "输出 token"
  },
  "ui.delivery": {
    "en": "Delivery",
    "zh-CN": "交付结果"
  },
  "ui.95-interval": {
    "en": "95% interval {p0}",
    "zh-CN": "95% 区间 {p0}"
  },
  "ui.provisional-2": {
    "en": "Provisional",
    "zh-CN": "暂定"
  },
  "ui.no-verified-success": {
    "en": "No verified success",
    "zh-CN": "尚无验证成功"
  },
  "ui.pareto-frontier-2": {
    "en": "Pareto frontier",
    "zh-CN": "Pareto 前沿"
  },
  "ui.tradeoff-dominated": {
    "en": "Tradeoff dominated",
    "zh-CN": "被其他方案支配"
  },
  "ui.time-frontier-cost-unknown": {
    "en": "Time frontier · cost unknown",
    "zh-CN": "时间前沿 · 成本未知"
  },
  "ui.cost-incomplete": {
    "en": "Cost incomplete",
    "zh-CN": "成本记录不完整"
  },
  "ui.median-first-verified-completion-late-completions-trials-with-unknow": {
    "en": "Median first verified completion: {p0}. {p1} late completions. {p2} trials with unknown token cost.",
    "zh-CN": "首次验证完成时间中位数：{p0}。{p1} 次逾期完成，{p2} 次试验的 token 成本未知。"
  },
  "ui.agent-configuration": {
    "en": "Agent configuration",
    "zh-CN": "智能体配置"
  },
  "ui.trials": {
    "en": "Trials",
    "zh-CN": "试验数"
  },
  "ui.pass-rate": {
    "en": "Pass rate",
    "zh-CN": "通过率"
  },
  "ui.mean-trial-time": {
    "en": "Mean trial time",
    "zh-CN": "平均试验耗时"
  },
  "ui.time-success": {
    "en": "Time / success",
    "zh-CN": "耗时 / 次成功"
  },
  "ui.token-estimate-success": {
    "en": "Token $ estimate / success",
    "zh-CN": "估计 token 成本 / 次成功"
  },
  "ui.reported-success": {
    "en": "Reported $ / success",
    "zh-CN": "报告成本 / 次成功"
  },
  "ui.sample-status": {
    "en": "Sample status",
    "zh-CN": "样本状态"
  },
  "ui.benchmark-your-model": {
    "en": "Benchmark your model",
    "zh-CN": "测试你的模型"
  },
  "ui.run-fresh-timed-trials-with-your-installed-coding-agent-or-the-api-c": {
    "en": "Run fresh timed trials with your installed coding agent or the API connection saved in Connections. Your agent keeps its native tools. Grades are added here automatically.",
    "zh-CN": "使用已安装的编程智能体或连接设置中保存的 API 连接，运行新的计时试验。智能体保留原生工具，评分会自动添加到这里。"
  },
  "ui.provider-default": {
    "en": "Provider default",
    "zh-CN": "服务商默认值"
  },
  "ui.tasks": {
    "en": "Tasks",
    "zh-CN": "任务"
  },
  "ui.advanced-settings": {
    "en": "Advanced settings",
    "zh-CN": "高级设置"
  },
  "ui.parallel-trials": {
    "en": "Parallel trials",
    "zh-CN": "并行试验数"
  },
  "ui.uses-your-configured-subscription-or-api-credits-api-cost-estimates-": {
    "en": "Uses your configured subscription or API credits. API cost estimates and provider-reported spending remain separate.",
    "zh-CN": "使用已配置的订阅或 API 额度。API 成本估计与服务商报告的支出单独记录。"
  },
  "ui.start-timed-trials": {
    "en": "Start timed trials",
    "zh-CN": "开始计时试验"
  },
  "ui.simjecture-owned-grades-shipped-community-grades-local-runs-appear-a": {
    "en": "{p0} Simjecture-owned grades · {p1} shipped community grades. Local runs appear as they finish. Community declarations keep separate comparison groups.",
    "zh-CN": "{p0} 条 Simjecture 官方评分 · {p1} 条随附社区评分。本地运行完成后自动显示。社区声明按独立比较组保留。"
  },
  "ui.running": {
    "en": "Running",
    "zh-CN": "运行中"
  },
  "ui.finished-3": {
    "en": "Finished",
    "zh-CN": "已结束"
  },
  "ui.working": {
    "en": "Working: {p0}",
    "zh-CN": "正在处理：{p0}"
  },
  "ui.unavailable-or-quota-limited": {
    "en": "Unavailable or quota limited: {p0}",
    "zh-CN": "不可用或受额度限制：{p0}"
  },
  "ui.runner-errors-need-attention": {
    "en": "{p0} runner errors need attention",
    "zh-CN": "有 {p0} 个执行器错误需要处理"
  },
  "ui.community": {
    "en": "Community · ",
    "zh-CN": "社区 · "
  },
  "ui.local": {
    "en": "Local · ",
    "zh-CN": "本地 · "
  },
  "ui.pack-s": {
    "en": "{p0}{p1} · pack {p2} · {p3}s · {p4}",
    "zh-CN": "{p0}{p1} · 任务包 {p2} · {p3} 秒 · {p4}"
  },
  "ui.no-controlled-trials-yet": {
    "en": "No controlled trials yet",
    "zh-CN": "暂无受控试验"
  },
  "ui.usd-per-million-tokens": {
    "en": "USD per million tokens. {p0}",
    "zh-CN": "每百万 token 的美元费用。{p0}"
  },
  "ui.official-source": {
    "en": "Official source",
    "zh-CN": "官方来源"
  },
  "ui.model": {
    "en": "Model",
    "zh-CN": "模型"
  },
  "ui.input": {
    "en": "Input",
    "zh-CN": "输入"
  },
  "ui.reference": {
    "en": "Reference",
    "zh-CN": "参考"
  },
  "ui.import-custom-results-in-a-self-hosted-simjecture-workspace": {
    "en": "Import custom results in a self-hosted Simjecture workspace.",
    "zh-CN": "可在自行托管的 Simjecture 工作区中导入自定义结果。"
  },
  "ui.browse-and-download-the-official-results-here-testing-models-and-imp": {
    "en": "Browse and download the official results here. Testing models and importing custom results are available in a self-hosted Simjecture workspace.",
    "zh-CN": "在此浏览和下载官方结果。测试模型和导入自定义结果功能可在自行托管的 Simjecture 工作区中使用。"
  },
  "ui.grades-imported-repeated-imports-do-not-add-trials": {
    "en": "{p0} grades imported. Repeated imports do not add trials.",
    "zh-CN": "已导入 {p0} 条评分。重复导入不会增加试验数。"
  },
  "ui.official-simjecture-measurements": {
    "en": "Official Simjecture measurements · ",
    "zh-CN": "Simjecture 官方测量 · "
  },
  "ui.maintained-result-edition-pack": {
    "en": " · maintained result edition · pack ",
    "zh-CN": " · 持续维护的结果版本 · 任务包 "
  },
  "ui.current-pack-community-and-locally-declared-trials-each-comparison-p": {
    "en": "Current-pack community and locally declared trials. Each comparison preserves its runner conditions.",
    "zh-CN": "当前任务包的社区及本地声明试验。每组比较均保留执行条件。"
  },
  "ui.these-submissions-are-separate-from-the-official-publication-importe": {
    "en": "These submissions are separate from the official publication. Imported and community execution/billing declarations are not independently certified.",
    "zh-CN": "这些提交与官方发布结果单独展示。导入及社区记录的执行和计费声明未经独立认证。"
  },
  "ui.community-and-local-measurements-use-their-declared-comparison-proto": {
    "en": "Community and local measurements use their declared comparison protocol.",
    "zh-CN": "社区及本地测量采用各自声明的比较协议。"
  },
  "ui.drag-to-resize": {
    "en": "{p0} · drag to resize",
    "zh-CN": "{p0} · 拖动可调整大小"
  },
  "ui.study-run-settings": {
    "en": "Study run settings",
    "zh-CN": "研究运行设置"
  },
  "ui.run-settings": {
    "en": "Run settings",
    "zh-CN": "运行设置"
  },
  "ui.these-operating-settings-do-not-extend-the-campaign-deadline-or-gran": {
    "en": "These operating settings do not extend the campaign deadline or grant more storage, memory, or compute.",
    "zh-CN": "这些运行设置不会延长研究截止时间，也不会增加存储、内存或计算资源。"
  },
  "ui.actions-per-worker-turn": {
    "en": "Actions per worker turn",
    "zh-CN": "执行智能体每轮操作数"
  },
  "ui.blank-allows-the-worker-to-continue-within-the-campaign-budget": {
    "en": "Blank allows the worker to continue within the campaign budget.",
    "zh-CN": "留空时，执行智能体可在研究预算内持续工作。"
  },
  "ui.worker-checkpoint-after-seconds": {
    "en": "Worker checkpoint after (seconds)",
    "zh-CN": "执行智能体检查点间隔（秒）"
  },
  "ui.blank-avoids-a-forced-interruption-the-director-reviews-progress-alo": {
    "en": "Blank avoids a forced interruption. The director reviews progress alongside the worker.",
    "zh-CN": "留空可避免强制中断。研究主管会与执行智能体并行审查进展。"
  },
  "ui.review-allowance-seconds": {
    "en": "Review allowance (seconds)",
    "zh-CN": "评审时限（秒）"
  },
  "ui.blank-uses-the-study-s-recorded-review-or-turn-allowance-every-revie": {
    "en": "Blank uses the study's recorded review or turn allowance. Every review stays within the campaign deadline.",
    "zh-CN": "留空则使用研究已记录的评审或轮次时限。所有评审均受研究截止时间约束。"
  },
  "ui.reason": {
    "en": "Reason",
    "zh-CN": "原因"
  },
  "ui.extend-study-time": {
    "en": "Extend study time",
    "zh-CN": "延长研究时间"
  },
  "ui.add-time-to-this-investigation-the-agent-keeps-its-context-and-evide": {
    "en": "Add time to this investigation. The agent keeps its context and evidence, and the running computation continues.",
    "zh-CN": "为本次研究增加时间。智能体保留上下文和证据，正在进行的计算会继续运行。"
  },
  "ui.additional-hours": {
    "en": "Additional hours",
    "zh-CN": "增加时长（小时）"
  },
  "ui.current-deadline": {
    "en": "Current deadline",
    "zh-CN": "当前截止时间"
  },
  "ui.new-deadline": {
    "en": "New deadline",
    "zh-CN": "新的截止时间"
  },
  "ui.times-shown-in": {
    "en": "Times shown in {p0}.",
    "zh-CN": "时间按 {p0} 时区显示。"
  },
  "ui.reason-optional": {
    "en": "Reason (optional)",
    "zh-CN": "原因（可选）"
  },
  "ui.this-adds-wall-time-and-may-use-more-model-credit-and-compute-the-di": {
    "en": "This adds wall time and may use more model credit and compute. The director is notified to update its plan. The report reserve and each experiment’s own timeout stay in place.",
    "zh-CN": "这会增加总运行时间，并可能消耗更多模型额度和计算资源。系统会通知研究主管更新计划。报告预留时间及各实验的超时限制仍然有效。"
  },
  "ui.active-experiment-limits": {
    "en": "Active experiment limits",
    "zh-CN": "运行中实验的时限"
  },
  "ui.recorded-job-limit-unchanged": {
    "en": "recorded job limit unchanged",
    "zh-CN": "已记录的任务时限不变"
  },
  "ui.choose-additional-time": {
    "en": "Choose additional time",
    "zh-CN": "请选择增加的时长"
  },
  "ui.add-hours": {
    "en": "Add {p0} hours",
    "zh-CN": "增加 {p0} 小时"
  },
  "ui.deadline": {
    "en": "Deadline · {p0}",
    "zh-CN": "截止时间 · {p0}"
  },
  "ui.extend-time": {
    "en": "Extend time",
    "zh-CN": "延长时间"
  },
  "ui.director": {
    "en": "Director",
    "zh-CN": "研究主管"
  },
  "ui.worker": {
    "en": "Worker",
    "zh-CN": "执行智能体"
  },
  "ui.requests-more-hours": {
    "en": "{p0} requests {p1} more hours: {p2}",
    "zh-CN": "{p0}申请增加 {p1} 小时：{p2}"
  },
  "ui.review-time-request": {
    "en": "Review time request",
    "zh-CN": "查看延期申请"
  },
  "ui.extension": {
    "en": "extension",
    "zh-CN": "延期"
  },
  "ui.extensions": {
    "en": "extensions",
    "zh-CN": "延期"
  },
  "ui.budget-history": {
    "en": "Budget history · {p0} {p1}",
    "zh-CN": "预算历史 · {p0} 次{p1}"
  },
  "ui.operator": {
    "en": "operator",
    "zh-CN": "操作者"
  },
  "ui.h-deadline": {
    "en": "+{p0} h · {p1} · deadline {p2}{p3}",
    "zh-CN": "+{p0} 小时 · {p1} · 截止时间 {p2}{p3}"
  },
  "ui.ask-your-agent-anything": {
    "en": "Ask your agent anything",
    "zh-CN": "向智能体提问"
  },
  "ui.two-ways-to-work": {
    "en": "Two ways to work",
    "zh-CN": "两种工作方式"
  },
  "ui.your-conversations": {
    "en": "Your conversations",
    "zh-CN": "你的对话"
  },
  "ui.each-conversation-keeps-its-own-files-simulations-and-studies-its-li": {
    "en": "Each conversation keeps its own files, simulations and studies. Its live runs and outputs appear in the Workspace panel beside the chat.",
    "zh-CN": "每个对话独立保存文件、仿真和研究。运行中的任务及其输出会显示在对话旁的工作区面板中。"
  },
  "ui.of": {
    "en": "{p0} of {p1}",
    "zh-CN": "第 {p0} 步，共 {p1} 步"
  },
  "ui.done": {
    "en": "Done",
    "zh-CN": "完成"
  },
  "ui.next": {
    "en": "Next",
    "zh-CN": "下一步"
  },
  "ui.use-light-theme": {
    "en": "Use light theme",
    "zh-CN": "使用浅色主题"
  },
  "ui.use-dark-theme": {
    "en": "Use dark theme",
    "zh-CN": "使用深色主题"
  },
  "ui.connecting": {
    "en": "Connecting",
    "zh-CN": "正在连接"
  },
  "ui.ready": {
    "en": "Ready",
    "zh-CN": "已就绪"
  },
  "ui.disconnected": {
    "en": "Disconnected",
    "zh-CN": "已断开"
  },
  "ui.live": {
    "en": "Live",
    "zh-CN": "实时连接"
  },
  "ui.retrying": {
    "en": "Retrying",
    "zh-CN": "正在重试"
  },
  "ui.workspace": {
    "en": "Workspace",
    "zh-CN": "工作区"
  },
  "ui.loading": {
    "en": "Loading",
    "zh-CN": "正在加载"
  },
  "ui.no-campaigns-found": {
    "en": "No campaigns found",
    "zh-CN": "未找到研究任务"
  },
  "ui.unnamed-campaign": {
    "en": "unnamed campaign",
    "zh-CN": "未命名研究任务"
  },
  "ui.agent-owned-investigation": {
    "en": "Agent-owned investigation",
    "zh-CN": "智能体主导的研究"
  },
  "ui.reading-durable-state": {
    "en": "Reading durable state",
    "zh-CN": "正在读取持久化状态"
  },
  "ui.cycle": {
    "en": "{p0} · cycle {p1}",
    "zh-CN": "{p0} · 第 {p1} 轮"
  },
  "ui.no-wall-time-estimate": {
    "en": "No wall-time estimate",
    "zh-CN": "暂无总运行时间估计"
  },
  "ui.working-in": {
    "en": "{p0} working in {p1}",
    "zh-CN": "{p0}正在{p1}中工作"
  },
  "ui.research-loop-active": {
    "en": "Research loop active.",
    "zh-CN": "研究循环正在运行。"
  },
  "ui.no-active-claim": {
    "en": "no active claim",
    "zh-CN": "无活跃论断"
  },
  "ui.current-action": {
    "en": "Current action · {p0}",
    "zh-CN": "当前操作 · {p0}"
  },
  "ui.campaign-record": {
    "en": "Campaign record",
    "zh-CN": "研究任务记录"
  },
  "ui.all-model-actions-have-ended": {
    "en": "All model actions have ended",
    "zh-CN": "所有模型操作已结束"
  },
  "ui.current-action-2": {
    "en": "Current action",
    "zh-CN": "当前操作"
  },
  "ui.waiting-for-the-next-typed-model-action": {
    "en": "Waiting for the next typed model action",
    "zh-CN": "正在等待下一个结构化模型操作"
  },
  "ui.campaign-paused": {
    "en": "Campaign paused",
    "zh-CN": "研究任务已暂停"
  },
  "ui.resume-from-the-next-action-boundary": {
    "en": "Resume from the next action boundary",
    "zh-CN": "从下一个操作边界恢复"
  },
  "ui.no-live-process": {
    "en": "No live process",
    "zh-CN": "无运行中的进程"
  },
  "ui.the-durable-record-remains-available": {
    "en": "The durable record remains available",
    "zh-CN": "持久化记录仍可查看"
  },
  "ui.no-registered-claims": {
    "en": "No registered claims",
    "zh-CN": "尚未注册论断"
  },
  "ui.model-turns": {
    "en": "{p0} model turns",
    "zh-CN": "{p0} 轮模型调用"
  },
  "ui.m-left": {
    "en": " · {p0}m left",
    "zh-CN": " · 剩余 {p0} 分钟"
  },
  "ui.pending": {
    "en": "Pending",
    "zh-CN": "等待中"
  },
  "ui.no-model-usage-recorded": {
    "en": "No model usage recorded",
    "zh-CN": "尚未记录模型用量"
  },
  "ui.heartbeat": {
    "en": "Heartbeat {p0}",
    "zh-CN": "心跳 {p0}"
  },
  "ui.visible-artifacts": {
    "en": "{p0} visible artifacts",
    "zh-CN": "{p0} 个可见产物"
  },
  "ui.back-to-this-conversation": {
    "en": "Back to this conversation",
    "zh-CN": "返回此对话"
  },
  "ui.open-the-research-workspace": {
    "en": "Open the research workspace",
    "zh-CN": "打开科研工作区"
  },
  "ui.this-web-session-is-read-only": {
    "en": "This web session is read-only",
    "zh-CN": "此网页会话为只读模式"
  },
  "ui.all-claim-kinds": {
    "en": "All claim kinds",
    "zh-CN": "所有论断类型"
  },
  "ui.scientific-only": {
    "en": "Scientific only",
    "zh-CN": "仅科学论断"
  },
  "ui.commissioning-stage-for": {
    "en": "Commissioning stage for {p0}, {p1}",
    "zh-CN": "{p0} 的工具验证阶段，{p1}"
  },
  "ui.claim": {
    "en": "{p0} claim {p1}, {p2}: {p3}",
    "zh-CN": "{p0}论断 {p1}，{p2}：{p3}"
  },
  "ui.commissioning-for-scientific-claim": {
    "en": "commissioning for scientific claim",
    "zh-CN": "科学论断的工具验证"
  },
  "ui.created-iteration": {
    "en": "created: iteration {p0}",
    "zh-CN": "创建于第 {p0} 轮"
  },
  "ui.updated-iteration": {
    "en": "updated: iteration {p0}",
    "zh-CN": "更新于第 {p0} 轮"
  },
  "ui.scientific-target": {
    "en": "scientific target: {p0}",
    "zh-CN": "科学目标：{p0}"
  },
  "ui.contract-v": {
    "en": "Contract v{p0}",
    "zh-CN": "契约 v{p0}"
  },
  "ui.workflow-stage": {
    "en": "Workflow stage",
    "zh-CN": "工作流阶段"
  },
  "ui.instrument-claims": {
    "en": "{p0} instrument claims",
    "zh-CN": "{p0} 个工具论断"
  },
  "ui.bound-programs": {
    "en": "{p0} bound programs",
    "zh-CN": "{p0} 个关联程序"
  },
  "ui.starting-point-limitations": {
    "en": "Starting-point limitations",
    "zh-CN": "起点的局限性"
  },
  "ui.no-campaign-generated-instrument-claim-has-been-registered-for-this-": {
    "en": "No campaign-generated instrument claim has been registered for this stage yet.",
    "zh-CN": "此阶段尚未注册由研究任务生成的工具论断。"
  },
  "ui.iteration": {
    "en": "Iteration {p0} · {p1}",
    "zh-CN": "第 {p0} 轮 · {p1}"
  },
  "ui.no-recorded-capability-execution-is-bound-to-these-commissioning-cla": {
    "en": "No recorded capability execution is bound to these commissioning claims.",
    "zh-CN": "这些工具验证论断尚未关联任何已记录的能力执行。"
  },
  "ui.evidence-record": {
    "en": "Evidence record",
    "zh-CN": "证据记录"
  },
  "ui.no-executions": {
    "en": "No executions",
    "zh-CN": "暂无执行记录"
  },
  "ui.execution-console-unavailable": {
    "en": "Execution console unavailable: {p0}",
    "zh-CN": "执行控制台不可用：{p0}"
  },
  "ui.execution": {
    "en": "Execution {p0}",
    "zh-CN": "执行{p0}"
  },
  "ui.supervisor-stopped-early-recorded-status-remained-at-the-stop": {
    "en": "Supervisor stopped early: {p0}. Recorded status: {p1}. {p2} remained at the stop.",
    "zh-CN": "监督进程提前停止：{p0}。记录状态：{p1}。停止时剩余 {p2}。"
  },
  "ui.harness-diagnostics": {
    "en": "Harness diagnostics",
    "zh-CN": "运行框架诊断"
  },
  "ui.context-or-report-generation-is-degraded-scientific-receipts-and-rev": {
    "en": "Context or report generation is degraded. Scientific receipts and review remain authoritative.",
    "zh-CN": "上下文或报告生成出现降级。科学计算回执及评审仍为判定依据。"
  },
  "ui.occurrence": {
    "en": "{p0}: {p1} · {p2} occurrence{p3}",
    "zh-CN": "{p0}：{p1} · 出现 {p2} 次{p3}"
  },
  "ui.per-request-counts-unavailable-from-native-cli": {
    "en": "Per-request counts unavailable from native CLI",
    "zh-CN": "原生 CLI 未提供逐请求计数"
  },
  "ui.tracked-requests": {
    "en": "{p0} tracked requests",
    "zh-CN": "已跟踪 {p0} 个请求"
  },
  "ui.tracked-requests-without-usage-yet-in-provider-retry-waits": {
    "en": "{p0} · {p1} tracked requests without usage yet · {p2} in provider retry waits. {p3}",
    "zh-CN": "{p0} · {p1} 个已跟踪请求尚无用量记录 · 服务商重试等待时间 {p2}。{p3}"
  },
  "ui.reported-totals-are-a-minimum-native-threads-and-unidentified-calls-": {
    "en": "Reported totals are a minimum: {p0} native threads and {p1} unidentified calls have unreported usage. A later cumulative worker counter can recover interrupted turns.",
    "zh-CN": "报告总量为下限：{p0} 个原生线程和 {p1} 次未识别调用尚未报告用量。后续执行智能体的累计计数可补回中断轮次的用量。"
  },
  "ui.historical-calls-lacked-final-usage-receipts-before-coverage-trackin": {
    "en": "{p0} historical calls lacked final usage receipts before coverage tracking. Their outstanding usage cannot be inferred as zero.",
    "zh-CN": "开始跟踪用量覆盖情况前，有 {p0} 次历史调用缺少最终用量回执。不能将其未报告用量视为零。"
  },
  "ui.input-cached-uncached-output-tokens": {
    "en": "{p0}: {p1} input / {p2} cached / {p3} uncached / {p4} output tokens",
    "zh-CN": "{p0}：输入 {p1} / 缓存 {p2} / 未缓存 {p3} / 输出 {p4} 个 token"
  },
  "ui.worker-awaiting-feedback": {
    "en": "Worker awaiting feedback",
    "zh-CN": "执行智能体正在等待反馈"
  },
  "ui.independent-report-assessments": {
    "en": "Independent report assessments",
    "zh-CN": "独立报告评估"
  },
  "ui.report-frozen-version": {
    "en": "Report {p0} · frozen version",
    "zh-CN": "报告 {p0} · 冻结版本"
  },
  "ui.open-frozen-report": {
    "en": "Open frozen report",
    "zh-CN": "打开冻结报告"
  },
  "ui.assess-current-report": {
    "en": "Assess current report",
    "zh-CN": "评估当前报告"
  },
  "ui.matched-by": {
    "en": "Matched by {p0}",
    "zh-CN": "由 {p0} 匹配"
  },
  "ui.no-matching-instrument-available": {
    "en": "No matching instrument available",
    "zh-CN": "无可用的匹配工具"
  },
  "ui.instrument-family-any-of-scientific-qualification-is-reviewed-separa": {
    "en": "Instrument family: any of {p0}. {p1}. Scientific qualification is reviewed separately.",
    "zh-CN": "工具系列：{p0} 中的任一种。{p1}。科学适用性另行评审。"
  },
  "ui.report-finalization": {
    "en": "Report & finalization",
    "zh-CN": "报告与收尾"
  },
  "ui.report": {
    "en": "{p0} · report {p1}",
    "zh-CN": "{p0} · 报告{p1}"
  },
  "ui.numerical-work-ends-by-is-reserved-for-writing-and-independent-repor": {
    "en": "Numerical work ends by {p0}. {p1} is reserved for writing and independent report review. Report acceptance does not approve scientific claims.",
    "zh-CN": "数值计算在 {p0} 前结束。预留 {p1} 用于撰写和独立评审报告。报告通过不代表科学论断获得认可。"
  },
  "ui.research-director-strategy-control": {
    "en": "Research director · strategy & control",
    "zh-CN": "研究主管 · 策略与控制"
  },
  "ui.reviewing-alongside-the-worker-separate-context": {
    "en": "Reviewing alongside the worker · separate context",
    "zh-CN": "与执行智能体并行评审 · 独立上下文"
  },
  "ui.director-route": {
    "en": "Director route: {p0}",
    "zh-CN": "研究主管路由：{p0}"
  },
  "ui.director-may-increase-allowances-with-a-recorded-reason": {
    "en": "Director may increase allowances with a recorded reason.",
    "zh-CN": "研究主管可在记录原因后提高限额。"
  },
  "ui.storage-increases-require-operator-delegation": {
    "en": "Storage increases require operator delegation.",
    "zh-CN": "增加存储需操作者授权。"
  },
  "ui.storage-allowance-per-experiment-and-file-shared-study-allowance": {
    "en": "Storage allowance: {p0} per experiment and file · {p1} shared study allowance. {p2}",
    "zh-CN": "存储限额：每个实验和文件 {p0} · 研究共享限额 {p1}。{p2}"
  },
  "ui.director-may-tune-deadlines-and-retries": {
    "en": "Director may tune deadlines and retries.",
    "zh-CN": "研究主管可调整时限及重试次数。"
  },
  "ui.tuning-requires-operator-delegation": {
    "en": "Tuning requires operator delegation.",
    "zh-CN": "调整参数需操作者授权。"
  },
  "ui.instrument-registration-per-probe-up-to-attempt-s-compute-cutoff-and": {
    "en": "Instrument registration: {p0} per probe · up to {p1} attempt(s). {p2} Compute cutoff and frozen identities remain enforced.",
    "zh-CN": "工具注册：每次探测 {p0} · 最多尝试 {p1} 次。{p2}计算截止时间和冻结标识仍然生效。"
  },
  "ui.on-probe": {
    "en": "{p0} on {p1} · probe {p2}/{p3} · {p4} · {p5}{p6}",
    "zh-CN": "{p1} 上的 {p0} · 探测 {p2}/{p3} · {p4} · {p5}{p6}"
  },
  "ui.unchanged-strategy-next-model-review-by-new-evidence-or-an-operation": {
    "en": "Unchanged strategy · next model review by {p0}. New evidence or an operational risk brings the review forward.",
    "zh-CN": "策略未变 · 下次模型评审不晚于 {p0}。出现新证据或运行风险时会提前评审。"
  },
  "ui.enabled-awaiting-the-first-strategy-review": {
    "en": "Enabled · awaiting the first strategy review.",
    "zh-CN": "已启用 · 等待首次策略评审。"
  },
  "ui.stop-replan": {
    "en": "Stop / replan",
    "zh-CN": "停止或重新规划"
  },
  "ui.continue-strategy": {
    "en": "Continue strategy",
    "zh-CN": "继续当前策略"
  },
  "ui.budget-science": {
    "en": "{p0} · budget {p1} · science {p2}",
    "zh-CN": "{p0} · 预算{p1} · 科学{p2}"
  },
  "ui.next-action": {
    "en": "Next action: {p0}",
    "zh-CN": "下一步操作：{p0}"
  },
  "ui.worker-wake-up-requested-prepare-or-analyze-work-while-experiments-c": {
    "en": "Worker wake-up requested · prepare or analyze work while experiments continue.",
    "zh-CN": "已请求唤醒执行智能体 · 实验继续运行时可进行准备或分析。"
  },
  "ui.worker-parked-until-feedback-campaign-clock-and-experiments-continue": {
    "en": "Worker parked until feedback · campaign clock and experiments continue.",
    "zh-CN": "执行智能体暂停等待反馈 · 研究计时和实验仍在继续。"
  },
  "ui.worker-wait-rejected": {
    "en": "Worker wait rejected: {p0}",
    "zh-CN": "执行智能体等待请求被拒绝：{p0}"
  },
  "ui.independent-report-assessment-requested": {
    "en": "Independent report assessment requested: {p0}",
    "zh-CN": "已请求独立评估报告：{p0}"
  },
  "ui.report-assessment-rejected": {
    "en": "Report assessment rejected: {p0}",
    "zh-CN": "报告评估请求被拒绝：{p0}"
  },
  "ui.storage-increase-rejected": {
    "en": "Storage increase rejected: {p0}",
    "zh-CN": "存储增加请求被拒绝：{p0}"
  },
  "ui.registration-tuning-rejected": {
    "en": "Registration tuning rejected: {p0}",
    "zh-CN": "注册参数调整被拒绝：{p0}"
  },
  "ui.stop-confirmed": {
    "en": "stop confirmed",
    "zh-CN": "已确认停止"
  },
  "ui.awaiting-confirmation": {
    "en": "awaiting confirmation",
    "zh-CN": "等待确认"
  },
  "ui.recorded-control-error": {
    "en": " · recorded control error: {p0}",
    "zh-CN": " · 已记录控制错误：{p0}"
  },
  "ui.stop-requested-partial-data-retained-when-available": {
    "en": "Stop requested: {p0} · {p1} · {p2}{p3} · partial data retained when available",
    "zh-CN": "已请求停止：{p0} · {p1} · {p2}{p3} · 尽可能保留部分数据"
  },
  "ui.worker-2": {
    "en": "Worker {p0}: {p1}",
    "zh-CN": "执行智能体{p0}：{p1}"
  },
  "ui.awaiting-worker-plan-or-challenge": {
    "en": "Awaiting worker plan or challenge",
    "zh-CN": "等待执行智能体计划或质疑"
  },
  "ui.no-replan-acknowledgement-required": {
    "en": "No replan acknowledgement required",
    "zh-CN": "无需确认重新规划"
  },
  "ui.solver-development": {
    "en": "Solver development",
    "zh-CN": "求解器开发"
  },
  "ui.experimental-solver-development-allowed-private-forks-protected-refe": {
    "en": "Experimental solver development allowed · private forks, protected reference installations, independent qualification.",
    "zh-CN": "允许实验性求解器开发 · 使用私有副本，保护参考安装，并独立验证适用性。"
  },
  "ui.experimental-solver-development-disabled-use-supplied-solver-impleme": {
    "en": "Experimental solver development disabled · use supplied solver implementations. Experiment and analysis scripting remains available.",
    "zh-CN": "未启用实验性求解器开发 · 使用提供的求解器实现，仍可编写实验和分析脚本。"
  },
  "ui.existing-study-source-permissions-follow-its-saved-operator-instruct": {
    "en": "Existing study · source permissions follow its saved operator instructions.",
    "zh-CN": "已有研究 · 源码权限遵循已保存的操作者指导。"
  },
  "ui.new-instrument": {
    "en": "new instrument",
    "zh-CN": "新工具"
  },
  "ui.change-parent": {
    "en": "{p0} change · parent {p1}",
    "zh-CN": "{p0}修改 · 上游 {p1}"
  },
  "ui.registered-instrument-development-provenance-not-declared": {
    "en": "Registered instrument · development provenance not declared",
    "zh-CN": "已注册工具 · 未声明开发来源"
  },
  "ui.preserved-assumptions": {
    "en": "Preserved assumptions: {p0}",
    "zh-CN": "保留的假设：{p0}"
  },
  "ui.validation-plan": {
    "en": "Validation plan: {p0}",
    "zh-CN": "验证计划：{p0}"
  },
  "ui.qualification-pending-no-reviewed-method-for-this-build": {
    "en": "Qualification pending · no reviewed method for this build.",
    "zh-CN": "等待适用性验证 · 此构建尚无通过评审的方法。"
  },
  "ui.approved-within-reviewed-scope": {
    "en": "approved within reviewed scope",
    "zh-CN": "在已评审范围内获批"
  },
  "ui.revision-required": {
    "en": "revision required",
    "zh-CN": "需要修订"
  },
  "ui.review-pending": {
    "en": "review pending",
    "zh-CN": "等待评审"
  },
  "ui.instrument-readiness": {
    "en": "Instrument readiness",
    "zh-CN": "工具就绪情况"
  },
  "ui.production-method": {
    "en": "Production method",
    "zh-CN": "正式方法"
  },
  "ui.view-registered-build-provenance": {
    "en": "View registered build provenance",
    "zh-CN": "查看已注册构建的来源"
  },
  "ui.scientific-coverage-cost": {
    "en": "Scientific coverage & cost",
    "zh-CN": "科学覆盖情况与成本"
  },
  "ui.target": {
    "en": "{p0}: {p1} {p2} / target {p3} {p4}",
    "zh-CN": "{p0}：{p1} {p2} / 目标 {p3} {p4}"
  },
  "ui.elapsed-estimated-additional": {
    "en": "Elapsed {p0} · estimated additional {p1} · {p2}",
    "zh-CN": "已耗时 {p0} · 预计还需 {p1} · {p2}"
  },
  "ui.awaiting-operational-timing-telemetry": {
    "en": "Awaiting operational timing telemetry",
    "zh-CN": "等待运行计时数据"
  },
  "ui.operator-control": {
    "en": "operator control",
    "zh-CN": "操作者控制"
  },
  "ui.stop-requested": {
    "en": "Stop requested: {p0}",
    "zh-CN": "已请求停止：{p0}"
  },
  "ui.measured-execution": {
    "en": "Measured execution: {p0} · {p1}",
    "zh-CN": "实测执行时间：{p0} · {p1}"
  },
  "ui.submission-to-result-includes-admission-transfer-and-result-collecti": {
    "en": "Submission to result: {p0} · includes admission, transfer and result collection.",
    "zh-CN": "从提交到结果：{p0} · 包含准入等待、传输和结果收集。"
  },
  "ui.inspect-the-receipt": {
    "en": "inspect the receipt",
    "zh-CN": "请检查回执"
  },
  "ui.recorded-value-integrity-failed": {
    "en": "Recorded value integrity failed: {p0}",
    "zh-CN": "记录值完整性检查失败：{p0}"
  },
  "ui.view-recorded-metric": {
    "en": "View recorded metric",
    "zh-CN": "查看记录的指标"
  },
  "ui.measured-execution-2": {
    "en": "Measured execution: {p0} · {p1} · {p2} · {p3}",
    "zh-CN": "实测执行：{p0} · {p1} · {p2} · {p3}"
  },
  "ui.view-execution-receipt": {
    "en": "View execution receipt",
    "zh-CN": "查看执行回执"
  },
  "ui.review-rationale": {
    "en": "Review rationale",
    "zh-CN": "评审理由"
  },
  "ui.open-artifact": {
    "en": "Open artifact",
    "zh-CN": "打开产物"
  },
  "ui.preview-artifact": {
    "en": "Preview artifact",
    "zh-CN": "预览产物"
  },
  "ui.launching": {
    "en": "Launching…",
    "zh-CN": "正在启动……"
  },
  "ui.launched": {
    "en": "Launched {p0}",
    "zh-CN": "已启动 {p0}"
  },
  "ui.launch-campaign": {
    "en": "Launch campaign",
    "zh-CN": "启动研究任务"
  },
  "ui.stop-the-verified-campaign-process-partial-workspace-files-remain-no": {
    "en": "Stop the verified campaign process? Partial workspace files remain non-evidentiary.",
    "zh-CN": "停止已验证的研究任务进程？工作区内的部分文件仍不能作为证据。"
  },
  "ui.glm-5-3-default": {
    "en": "glm-5.3 (default)",
    "zh-CN": "glm-5.3（默认）"
  },
  "ui.enter-the-backend-model-id": {
    "en": "Enter the backend model ID",
    "zh-CN": "输入后端模型 ID"
  },
  "ui.all": {
    "en": "All",
    "zh-CN": "全部"
  },
  "ui.code": {
    "en": "Code",
    "zh-CN": "代码"
  },
  "ui.papers": {
    "en": "Papers",
    "zh-CN": "论文"
  },
  "ui.slides": {
    "en": "Slides",
    "zh-CN": "演示文稿"
  },
  "ui.documents": {
    "en": "Documents",
    "zh-CN": "文档"
  },
  "ui.conversations": {
    "en": "Conversations",
    "zh-CN": "对话"
  },
  "ui.studies": {
    "en": "Studies",
    "zh-CN": "研究"
  },
  "ui.not-indexed-yet": {
    "en": "Not indexed yet",
    "zh-CN": "尚未建立索引"
  },
  "ui.completed-replies-from-your-conversations-in-this-workspace-search-a": {
    "en": "Completed replies from your conversations in this workspace. Search and refresh update the index.",
    "zh-CN": "此工作区对话中已完成的回复。搜索和刷新操作会更新索引。"
  },
  "ui.private-to-your-account-and-workspace": {
    "en": "Private to your account and workspace",
    "zh-CN": "仅当前账户和工作区可见"
  },
  "ui.folder-connected-indexing-has-started": {
    "en": "Folder connected. Indexing has started.",
    "zh-CN": "已连接文件夹，正在建立索引。"
  },
  "ui.checking-connected-sources-for-changes": {
    "en": "Checking connected sources for changes.",
    "zh-CN": "正在检查已连接来源的变化。"
  },
  "ui.mcp-configuration-copied": {
    "en": "MCP configuration copied.",
    "zh-CN": "已复制 MCP 配置。"
  },
  "ui.all-connected-sources": {
    "en": "All connected sources",
    "zh-CN": "所有已连接来源"
  },
  "ui.searching": {
    "en": "Searching…",
    "zh-CN": "正在搜索……"
  },
  "ui.library-is-updating": {
    "en": " · Library is updating",
    "zh-CN": " · 知识库正在更新"
  },
  "ui.matching-sources": {
    "en": "matching sources",
    "zh-CN": "个匹配来源"
  },
  "ui.recent-sources": {
    "en": "recent sources",
    "zh-CN": "个近期来源"
  },
  "ui.no-matching-sources-yet": {
    "en": "No matching sources yet",
    "zh-CN": "暂无匹配来源"
  },
  "ui.your-research-within-reach": {
    "en": "Your research, within reach",
    "zh-CN": "随时查阅你的研究资料"
  },
  "ui.try-a-distinctive-phrase-a-filename-or-fewer-words-check-sources-if-": {
    "en": "Try a distinctive phrase, a filename, or fewer words. Check Sources if a folder is still indexing.",
    "zh-CN": "请尝试更有辨识度的短语、文件名或减少关键词。如果文件夹仍在建立索引，可在来源页面查看进度。"
  },
  "ui.completed-replies-from-your-conversations-in-this-workspace-will-app": {
    "en": "Completed replies from your conversations in this workspace will appear here.",
    "zh-CN": "此工作区对话中已完成的回复会显示在这里。"
  },
  "ui.connect-a-research-folder-to-find-papers-code-and-notes-completed-co": {
    "en": "Connect a research folder to find papers, code and notes. Completed conversations and study reports will also appear here.",
    "zh-CN": "连接研究文件夹，即可查找论文、代码和笔记。已完成的对话及研究报告也会显示在这里。"
  },
  "ui.view-connected-sources": {
    "en": "View connected sources",
    "zh-CN": "查看已连接来源"
  },
  "ui.search-could-not-finish": {
    "en": "Search could not finish",
    "zh-CN": "搜索未能完成"
  },
  "ui.indexed": {
    "en": "{p0} · Indexed {p1}",
    "zh-CN": "{p0} · 索引时间 {p1}"
  },
  "ui.preserved-earlier-version": {
    "en": " · Preserved earlier version",
    "zh-CN": " · 保留的早期版本"
  },
  "ui.revision": {
    "en": "Revision {p0}{p1}",
    "zh-CN": "版本 {p0}{p1}"
  },
  "ui.discuss-this": {
    "en": "Discuss this",
    "zh-CN": "讨论此内容"
  },
  "ui.use-in-conversation": {
    "en": "Use in conversation",
    "zh-CN": "用于对话"
  },
  "ui.add-to": {
    "en": "Add to {p0}",
    "zh-CN": "添加到 {p0}"
  },
  "ui.download-original": {
    "en": "Download original",
    "zh-CN": "下载原文件"
  },
  "ui.open-conversation": {
    "en": "Open conversation ↗",
    "zh-CN": "打开对话 ↗"
  },
  "ui.copy-citation": {
    "en": "Copy citation",
    "zh-CN": "复制引用"
  },
  "ui.citation-copied": {
    "en": "Citation copied.",
    "zh-CN": "已复制引用。"
  },
  "ui.previous": {
    "en": "← Previous",
    "zh-CN": "← 上一节"
  },
  "ui.next-2": {
    "en": "Next →",
    "zh-CN": "下一节 →"
  },
  "ui.section-of": {
    "en": "Section {p0} of {p1}",
    "zh-CN": "第 {p0} 节，共 {p1} 节"
  },
  "ui.this-is-a-retained-indexed-passage-the-current-source-has-changed-wa": {
    "en": "This is a retained indexed passage. The current source has changed, was removed, or is unavailable.",
    "zh-CN": "这是保留的索引片段。当前来源已更改、移除或无法访问。"
  },
  "ui.available-within-this-workspace": {
    "en": "Available within this workspace",
    "zh-CN": "在此工作区内可用"
  },
  "ui.disabled": {
    "en": "Disabled",
    "zh-CN": "已停用"
  },
  "ui.excluded-paths": {
    "en": "Excluded paths: {p0}",
    "zh-CN": "排除路径：{p0}"
  },
  "ui.checked": {
    "en": "Checked {p0}",
    "zh-CN": "检查时间 {p0}"
  },
  "ui.indexed-items": {
    "en": "{p0} indexed items · {p1}",
    "zh-CN": "{p0} 个索引条目 · {p1}"
  },
  "ui.disable": {
    "en": "Disable",
    "zh-CN": "停用"
  },
  "ui.enable": {
    "en": "Enable",
    "zh-CN": "启用"
  },
  "ui.disconnect": {
    "en": "Disconnect",
    "zh-CN": "断开连接"
  },
  "ui.folder-disconnected-from-this-workspace-original-files-are-unchanged": {
    "en": "Folder disconnected from this workspace. Original files are unchanged.",
    "zh-CN": "已从此工作区断开文件夹连接，原文件保持不变。"
  },
  "ui.indexing-notes": {
    "en": "{p0}{p1} indexing notes",
    "zh-CN": "{p0}{p1} 条索引说明"
  },
  "ui.knowledge": {
    "en": "▤ Knowledge · {p0} {p1}",
    "zh-CN": "▤ 知识库 · {p0} {p1}"
  },
  "ui.remove-reference": {
    "en": "Remove reference {p0}",
    "zh-CN": "移除引用 {p0}"
  },
  "ui.source-attached-edit-your-question-and-send-when-ready": {
    "en": "Source attached. Edit your question and send when ready.",
    "zh-CN": "已附加来源。请编辑问题，准备好后发送。"
  },
  "ui.sources-used": {
    "en": "Sources used · {p0}",
    "zh-CN": "使用的来源 · {p0}"
  },
  "ui.copy": {
    "en": "Copy",
    "zh-CN": "复制"
  },
  "ui.copy-code": {
    "en": "Copy code",
    "zh-CN": "复制代码"
  },
  "ui.copied": {
    "en": "Copied",
    "zh-CN": "已复制"
  },
  "ui.press-ctrl-c-to-copy": {
    "en": "Press Ctrl+C to copy",
    "zh-CN": "按 Ctrl+C 复制"
  },
  "ui.show-more": {
    "en": "Show {p0} more {p1}",
    "zh-CN": "再显示 {p0} 个{p1}"
  },
  "ui.changed-from-the-copied-input": {
    "en": "Changed from the copied input",
    "zh-CN": "与复制的输入不同"
  },
  "ui.conversation-files-shared": {
    "en": "Conversation files (shared)",
    "zh-CN": "对话文件（共享）"
  },
  "ui.command-outputs": {
    "en": "Command outputs",
    "zh-CN": "命令输出"
  },
  "ui.run-outputs": {
    "en": "Run outputs",
    "zh-CN": "运行输出"
  },
  "ui.this-job-used-the-shared-project-folder-these-files-are-not-specific": {
    "en": "This job used the shared project folder. These files are not specific to this run.",
    "zh-CN": "此任务使用共享项目文件夹。这些文件并非本次运行独有。"
  },
  "ui.files-retained-from-this-command-s-isolated-workspace": {
    "en": "Files retained from this command’s isolated workspace.",
    "zh-CN": "从此命令的隔离工作区保留的文件。"
  },
  "ui.files-created-or-changed-in-this-simulation-s-workspace": {
    "en": "Files created or changed in this simulation’s workspace.",
    "zh-CN": "此仿真工作区中新建或修改的文件。"
  },
  "ui.no-project-files-listed": {
    "en": "No project files listed.",
    "zh-CN": "暂无项目文件。"
  },
  "ui.no-run-outputs-saved-yet": {
    "en": "No run outputs saved yet.",
    "zh-CN": "尚未保存运行输出。"
  },
  "ui.complete-console-logs": {
    "en": "Complete console logs",
    "zh-CN": "完整控制台日志"
  },
  "ui.copied-inputs": {
    "en": "Copied inputs ({p0})",
    "zh-CN": "复制的输入（{p0}）"
  },
  "ui.conversation-files-copied-when-this-run-started-they-can-include-rep": {
    "en": "Conversation files copied when this run started. They can include reports and results from other simulations.",
    "zh-CN": "本次运行开始时复制的对话文件，可能包含其他仿真的报告和结果。"
  },
  "ui.cli-managed-command": {
    "en": "CLI-managed command",
    "zh-CN": "CLI 管理的命令"
  },
  "ui.interactive-exploration": {
    "en": "Interactive exploration",
    "zh-CN": "交互式探索"
  },
  "ui.command-location": {
    "en": "Command & location",
    "zh-CN": "命令与位置"
  },
  "ui.conversation-files": {
    "en": "Conversation files",
    "zh-CN": "对话文件"
  },
  "ui.live-console": {
    "en": "LIVE CONSOLE",
    "zh-CN": "实时控制台"
  },
  "ui.stop-command": {
    "en": "Stop command",
    "zh-CN": "停止命令"
  },
  "ui.stop-run": {
    "en": "Stop run",
    "zh-CN": "停止运行"
  },
  "ui.move-to-simulations": {
    "en": "Move to Simulations",
    "zh-CN": "移至仿真"
  },
  "ui.move-to-commands": {
    "en": "Move to Commands",
    "zh-CN": "移至命令"
  },
  "ui.command-console": {
    "en": "Command console",
    "zh-CN": "命令控制台"
  },
  "ui.simulation-console": {
    "en": "Simulation console",
    "zh-CN": "仿真控制台"
  },
  "ui.s-elapsed": {
    "en": "{p0}s elapsed",
    "zh-CN": "已运行 {p0} 秒"
  },
  "ui.conversation": {
    "en": "Conversation",
    "zh-CN": "对话"
  },
  "ui.study": {
    "en": "Study",
    "zh-CN": "研究"
  },
  "ui.standalone-study": {
    "en": "Standalone study",
    "zh-CN": "独立研究"
  },
  "ui.available-after-a-study-is-started": {
    "en": "Available after a study is started",
    "zh-CN": "研究启动后可用"
  },
  "ui.simjecture-research-workspace": {
    "en": "Simjecture · Research workspace",
    "zh-CN": "Simjecture · 科研工作区"
  },
  "ui.skip-to-main-content": {
    "en": "Skip to main content",
    "zh-CN": "跳到主要内容"
  },
  "ui.workspace-and-account": {
    "en": "Workspace and account",
    "zh-CN": "工作区与账户"
  },
  "ui.toggle-conversations": {
    "en": "Toggle conversations",
    "zh-CN": "展开或收起对话"
  },
  "ui.new-conversation": {
    "en": "New conversation",
    "zh-CN": "新建对话"
  },
  "ui.experiment-monitor": {
    "en": "Experiment monitor",
    "zh-CN": "实验监控"
  },
  "ui.loading-workspace": {
    "en": "Loading workspace",
    "zh-CN": "正在加载工作区"
  },
  "ui.your-account": {
    "en": "Your account",
    "zh-CN": "你的账户"
  },
  "ui.loading-workspace-2": {
    "en": "Loading workspace…",
    "zh-CN": "正在加载工作区……"
  },
  "ui.dark-mode-2": {
    "en": "Dark mode",
    "zh-CN": "深色模式"
  },
  "ui.your-workspaces": {
    "en": "Your workspaces",
    "zh-CN": "你的工作区"
  },
  "ui.close-workspaces": {
    "en": "Close workspaces",
    "zh-CN": "关闭工作区列表"
  },
  "ui.new-workspace": {
    "en": "New workspace",
    "zh-CN": "新建工作区"
  },
  "ui.lab-or-team-name": {
    "en": "Lab or team name",
    "zh-CN": "实验室或团队名称"
  },
  "ui.create": {
    "en": "Create",
    "zh-CN": "创建"
  },
  "ui.close-project-settings": {
    "en": "Close project settings",
    "zh-CN": "关闭项目设置"
  },
  "ui.name": {
    "en": "Name",
    "zh-CN": "名称"
  },
  "ui.description": {
    "en": "Description",
    "zh-CN": "描述"
  },
  "ui.shared-instructions": {
    "en": "Shared instructions",
    "zh-CN": "共享指导"
  },
  "ui.what-should-an-agent-know-when-working-on-this-project": {
    "en": "What should an agent know when working on this project?",
    "zh-CN": "智能体开展此项目时需要了解哪些信息？"
  },
  "ui.save-project": {
    "en": "Save project",
    "zh-CN": "保存项目"
  },
  "ui.simjecture-research-workspace-2": {
    "en": "Simjecture research workspace",
    "zh-CN": "Simjecture 科研工作区"
  },
  "ui.research-workspace": {
    "en": "Research workspace",
    "zh-CN": "科研工作区"
  },
  "ui.workspace-navigation": {
    "en": "Workspace navigation",
    "zh-CN": "工作区导航"
  },
  "ui.overview": {
    "en": "Overview",
    "zh-CN": "概览"
  },
  "ui.knowledge-2": {
    "en": "Knowledge",
    "zh-CN": "知识库"
  },
  "ui.resources": {
    "en": "Resources",
    "zh-CN": "资源"
  },
  "ui.research-tools": {
    "en": "Research tools",
    "zh-CN": "科研工具"
  },
  "ui.benchmarks": {
    "en": "Benchmarks",
    "zh-CN": "基准测试"
  },
  "ui.machines": {
    "en": "Machines",
    "zh-CN": "计算设备"
  },
  "ui.projects": {
    "en": "Projects",
    "zh-CN": "项目"
  },
  "ui.projects-2": {
    "en": "PROJECTS",
    "zh-CN": "项目"
  },
  "ui.conversations-2": {
    "en": "CONVERSATIONS",
    "zh-CN": "对话"
  },
  "ui.simulations": {
    "en": "SIMULATIONS",
    "zh-CN": "仿真"
  },
  "ui.interface-language": {
    "en": "Interface language",
    "zh-CN": "界面语言"
  },
  "ui.checking-execution": {
    "en": "Checking execution…",
    "zh-CN": "正在检查执行环境……"
  },
  "ui.dismiss-execution-warning": {
    "en": "Dismiss execution warning",
    "zh-CN": "关闭执行警告"
  },
  "ui.technical-details": {
    "en": "Technical details",
    "zh-CN": "技术详情"
  },
  "ui.resize-left-sidebar": {
    "en": "Resize left sidebar",
    "zh-CN": "调整左侧栏宽度"
  },
  "ui.collapse-left-sidebar": {
    "en": "Collapse left sidebar",
    "zh-CN": "收起左侧栏"
  },
  "ui.collapse-right-sidebar": {
    "en": "Collapse right sidebar",
    "zh-CN": "收起右侧栏"
  },
  "ui.your-research-library": {
    "en": "YOUR RESEARCH LIBRARY",
    "zh-CN": "你的科研资料库"
  },
  "ui.connect-folder": {
    "en": "＋ Connect folder",
    "zh-CN": "＋ 连接文件夹"
  },
  "ui.knowledge-sections": {
    "en": "Knowledge sections",
    "zh-CN": "知识库分区"
  },
  "ui.search": {
    "en": "Search",
    "zh-CN": "搜索"
  },
  "ui.sources": {
    "en": "Sources",
    "zh-CN": "资料源"
  },
  "ui.agent-access": {
    "en": "Agent access",
    "zh-CN": "智能体访问"
  },
  "ui.search-your-research": {
    "en": "Search your research",
    "zh-CN": "搜索科研资料"
  },
  "ui.search-a-method-paper-example-or-past-decision": {
    "en": "Search a method, paper, example or past decision…",
    "zh-CN": "搜索方法、论文、示例或以往决策……"
  },
  "ui.filter-by-content-type": {
    "en": "Filter by content type",
    "zh-CN": "按内容类型筛选"
  },
  "ui.filter-by-source": {
    "en": "Filter by source",
    "zh-CN": "按资料源筛选"
  },
  "ui.loading-your-library": {
    "en": "Loading your library…",
    "zh-CN": "正在加载资料库……"
  },
  "ui.files-stay-on-your-machine": {
    "en": "Files stay on your machine",
    "zh-CN": "文件保留在你的机器上"
  },
  "ui.source-preview": {
    "en": "Source preview",
    "zh-CN": "资料预览"
  },
  "ui.follow-an-idea-to-its-source": {
    "en": "Follow an idea to its source",
    "zh-CN": "追溯想法的资料来源"
  },
  "ui.connected-sources": {
    "en": "Connected sources",
    "zh-CN": "已连接的资料源"
  },
  "ui.refresh-now": {
    "en": "Refresh now",
    "zh-CN": "立即刷新"
  },
  "ui.one-library-for-your-agents": {
    "en": "One library for your agents",
    "zh-CN": "供所有智能体共用的资料库"
  },
  "ui.mcp-configuration": {
    "en": "MCP configuration",
    "zh-CN": "MCP 配置"
  },
  "ui.copy-configuration": {
    "en": "Copy configuration",
    "zh-CN": "复制配置"
  },
  "ui.search-from-a-terminal": {
    "en": "Search from a terminal",
    "zh-CN": "从终端搜索"
  },
  "ui.project": {
    "en": "PROJECT",
    "zh-CN": "项目"
  },
  "ui.new-conversation-2": {
    "en": "＋ New conversation",
    "zh-CN": "＋ 新建对话"
  },
  "ui.shared-context": {
    "en": "Shared context",
    "zh-CN": "共享上下文"
  },
  "ui.add-files": {
    "en": "Add files",
    "zh-CN": "添加文件"
  },
  "ui.your-research-request": {
    "en": "Your research request",
    "zh-CN": "你的研究请求"
  },
  "ui.choose-agent-and-model": {
    "en": "Choose agent and model",
    "zh-CN": "选择智能体和模型"
  },
  "ui.send-request": {
    "en": "Send request",
    "zh-CN": "发送请求"
  },
  "ui.knowledge-sources": {
    "en": "▤ Knowledge sources",
    "zh-CN": "▤ 知识库资料源"
  },
  "ui.interactive": {
    "en": "Interactive",
    "zh-CN": "交互探索"
  },
  "ui.best-for": {
    "en": "Best for",
    "zh-CN": "适用场景"
  },
  "ui.interactive-examples": {
    "en": "Interactive examples",
    "zh-CN": "交互探索示例"
  },
  "ui.simulate-a-double-pendulum": {
    "en": "Simulate a double pendulum",
    "zh-CN": "仿真双摆运动"
  },
  "ui.plot-both-paths-and-check-energy-drift-python": {
    "en": "Plot both paths and check energy drift · Python",
    "zh-CN": "绘制两条轨迹并检查能量漂移 · Python"
  },
  "ui.autonomous-study-2": {
    "en": "Autonomous study",
    "zh-CN": "自主研究"
  },
  "ui.autonomous-study-examples": {
    "en": "Autonomous study examples",
    "zh-CN": "自主研究示例"
  },
  "ui.does-a-pendulum-keep-the-same-period": {
    "en": "Does a pendulum keep the same period?",
    "zh-CN": "单摆的周期始终相同吗？"
  },
  "ui.your-agent-drafts-a-10-minute-study-for-you-to-review-python": {
    "en": "Your agent drafts a 10-minute study for you to review · Python",
    "zh-CN": "智能体起草一项 10 分钟研究供你审阅 · Python"
  },
  "ui.your-compute": {
    "en": "YOUR COMPUTE",
    "zh-CN": "你的计算资源"
  },
  "ui.add-machine": {
    "en": "Add machine",
    "zh-CN": "添加计算设备"
  },
  "ui.refresh-machine-availability": {
    "en": "Refresh machine availability",
    "zh-CN": "刷新计算设备可用状态"
  },
  "ui.checked-every-30-seconds": {
    "en": "Checked every 30 seconds",
    "zh-CN": "每 30 秒检查一次"
  },
  "ui.add-this-computer": {
    "en": "Add this computer",
    "zh-CN": "添加本机"
  },
  "ui.worker-jobs": {
    "en": "Worker jobs",
    "zh-CN": "执行节点任务"
  },
  "ui.close-jobs": {
    "en": "Close jobs",
    "zh-CN": "关闭任务列表"
  },
  "ui.detailed-receipts": {
    "en": "Detailed receipts",
    "zh-CN": "详细执行凭据"
  },
  "ui.ssh-connection": {
    "en": "SSH CONNECTION",
    "zh-CN": "SSH 连接"
  },
  "ui.close-machine-settings": {
    "en": "Close machine settings",
    "zh-CN": "关闭计算设备设置"
  },
  "ui.ssh-address": {
    "en": "SSH address",
    "zh-CN": "SSH 地址"
  },
  "ui.password": {
    "en": "Password",
    "zh-CN": "密码"
  },
  "ui.optional": {
    "en": "Optional",
    "zh-CN": "可选"
  },
  "ui.use-the-host-name": {
    "en": "Use the host name",
    "zh-CN": "使用主机名"
  },
  "ui.display-name": {
    "en": "Display name",
    "zh-CN": "显示名称"
  },
  "ui.generated-automatically": {
    "en": "Generated automatically",
    "zh-CN": "自动生成"
  },
  "ui.machine-id": {
    "en": "Machine ID",
    "zh-CN": "设备 ID"
  },
  "ui.this-computer": {
    "en": "This computer",
    "zh-CN": "本机"
  },
  "ui.connection": {
    "en": "Connection",
    "zh-CN": "连接"
  },
  "ui.choose-a-persistent-directory-automatically": {
    "en": "Choose a persistent directory automatically",
    "zh-CN": "自动选择持久目录"
  },
  "ui.worker-directory": {
    "en": "Worker directory",
    "zh-CN": "执行节点目录"
  },
  "ui.detect-automatically": {
    "en": "Detect automatically",
    "zh-CN": "自动检测"
  },
  "ui.cpu-budget": {
    "en": "CPU budget",
    "zh-CN": "CPU 配额"
  },
  "ui.ram-budget-mib": {
    "en": "RAM budget (MiB)",
    "zh-CN": "内存配额（MiB）"
  },
  "ui.detect-automatically-type-none-for-cpu-only": {
    "en": "Detect automatically; type none for CPU only",
    "zh-CN": "自动检测；输入 none 以仅使用 CPU"
  },
  "ui.gpu-ids": {
    "en": "GPU IDs",
    "zh-CN": "GPU ID"
  },
  "ui.choose-automatically": {
    "en": "Choose automatically",
    "zh-CN": "自动选择"
  },
  "ui.concurrent-jobs": {
    "en": "Concurrent jobs",
    "zh-CN": "并发任务数"
  },
  "ui.linux-sandbox": {
    "en": "Linux sandbox",
    "zh-CN": "Linux 沙箱"
  },
  "ui.cooperative-restricted-container": {
    "en": "Cooperative · restricted container",
    "zh-CN": "协作执行 · 受限容器"
  },
  "ui.native-process-trusted-host": {
    "en": "Native process · trusted host",
    "zh-CN": "原生进程 · 可信主机"
  },
  "ui.experiment-environment": {
    "en": "Experiment environment",
    "zh-CN": "实验执行环境"
  },
  "ui.optional-your-agent-can-prepare-scientific-tools-later": {
    "en": "Optional. Your agent can prepare scientific tools later.",
    "zh-CN": "可选，智能体可稍后准备科研工具。"
  },
  "ui.instrument-descriptor-directories": {
    "en": "Instrument descriptor directories",
    "zh-CN": "工具描述文件目录"
  },
  "ui.use-your-ssh-agent": {
    "en": "Use your SSH agent",
    "zh-CN": "使用 SSH agent"
  },
  "ui.ssh-private-key-path": {
    "en": "SSH private key path",
    "zh-CN": "SSH 私钥路径"
  },
  "ui.managed-automatically": {
    "en": "Managed automatically",
    "zh-CN": "自动管理"
  },
  "ui.known-hosts-file": {
    "en": "Known hosts file",
    "zh-CN": "已知主机文件"
  },
  "ui.choose-an-unprivileged-account": {
    "en": "Choose an unprivileged account",
    "zh-CN": "选择非特权账户"
  },
  "ui.run-worker-as-user": {
    "en": "Run worker as user",
    "zh-CN": "执行节点运行账户"
  },
  "ui.python-executable": {
    "en": "Python executable",
    "zh-CN": "Python 可执行文件"
  },
  "ui.your-agent-your-machine": {
    "en": "YOUR AGENT, YOUR MACHINE",
    "zh-CN": "你的智能体，你的计算设备"
  },
  "ui.api-connections-if-you-need-them": {
    "en": "API connections, if you need them.",
    "zh-CN": "按需配置 API 连接。"
  },
  "ui.optional-compatible-api": {
    "en": "OPTIONAL · COMPATIBLE API",
    "zh-CN": "可选 · 兼容 API"
  },
  "ui.provider": {
    "en": "Provider",
    "zh-CN": "服务提供方"
  },
  "ui.custom-openai-compatible": {
    "en": "Custom / OpenAI-compatible",
    "zh-CN": "自定义 / OpenAI 兼容"
  },
  "ui.local-model-server": {
    "en": "Local model server",
    "zh-CN": "本地模型服务"
  },
  "ui.api-base-url": {
    "en": "API base URL",
    "zh-CN": "API 基础地址"
  },
  "ui.api-key": {
    "en": "API key",
    "zh-CN": "API 密钥"
  },
  "ui.enter-a-key-stored-only-on-this-machine": {
    "en": "Enter a key; stored only on this machine",
    "zh-CN": "输入密钥；仅保存在本机"
  },
  "ui.save-api-connection": {
    "en": "Save API connection",
    "zh-CN": "保存 API 连接"
  },
  "ui.where-your-work-runs": {
    "en": "Where your work runs",
    "zh-CN": "研究在哪里运行"
  },
  "ui.check-experiment-readiness": {
    "en": "Check experiment readiness",
    "zh-CN": "检查实验执行就绪状态"
  },
  "ui.already-using-a-cli": {
    "en": "Already using a CLI?",
    "zh-CN": "已经在使用 CLI？"
  },
  "ui.simjecture-benchmark-results": {
    "en": "SIMJECTURE BENCHMARK RESULTS",
    "zh-CN": "Simjecture 基准测试结果"
  },
  "ui.model-leaderboard": {
    "en": "Model leaderboard",
    "zh-CN": "模型排行榜"
  },
  "ui.test-a-model": {
    "en": "＋ Test a model",
    "zh-CN": "＋ 测试模型"
  },
  "ui.download-results": {
    "en": "Download results",
    "zh-CN": "下载结果"
  },
  "ui.results-source": {
    "en": "Results source",
    "zh-CN": "结果来源"
  },
  "ui.official-simjecture-results": {
    "en": "Official Simjecture results",
    "zh-CN": "Simjecture 官方结果"
  },
  "ui.results": {
    "en": "Results",
    "zh-CN": "结果"
  },
  "ui.task-leaderboard": {
    "en": "Task leaderboard",
    "zh-CN": "任务排行榜"
  },
  "ui.benchmark-task": {
    "en": "Benchmark task",
    "zh-CN": "基准测试任务"
  },
  "ui.comparison-group": {
    "en": "Comparison group",
    "zh-CN": "对比组"
  },
  "ui.model-or-coding-agent": {
    "en": "Model or coding agent",
    "zh-CN": "模型或编程智能体"
  },
  "ui.find-a-model": {
    "en": "Find a model",
    "zh-CN": "查找模型"
  },
  "ui.rank-by": {
    "en": "Rank by",
    "zh-CN": "排序依据"
  },
  "ui.completion-rate": {
    "en": "Completion rate",
    "zh-CN": "完成率"
  },
  "ui.fastest-completion": {
    "en": "Fastest completion",
    "zh-CN": "最快完成"
  },
  "ui.lowest-cost-per-task": {
    "en": "Lowest cost per task",
    "zh-CN": "单项任务最低费用"
  },
  "ui.filter-reasoning-effort": {
    "en": "Filter reasoning effort",
    "zh-CN": "筛选推理强度"
  },
  "ui.all-efforts": {
    "en": "All efforts",
    "zh-CN": "所有推理强度"
  },
  "ui.low": {
    "en": "Low",
    "zh-CN": "低"
  },
  "ui.medium": {
    "en": "Medium",
    "zh-CN": "中"
  },
  "ui.high": {
    "en": "High",
    "zh-CN": "高"
  },
  "ui.xhigh": {
    "en": "Xhigh",
    "zh-CN": "超高"
  },
  "ui.max": {
    "en": "Max",
    "zh-CN": "最大"
  },
  "ui.ultra": {
    "en": "Ultra",
    "zh-CN": "极高"
  },
  "ui.cost-basis": {
    "en": "Cost basis",
    "zh-CN": "费用计算依据"
  },
  "ui.api-equivalent-cache-adjusted": {
    "en": "API equivalent · cache adjusted",
    "zh-CN": "API 等效费用 · 已调整缓存折扣"
  },
  "ui.api-equivalent-no-cache-discounts": {
    "en": "API equivalent · no cache discounts",
    "zh-CN": "API 等效费用 · 不计缓存折扣"
  },
  "ui.finish-time-ranking": {
    "en": "Finish time ranking",
    "zh-CN": "完成时间排名"
  },
  "ui.cost-ranking": {
    "en": "Cost ranking",
    "zh-CN": "费用排名"
  },
  "ui.upper-left-is-better-dashed-lines-connect-the-same-model-s-reasoning": {
    "en": "Upper left is better. Dashed lines connect the same model's reasoning efforts.",
    "zh-CN": "越靠左上越好。虚线连接同一模型的不同推理强度。"
  },
  "ui.methodology": {
    "en": "Methodology ↗",
    "zh-CN": "测试方法 ↗"
  },
  "ui.published-api-tariffs": {
    "en": "Published API tariffs",
    "zh-CN": "公开 API 价格"
  },
  "ui.import-grades": {
    "en": "Import grades",
    "zh-CN": "导入评分"
  },
  "ui.download-raw-grades": {
    "en": "Download raw grades",
    "zh-CN": "下载原始评分"
  },
  "ui.prepare-or-grade-a-task": {
    "en": "Prepare or grade a task",
    "zh-CN": "准备任务或评分"
  },
  "ui.your-benchmark-conversations": {
    "en": "Your benchmark conversations",
    "zh-CN": "你的基准测试对话"
  },
  "ui.latest-numerical-grade": {
    "en": "Latest numerical grade",
    "zh-CN": "最新数值评分"
  },
  "ui.explore-your-workbench": {
    "en": "EXPLORE YOUR WORKBENCH",
    "zh-CN": "探索你的科研工作台"
  },
  "ui.connect-existing-tool": {
    "en": "＋ Connect existing tool",
    "zh-CN": "＋ 连接已有工具"
  },
  "ui.search-tools-physics-or-capabilities": {
    "en": "Search tools, physics, or capabilities…",
    "zh-CN": "搜索工具、物理领域或功能……"
  },
  "ui.search-research-tools": {
    "en": "Search research tools",
    "zh-CN": "搜索科研工具"
  },
  "ui.filter-tools-by-category": {
    "en": "Filter tools by category",
    "zh-CN": "按类别筛选工具"
  },
  "ui.filter-tools-by-availability": {
    "en": "Filter tools by availability",
    "zh-CN": "按可用状态筛选工具"
  },
  "ui.all-tools": {
    "en": "All tools",
    "zh-CN": "所有工具"
  },
  "ui.installed": {
    "en": "Installed",
    "zh-CN": "已安装"
  },
  "ui.available-to-add": {
    "en": "Available to add",
    "zh-CN": "可添加"
  },
  "ui.setup-activity": {
    "en": "Setup activity",
    "zh-CN": "配置进度"
  },
  "ui.discover-more": {
    "en": "Discover more",
    "zh-CN": "发现更多工具"
  },
  "ui.no-matching-tools": {
    "en": "No matching tools",
    "zh-CN": "没有匹配的工具"
  },
  "ui.clear-filters": {
    "en": "Clear filters",
    "zh-CN": "清除筛选"
  },
  "ui.research-tool": {
    "en": "RESEARCH TOOL",
    "zh-CN": "科研工具"
  },
  "ui.tool-details": {
    "en": "Tool details",
    "zh-CN": "工具详情"
  },
  "ui.close-tool-details": {
    "en": "Close tool details",
    "zh-CN": "关闭工具详情"
  },
  "ui.check-readiness": {
    "en": "Check readiness",
    "zh-CN": "检查就绪状态"
  },
  "ui.connect-a-research-tool": {
    "en": "Connect a research tool",
    "zh-CN": "连接科研工具"
  },
  "ui.existing-installation": {
    "en": "EXISTING INSTALLATION",
    "zh-CN": "已有安装"
  },
  "ui.close-tool-registration": {
    "en": "Close tool registration",
    "zh-CN": "关闭工具注册"
  },
  "ui.my-research-solver": {
    "en": "My research solver",
    "zh-CN": "我的科研求解器"
  },
  "ui.capability-directory": {
    "en": "Capability directory",
    "zh-CN": "capability 目录"
  },
  "ui.register-tool": {
    "en": "Register tool",
    "zh-CN": "注册工具"
  },
  "ui.conversation-project": {
    "en": "Conversation project",
    "zh-CN": "对话所属项目"
  },
  "ui.project-2": {
    "en": "Project",
    "zh-CN": "项目"
  },
  "ui.research-mode": {
    "en": "Research mode",
    "zh-CN": "研究模式"
  },
  "ui.research-navigation": {
    "en": "Research navigation",
    "zh-CN": "研究导航"
  },
  "ui.continuing-an-earlier-investigation": {
    "en": "Continuing an earlier investigation ↗",
    "zh-CN": "延续先前的研究 ↗"
  },
  "ui.message-your-research-agent": {
    "en": "Message your research agent",
    "zh-CN": "向科研智能体发送消息"
  },
  "ui.dismiss-session-warning": {
    "en": "Dismiss session warning",
    "zh-CN": "关闭会话提示"
  },
  "ui.attach-files": {
    "en": "Attach files",
    "zh-CN": "附加文件"
  },
  "ui.conversation-agent": {
    "en": "Conversation agent",
    "zh-CN": "对话智能体"
  },
  "ui.model-id": {
    "en": "Model ID",
    "zh-CN": "模型 ID"
  },
  "ui.exact-model-id": {
    "en": "Exact model ID",
    "zh-CN": "准确的模型 ID"
  },
  "ui.reasoning-effort": {
    "en": "Reasoning effort",
    "zh-CN": "推理强度"
  },
  "ui.default": {
    "en": "Default",
    "zh-CN": "默认"
  },
  "ui.extra-high": {
    "en": "Extra high",
    "zh-CN": "超高"
  },
  "ui.refresh-model-choices": {
    "en": "Refresh model choices",
    "zh-CN": "刷新模型选项"
  },
  "ui.refresh": {
    "en": "↻ Refresh",
    "zh-CN": "↻ 刷新"
  },
  "ui.stop": {
    "en": "Stop",
    "zh-CN": "停止"
  },
  "ui.send-message": {
    "en": "Send message",
    "zh-CN": "发送消息"
  },
  "ui.got-it": {
    "en": "Got it",
    "zh-CN": "知道了"
  },
  "ui.discuss": {
    "en": "Discuss",
    "zh-CN": "讨论"
  },
  "ui.review-the-brief": {
    "en": "Review the brief",
    "zh-CN": "审阅简报"
  },
  "ui.launch": {
    "en": "Launch",
    "zh-CN": "启动"
  },
  "ui.read-the-report": {
    "en": "Read the report",
    "zh-CN": "阅读报告"
  },
  "ui.prepare-another-study": {
    "en": "Prepare another study",
    "zh-CN": "准备另一项研究"
  },
  "ui.step-1-of-2": {
    "en": "STEP 1 OF 2",
    "zh-CN": "第 1 步，共 2 步"
  },
  "ui.grill-me": {
    "en": "Grill me",
    "zh-CN": "逐项提问"
  },
  "ui.draft-from-this-conversation": {
    "en": "Draft from this conversation",
    "zh-CN": "根据当前对话起草"
  },
  "ui.discuss-or-refine": {
    "en": "Discuss or refine",
    "zh-CN": "讨论或完善"
  },
  "ui.start-research": {
    "en": "Start research ↗",
    "zh-CN": "启动研究 ↗"
  },
  "ui.review-or-edit-the-study-details": {
    "en": "Review or edit the study details",
    "zh-CN": "审阅或编辑研究详情"
  },
  "ui.study-brief": {
    "en": "Study brief",
    "zh-CN": "研究简报"
  },
  "ui.time-budget-hours": {
    "en": "Time budget (hours)",
    "zh-CN": "时间预算（小时）"
  },
  "ui.allow-experimental-solver-development": {
    "en": "Allow experimental solver development",
    "zh-CN": "允许实验性求解器开发"
  },
  "ui.execution-machines": {
    "en": "Execution machines",
    "zh-CN": "执行设备"
  },
  "ui.execution-settings": {
    "en": "Execution settings",
    "zh-CN": "执行设置"
  },
  "ui.tool-access": {
    "en": "Tool access",
    "zh-CN": "工具访问权限"
  },
  "ui.research-director-may-stop-a-costly-experiment-and-change-the-plan": {
    "en": "Research director · may stop a costly experiment and change the plan",
    "zh-CN": "研究主管 · 可停止高成本实验并调整计划"
  },
  "ui.reviewer-and-director-agent": {
    "en": "Reviewer and director agent",
    "zh-CN": "评审与研究主管使用的智能体"
  },
  "ui.same-as-conversation-agent": {
    "en": "Same as conversation agent",
    "zh-CN": "与对话智能体相同"
  },
  "ui.reviewer-and-director-model": {
    "en": "Reviewer and director model",
    "zh-CN": "评审与研究主管使用的模型"
  },
  "ui.reviewer-and-director-reasoning": {
    "en": "Reviewer and director reasoning",
    "zh-CN": "评审与研究主管的推理强度"
  },
  "ui.use-agent-setting": {
    "en": "Use agent setting",
    "zh-CN": "使用智能体设置"
  },
  "ui.linux-sandbox-recommended": {
    "en": "Linux sandbox (recommended)",
    "zh-CN": "Linux 沙箱（推荐）"
  },
  "ui.cooperative-container-execution": {
    "en": "Cooperative container execution",
    "zh-CN": "容器协作执行"
  },
  "ui.native-process-trusted-host-2": {
    "en": "Native process — trusted host",
    "zh-CN": "原生进程 — 可信主机"
  },
  "ui.save-brief": {
    "en": "Save brief",
    "zh-CN": "保存简报"
  },
  "ui.start-autonomous-study": {
    "en": "Start autonomous study ↗",
    "zh-CN": "启动自主研究 ↗"
  },
  "ui.simulations-2": {
    "en": "Simulations",
    "zh-CN": "仿真"
  },
  "ui.commands": {
    "en": "Commands",
    "zh-CN": "命令"
  },
  "ui.files": {
    "en": "Files",
    "zh-CN": "文件"
  },
  "ui.simulation-history": {
    "en": "Simulation history",
    "zh-CN": "仿真历史"
  },
  "ui.selected-simulation": {
    "en": "Selected simulation",
    "zh-CN": "已选仿真"
  },
  "ui.command-history": {
    "en": "Command history",
    "zh-CN": "命令历史"
  },
  "ui.selected-command": {
    "en": "Selected command",
    "zh-CN": "已选命令"
  },
  "ui.folder-on-this-computer": {
    "en": "Folder on this computer",
    "zh-CN": "本机上的文件夹"
  },
  "ui.open-study-brief": {
    "en": "Open study brief ↗",
    "zh-CN": "打开研究简报 ↗"
  },
  "ui.delete-conversation-2": {
    "en": "Delete conversation?",
    "zh-CN": "删除对话？"
  },
  "ui.close-workspace-details": {
    "en": "Close workspace details",
    "zh-CN": "关闭工作区详情"
  },
  "ui.connecting-to-workspace": {
    "en": "Connecting to workspace…",
    "zh-CN": "正在连接工作区……"
  },
  "ui.connecting-2": {
    "en": "Connecting…",
    "zh-CN": "正在连接……"
  },
  "ui.experiment-monitor-2": {
    "en": "Experiment monitor ↗",
    "zh-CN": "实验监控 ↗"
  },
  "ui.simjecture-on-github": {
    "en": "Simjecture on GitHub ↗",
    "zh-CN": "GitHub 上的 Simjecture ↗"
  },
  "ui.connect-a-research-folder": {
    "en": "Connect a research folder",
    "zh-CN": "连接科研文件夹"
  },
  "ui.close-folder-dialog": {
    "en": "Close folder dialog",
    "zh-CN": "关闭文件夹对话框"
  },
  "ui.folder-path": {
    "en": "Folder path",
    "zh-CN": "文件夹路径"
  },
  "ui.optional-2": {
    "en": "(optional)",
    "zh-CN": "（可选）"
  },
  "ui.simulation-examples": {
    "en": "Simulation examples",
    "zh-CN": "仿真示例"
  },
  "ui.optional-one-pattern-per-line": {
    "en": "(optional, one pattern per line)",
    "zh-CN": "（可选，每行一个匹配规则）"
  },
  "ui.exclude-paths": {
    "en": "Exclude paths",
    "zh-CN": "排除路径"
  },
  "ui.connect-folder-2": {
    "en": "Connect folder",
    "zh-CN": "连接文件夹"
  },
  "ui.knowledge-sources-2": {
    "en": "Knowledge sources",
    "zh-CN": "知识库资料源"
  },
  "ui.close-source-selection": {
    "en": "Close source selection",
    "zh-CN": "关闭资料源选择"
  },
  "ui.use-all-enabled-workspace-sources": {
    "en": "Use all enabled workspace sources",
    "zh-CN": "使用工作区中所有已启用的资料源"
  },
  "ui.apply-to-conversation": {
    "en": "Apply to conversation",
    "zh-CN": "应用到对话"
  },
  "ui.study-details-simjecture": {
    "en": "Study details · Simjecture",
    "zh-CN": "研究详情 · Simjecture"
  },
  "ui.simjecture-home": {
    "en": "Simjecture home",
    "zh-CN": "Simjecture 首页"
  },
  "ui.study-details": {
    "en": "Study details",
    "zh-CN": "研究详情"
  },
  "ui.select-campaign": {
    "en": "Select campaign",
    "zh-CN": "选择研究"
  },
  "ui.switch-color-theme": {
    "en": "Switch color theme",
    "zh-CN": "切换颜色主题"
  },
  "ui.pause": {
    "en": "Pause",
    "zh-CN": "暂停"
  },
  "ui.resume": {
    "en": "Resume",
    "zh-CN": "继续"
  },
  "ui.new-hypothesis": {
    "en": "New hypothesis",
    "zh-CN": "新建假设"
  },
  "ui.no-campaign-selected": {
    "en": "No campaign selected",
    "zh-CN": "未选择研究"
  },
  "ui.start-a-campaign": {
    "en": "Start a campaign",
    "zh-CN": "启动研究"
  },
  "ui.loading-campaign": {
    "en": "Loading campaign…",
    "zh-CN": "正在加载研究……"
  },
  "ui.operational-guidance": {
    "en": "Operational guidance",
    "zh-CN": "操作指导"
  },
  "ui.campaign-summary": {
    "en": "Campaign summary",
    "zh-CN": "研究概况"
  },
  "ui.claims": {
    "en": "Claims",
    "zh-CN": "论断"
  },
  "ui.campaign-time": {
    "en": "Campaign time",
    "zh-CN": "研究用时"
  },
  "ui.model-usage": {
    "en": "Model usage",
    "zh-CN": "模型用量"
  },
  "ui.durable-claim-ledger": {
    "en": "Durable claim ledger",
    "zh-CN": "持久化论断台账"
  },
  "ui.claim-graph": {
    "en": "Claim graph",
    "zh-CN": "论断关系图"
  },
  "ui.graph-controls": {
    "en": "Graph controls",
    "zh-CN": "关系图操作"
  },
  "ui.zoom-out": {
    "en": "Zoom out",
    "zh-CN": "缩小"
  },
  "ui.fit-every-graph-node": {
    "en": "Fit every graph node",
    "zh-CN": "显示所有图节点"
  },
  "ui.fit-all": {
    "en": "Fit all",
    "zh-CN": "适配全部"
  },
  "ui.zoom-in": {
    "en": "Zoom in",
    "zh-CN": "放大"
  },
  "ui.reset-layout": {
    "en": "Reset layout",
    "zh-CN": "重置布局"
  },
  "ui.graph-legend": {
    "en": "Graph legend",
    "zh-CN": "图例"
  },
  "ui.scientific": {
    "en": "Scientific",
    "zh-CN": "科学"
  },
  "ui.instrument": {
    "en": "Instrument",
    "zh-CN": "工具"
  },
  "ui.diagnostic": {
    "en": "Diagnostic",
    "zh-CN": "诊断"
  },
  "ui.control": {
    "en": "Control",
    "zh-CN": "控制"
  },
  "ui.commissioning-stage": {
    "en": "Commissioning stage",
    "zh-CN": "调试验证阶段"
  },
  "ui.supported": {
    "en": "Supported",
    "zh-CN": "获支持"
  },
  "ui.falsified": {
    "en": "Falsified",
    "zh-CN": "已证伪"
  },
  "ui.open-2": {
    "en": "Open",
    "zh-CN": "未定论"
  },
  "ui.qualified-limited": {
    "en": "Qualified / limited",
    "zh-CN": "已验证 / 有限制"
  },
  "ui.typed-claim-relationship-graph": {
    "en": "Typed claim relationship graph",
    "zh-CN": "按类型区分的论断关系图"
  },
  "ui.selected-record": {
    "en": "Selected record",
    "zh-CN": "已选记录"
  },
  "ui.record-inspector": {
    "en": "Record inspector",
    "zh-CN": "记录详情"
  },
  "ui.numerical-work": {
    "en": "Numerical work",
    "zh-CN": "数值计算"
  },
  "ui.execution-monitor": {
    "en": "Execution monitor",
    "zh-CN": "执行监控"
  },
  "ui.recent-simulations-and-calculations": {
    "en": "Recent simulations and calculations",
    "zh-CN": "近期仿真与计算"
  },
  "ui.auditable-agent-record": {
    "en": "Auditable agent record",
    "zh-CN": "可审计的智能体记录"
  },
  "ui.research-trace": {
    "en": "Research trace",
    "zh-CN": "研究过程记录"
  },
  "ui.research-loop-progress": {
    "en": "Research loop progress",
    "zh-CN": "研究循环进度"
  },
  "ui.token-usage": {
    "en": "Token usage",
    "zh-CN": "Token 用量"
  },
  "ui.durable-campaign-record": {
    "en": "Durable campaign record",
    "zh-CN": "持久化研究记录"
  },
  "ui.evidence-and-conclusion": {
    "en": "Evidence and conclusion",
    "zh-CN": "证据与结论"
  },
  "ui.campaign-record-views": {
    "en": "Campaign record views",
    "zh-CN": "研究记录视图"
  },
  "ui.artifacts": {
    "en": "Artifacts",
    "zh-CN": "产物"
  },
  "ui.conclusion": {
    "en": "Conclusion",
    "zh-CN": "结论"
  },
  "ui.new-campaign": {
    "en": "New campaign",
    "zh-CN": "新建研究"
  },
  "ui.give-simjecture-a-hypothesis": {
    "en": "Give Simjecture a hypothesis",
    "zh-CN": "向 Simjecture 提出一个假设"
  },
  "ui.close": {
    "en": "Close",
    "zh-CN": "关闭"
  },
  "ui.backend": {
    "en": "Backend",
    "zh-CN": "后端"
  },
  "ui.experiment-execution": {
    "en": "Experiment execution",
    "zh-CN": "实验执行方式"
  },
  "ui.bubblewrap-kernel-isolation": {
    "en": "Bubblewrap — kernel isolation",
    "zh-CN": "Bubblewrap — 内核隔离"
  },
  "ui.cooperative-proot-restricted-containers": {
    "en": "Cooperative PRoot — restricted containers",
    "zh-CN": "PRoot 协作执行 — 受限容器"
  },
  "ui.required": {
    "en": "Required",
    "zh-CN": "必填"
  },
  "ui.root-hypothesis": {
    "en": "Root hypothesis",
    "zh-CN": "根假设"
  },
  "ui.state-one-falsifiable-scientific-hypothesis": {
    "en": "State one falsifiable scientific hypothesis…",
    "zh-CN": "陈述一个可证伪的科学假设……"
  },
  "ui.constraints-preferred-tools-or-commissioning-material": {
    "en": "Constraints, preferred tools, or commissioning material…",
    "zh-CN": "约束条件、首选工具或调试验证材料……"
  },
  "ui.campaign-id": {
    "en": "Campaign ID",
    "zh-CN": "研究 ID"
  },
  "ui.wall-time-envelope": {
    "en": "Wall-time envelope",
    "zh-CN": "实际用时上限"
  },
  "ui.30-minutes": {
    "en": "30 minutes",
    "zh-CN": "30 分钟"
  },
  "ui.2-hours": {
    "en": "2 hours",
    "zh-CN": "2 小时"
  },
  "ui.6-hours": {
    "en": "6 hours",
    "zh-CN": "6 小时"
  },
  "ui.12-hours": {
    "en": "12 hours",
    "zh-CN": "12 小时"
  },
  "ui.24-hours": {
    "en": "24 hours",
    "zh-CN": "24 小时"
  },
  "ui.allow-experimental-source-forks": {
    "en": "Allow experimental source forks",
    "zh-CN": "允许创建实验性源代码副本"
  },
  "ui.use-supplied-solver-implementations": {
    "en": "Use supplied solver implementations",
    "zh-CN": "使用提供的求解器实现"
  },
  "ui.numerical-instrument-registry": {
    "en": "Numerical instrument registry",
    "zh-CN": "数值工具注册表"
  },
  "ui.directory-containing-installed-capability-manifests": {
    "en": "Directory containing installed capability manifests",
    "zh-CN": "包含已安装 capability 清单的目录"
  },
  "ui.execution-limits": {
    "en": "Execution limits",
    "zh-CN": "执行限制"
  },
  "ui.agent-watchdog-seconds": {
    "en": "Agent watchdog (seconds)",
    "zh-CN": "智能体看门狗时限（秒）"
  },
  "ui.interactive-turns": {
    "en": "interactive turns",
    "zh-CN": "交互轮次"
  },
  "ui.research-campaigns": {
    "en": "research campaigns",
    "zh-CN": "研究任务"
  },
  "ui.available-2": {
    "en": "{p0} / {p1} {p2} available",
    "zh-CN": "可用{p2}：{p0} / {p1}"
  },
  "ui.evidence": {
    "en": "Evidence",
    "zh-CN": "证据"
  },
  "ui.constraints": {
    "en": "Constraints",
    "zh-CN": "约束"
  },
  "ui.time-budget": {
    "en": "Time budget",
    "zh-CN": "时间预算"
  },
  "ui.execution-2": {
    "en": "Execution",
    "zh-CN": "执行环境"
  },
  "ui.preparing": {
    "en": "Preparing",
    "zh-CN": "正在准备"
  },
  "ui.last-check-stale": {
    "en": "Last check stale",
    "zh-CN": "上次检查已过期"
  },
  "ui.offline": {
    "en": "Offline",
    "zh-CN": "离线"
  },
  "ui.online": {
    "en": "Online",
    "zh-CN": "在线"
  },
  "ui.setup-needs-attention": {
    "en": "Setup needs attention",
    "zh-CN": "配置需要处理"
  },
  "ui.needs-setup": {
    "en": "Needs setup",
    "zh-CN": "需要配置"
  },
  "ui.checking": {
    "en": "Checking…",
    "zh-CN": "正在检查……"
  },
  "ui.not-prepared": {
    "en": "Not prepared",
    "zh-CN": "尚未准备"
  },
  "ui.scientific-attention": {
    "en": "Scientific attention",
    "zh-CN": "科学研究辅助"
  },
  "ui.finite-element-simulation": {
    "en": "Finite-element simulation",
    "zh-CN": "有限元仿真"
  },
  "ui.parametric-cad": {
    "en": "Parametric CAD",
    "zh-CN": "参数化 CAD"
  },
  "ui.geometry-and-meshing": {
    "en": "Geometry and meshing",
    "zh-CN": "几何建模与网格划分"
  },
  "ui.python-research-stack": {
    "en": "Python research stack",
    "zh-CN": "Python 科研环境"
  },
  "ui.numerical-exploration": {
    "en": "Numerical exploration",
    "zh-CN": "数值探索"
  },
  "ui.cylinder-flow": {
    "en": "Cylinder flow",
    "zh-CN": "圆柱绕流"
  },
  "ui.warp-lbm-2d-fluid-dynamics": {
    "en": "Warp-LBM · 2D fluid dynamics",
    "zh-CN": "Warp-LBM · 二维流体动力学"
  },
  "ui.iter-pack": {
    "en": "ITER pack",
    "zh-CN": "ITER 工具包"
  },
  "ui.diagnostics-data": {
    "en": "Diagnostics & data",
    "zh-CN": "诊断与数据"
  },
  "ui.edge-plasma": {
    "en": "Edge plasma",
    "zh-CN": "边缘等离子体"
  },
  "ui.tokamak-mhd": {
    "en": "Tokamak MHD",
    "zh-CN": "托卡马克磁流体力学"
  },
  "ui.scenario-modelling": {
    "en": "Scenario modelling",
    "zh-CN": "运行场景建模"
  },
  "ui.particle-in-cell": {
    "en": "Particle-in-cell",
    "zh-CN": "粒子网格法"
  },
  "ui.gpu-particle-in-cell": {
    "en": "GPU particle-in-cell",
    "zh-CN": "GPU 粒子网格法"
  },
  "ui.hydrodynamics-mhd": {
    "en": "Hydrodynamics & MHD",
    "zh-CN": "流体动力学与磁流体力学"
  },
  "ui.atomic-physics": {
    "en": "Atomic physics",
    "zh-CN": "原子物理"
  },
  "ui.equation-of-state": {
    "en": "Equation of state",
    "zh-CN": "状态方程"
  },
  "ui.electron-ion-equation-of-state": {
    "en": "Electron/ion equation of state",
    "zh-CN": "电子 / 离子状态方程"
  },
  "ui.material-eos-builder": {
    "en": "Material EOS builder",
    "zh-CN": "材料状态方程构建器"
  },
  "ui.model-profiles-and-table-export": {
    "en": "Model profiles and table export",
    "zh-CN": "模型配置与表格导出"
  },
  "ui.opacity-tables": {
    "en": "Opacity tables",
    "zh-CN": "不透明度表"
  },
  "ui.atomic-structure-rates": {
    "en": "Atomic structure & rates",
    "zh-CN": "原子结构与速率"
  },
  "ui.prepare": {
    "en": "Prepare",
    "zh-CN": "准备"
  },
  "ui.checking-prerequisites": {
    "en": "Checking prerequisites",
    "zh-CN": "正在检查前置条件"
  },
  "ui.install": {
    "en": "Install",
    "zh-CN": "安装"
  },
  "ui.downloading-and-building": {
    "en": "Downloading and building",
    "zh-CN": "正在下载和构建"
  },
  "ui.verify": {
    "en": "Verify",
    "zh-CN": "验证"
  },
  "ui.running-readiness-checks": {
    "en": "Running readiness checks",
    "zh-CN": "正在检查就绪情况"
  },
  "ui.under-a-minute": {
    "en": "under a minute",
    "zh-CN": "不到一分钟"
  },
  "ui.about-min": {
    "en": "about {p0} min",
    "zh-CN": "约 {p0} 分钟"
  },
  "ui.about-h": {
    "en": "about {p0} h",
    "zh-CN": "约 {p0} 小时"
  },
  "ui.general-python-with-numpy-scipy-pandas-matplotlib-and-pyvista-for-3d": {
    "en": "General Python with NumPy, SciPy, pandas, Matplotlib and PyVista for 3D visualization. Ask your agent to write and run a numerical calculation.",
    "zh-CN": "包含 NumPy、SciPy、pandas、Matplotlib 及用于三维可视化的 PyVista。可请智能体编写并运行数值计算。"
  },
  "ui.numerical-libraries-support-the-installed-examples-available-through": {
    "en": "Numerical libraries support the installed examples. Available through the tools provided by your administrator.",
    "zh-CN": "数值库支持已安装的示例，可通过管理员提供的工具使用。"
  },
  "ui.client-installed": {
    "en": "Client installed",
    "zh-CN": "客户端已安装"
  },
  "ui.model-service-connected-per-study-disabled-by-default": {
    "en": "Model service connected per study · disabled by default",
    "zh-CN": "按研究连接模型服务 · 默认停用"
  },
  "ui.included": {
    "en": "Included",
    "zh-CN": "已内置"
  },
  "ui.included-with-simjecture": {
    "en": "Included with Simjecture",
    "zh-CN": "Simjecture 内置"
  },
  "ui.provided-by-your-administrator": {
    "en": "Provided by your administrator",
    "zh-CN": "由管理员提供"
  },
  "ui.stopping-setup-2": {
    "en": "Stopping setup…",
    "zh-CN": "正在停止配置……"
  },
  "ui.installing": {
    "en": "Installing…",
    "zh-CN": "正在安装……"
  },
  "ui.readiness-check-is-running": {
    "en": "Readiness check is running.",
    "zh-CN": "正在进行就绪检查。"
  },
  "ui.setup-is-running": {
    "en": "Setup is running.",
    "zh-CN": "正在配置。"
  },
  "ui.needs-attention": {
    "en": "Needs attention",
    "zh-CN": "需要处理"
  },
  "ui.readiness-check-failed-diagnose-with-an-agent": {
    "en": "Readiness check failed · diagnose with an agent",
    "zh-CN": "就绪检查失败 · 请智能体诊断"
  },
  "ui.setup-did-not-finish-diagnose-with-an-agent": {
    "en": "Setup did not finish · diagnose with an agent",
    "zh-CN": "配置未完成 · 请智能体诊断"
  },
  "ui.stopped": {
    "en": "Stopped",
    "zh-CN": "已停止"
  },
  "ui.setup-was-stopped-install-again-when-ready": {
    "en": "Setup was stopped · install again when ready",
    "zh-CN": "配置已停止 · 准备好后可重新安装"
  },
  "ui.detected": {
    "en": "Detected",
    "zh-CN": "已检测到"
  },
  "ui.local-build-registration-needed": {
    "en": "{p0} local build{p1} · registration needed",
    "zh-CN": "{p0} 个本地构建{p1} · 需要注册"
  },
  "ui.ready-2": {
    "en": "✓ Ready",
    "zh-CN": "✓ 已就绪"
  },
  "ui.installed-2": {
    "en": "✓ Installed",
    "zh-CN": "✓ 已安装"
  },
  "ui.readiness-check-passed": {
    "en": "Readiness check passed",
    "zh-CN": "就绪检查通过"
  },
  "ui.installed-check-readiness-when-you-need-it": {
    "en": "Installed · check readiness when you need it",
    "zh-CN": "已安装 · 可按需检查就绪情况"
  },
  "ui.not-installed": {
    "en": "Not installed",
    "zh-CN": "未安装"
  },
  "ui.guided-setup-with-your-agent": {
    "en": "Guided setup with your agent",
    "zh-CN": "由智能体指导配置"
  },
  "ui.one-click-install-when-you-need-it": {
    "en": "One-click install when you need it",
    "zh-CN": "按需一键安装"
  },
  "ui.setup-guide": {
    "en": "Setup guide",
    "zh-CN": "配置指南"
  },
  "ui.diagnose-with-agent": {
    "en": "Diagnose with agent",
    "zh-CN": "请智能体诊断"
  },
  "ui.view-installations": {
    "en": "View installations",
    "zh-CN": "查看安装"
  },
  "ui.install-with-agent": {
    "en": "Install with agent",
    "zh-CN": "请智能体安装"
  },
  "ui.starting": {
    "en": "Starting…",
    "zh-CN": "正在启动……"
  },
  "ui.working-2": {
    "en": "Working",
    "zh-CN": "正在处理"
  },
  "ui.step-of": {
    "en": "Step {p0} of {p1} · {p2}",
    "zh-CN": "第 {p0} 步，共 {p1} 步 · {p2}"
  },
  "ui.about-left-usually": {
    "en": "About {p0} left · usually {p1}",
    "zh-CN": "预计还需 {p0} · 通常为 {p1}"
  },
  "ui.taking-longer-than-the-usual": {
    "en": "Taking longer than the usual {p0}",
    "zh-CN": "已超过通常所需的 {p0}"
  },
  "ui.first-timed-run-on-this-machine-duration-depends-on-network-and-cpu": {
    "en": "First timed run on this machine · duration depends on network and CPU",
    "zh-CN": "此设备首次计时运行 · 耗时取决于网络与 CPU"
  },
  "ui.stop-setting-up-output-so-far-is-kept-and-you-can-start-again-later": {
    "en": "Stop setting up {p0}?\n\nOutput so far is kept and you can start again later.",
    "zh-CN": "停止配置 {p0}？\n\n已有输出会保留，可稍后重新开始。"
  },
  "ui.tool-setup-running": {
    "en": "{p0} tool setup{p1} running",
    "zh-CN": "{p0} 个工具配置{p1}正在运行"
  },
  "ui.the-report-will-be-explained-here-automatically-when-the-interactive": {
    "en": "The report will be explained here automatically when the interactive agent is free. Keep the workspace server running; closing the browser is fine.",
    "zh-CN": "交互智能体空闲时会自动在此解读报告。请保持工作区服务运行，浏览器可关闭。"
  },
  "ui.experiments": {
    "en": "Experiments",
    "zh-CN": "实验"
  },
  "ui.independent-reviews": {
    "en": "Independent reviews",
    "zh-CN": "独立评审"
  },
  "ui.provider-retry-wait": {
    "en": "Provider retry wait",
    "zh-CN": "服务商重试等待"
  },
  "ui.time-remaining": {
    "en": "Time remaining",
    "zh-CN": "剩余时间"
  },
  "ui.reported": {
    "en": "reported",
    "zh-CN": "已报告"
  },
  "ui.tracked-requests-without-usage-yet-cache-usage": {
    "en": "{p0} tracked requests; {p1} without usage yet. Cache usage {p2}. {p3}",
    "zh-CN": "已跟踪 {p0} 个请求；{p1} 个尚无用量记录。缓存用量{p2}。{p3}"
  },
  "ui.instrument-family-any-of-scientific-qualification-is-separate": {
    "en": "Instrument family: any of {p0}. {p1}; scientific qualification is separate.",
    "zh-CN": "工具系列：{p0} 中的任一种。{p1}；科学适用性另行验证。"
  },
  "ui.cooperative-execution-is-not-a-security-sandbox-it-does-not-isolate-": {
    "en": "Cooperative execution is not a security sandbox: it does not isolate host files or networking. Use only trusted code under a dedicated non-root account.",
    "zh-CN": "协作执行不属于安全沙箱，不隔离主机文件或网络。请使用专用的非 root 账户，仅运行可信代码。"
  },
  "ui.isolated-experiments-cannot-run-on-this-host-cooperative-mode-needs-": {
    "en": "Isolated experiments cannot run on this host. Cooperative mode needs PRoot and a dedicated non-root account.",
    "zh-CN": "此主机无法运行隔离实验。协作模式需要 PRoot 和专用的非 root 账户。"
  },
  "ui.verified-tools-ready": {
    "en": "Verified tools ready",
    "zh-CN": "已验证的工具已就绪"
  },
  "ui.experiments-unavailable": {
    "en": "Experiments unavailable",
    "zh-CN": "实验不可用"
  },
  "ui.isolated-experiments-ready": {
    "en": "Isolated experiments ready",
    "zh-CN": "隔离实验环境已就绪"
  },
  "ui.execution-status-unchecked": {
    "en": "Execution status unchecked",
    "zh-CN": "尚未检查执行状态"
  },
  "ui.research-started-keep-a-tab-open-or-sign-in-to-retain-the-investigat": {
    "en": "Research started. Keep a tab open, or sign in to retain the investigation.",
    "zh-CN": "研究已启动。请保留此标签页，或登录以保存研究。"
  },
  "ui.autonomous-study-started-you-can-close-this-page-and-return-later": {
    "en": "Autonomous study started. You can close this page and return later.",
    "zh-CN": "自主研究已启动，可关闭此页面并稍后返回。"
  },
  "ui.s-ago": {
    "en": "{p0}s ago",
    "zh-CN": "{p0} 秒前"
  },
  "ui.m-s-ago": {
    "en": "{p0}m {p1}s ago",
    "zh-CN": "{p0} 分 {p1} 秒前"
  },
  "ui.connection-interrupted-your-work-stays-on-disk": {
    "en": "Connection interrupted: {p0}. Your work stays on disk.",
    "zh-CN": "连接中断：{p0}。工作内容已保存在磁盘上。"
  },
  "ui.switch-to-light-mode": {
    "en": "Switch to light mode",
    "zh-CN": "切换到浅色模式"
  },
  "ui.switch-to-dark-mode": {
    "en": "Switch to dark mode",
    "zh-CN": "切换到深色模式"
  },
  "ui.prepare-a-linked-phase-with-a-new-budget-the-previous-study-stays-un": {
    "en": "Prepare a linked phase with a new budget. The previous study stays unchanged. Selected files are snapshotted at launch; earlier results keep their original status. Review the brief and model before starting.",
    "zh-CN": "使用新预算准备关联研究阶段。原研究保持不变，启动时会为所选文件建立快照，先前结果保留原有状态。开始前请检查简报和模型。"
  },
  "ui.guidance-reaches-the-agent-at-its-next-checkpoint-it-does-not-change": {
    "en": "Guidance reaches the agent at its next checkpoint. It does not change the deadline or existing experiment contracts. Use Continue investigation for a new question or requirements.",
    "zh-CN": "指导会在下一个检查点送达智能体，不改变截止时间或已有实验契约。如需提出新问题或新要求，请使用“继续研究”。"
  },
  "ui.what-should-the-next-phase-investigate": {
    "en": "What should the next phase investigate?",
    "zh-CN": "下一阶段要研究什么？"
  },
  "ui.guidance-for-the-agent": {
    "en": "Guidance for the agent",
    "zh-CN": "给智能体的指导"
  },
  "ui.optional-when-preparing-with-an-agent-discuss-the-next-direction-in-": {
    "en": "Optional when preparing with an agent: discuss the next direction in chat, then review the agent’s brief before launch.",
    "zh-CN": "由智能体准备时可选：先在对话中讨论下一步方向，启动前再检查智能体生成的简报。"
  },
  "ui.new-wall-time-budget-hours": {
    "en": "New wall-time budget (hours)",
    "zh-CN": "新的总运行时间预算（小时）"
  },
  "ui.working-files-to-inherit-available": {
    "en": "Working files to inherit ({p0} available)",
    "zh-CN": "要继承的工作文件（{p0} 个可用）"
  },
  "ui.prepare-directly": {
    "en": "Prepare directly",
    "zh-CN": "直接准备"
  },
  "ui.finish-time-ranked-from-fastest-unfinished-runs-are-red": {
    "en": "Finish time ranked from fastest; unfinished runs are red",
    "zh-CN": "按完成速度排名，未完成运行以红色显示"
  },
  "ui.task-cost-ranked-from-cheapest-unfinished-runs-show-recorded-spendin": {
    "en": "Task cost ranked from cheapest; unfinished runs show recorded spending in red",
    "zh-CN": "按任务成本从低到高排名，未完成运行的已记录支出以红色显示"
  },
  "ui.unfinished": {
    "en": " · Unfinished",
    "zh-CN": " · 未完成"
  },
  "ui.unfinished-2": {
    "en": "Unfinished",
    "zh-CN": "未完成"
  },
  "ui.no-fixed-tariff": {
    "en": "No fixed tariff",
    "zh-CN": "无固定费率"
  },
  "ui.cost-time-pareto-plot-lower-cost-is-left-faster-completion-is-top-up": {
    "en": "Cost-time Pareto plot. Lower cost is left; faster completion is top. Upper left is better.",
    "zh-CN": "成本—耗时 Pareto 图。越靠左成本越低，越靠上完成越快；左上方更优。"
  },
  "ui.attempt": {
    "en": "attempt",
    "zh-CN": "尝试"
  },
  "ui.attempts": {
    "en": "attempts",
    "zh-CN": "尝试"
  },
  "ui.input-output-usd-per-million-tokens-this-is-separate-from-task-cost": {
    "en": "Input / output USD per million tokens; this is separate from task cost.",
    "zh-CN": "每百万输入 / 输出 token 的美元费用，与任务成本分开记录。"
  },
  "ui.time-rank-median-independently-verified-completion-cost-rank-mean-ap": {
    "en": "Time rank = median independently verified completion. Cost rank = mean API-equivalent cost per attempt, including failures. Partial usage has a lower bound and no cost rank. ",
    "zh-CN": "时间排名依据独立验证完成时间的中位数；成本排名依据每次尝试的平均 API 等效成本，包含失败尝试。用量不完整时仅显示下限，不参与成本排名。"
  },
  "ui.rz-has-one-measured-attempt-per-configuration-ranks-describe-this-in": {
    "en": "RZ has one measured attempt per configuration; ranks describe this initial sweep.",
    "zh-CN": "RZ 每个配置仅有一次实测尝试，排名反映此次初步测量。"
  },
  "ui.csv-schedules-five-fresh-attempts-quota-blocked-attempts-are-exclude": {
    "en": "CSV schedules five fresh attempts; quota-blocked attempts are excluded.",
    "zh-CN": "CSV 为每个配置安排五次新尝试，因额度限制未运行的尝试不计入。"
  },
  "ui.api-tariffs-are-published-prices-task-cost-depends-on-tokens-used": {
    "en": " API tariffs are published prices; task cost depends on tokens used.",
    "zh-CN": "API 费率采用公布价格，任务成本取决于实际使用的 token 数。"
  },
  "ui.describe-a-question-a-puzzling-result-or-a-simulation-you-want-to-ru": {
    "en": "Describe a question, a puzzling result or a simulation you want to run. ",
    "zh-CN": "描述一个问题、令人困惑的结果，或你想运行的仿真。"
  },
  "ui.the-hosted-agent-and-model-are-provided-for-this-workspace": {
    "en": "The hosted agent and model are provided for this workspace.",
    "zh-CN": "此工作区已提供托管智能体和模型。"
  },
  "ui.choose-which-agent-and-model-answers-from-the-menu-on-the-right": {
    "en": "Choose which agent and model answers from the menu on the right.",
    "zh-CN": "在右侧菜单中选择用于回答的智能体和模型。"
  },
  "ui.reuse-earlier-conversations": {
    "en": "Reuse earlier conversations",
    "zh-CN": "复用先前对话"
  },
  "ui.bring-your-own-references": {
    "en": "Bring your own references",
    "zh-CN": "添加自己的参考资料"
  },
  "ui.search-completed-replies-from-your-conversations-under-knowledge-you": {
    "en": "Search completed replies from your conversations under Knowledge. Your agent can use them as references in this workspace.",
    "zh-CN": "在知识库中搜索先前对话中已完成的回复。智能体可在此工作区中将其用作参考。"
  },
  "ui.connect-folders-of-papers-and-notes-under-knowledge-your-agent-can-s": {
    "en": "Connect folders of papers and notes under Knowledge. Your agent can search them and cite what it used.",
    "zh-CN": "在知识库中连接论文和笔记文件夹。智能体可搜索这些资料，并引用所用内容。"
  },
  "ui.interactive-is-a-conversation-you-steer-each-step-autonomous-study-r": {
    "en": "Interactive is a conversation: you steer each step. Autonomous study runs on its own within a time budget, then an independent review checks the evidence. Start in Interactive; switch to Autonomous study inside the conversation once your claim is clear.",
    "zh-CN": "交互模式采用对话方式，由你指导每一步。自主研究在时间预算内独立运行，随后由独立评审检查证据。可先从交互模式开始，论断明确后再在对话中切换到自主研究。"
  },
  "ui.explore-the-available-research-tools": {
    "en": "Explore the available research tools",
    "zh-CN": "浏览可用的科研工具"
  },
  "ui.add-research-tools-when-you-need-them": {
    "en": "Add research tools when you need them",
    "zh-CN": "按需添加科研工具"
  },
  "ui.open-research-tools-to-see-the-verified-solvers-available-here-your-": {
    "en": "Open Research tools to see the verified solvers available here. Your administrator manages installation and setup.",
    "zh-CN": "打开科研工具，查看此处已验证的求解器。管理员负责安装和配置。"
  },
  "ui.python-is-ready-now-install-solvers-such-as-warpx-from-research-tool": {
    "en": "Python is ready now. Install solvers such as WarpX from Research tools; setup shows its progress and you can keep working meanwhile.",
    "zh-CN": "Python 已就绪。可在科研工具中安装 WarpX 等求解器；配置时会显示进度，你也可以继续其他工作。"
  },
  "ui.dsh-autonomous-researcher": {
    "en": "DSH · autonomous researcher",
    "zh-CN": "DSH · 自主研究智能体"
  },
  "ui.commission": {
    "en": "Commission",
    "zh-CN": "验证工具"
  },
  "ui.falsify": {
    "en": "Falsify",
    "zh-CN": "证伪"
  },
  "ui.judge": {
    "en": "Judge",
    "zh-CN": "评审"
  },
  "ui.scientific-target-2": {
    "en": "Scientific target",
    "zh-CN": "科学目标"
  },
  "ui.rationale": {
    "en": "Rationale",
    "zh-CN": "理由"
  },
  "ui.closure": {
    "en": "Closure",
    "zh-CN": "结论依据"
  },
  "ui.child-claims": {
    "en": "Child claims · {p0}",
    "zh-CN": "子论断 · {p0}"
  },
  "ui.evidence-contracts": {
    "en": "Evidence contracts · {p0}",
    "zh-CN": "证据契约 · {p0}"
  },
  "ui.observable": {
    "en": "Observable",
    "zh-CN": "观测量"
  },
  "ui.expected-outcomes": {
    "en": "Expected outcomes",
    "zh-CN": "预期结果"
  },
  "ui.decision-rule": {
    "en": "Decision rule",
    "zh-CN": "判定规则"
  },
  "ui.required-observation": {
    "en": "Required observation",
    "zh-CN": "所需观测"
  },
  "ui.uncertainty": {
    "en": "Uncertainty",
    "zh-CN": "不确定性"
  },
  "ui.inconclusive-when": {
    "en": "Inconclusive when",
    "zh-CN": "无法确定结论的条件"
  },
  "ui.evidence-2": {
    "en": "Evidence · {p0}",
    "zh-CN": "证据 · {p0}"
  },
  "ui.guided-starting-point": {
    "en": "Guided starting point",
    "zh-CN": "指导性起点"
  },
  "ui.commissioning-claims": {
    "en": "Commissioning claims · {p0}",
    "zh-CN": "工具验证论断 · {p0}"
  },
  "ui.bound-executions": {
    "en": "Bound executions · {p0}",
    "zh-CN": "关联执行 · {p0}"
  },
  "ui.stdout": {
    "en": "Stdout",
    "zh-CN": "标准输出"
  },
  "ui.stderr": {
    "en": "Stderr",
    "zh-CN": "标准错误"
  },
  "ui.reasoning": {
    "en": "Reasoning",
    "zh-CN": "推理"
  },
  "ui.cached": {
    "en": "Cached",
    "zh-CN": "已缓存"
  },
  "ui.job": {
    "en": "{p0} job {p1}{p2}.",
    "zh-CN": "{p0}任务{p1}{p2}。"
  },
  "ui.typed-simjecture-tool": {
    "en": "typed Simjecture tool",
    "zh-CN": "结构化 Simjecture 工具"
  },
  "ui.calling": {
    "en": "Calling",
    "zh-CN": "正在调用"
  },
  "ui.tool-call": {
    "en": "Tool call",
    "zh-CN": "工具调用"
  },
  "ui.dsh-conversation-compaction": {
    "en": "DSH conversation compaction {p0}{p1}{p2}.",
    "zh-CN": "DSH 对话压缩{p0}{p1}{p2}。"
  },
  "ui.model-route-selected": {
    "en": "Model route selected: {p0}/{p1}.",
    "zh-CN": "已选择模型路由：{p0}/{p1}。"
  },
  "ui.durable-dsh-session": {
    "en": "Durable DSH session {p0}.",
    "zh-CN": "持久化 DSH 会话{p0}。"
  },
  "ui.autonomous-researcher-is": {
    "en": "Autonomous researcher is {p0}.",
    "zh-CN": "自主研究智能体{p0}。"
  },
  "ui.model-2": {
    "en": "Model {p0}.",
    "zh-CN": "模型{p0}。"
  },
  "ui.dsh-turn": {
    "en": "DSH turn {p0}.",
    "zh-CN": "DSH 轮次{p0}。"
  },
  "ui.evidence-for": {
    "en": " · evidence for {p0}",
    "zh-CN": " · {p0} 的证据"
  },
  "ui.evidence-review-2": {
    "en": "Evidence & review",
    "zh-CN": "证据与评审"
  },
  "ui.community-local": {
    "en": "Community & local",
    "zh-CN": "社区与本地"
  },
  "ui.your-runs-community-contributions": {
    "en": "Your runs & community contributions",
    "zh-CN": "你的运行与社区贡献"
  },
  "ui.editable": {
    "en": "EDITABLE",
    "zh-CN": "可编辑"
  },
  "ui.your-agent-fills-these-in-from-the-conversation-change-anything-you-": {
    "en": "Your agent fills these in from the conversation. Change anything you like; a study keeps the brief it started with.",
    "zh-CN": "智能体会根据对话填写这些内容，你可自由修改。研究会保留启动时使用的简报。"
  },
  "ui.question-or-claim-to-test": {
    "en": "Question or claim to test",
    "zh-CN": "待检验的问题或论断"
  },
  "ui.what-precise-question-should-the-investigation-answer": {
    "en": "What precise question should the investigation answer?",
    "zh-CN": "本研究需要回答的具体问题是什么？"
  },
  "ui.what-evidence-would-answer-it": {
    "en": "What evidence would answer it?",
    "zh-CN": "需要什么证据来回答？"
  },
  "ui.measurements-comparison-counterexample-and-validation-requirements": {
    "en": "Measurements, comparison, counterexample, and validation requirements",
    "zh-CN": "测量、对比、反例及验证要求"
  },
  "ui.constraints-and-available-inputs": {
    "en": "Constraints and available inputs",
    "zh-CN": "约束与可用输入"
  },
  "ui.what-may-change-what-must-stay-fixed-which-project-files-matter": {
    "en": "What may change? What must stay fixed? Which project files matter?",
    "zh-CN": "哪些条件可调整，哪些必须固定？需要使用哪些项目文件？"
  },
  "ui.when-should-the-study-stop": {
    "en": "When should the study stop?",
    "zh-CN": "研究何时停止？"
  },
  "ui.when-the-question-is-answered-a-no-counts": {
    "en": "When the question is answered (a “no” counts)",
    "zh-CN": "问题得到回答时（否定结论也算）"
  },
  "ui.when-the-claim-holds-or-a-fixed-version-does": {
    "en": "When the claim holds, or a fixed version does",
    "zh-CN": "原论断或修正版得到支持时"
  },
  "ui.files-live-runs": {
    "en": "Files & live runs",
    "zh-CN": "文件与实时任务"
  },
  "ui.study-details-evidence-review": {
    "en": "Study details · Evidence & review",
    "zh-CN": "研究详情 · 证据与评审"
  },
  "ui.glm-5-3-codex-glm-default": {
    "en": "glm-5.3 (Codex GLM default)",
    "zh-CN": "glm-5.3（Codex GLM 默认）"
  },
  "ui.no-additional-constraints-specified": {
    "en": "No additional constraints specified.",
    "zh-CN": "未指定额外约束。"
  },
  "ui.no-hosted-time-limit": {
    "en": "No hosted time limit",
    "zh-CN": "无托管时间限制"
  },
  "ui.this-host": {
    "en": "This host",
    "zh-CN": "当前主机"
  },
  "ui.a-supported-claim-or-independently-tested-repair": {
    "en": "A supported claim or independently tested repair.",
    "zh-CN": "论断获得支持，或修正版通过独立检验。"
  },
  "ui.an-independently-reviewed-answer-including-a-negative-result": {
    "en": "An independently reviewed answer, including a negative result.",
    "zh-CN": "得到独立评审的答案，包括否定结论。"
  },
  "ui.unlimited-2": {
    "en": "Unlimited",
    "zh-CN": "不限"
  },
  "ui.incomplete-contract": {
    "en": "Incomplete contract",
    "zh-CN": "未满足完整契约"
  },
  "ui.numbers-pass-findings-missing": {
    "en": "Numbers pass; findings missing",
    "zh-CN": "数值检查通过，但缺少结论"
  },
  "ui.quota-interrupted-after-work": {
    "en": "Quota interrupted after work",
    "zh-CN": "运行后因额度限制中断"
  },
  "ui.complete": {
    "en": "Complete",
    "zh-CN": "已完成"
  },
  "ui.verified-after-deadline": {
    "en": "Verified after deadline",
    "zh-CN": "截止后验证通过"
  },
  "ui.numbers-pass-findings-missing-2": {
    "en": "Numbers pass · findings missing",
    "zh-CN": "数值通过 · 缺少结论"
  },
  "ui.interrupted": {
    "en": "Interrupted · {p0}",
    "zh-CN": "已中断 · {p0}"
  },
  "ui.verified-pass": {
    "en": "Verified pass",
    "zh-CN": "验证通过"
  },
  "ui.recent-shown": {
    "en": "{p0} recent shown",
    "zh-CN": "显示最近 {p0} 条"
  },
  "ui.no-claim-binding": {
    "en": "no claim binding",
    "zh-CN": "未关联论断"
  },
  "ui.return-code": {
    "en": "return code {p0}",
    "zh-CN": "返回码 {p0}"
  },
  "ui.timed-out": {
    "en": "timed out",
    "zh-CN": "已超时"
  },
  "ui.not-fully-reported-2": {
    "en": "Not fully reported",
    "zh-CN": "未完整报告"
  },
  "ui.hours": {
    "en": "{p0} hours",
    "zh-CN": "{p0} 小时"
  },
  "ui.use-supplied-solver-implementations-experiment-and-analysis-scripts-": {
    "en": "Use supplied solver implementations; experiment and analysis scripts remain available.",
    "zh-CN": "使用提供的求解器实现；仍可编写实验和分析脚本。"
  },
  "ui.allowed-on-the-agent-s-own-solver-copies-results-from-a-changed-solv": {
    "en": "Allowed on the agent's own solver copies; results from a changed solver are checked before they count.",
    "zh-CN": "允许修改智能体自己的求解器副本；修改后得到的结果须经过检查才能采信。"
  },
  "ui.this-turn-was-interrupted-your-files-are-saved-send-a-message-to-con": {
    "en": "This turn was interrupted. Your files are saved; send a message to continue.",
    "zh-CN": "本轮已中断。文件已保存，发送消息即可继续。"
  },
  "ui.connect-a-separately-managed-model-service-and-enable-it-for-a-study": {
    "en": "Connect a separately managed model service and enable it for a study. Shadow mode records suggestions; alert mode permits bounded director requests. Opening this guide does not download weights or allocate a GPU.",
    "zh-CN": "连接单独管理的模型服务，并按研究启用。影子模式记录建议；警报模式允许受限的研究主管请求。打开此指南不会下载权重或分配 GPU。"
  },
  "ui.simjecture-runs-the-pinned-installer-in-its-own-runtime-folder-then-": {
    "en": "Simjecture runs the pinned installer in its own runtime folder, then checks that the tool works. Progress and output appear here; you can close this window or stop setup at any time.",
    "zh-CN": "Simjecture 在独立运行环境目录中执行固定版本的安装程序，随后检查工具是否可用。此处显示进度和输出，你可随时关闭窗口或停止配置。"
  },
  "ui.you-can-close-this-window-setup-continues-and-its-progress-stays-on-": {
    "en": "You can close this window; setup continues and its progress stays on this page.",
    "zh-CN": "可关闭此窗口；配置会继续运行，进度保留在此页面。"
  },
  "ui.min": {
    "en": "{p0} min",
    "zh-CN": "{p0} 分钟"
  },
  "ui.time-budget-hours-0-unlimited": {
    "en": "Time budget (hours; 0 = unlimited)",
    "zh-CN": "时间预算（小时；0 表示不限）"
  },
  "ui.no-project": {
    "en": "No project",
    "zh-CN": "无项目"
  },
  "ui.conversations-shared-context-and-research-studies": {
    "en": "Conversations, shared context and research studies.",
    "zh-CN": "对话、共享上下文与科研研究。"
  },
  "ui.studies-2": {
    "en": "{p0} studies",
    "zh-CN": "{p0} 项研究"
  },
  "ui.start-a-conversation-to-explore-a-question-in-this-project": {
    "en": "Start a conversation to explore a question in this project.",
    "zh-CN": "开始对话，在此项目中探索研究问题。"
  },
  "ui.add-scientific-files-within-a-conversation": {
    "en": "Add scientific files within a conversation.",
    "zh-CN": "请在对话中添加科研文件。"
  },
  "ui.completed-2": {
    "en": " completed",
    "zh-CN": " 次完成"
  },
  "ui.per-configuration": {
    "en": " per configuration",
    "zh-CN": " 每个配置"
  },
  "ui.scheduled": {
    "en": " scheduled ",
    "zh-CN": " 次计划"
  },
  "ui.min-deadline": {
    "en": " min deadline · ",
    "zh-CN": " 分钟时限 · "
  },
  "ui.attempts-unavailable-before-inference-excluded-from-scores": {
    "en": " attempts unavailable before inference; excluded from scores.",
    "zh-CN": " 次尝试在推理前不可用，未计入评分。"
  },
  "ui.complete-2": {
    "en": " complete",
    "zh-CN": " 已完成"
  },
  "ui.passed-per-trial-per-success": {
    "en": "{p0}\n{p1}/{p2} passed\n{p3} per trial\n{p4} · {p5} per success{p6}",
    "zh-CN": "{p0}\n{p1}/{p2} 通过\n每次试验 {p3}\n每次成功 {p4} · {p5}{p6}"
  },
  "ui.task-definitions-and-deadlines-stay-fixed-hardware-and-runner-settin": {
    "en": "Task definitions and deadlines stay fixed. Hardware and runner settings create separate comparison groups. One trial is provisional; five are required for Pareto eligibility.",
    "zh-CN": "任务定义和截止时间保持固定。不同硬件及执行器设置划分为独立比较组。一次试验的结果为暂定，至少五次试验才可参与 Pareto 比较。"
  },
  "ui.finished-passed": {
    "en": "{p0}/{p1} finished · {p2} passed · {p3}",
    "zh-CN": "{p0}/{p1} 已结束 · {p2} 通过 · {p3}"
  },
  "ui.progress": {
    "en": "{p0} progress",
    "zh-CN": "{p0} 进度"
  },
  "ui.remaining": {
    "en": "{p0} remaining",
    "zh-CN": "剩余 {p0}"
  },
  "ui.claim-2": {
    "en": "{p0} claim",
    "zh-CN": "{p0}论断"
  },
  "ui.parent": {
    "en": "parent: {p0}",
    "zh-CN": "父论断：{p0}"
  },
  "ui.total": {
    "en": "{p0} total",
    "zh-CN": "共 {p0} 次"
  },
  "ui.running-2": {
    "en": "{p0} running",
    "zh-CN": "{p0} 次运行中"
  },
  "ui.succeeded": {
    "en": "{p0} succeeded",
    "zh-CN": "{p0} 次成功"
  },
  "ui.failed": {
    "en": "{p0} failed",
    "zh-CN": "{p0} 次失败"
  },
  "ui.recorded": {
    "en": "{p0} recorded",
    "zh-CN": "已记录 {p0} 次"
  },
  "ui.claim-3": {
    "en": "claim {p0}",
    "zh-CN": "论断 {p0}"
  },
  "ui.stage": {
    "en": "stage {p0}",
    "zh-CN": "阶段 {p0}"
  },
  "ui.model-3": {
    "en": "model {p0}",
    "zh-CN": "模型 {p0}"
  },
  "ui.route": {
    "en": "route {p0}",
    "zh-CN": "路由 {p0}"
  },
  "ui.machine-2": {
    "en": "machine {p0}",
    "zh-CN": "设备 {p0}"
  },
  "ui.job-2": {
    "en": "job {p0}",
    "zh-CN": "任务 {p0}"
  },
  "ui.ssh-unavailable-remote-execution-may-continue": {
    "en": "SSH unavailable; remote execution may continue",
    "zh-CN": "SSH 不可用；远程执行可能仍在继续"
  },
  "ui.strategy-review-interval-healthy-experiments-with-unchanged-work-may": {
    "en": "Strategy review interval: {p0}. Healthy experiments with unchanged work may wait up to {p1}; operational checks continue.",
    "zh-CN": "策略评审间隔：{p0}。运行正常且工作内容未变化的实验最多可等待 {p1}；运行检查仍会继续。"
  },
  "ui.storage-increase-granted-per-experiment-and-file-shared-study-allowa": {
    "en": "Storage increase granted: {p0} → {p1} per experiment and file; {p2} → {p3} shared study allowance. Applies to new experiments; prior reservations and deadline unchanged. Worker resumed.",
    "zh-CN": "已批准增加存储：每个实验和文件 {p0} → {p1}；研究共享限额 {p2} → {p3}。适用于新实验；已有预留与截止时间不变。执行智能体已恢复。"
  },
  "ui.registration-tuning-granted-per-probe-attempt-s-worker-resumed-compu": {
    "en": "Registration tuning granted: {p0} → {p1} per probe; {p2} → {p3} attempt(s). Worker resumed; compute cutoff and frozen identities unchanged.",
    "zh-CN": "已批准调整注册参数：每次探测 {p0} → {p1}；尝试次数 {p2} → {p3}。执行智能体已恢复；计算截止时间及冻结标识不变。"
  },
  "ui.this-older-run-recorded-input-paths-only-changes-to-those-input-file": {
    "en": "This older run recorded input paths only; changes to those input files cannot be identified retrospectively.",
    "zh-CN": "此早期运行仅记录了输入路径，无法追溯识别这些输入文件的变化。"
  },
  "panels.expand.left": {
    "en": "Expand left sidebar",
    "zh-CN": "展开左侧边栏"
  },
  "panels.expand.right": {
    "en": "Expand right sidebar",
    "zh-CN": "展开右侧边栏"
  },
  "ui.skip-tour": {
    "en": "Skip tour",
    "zh-CN": "跳过引导"
  },
  "ui.back": {
    "en": "Back",
    "zh-CN": "上一步"
  },
  "status.running": {
    "en": "running",
    "zh-CN": "运行中"
  },
  "status.working": {
    "en": "working",
    "zh-CN": "正在处理"
  },
  "status.pending": {
    "en": "pending",
    "zh-CN": "等待中"
  },
  "status.queued": {
    "en": "queued",
    "zh-CN": "排队中"
  },
  "status.starting": {
    "en": "starting",
    "zh-CN": "正在启动"
  },
  "status.stopping": {
    "en": "stopping",
    "zh-CN": "正在停止"
  },
  "status.succeeded": {
    "en": "succeeded",
    "zh-CN": "成功"
  },
  "status.failed": {
    "en": "failed",
    "zh-CN": "失败"
  },
  "status.completed": {
    "en": "completed",
    "zh-CN": "已完成"
  },
  "status.finished": {
    "en": "finished",
    "zh-CN": "已结束"
  },
  "status.cancelled": {
    "en": "cancelled",
    "zh-CN": "已取消"
  },
  "status.canceled": {
    "en": "canceled",
    "zh-CN": "已取消"
  },
  "status.paused": {
    "en": "paused",
    "zh-CN": "已暂停"
  },
  "status.idle": {
    "en": "idle",
    "zh-CN": "空闲"
  },
  "status.ready": {
    "en": "ready",
    "zh-CN": "已就绪"
  },
  "status.unavailable": {
    "en": "unavailable",
    "zh-CN": "不可用"
  },
  "status.unknown": {
    "en": "unknown",
    "zh-CN": "未知"
  },
  "status.initialized": {
    "en": "initialized",
    "zh-CN": "已初始化"
  },
  "status.active": {
    "en": "active",
    "zh-CN": "活跃"
  },
  "status.waiting": {
    "en": "waiting",
    "zh-CN": "等待中"
  },
  "status.budget_exhausted": {
    "en": "budget exhausted",
    "zh-CN": "预算已耗尽"
  },
  "status.timed_out": {
    "en": "timed out",
    "zh-CN": "已超时"
  },
  "status.timeout": {
    "en": "timeout",
    "zh-CN": "超时"
  },
  "status.not_started": {
    "en": "not started",
    "zh-CN": "未开始"
  },
  "status.recorded": {
    "en": "recorded",
    "zh-CN": "已记录"
  },
  "status.connected": {
    "en": "connected",
    "zh-CN": "已连接"
  },
  "status.disconnected": {
    "en": "disconnected",
    "zh-CN": "已断开"
  },
  "status.unreachable": {
    "en": "unreachable",
    "zh-CN": "无法连接"
  },
  "status.offline": {
    "en": "offline",
    "zh-CN": "离线"
  },
  "status.online": {
    "en": "online",
    "zh-CN": "在线"
  },
  "status.pass": {
    "en": "pass",
    "zh-CN": "通过"
  },
  "status.fail": {
    "en": "fail",
    "zh-CN": "失败"
  },
  "status.passed": {
    "en": "passed",
    "zh-CN": "通过"
  },
  "status.error": {
    "en": "error",
    "zh-CN": "错误"
  },
  "status.warning": {
    "en": "warning",
    "zh-CN": "警告"
  },
  "status.ok": {
    "en": "ok",
    "zh-CN": "正常"
  },
  "status.approved": {
    "en": "approved",
    "zh-CN": "已批准"
  },
  "status.rejected": {
    "en": "rejected",
    "zh-CN": "已拒绝"
  },
  "status.supported": {
    "en": "supported",
    "zh-CN": "获得支持"
  },
  "status.refuted": {
    "en": "refuted",
    "zh-CN": "已证伪"
  },
  "status.inconclusive": {
    "en": "inconclusive",
    "zh-CN": "结论不确定"
  },
  "status.proposed": {
    "en": "proposed",
    "zh-CN": "已提出"
  },
  "status.open": {
    "en": "open",
    "zh-CN": "开放"
  },
  "status.closed": {
    "en": "closed",
    "zh-CN": "已关闭"
  },
  "status.draft": {
    "en": "draft",
    "zh-CN": "草稿"
  },
  "status.unreviewed": {
    "en": "unreviewed",
    "zh-CN": "未评审"
  },
  "status.review_pending": {
    "en": "review pending",
    "zh-CN": "等待评审"
  },
  "status.needs_review": {
    "en": "needs review",
    "zh-CN": "需要评审"
  },
  "status.revision_required": {
    "en": "revision required",
    "zh-CN": "需要修订"
  },
  "status.accepted": {
    "en": "accepted",
    "zh-CN": "已接受"
  },
  "status.scientific": {
    "en": "scientific",
    "zh-CN": "科学"
  },
  "status.instrument": {
    "en": "instrument",
    "zh-CN": "工具"
  },
  "status.method": {
    "en": "method",
    "zh-CN": "方法"
  },
  "status.engine": {
    "en": "engine",
    "zh-CN": "引擎"
  },
  "status.worker": {
    "en": "worker",
    "zh-CN": "执行智能体"
  },
  "status.director": {
    "en": "director",
    "zh-CN": "研究主管"
  },
  "status.operator": {
    "en": "operator",
    "zh-CN": "操作者"
  },
  "status.research": {
    "en": "research",
    "zh-CN": "研究"
  },
  "status.commission": {
    "en": "commission",
    "zh-CN": "工具验证"
  },
  "status.commissioning": {
    "en": "commissioning",
    "zh-CN": "工具验证"
  },
  "status.falsify": {
    "en": "falsify",
    "zh-CN": "证伪"
  },
  "status.repair": {
    "en": "repair",
    "zh-CN": "修正"
  },
  "status.judge": {
    "en": "judge",
    "zh-CN": "评审"
  },
  "status.review": {
    "en": "review",
    "zh-CN": "评审"
  },
  "status.finalization": {
    "en": "finalization",
    "zh-CN": "收尾"
  },
  "status.report": {
    "en": "report",
    "zh-CN": "报告"
  },
  "status.writing": {
    "en": "writing",
    "zh-CN": "撰写"
  },
  "status.responded": {
    "en": "responded",
    "zh-CN": "已响应"
  },
  "status.verified": {
    "en": "verified",
    "zh-CN": "已验证"
  },
  "status.parked": {
    "en": "parked",
    "zh-CN": "已暂停等待"
  },
  "status.granted": {
    "en": "granted",
    "zh-CN": "已批准"
  },
  "status.requested": {
    "en": "requested",
    "zh-CN": "已请求"
  },
  "status.updated": {
    "en": "updated",
    "zh-CN": "已更新"
  },
  "status.stopped": {
    "en": "stopped",
    "zh-CN": "已停止"
  },
  "status.submitted": {
    "en": "submitted",
    "zh-CN": "已提交"
  },
  "status.preparing": {
    "en": "preparing",
    "zh-CN": "正在准备"
  },
  "status.retrying": {
    "en": "retrying",
    "zh-CN": "正在重试"
  },
  "status.retry_wait": {
    "en": "retry wait",
    "zh-CN": "等待重试"
  },
  "status.completed_with_issues": {
    "en": "completed with issues",
    "zh-CN": "已完成但有问题"
  },
  "status.complete": {
    "en": "complete",
    "zh-CN": "完成"
  },
  "status.partial": {
    "en": "partial",
    "zh-CN": "部分完成"
  },
  "status.disabled": {
    "en": "disabled",
    "zh-CN": "已停用"
  },
  "status.enabled": {
    "en": "enabled",
    "zh-CN": "已启用"
  },
  "status.healthy": {
    "en": "healthy",
    "zh-CN": "正常"
  },
  "status.degraded": {
    "en": "degraded",
    "zh-CN": "降级"
  },
  "status.blocked": {
    "en": "blocked",
    "zh-CN": "受阻"
  },
  "status.satisfied": {
    "en": "satisfied",
    "zh-CN": "已满足"
  },
  "status.unsatisfied": {
    "en": "unsatisfied",
    "zh-CN": "未满足"
  },
  "status.success": {
    "en": "success",
    "zh-CN": "成功"
  },
  "status.aborted": {
    "en": "aborted",
    "zh-CN": "已中止"
  },
  "status.initializing": {
    "en": "initializing",
    "zh-CN": "正在初始化"
  },
  "status.analyzing": {
    "en": "analyzing",
    "zh-CN": "正在分析"
  },
  "status.executing": {
    "en": "executing",
    "zh-CN": "正在执行"
  },
  "status.reviewing": {
    "en": "reviewing",
    "zh-CN": "正在评审"
  },
  "status.read_only": {
    "en": "read only",
    "zh-CN": "只读"
  },
  "status.low": {
    "en": "low",
    "zh-CN": "低"
  },
  "status.medium": {
    "en": "medium",
    "zh-CN": "中"
  },
  "status.high": {
    "en": "high",
    "zh-CN": "高"
  },
  "status.xhigh": {
    "en": "xhigh",
    "zh-CN": "很高"
  },
  "status.max": {
    "en": "max",
    "zh-CN": "最高"
  },
  "status.ultra": {
    "en": "ultra",
    "zh-CN": "极高"
  },
  "status.default": {
    "en": "default",
    "zh-CN": "默认"
  },
  "status.related": {
    "en": "related",
    "zh-CN": "相关"
  },
  "status.supports": {
    "en": "supports",
    "zh-CN": "支持"
  },
  "status.contradicts": {
    "en": "contradicts",
    "zh-CN": "反驳"
  },
  "status.depends_on": {
    "en": "depends on",
    "zh-CN": "依赖"
  },
  "status.instrument_of": {
    "en": "instrument of",
    "zh-CN": "验证工具关联"
  },
  "status.derived_from": {
    "en": "derived from",
    "zh-CN": "派生自"
  },
  "status.refines": {
    "en": "refines",
    "zh-CN": "细化"
  },
  "status.tests": {
    "en": "tests",
    "zh-CN": "检验"
  },
  "ui.cad-simulation": {
    "en": "CAD & simulation",
    "zh-CN": "CAD 与仿真"
  },
  "status.cad_&_simulation": {
    "en": "CAD & simulation",
    "zh-CN": "CAD 与仿真"
  },
  "ui.analysis-data": {
    "en": "Analysis & data",
    "zh-CN": "分析与数据"
  },
  "status.analysis_&_data": {
    "en": "Analysis & data",
    "zh-CN": "分析与数据"
  },
  "ui.fluids-mhd": {
    "en": "Fluids & MHD",
    "zh-CN": "流体与磁流体力学"
  },
  "status.fluids_&_mhd": {
    "en": "Fluids & MHD",
    "zh-CN": "流体与磁流体力学"
  },
  "ui.plasma-fusion": {
    "en": "Plasma & fusion",
    "zh-CN": "等离子体与聚变"
  },
  "status.plasma_&_fusion": {
    "en": "Plasma & fusion",
    "zh-CN": "等离子体与聚变"
  },
  "ui.materials-radiation": {
    "en": "Materials & radiation",
    "zh-CN": "材料与辐射"
  },
  "status.materials_&_radiation": {
    "en": "Materials & radiation",
    "zh-CN": "材料与辐射"
  },
  "ui.workflow-assistance": {
    "en": "Workflow assistance",
    "zh-CN": "工作流辅助"
  },
  "status.workflow_assistance": {
    "en": "Workflow assistance",
    "zh-CN": "工作流辅助"
  },
  "ui.connected-tools": {
    "en": "Connected tools",
    "zh-CN": "已连接工具"
  },
  "status.connected_tools": {
    "en": "Connected tools",
    "zh-CN": "已连接工具"
  },
  "time.minutes": {
    "en": "{p0} min",
    "zh-CN": "{p0} 分钟"
  },
  "time.hours": {
    "en": "{p0} h",
    "zh-CN": "{p0} 小时"
  },
  "panels.collapse.left": {
    "en": "Collapse left sidebar",
    "zh-CN": "收起左侧边栏"
  },
  "panels.collapse.right": {
    "en": "Collapse right sidebar",
    "zh-CN": "收起右侧边栏"
  },
  "ui.recorded-conversation-agent-read-only-session": {
    "en": "Recorded conversation agent · read-only session",
    "zh-CN": "已记录的对话智能体 · 只读会话"
  },
  "ui.provided-by-simjecture-model-settings-managed-by-the-host": {
    "en": "Provided by Simjecture · model settings managed by the host",
    "zh-CN": "由 Simjecture 提供 · 模型设置由托管方管理"
  },
  "ui.cpu-cores": {
    "en": "CPU cores",
    "zh-CN": "CPU 核心数"
  },
  "ui.ram-budget": {
    "en": "RAM budget",
    "zh-CN": "内存预算"
  },
  "ui.gpus": {
    "en": "GPUs",
    "zh-CN": "GPU"
  },
  "ui.cooperative-runtime": {
    "en": "Cooperative runtime",
    "zh-CN": "协作运行环境"
  },
  "ui.native-process": {
    "en": "Native process",
    "zh-CN": "原生进程"
  },
  "ui.starter-presets": {
    "en": "Starter presets",
    "zh-CN": "起始预设"
  },
  "ui.plot-the-field-lines-and-track-magnetic-and-kinetic-energy-flash": {
    "en": "Plot the field lines and track magnetic and kinetic energy · FLASH",
    "zh-CN": "绘制磁力线并跟踪磁能与动能 · FLASH"
  },
  "ui.two-almost-identical-starts-in-the-lorenz-system-python": {
    "en": "Two almost identical starts in the Lorenz system · Python",
    "zh-CN": "比较 Lorenz 系统中几乎相同的两个初态 · Python"
  },
  "ui.not-recorded": {
    "en": "Not recorded",
    "zh-CN": "未记录"
  },
  "ui.coding-agent": {
    "en": "Coding agent",
    "zh-CN": "编程智能体"
  },
  "ui.model-id-suggestions-or-your-own": {
    "en": "Model ID · suggestions or your own",
    "zh-CN": "模型 ID · 选择建议或自行输入"
  },
  "ui.fresh-trials-per-task": {
    "en": "Fresh trials per task",
    "zh-CN": "每个任务的新试验次数"
  },
  "ui.scientific-claim-qualified-by-this-record": {
    "en": "scientific claim qualified by this record",
    "zh-CN": "此记录所验证的科学论断"
  },
  "ui.scientific-claim": {
    "en": "scientific claim",
    "zh-CN": "科学论断"
  },
  "ui.model-request-retry": {
    "en": "Model request retry {p0} {p1}{p2}.",
    "zh-CN": "模型请求重试 {p0} {p1}{p2}。"
  },
  "ui.updating": {
    "en": "Updating…",
    "zh-CN": "正在更新……"
  },
  "ui.up-to-date": {
    "en": "Up to date",
    "zh-CN": "已更新"
  },
  "ui.api-coding-agent": {
    "en": "API coding agent",
    "zh-CN": "API 编程智能体"
  },
  "ui.research-figure": {
    "en": "Research figure",
    "zh-CN": "科研图片"
  },
  "ui.figure": {
    "en": "Figure",
    "zh-CN": "图片"
  },
  "ui.or": {
    "en": " or ",
    "zh-CN": " 或 "
  },
  "ui.csv-diagnostics-no-hdf5-dependency": {
    "en": "CSV diagnostics; no HDF5 dependency.",
    "zh-CN": "CSV 诊断；无需 HDF5 依赖。"
  },
  "ui.this-workspace-is-read-only": {
    "en": "This workspace is read-only",
    "zh-CN": "此工作区为只读模式"
  },
  "ui.unable-to-start-a-visitor-session": {
    "en": "Unable to start a visitor session",
    "zh-CN": "无法启动访客会话"
  },
  "ui.request-failed": {
    "en": "Request failed ({p0})",
    "zh-CN": "请求失败（{p0}）"
  },
  "ui.shared-files-may-be-at-most-20-mb-each": {
    "en": "Shared files may be at most 20 MB each",
    "zh-CN": "每个共享文件最多为 20 MB"
  },
  "ui.the-local-server-returned-http": {
    "en": "The local server returned HTTP {p0}",
    "zh-CN": "本地服务返回 HTTP {p0}"
  },
  "ui.request-failed-with-http": {
    "en": "Request failed with HTTP {p0}",
    "zh-CN": "请求失败，HTTP {p0}"
  },
  "ui.for": {
    "en": " for {p0}",
    "zh-CN": "，持续 {p0}"
  },
  "ui.after": {
    "en": " after {p0}",
    "zh-CN": "，在 {p0} 后"
  },
  "ui.iteration-2": {
    "en": "iteration {p0}",
    "zh-CN": "第 {p0} 轮"
  },
  "ui.loading-the-bounded-console-record": {
    "en": "Loading the bounded console record…",
    "zh-CN": "正在加载限定范围的控制台记录……"
  },
  "ui.execution-in-progress": {
    "en": "$ execution in progress",
    "zh-CN": "$ 正在执行"
  },
  "ui.no-console-excerpt-was-retained-for-this-execution": {
    "en": "No console excerpt was retained for this execution.",
    "zh-CN": "本次执行未保留控制台摘要。"
  },
  "ui.gpt-reserve-dynamic-router": {
    "en": "GPT Reserve · dynamic router",
    "zh-CN": "GPT Reserve · 动态路由"
  },
  "ui.effort-3": {
    "en": "{p0} · {p1} effort",
    "zh-CN": "{p0} · {p1} 推理强度"
  },
  "ui.last-agent-activity": {
    "en": "Last agent activity: {p0}{p1}",
    "zh-CN": "智能体上次活动：{p0}{p1}"
  },
  "ui.monitored-simulation-in-this-turn": {
    "en": " · {p0} monitored simulation{p1} in this turn",
    "zh-CN": " · 本轮有 {p0} 个受监控仿真{p1}"
  },
  "ui.last-agent-activity-2": {
    "en": "Last agent activity: ",
    "zh-CN": "智能体上次活动："
  },
  "ui.full-log-p0": {
    "en": "Full log: {p0}",
    "zh-CN": "完整日志：{p0}"
  },
  "ui.p0-earlier-attempt-p1-kept": {
    "en": "{p0} earlier attempt{p1} kept",
    "zh-CN": "已保留 {p0} 次先前尝试{p1}"
  },
  "ui.waiting-for-setup-output": {
    "en": "Waiting for setup output…",
    "zh-CN": "正在等待配置输出……"
  },
  "ui.no-output-was-recorded": {
    "en": "No output was recorded.",
    "zh-CN": "未记录输出。"
  },
  "ui.p0-p1-min-per-trial": {
    "en": "{p0} · {p1} min per trial",
    "zh-CN": "{p0} · 每次试验 {p1} 分钟"
  },
  "ui.graded-trials": {
    "en": "Graded trials",
    "zh-CN": "已评分试验"
  },
  "ui.comparison-groups": {
    "en": "Comparison groups",
    "zh-CN": "比较组"
  },
  "ui.repeated-configurations": {
    "en": "Repeated configurations",
    "zh-CN": "重复配置"
  },
  "ui.completed-trials": {
    "en": "Completed trials",
    "zh-CN": "已完成试验"
  },
  "ui.configurations-tested": {
    "en": "Configurations tested",
    "zh-CN": "已测配置"
  },
  "ui.graded-attempts": {
    "en": "Graded attempts",
    "zh-CN": "已评分尝试"
  },
  "ui.scientific-coding-tasks": {
    "en": "Scientific coding tasks",
    "zh-CN": "科学编程任务"
  },
  "ui.completed-attempts": {
    "en": "Completed attempts",
    "zh-CN": "已完成尝试"
  },
  "ui.waiting-for-command-output": {
    "en": "Waiting for command output…",
    "zh-CN": "正在等待命令输出……"
  },
  "ui.waiting-for-simulation-output": {
    "en": "Waiting for simulation output…",
    "zh-CN": "正在等待仿真输出……"
  },
  "ui.hypothesis-not-yet-recorded": {
    "en": "Hypothesis not yet recorded",
    "zh-CN": "尚未记录假设"
  },
  "ui.guidance": {
    "en": "**Guidance:** {p0}",
    "zh-CN": "**指导：** {p0}"
  },
  "ui.searching-for-a-counterexample": {
    "en": "Searching for a counterexample.",
    "zh-CN": "正在寻找反例。"
  },
  "ui.qualifies-instruments-for": {
    "en": "Qualifies instruments for {p0}",
    "zh-CN": "为 {p0} 验证工具"
  },
  "ui.enables-evidence-for": {
    "en": "enables evidence for",
    "zh-CN": "为以下论断提供证据支持"
  },
  "ui.commissioning-gate-for": {
    "en": "Commissioning gate for `{p0}`",
    "zh-CN": "`{p0}` 的工具验证关卡"
  },
  "ui.claim-metadata-compact": {
    "en": "claim-metadata compact",
    "zh-CN": "论断元数据摘要"
  },
  "ui.operator-validation": {
    "en": "Operator validation",
    "zh-CN": "操作者验证"
  },
  "ui.observation-assessment": {
    "en": "Observation assessment",
    "zh-CN": "观测评估"
  },
  "ui.metric-target-reached": {
    "en": "Metric target reached",
    "zh-CN": "已达到指标目标"
  },
  "ui.metric-target-outstanding": {
    "en": "Metric target outstanding",
    "zh-CN": "尚未达到指标目标"
  },
  "ui.estimated-additional-time": {
    "en": "Estimated additional time: {p0}",
    "zh-CN": "预计还需时间：{p0}"
  },
  "ui.exceeds-remaining-wall-budget": {
    "en": "Exceeds remaining wall budget",
    "zh-CN": "超出剩余总运行时间预算"
  },
  "ui.no-final-answer-was-recorded": {
    "en": "No final answer was recorded.",
    "zh-CN": "尚未记录最终答复。"
  },
  "ui.not-completed": {
    "en": "Not completed",
    "zh-CN": "未完成"
  },
  "ui.choose-at-most-100-grade-files-up-to-4-mb-each": {
    "en": "Choose at most 100 grade files, up to 4 MB each.",
    "zh-CN": "最多选择 100 个评分文件，每个不超过 4 MB。"
  },
  "ui.import-at-most-1000-grades-at-a-time": {
    "en": "Import at most 1000 grades at a time.",
    "zh-CN": "每次最多导入 1000 条评分。"
  },
  "ui.choose-at-most-eight-reference-passages": {
    "en": "Choose at most eight reference passages.",
    "zh-CN": "最多可选择八个引用片段。"
  },
  "ui.moved-to-simulations": {
    "en": "Moved to Simulations",
    "zh-CN": "已移至仿真"
  },
  "ui.moved-to-commands": {
    "en": "Moved to Commands",
    "zh-CN": "已移至命令"
  },
  "ui.model-choices-are-still-loading-please-try-again-in-a-moment": {
    "en": "Model choices are still loading. Please try again in a moment.",
    "zh-CN": "模型选项仍在加载，请稍后重试。"
  },
  "ui.choose-a-model-or-enter-its-exact-id-in-other-model": {
    "en": "Choose a model, or enter its exact ID in Other model.",
    "zh-CN": "请选择模型，或在“其他模型”中输入准确 ID。"
  },
  "ui.exceeds-64-mb-copy-it-to-the-project-folder-directly": {
    "en": "{p0} exceeds 64 MB. Copy it to the project folder directly.",
    "zh-CN": "{p0} 超过 64 MB，请直接复制到项目文件夹。"
  },
  "ui.unable-to-save-run-settings": {
    "en": "Unable to save run settings",
    "zh-CN": "无法保存运行设置"
  },
  "ui.unable-to-extend-study-time": {
    "en": "Unable to extend study time",
    "zh-CN": "无法延长研究时间"
  },
  "ui.waiting-for-the-first-command-heartbeat": {
    "en": "Waiting for the first command heartbeat…",
    "zh-CN": "正在等待首次命令心跳……"
  },
  "ui.heartbeat-received-after-p0": {
    "en": "Heartbeat received after {p0}.",
    "zh-CN": "在 {p0} 后收到心跳。"
  },
  "ui.stdout-captured-p0": {
    "en": "stdout captured: {p0}",
    "zh-CN": "已捕获标准输出：{p0}"
  },
  "ui.stderr-captured-p0": {
    "en": "stderr captured: {p0}",
    "zh-CN": "已捕获标准错误：{p0}"
  },
  "ui.p0-tokens-condensed": {
    "en": " ({p0} tokens condensed)",
    "zh-CN": "（压缩 {p0} 个 token）"
  },
  "ui.tool-description.freecad": {
    "en": "Parametric CAD and STEP geometry",
    "zh-CN": "参数化 CAD 与 STEP 几何建模"
  },
  "ui.tool-description.gmsh": {
    "en": "Geometry preparation and finite-element meshing",
    "zh-CN": "几何预处理与有限元网格生成"
  },
  "ui.tool-description.elmer": {
    "en": "Finite-element and multiphysics simulation · guided setup",
    "zh-CN": "有限元与多物理场仿真 · 引导配置"
  },
  "ui.tool-description.warp-lbm": {
    "en": "2D GPU fluid dynamics · contributed by Zifei Meng",
    "zh-CN": "二维 GPU 流体动力学 · Zifei Meng 贡献"
  },
  "ui.tool-description.iter-pack": {
    "en": "CHERAB / Raysect and IMAS · verified demos",
    "zh-CN": "CHERAB / Raysect 与 IMAS · 已验证的示例"
  },
  "ui.tool-description.solps": {
    "en": "Tokamak edge and neutrals · guided setup",
    "zh-CN": "托卡马克边缘等离子体与中性粒子 · 引导配置"
  },
  "ui.tool-description.jorek": {
    "en": "Nonlinear MHD · guided setup",
    "zh-CN": "非线性磁流体动力学 · 引导配置"
  },
  "ui.tool-description.dina": {
    "en": "Tokamak scenarios and control · guided setup",
    "zh-CN": "托卡马克运行场景与控制 · 引导配置"
  },
  "ui.tool-description.warpx-cpu": {
    "en": "Particle-in-cell plasma simulations",
    "zh-CN": "粒子网格法等离子体仿真"
  },
  "ui.tool-description.warpx-cuda": {
    "en": "GPU plasma simulations · agent-assisted setup",
    "zh-CN": "GPU 等离子体仿真 · 智能体辅助配置"
  },
  "ui.tool-description.flash": {
    "en": "Hydrodynamics and MHD · agent-assisted setup",
    "zh-CN": "流体动力学与磁流体动力学 · 智能体辅助配置"
  },
  "ui.tool-description.atomec": {
    "en": "Average-atom equation of state",
    "zh-CN": "平均原子状态方程"
  },
  "ui.tool-description.singularity-eos": {
    "en": "Equation-of-state library",
    "zh-CN": "状态方程库"
  },
  "ui.tool-description.m-aneos": {
    "en": "Multiphase equation of state",
    "zh-CN": "多相状态方程"
  },
  "ui.tool-description.feos": {
    "en": "Electron/ion QEOS thermodynamics; no opacity",
    "zh-CN": "电子与离子 QEOS 热力学；不含不透明度"
  },
  "ui.tool-description.material-eos": {
    "en": "Model profiles and FLASH tables; no opacity",
    "zh-CN": "模型配置与 FLASH 表格；不含不透明度"
  },
  "ui.tool-description.optab": {
    "en": "Opacity tables",
    "zh-CN": "不透明度表"
  },
  "ui.tool-description.fac": {
    "en": "Relativistic atomic structure and rates",
    "zh-CN": "相对论原子结构与跃迁速率"
  },
  "ui.tool-description.conjecture-1": {
    "en": "Optional scientific attention coprocessor. Record suggested wakeups in shadow mode or explicitly enable bounded director requests for a study. Connect a separately managed model service; ordinary studies do not load or run the model. Experimental: a repeatable workflow advantage has not been established.",
    "zh-CN": "可选的科研注意力协处理器。可在影子模式下记录建议唤醒时机，也可明确为研究启用受限的主管请求。需连接单独管理的模型服务；普通研究不会加载或运行该模型。此功能尚处于实验阶段，尚未证明能稳定改善研究工作流程。"
  },
  "ui.usage-cost-note": {
    "en": "Provider billing and cache pricing are not inferred from token totals.",
    "zh-CN": "不会根据 token 总数推算服务商账单或缓存费用。"
  },
  "ui.no-completed-turn-usage": {
    "en": "No completed-turn provider usage is available for this record.",
    "zh-CN": "此记录尚无已完成轮次的服务商用量信息。"
  },
  "ui.benchmark-pricing-note": {
    "en": "Standard short-context published token-rate equivalent, including Grok Build Fast rates; DeepSeek peak and Gemini introductory rates. Excludes hosted tools, cache storage, discounts, subscriptions and hardware. Missing usage stays unknown. Reported costs are operator supplied.",
    "zh-CN": "按公开的标准短上下文 token 费率折算，包含 Grok Build Fast 费率、DeepSeek 高峰费率与 Gemini 推广费率。不包含托管工具、缓存存储、折扣、订阅和硬件成本。缺失的用量保持未知，已报告费用由操作人员提供。"
  },
  "status.inactive": {
    "en": "inactive",
    "zh-CN": "未运行"
  },
  "status.diagnostic": {
    "en": "diagnostic",
    "zh-CN": "诊断"
  },
  "status.control": {
    "en": "control",
    "zh-CN": "控制"
  },
  "status.study": {
    "en": "study",
    "zh-CN": "研究"
  },
  "status.root": {
    "en": "root",
    "zh-CN": "根节点"
  },
  "ui.machine-count-label": {
    "en": "machines",
    "zh-CN": "台设备"
  },
  "ui.online-count-label": {
    "en": "online",
    "zh-CN": "台在线"
  },
  "ui.gpu-count-label": {
    "en": "GPUs",
    "zh-CN": "块 GPU"
  },
  "time.heartbeat-seconds": {
    "en": "{p0} s ago",
    "zh-CN": "{p0} 秒前"
  },
  "time.heartbeat-minutes": {
    "en": "{p0} min ago",
    "zh-CN": "{p0} 分钟前"
  },
  "time.heartbeat-hours": {
    "en": "{p0} h ago",
    "zh-CN": "{p0} 小时前"
  },
  "ui.knowledge-source": {
    "en": "source",
    "zh-CN": "个资料源"
  },
  "ui.knowledge-sources-count": {
    "en": "sources",
    "zh-CN": "个资料源"
  },
  "ui.current-job": {
    "en": "job {p0}{p1}",
    "zh-CN": "任务 {p0}{p1}"
  },
  "ui.graph-commissioning-counts": {
    "en": "{p0} instrument claim{p1} · {p2} bound program{p3}{p4}",
    "zh-CN": "{p0} 条工具论断{p1} · {p2} 个绑定程序{p3}{p4}"
  },
  "ui.guided-suffix": {
    "en": " · guided",
    "zh-CN": " · 已引导"
  },
  "ui.graph-scientific-target": {
    "en": "scientific target: {p0} · E{p1}/S{p2}/C{p3}",
    "zh-CN": "科学目标：{p0} · E{p1}/S{p2}/C{p3}"
  },
  "ui.ssh-connection-unavailable": {
    "en": "SSH connection unavailable",
    "zh-CN": "SSH 连接不可用"
  },
  "ui.event-turn": {
    "en": "turn {p0}",
    "zh-CN": "第 {p0} 轮"
  },
  "ui.event-step": {
    "en": "step {p0}",
    "zh-CN": "第 {p0} 步"
  },
  "ui.event-role": {
    "en": "role {p0}",
    "zh-CN": "角色 {p0}"
  },
  "ui.evidence-capability": {
    "en": "Evidence capability",
    "zh-CN": "证据工具"
  },
  "ui.workbench-capability": {
    "en": "Workbench capability",
    "zh-CN": "工作台工具"
  },
  "ui.python-calculation": {
    "en": "Python calculation",
    "zh-CN": "Python 计算"
  },
  "ui.items-checked": {
    "en": "{p0} checked",
    "zh-CN": "已检查 {p0} 项"
  },
  "ui.csv-diagnostics-note": {
    "en": "CSV diagnostics; no HDF5 dependency.",
    "zh-CN": "CSV 诊断数据；无需 HDF5 依赖。"
  },
  "ui.timed-trials-started": {
    "en": "Timed trials started; grades appear automatically.",
    "zh-CN": "计时试验已启动，评分将自动显示。"
  },
  "ui.conversation-deleted-response": {
    "en": "Conversation and its saved folders deleted",
    "zh-CN": "对话及其保存的文件夹已删除"
  },
  "ui.continuation-preparing-response": {
    "en": "Your agent is preparing the continuation in chat.",
    "zh-CN": "智能体正在对话中准备后续研究。"
  },
  "ui.continuation-parent-response": {
    "en": "Parent attached. Choose a model, then Prepare with agent.",
    "zh-CN": "已关联原研究。请选择模型，再点击“与智能体一起准备”。"
  },
  "ui.continuation-draft-response": {
    "en": "Draft ready. Review the brief, model and budget before launch.",
    "zh-CN": "草稿已就绪。启动前请检查研究概要、模型和预算。"
  },
  "ui.campaign-resumed-response": {
    "en": "campaign resumed",
    "zh-CN": "研究已继续运行"
  },
  "ui.report-assessment-response": {
    "en": "Independent report assessment {p0}",
    "zh-CN": "独立报告评估：{p0}"
  },
  "status.enables_evidence_for": {
    "en": "enables evidence for",
    "zh-CN": "为以下论断提供证据支持"
  },
  "ui.benchmark-task.csv-energy.title": {
    "en": "CSV energy accounting",
    "zh-CN": "CSV 能量核算"
  },
  "ui.benchmark-task.rz-diagnostics.title": {
    "en": "Recorded RZ diagnostics",
    "zh-CN": "已记录的 RZ 诊断数据"
  },
  "ui.benchmark-official.csv-energy.title": {
    "en": "Radiation energy accounting",
    "zh-CN": "辐射能量核算"
  },
  "ui.benchmark-official.csv-energy.description": {
    "en": "Write a reducer for two recorded CSV cases. Compare escaped radiation with the energy removed by the radiation operator, then deliver results and findings.",
    "zh-CN": "为两个已记录的 CSV 算例编写数据归约程序，比较逸出辐射能与辐射算子扣除的能量，并提交结果与分析。"
  },
  "ui.benchmark-official.csv-energy.inputs": {
    "en": "Two solver CSV cases · three independent numerical holdouts",
    "zh-CN": "两个求解器 CSV 算例 · 三组独立数值留出验证数据"
  },
  "ui.benchmark-official.rz-diagnostics.title": {
    "en": "RZ plasma diagnostics",
    "zh-CN": "RZ 等离子体诊断"
  },
  "ui.benchmark-official.rz-diagnostics.description": {
    "en": "Write a reproducible analysis of two recorded plasma simulations: kinetic energy, compression, radiation windows, grid differences and plot data.",
    "zh-CN": "对两项已记录的等离子体仿真开展可复现分析，涵盖动能、压缩、辐射时间窗、网格差异与绘图数据。"
  },
  "ui.benchmark-official.rz-diagnostics.inputs": {
    "en": "64 × 4 and 128 × 4 RZ grids · 401 HDF5 frames each",
    "zh-CN": "64 × 4 与 128 × 4 的 RZ 网格 · 每组 401 帧 HDF5 数据"
  },
  "status.qualifies": {
    "en": "qualifies",
    "zh-CN": "验证"
  }
};
