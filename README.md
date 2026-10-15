# Wild Designer

没想法、不会布局，或者觉得设计不对却说不清时，先通过看对比、指画面帮你把感觉说出来，再据此确定方案并做出来。

Wild Designer 是一个以中文协作为主的 Agent Skill，适用于 UI、网站、封面、PPT 配图和风格探索。它从目标和内容出发，给出布局、视觉方向、推荐理由与取舍；已有稿则先找问题，再做有依据的修改。

**可以独立使用。** 确定设计方案不需要 Cowart、Figma、Paper 或生图服务。需要视觉稿、HTML 原型或可编辑设计时，再使用当前宿主真实可用的工具。

## 它会怎样帮你

- **先想清楚布局。** 谁在看、要理解或完成什么、第一眼看哪里，再决定结构、字体和颜色。
- **用画面引导，不问抽象问题。** 不问“你喜欢什么风格”，而是给两个只差一处的小样问“哪个更接近”，或请你指出最别扭的一块；你的反应会被翻译成设计规则并沿用。
- **你的眼睛是最终裁判。** 助手会给有理由的推荐，但审美以你看到实物后的反应为准；你说“你定”时才由助手定案。
- **少提问。** 信息够用就推进；方向未定时默认两个有实质差异的方向，已有方向就直接做一版。
- **让反馈推动修改。** “太普通、太挤、太花”会被拆成可见问题、影响、保留项和关键改动，再比较新旧得失。
- **反馈和过渡进入方案。** 组件回应操作，内容切换保持连贯；成功提示来自真实结果。
- **保留有效决定。** 复用同一份设计规范或风格约定，保留候选与来源，区分推荐、备选和正式采用。

例如“为独立摄影师做首页”，方案会说明作品如何分组、第一屏展示什么、预约入口放在哪里，以及不同布局的代价。只给“极简、黑白、衬线字体”不算完成方案。

## 安装

将本仓库作为一个 Skill 文件夹放入宿主的技能目录。Codex 可使用：

```sh
git clone https://github.com/AKin-lvyifang/wild-designer.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/wild-designer"
```

已有同名目录时先检查并保留自己的修改，不直接覆盖。然后按宿主要求重新加载技能或开始新会话。其他支持 `SKILL.md` 的 Agent 使用各自的技能目录；工具适配是否可用仍由宿主决定。

设计说明本身无需安装 Python 或前端依赖。`scripts/` 中两个可选辅助工具使用 Python 3 标准库，不负责创作，也不会自行连接应用。

## 使用示例

```text
$wild-designer 我想做一个记账工具首页，但没想法，也说不清喜欢什么样的。

$wild-designer 这版看着不对劲，但我说不出哪里不对。

$wild-designer 我想要高级一点的感觉，帮我弄清楚“高级”具体是什么。

$wild-designer 按这个方向做 HTML 原型，导航用动态图标，内容切换有过渡。

$wild-designer 做一版发布页，滚动时轻轻渐隐浮现，方向你来定。

$wild-designer 参考这张图的留白和标题比例，做两个方向；有画布就放进去。
```

你可以只要方案，也可以要求视觉稿或原型。已有项目规范和当前明确要求优先，不必为使用 Skill 补一整套设计问卷。

## 可选组件参考

以下是作者常用的可选参考，不是必需项；项目已有组件或你有自己的偏好时以那些为准。导航图标可参考 [AnimateIcons](https://github.com/Avijit07x/animateicons) 与 [lucide-animated](https://github.com/pqoqubbw/icons)，按钮可参考 [Amicro](https://github.com/Subhan-code/Amicro--Micro-transitions-) 的合适组件。

优先复用项目已有封装，再按需要读取少量组件；本仓库不包含这些库的源码或依赖。非 React 项目沿原技术栈表达同样反馈，不为一个动画更换框架。库里的演示效果也需要适配：例如成功勾号与“已保存”必须绑定真实结果，不能悬停就宣称成功。

内容切换、展开收起和列表变化有轻量过渡；展示页进入阅读区渐渐清晰，离开可轻淡出。工作区常驻导航和高频操作保持稳定。尊重减少动态效果设置，不规定必须有几处动画或必须移动多少像素。

## 文件与可选能力

| 入口 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 引导说出感觉、确定方案、改稿与交付主线 |
| [style-guidance.md](references/style-guidance.md) | 从目标形成布局、比较方向、诊断反馈、保持风格 |
| [interaction-motion.md](references/interaction-motion.md) | 组件来源、状态反馈、内容过渡和实际检查 |
| [versions.md](references/versions.md) | 多稿时的候选、采用状态和文件路径规则 |
| [tool-routing.md](references/tool-routing.md) | 按需生图、HTML、可编辑设计与真实能力边界 |
| [cowart-workflow.md](references/cowart-workflow.md) / [canvas-state.md](references/canvas-state.md) | 只在使用 Cowart 时加载的画布保存与版本合同 |
| [route_design.py](scripts/route_design.py) | 根据已核实输入规划可选工具路径，不主动探测工具 |
| [canvas_notes.py](scripts/canvas_notes.py) | 准备与验证 Cowart 记录更新，不直接写画布 |

`ui-ux-pro-max` 和 `design-md` 可补具体资料缺口，但不是运行依赖。Skill 不会为了探索风格自动安装它们。Cowart、Paper、Figma 同样是可选交付路径，不是独立方案的前置条件。

## 验证范围

运行辅助程序的本地测试：

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
```

测试使用模拟能力和合成画布数据，检查路由、来源保护、采用状态及保存回执。它们不调用生图，不证明设计更好看，也不证明当前宿主的 Paper/Figma/Cowart 端到端可用。

设计质量通过实际画面、目标适配和用户反馈判断；动画与功能需要在可运行环境观察。自动检查区分发现问题、已核对范围和待复核部分，跳过或零告警不等于验收通过。

## 方法来源与许可

设计判断、候选差异和改稿方法参考了 [draw-ui](https://github.com/oil-oil/draw-ui) 与 [Oil UI](https://github.com/oil-oil/oil-ui) 的公开资料，并按独立方案、少提问和跨媒介协作重新组织。[风格指南](references/style-guidance.md#公开方法参考)列有对应版本的阅读入口。这两个 Skill 不是本项目的运行依赖。

本仓库以 [MIT](LICENSE) 许可发布。提到的组件库、字体、设计工具和画布服务仍遵循各自许可证；本仓库不代替它们授权。
