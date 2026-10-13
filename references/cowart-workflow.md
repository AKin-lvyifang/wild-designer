# Cowart 执行合同

这是可选 Cowart 分支的能力与保存合同。以当前宿主真正暴露的工具 schema 为准；不声明已安装、已连接或已在当前环境验证。独立设计方案与其他交付不需要读取本文件。

## 发现与路径

发现 render、get selection、get/save canvas state、insert image 和需要时 read page asset。工具可能带 `mcp__cowart_mcp__` 前缀，也可能由宿主改名；不要猜可调用标识。工具未加载时先发现一次；新安装后仍没有则解释需要完整重启/新会话。只有独立 MCP 探针通过不代表宿主 widget 已挂载。

项目聊天用明确的用户项目目录；侧边栏 Cowart 使用其上下文返回的 `projectDir` 和 `canvasDir`。所有后续读写沿用这组路径；禁止用插件缓存作为作品目录。不要调用 localhost 开发服务，不编辑 canvas JSON 文件，不改插件缓存。

按用户对 Wild Designer 的自动预览偏好：本次产物需要预览、工具就绪且尚无该目标的已开 widget 时，调用 render 一次；已有画布直接复用。这项偏好不授权关闭/重开应用，不保证宿主右侧分屏。画布探测或打开失败时继续图像交付，不将可选预览作为生图前置条件。

## 每次生成

1. Cowart 就绪时，`get_cowart_selection` 取得选择；`get_cowart_canvas_state` 取得 snapshot、revision 和 viewState，明确 pageId、targetId、基底 nodeId 和不可变约束。用户仅咨询/整理 brief 时不自动出图；已经要求设计且上下文足够时直接推进，不再问一次是否生成。Cowart 缺失不阻塞 imagegen。
2. 若是编辑，通过确切的输入附件/本地路径/`read_cowart_page_asset` 取得基底和参考，先查看图片。记录“借用 / 保留 / 排除”，不要从全画布猜批注意图。
3. 用内置 imagegen 和其实际 schema。提示包含目标尺寸与宽高比、完整画面、文案、视觉层级、确定的约束和此次变化；编辑的 reference 指向准确版本。遵守 imagegen 要求的路径/最近图片机制，不能虚构尺寸参数。一次只生成当前决策需要的候选。
4. 使用本次返回的图片和受支持的路径/下载结果。若只返回 data URI，可在工具允许且返回值明确对应本次生成时解码为一个新的本地文件；若没有可取回的数据，停止插入并说明。禁止读会话/日志，禁止扫描历史图片碰运气。
5. 检查实际结果。用原生 `insert_cowart_image` 插入新图片，传准确 pageId、可选原图 anchor、`placement: "right"`、不覆盖文件的新 fileName，及 `shapeMeta`/`assetMeta` 来源字段。其 schema 支持 `imagePath`、`pageId`、`anchorShapeId`、`sourceShapeId`、`replaceAiImageHolder`、`displayWidth/Height`、`shapeMeta`、`assetMeta`；以当前 schema 为准。
6. 不将既有 AI holder 作为可删除对象；Wild Designer 默认保留原物，不走官方“替换 holder”的默认路径。选择普通原图作 anchor；只有 holder 时优先不传 anchor，明确 pageId，并设置 `replaceAiImageHolder: false`。不要把普通图片更新当成换图。保持图片自然宽高比。
7. 记录返回的 shapeId、assetId、pageId 和资产位置，重新读最新 snapshot，再将该 node 加入文字记录。原生插入会改变 revision，不能沿用插入前的 revision。

示意来源字段（只替换真实值；不要复制占位 ID）：

```json
{
  "wildDesigner": {
    "schemaVersion": 1,
    "projectId": "wd-项目的稳定UUID",
    "targetId": "target-目标的稳定UUID",
    "nodeId": "node-候选的稳定UUID",
    "parentNodeId": "node-基底或省略",
    "sourceIds": ["node-来源候选"],
    "referenceIds": ["shape-或用户附件的稳定标识"],
    "intent": "让标题更醒目，保留品牌蓝"
  }
}
```

生成前分配并持有 nodeId，重试不得另造 ID。插入是非幂等操作：返回不确定时，读取当前 store，寻找 `meta.wildDesigner.nodeId`；找到一张就复用，多张则停止排查。没有找到也不能在原请求仍未确定结束时盲目再插。生成完成默认备选，不因选中了某张图或插入成功而采用。

## 保存文字记录

使用 [canvas-state.md](canvas-state.md) 的本地 plan helper。它只生成待提交 JSON，不直写真实画布，也不启动 Cowart。

1. 读取最新完整 snapshot，保留返回 revision；不要带 `ifRevision` 得到无 snapshot 的 unchanged 响应。
2. 在临时文件保存该次 `structuredContent`，运行 helper。准备好的参数中必须有原样 `expectedRevision` 和 `protectImageRecords: true`；传给实际 `save_cowart_canvas_state` 工具。
3. 返回冲突时重新读当前状态、重算操作，最多两次；其他错误停止。绝不删去 expectedRevision 重试。不向工具添加 schema 没有的参数。
4. 检查 `ok`、`isError`、`skippedRecords`，再读取最新状态核对 owned note、采用状态和已有记录。保存可能在丢弃无效记录后返回 ok，因此 skippedRecords 非空仍是未通过，不能声称成功，也不能用旧全量快照回滚。
5. 新版本不认识当前 tldraw schema 时停止 full snapshot 更新，保留 brief 和应写入的文字说明供用户粘贴，并明确“尚未写入画布”。不要假装有 add_text/create_branch 等工具。

宿主 widget 的真实视觉验证需要在用户当前宿主确认；MCP 接受记录和返回 HTML 只证明后端合同。版本状态文字先验证保存和读回，再由真实画布确认布局、文本可读性和遮挡；没有宿主观察能力时说明未验证。
