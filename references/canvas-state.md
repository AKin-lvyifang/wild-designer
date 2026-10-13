# Cowart 画布中的设计状态

仅在使用 Cowart 适配时，使用一张普通 tldraw text shape 作为每个目标的可见记录。原生插入的 image shape 保持完整、可选、可移动；本技能不重排原作。标题可为“风格探索”“首页”“详情页”，来源边用 `v1 → v3` 文字呈现。它不是自动框架树、连接箭头或新的控件。

## 唯一状态与来源

文字 shape 的 `meta.wildDesigner` 是可变状态真源；图片 shape/asset 上的 `wildDesigner` 是不可变来源标识，不存可变的采用状态。记录里有 schemaVersion、owner、projectId、targetId、pageId、brief、stage、chosenStyle、constraints、nextDecision、mainNodeId、nodes、decisions。

- `projectId`：首轮创建一次 UUID，后续从本画布同项目记录中复用。`targetId`：设计目标 UUID，绑定一个 Cowart pageId。主页和详情各一个，风格探索可独立成目标。
- `nodeId`：候选 UUID。`shapeId` 来自真正插入成功的 image shape；不凭文件名或“v2”推断。
- node 保留 label、parentNodeId、sourceIds、referenceIds、intent、prompt、stage、style 与 status。sourceIds/parentNodeId 指向此目标中已知 node；外部或跨目标参考使用带目标/shape 的 referenceIds，避免假造本地谱系。
- brief 是简短 JSON 对象，含 originalIntent 和已经确认的信息。可按需保存 `designIntent`、`styleContract` 或其引用、`reviewNotes`（反馈原话、可见问题、保留项、变化与得失）；`decisions` 只记采用切换，不把它冒充设计诊断。长规范引用其路径，不拷贝全文。constraints 是确认过的保留项。stages 为 brief/explore/compose/refine/integrate。
- status 只有 proposed/adopted/superseded。每个 target 最多一张已采用稿；新候选不影响 mainNodeId。重新采用早期稿保留历史决定，不删除任何候选。

## 本地 helper

`scripts/canvas_notes.py` 只依赖 Python 标准库。输入来自本次 MCP 的 `structuredContent`；输出是 save 工具参数。不要让 helper 写入实际 canvas 文件。

```sh
python3 /绝对路径/wild-designer/scripts/canvas_notes.py plan \
  --state /临时路径/state.json --operation /临时路径/operation.json \
  --out /临时路径/save-args.json
```

操作示例（ID、路径和坐标都应取真实上下文，不能照抄）：

```json
{
  "projectId": "wd-demo",
  "targetId": "target-home",
  "pageId": "page:page",
  "title": "首页",
  "brief": {"originalIntent": "温暖、有手作感", "medium": "UI视觉稿"},
  "stage": "explore",
  "chosenStyle": "温暖的编辑排版",
  "constraints": ["保留品牌蓝", "保留已确认文案"],
  "nextDecision": "选择标题比例",
  "notePosition": {"x": 1800, "y": 100},
  "nodes": [{
    "id": "node-first",
    "shapeId": "shape:实际返回的图片ID",
    "label": "第一版",
    "sourceIds": [],
    "referenceIds": [],
    "intent": "建立首页层级",
    "prompt": "完整首页，温暖、疏朗，保留品牌蓝",
    "stage": "compose",
    "style": "温暖的编辑排版"
  }]
}
```

`nodes` 是新增或原样重发的 node；不得改写已有 node 的 provenance。可以省略 nodes，仅更新 brief 或下一步决定。notePosition 只在首次创建记录时必填，先从画布读取找到不遮挡作品的空位；记录后续被用户移动时保留其位置。文字较长时选足够空白空间，不自行移动用户作品。

采用时附加：

```json
{"adopt": {"nodeId": "node-second", "userSelection": "首页采用第二版"}}
```

只有用户确实表达了这次选择，或明确委托助手定案时才能填写 userSelection；委托时保留真实原话及选定理由。helper 不会替你判断用户意图，不能把助手建议当授权。重复同一采用操作不会新增重复历史。节点必须属于当前 target/page；用户原图可作为外部 reference，不能以本技能身份占有其 meta。

保存工具返回后读回最新状态，验证：

```sh
python3 /绝对路径/wild-designer/scripts/canvas_notes.py verify \
  --plan /临时路径/save-args.json --operation /临时路径/operation.json \
  --receipt /临时路径/save-result.json --readback /临时路径/latest-state.json
```

receipt 可为 MCP 完整 result 或 structuredContent。verify 拒绝 skippedRecords、记录丢失或 own note 不一致；并发发生的其他变化只能复核，不能覆盖回去。Helper 不发送 MCP 调用、不绕过宿主授权、不创建图片资产；其测试只用合成数据。
