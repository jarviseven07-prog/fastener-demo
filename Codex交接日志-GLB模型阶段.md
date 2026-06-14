# 紧固件手势交互项目交接日志 - GLB 模型阶段

> 给 Claude / 后续开发者接手用。当前日期：2026-06-15  
> 当前项目目录：`C:\Users\Mr4th\文档\3d粒子交互`

---

## 1. 当前项目目标

最终目标是把现有 Three.js + MediaPipe 手势交互网页里的代码几何体，替换成真实感 GLB 模型。

产品包含：

- 六角螺栓，必须是全螺纹
- 六角螺母
- 平垫圈
- 弹簧垫圈
- 锯齿垫圈
- 组装总成，由上面 5 个单体按顺序组合

网页目标功能：

- 单件旋转展示
- 缩放查看细节
- 信息卡展示
- 手势交互
- 组装 / 拆解动画

---

## 2. 当前项目文件状态

当前项目根目录已经放入网页源码：

```text
C:\Users\Mr4th\文档\3d粒子交互\
  demo.html
  demo_en.html
  demo_th.html
  lib/
  mediapipe/
  models/
  tools/
  tripo_views/
  serve-static.mjs
```

源码来源：

```text
C:\Users\Mr4th\Desktop\files (2)\fastener_web
```

注意：`demo.html` 是中文主文件；`demo_en.html` 和 `demo_th.html` 是同步版本。后续修改建模逻辑时，优先改 `demo.html`，确认无误后再同步到英文 / 泰文版本。不要直接整文件覆盖翻译版文案。

---

## 3. 本地访问方式

已创建静态服务器文件：

```text
C:\Users\Mr4th\文档\3d粒子交互\serve-static.mjs
```

启动方式：

```powershell
node serve-static.mjs
```

或使用 Codex 自带 Node：

```powershell
C:\Users\Mr4th\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe serve-static.mjs
```

访问地址：

```text
http://localhost:8000/demo.html
```

当前已经启动过一次服务，并确认 `demo.html` 返回 `200`。如果浏览器提示 `ERR_CONNECTION_REFUSED`，重新在项目根目录启动 `serve-static.mjs` 即可。

---

## 4. GLB 模型来源与命名

用户用 Tripo 生成的原始模型在：

```text
C:\Users\Mr4th\Desktop\glb
```

原文件：

```text
hex+nut+3d+model.glb       -> 六角螺母
metal+bolt+3d+model.glb    -> 六角螺栓
metal+washer+3d+model.glb  -> 平垫圈
ring+gear+3d+model.glb     -> 锯齿垫圈
split+ring+3d+model.glb    -> 弹簧垫圈
```

已复制并规范命名到：

```text
C:\Users\Mr4th\文档\3d粒子交互\models\raw
```

规范文件名：

```text
hex_bolt.glb
hex_nut.glb
flat_washer.glb
spring_washer.glb
serrated_washer.glb
```

---

## 5. 模型压缩结果

原始 Tripo 模型每个约 90-100 万三角面，网页实时交互太重。

已生成三个版本：

### 5.1 原始模型

```text
models/raw/
```

保留不动，作为备份。

### 5.2 glTF-Transform 高质量优化版

```text
models/optimized/
```

文件大小降低明显，但面数仍偏高，约 15-24 万面/个。可作为视觉质量备选。

### 5.3 推荐网页使用版本

推荐使用：

```text
models/optimized_fast/
```

该版本已控制到适合网页实时交互的面数，并补了 `TANGENT`，Three.js 法线贴图显示更稳。

最终统计：

```text
hex_bolt.glb         8.53 MB   150,030 面
hex_nut.glb          7.25 MB   120,021 面
flat_washer.glb      3.93 MB    50,009 面
spring_washer.glb    3.95 MB    79,985 面
serrated_washer.glb  6.45 MB   120,012 面
```

总计：

```text
30.11 MB
520,057 三角面
```

该版本没有启用 Draco / Meshopt 扩展，所以后续 Three.js 的 `GLTFLoader` 可以直接加载，不需要额外解码器。

---

## 6. 用过的压缩工具

用过 `@gltf-transform/cli`：

```powershell
npx --cache .npm-cache --yes @gltf-transform/cli ...
```

也创建了一个本地强制减面脚本：

```text
tools/simplify_glb.py
```

这个脚本是顶点聚类减面，比较激进，但适合把 Tripo 高面数扫描网格压到网页可用范围。

后续一般不需要再跑；除非发现模型视觉质量不够，再回到 `models/raw` 或 `models/optimized` 重新调压缩参数。

---

## 7. 参考图与生成过程

为 Tripo 生成模型时，做过一些参考图，保存在：

```text
tripo_views/
```

重要子目录：

```text
tripo_views/single_45/
```

里面有 45 度单图参考：

```text
hex_bolt_45.png
hex_nut_45.png
flat_washer_45.png
spring_washer_45.png
serrated_washer_45.png
serrated_washer_real_single.png
hex_bolt_long_full_thread.png
```

注意：用户已经停止图片生成，后续不需要继续做图，除非模型有明显错误。

---

## 8. 关键注意事项

### 8.1 螺栓必须全螺纹

客户要求螺栓为全螺纹。原始素材里有半螺纹图，但最终模型应按全螺纹处理。

当前 `models/optimized_fast/hex_bolt.glb` 来自用户最后选定的 Tripo 模型，应检查模型是否确实全螺纹。

### 8.2 组装动画需要独立零件

不要把 5 个零件合成一个不可拆分的 mesh 来做组装动画。当前做法建议：

- 单件展示：加载对应单体 GLB
- 组装总成：分别加载 5 个单体 GLB，按顺序摆位，并用每个 root group 做动画

组装顺序需求：

```text
螺母 -> 弹簧垫圈 -> 锯齿垫圈 -> 平垫圈 -> 螺栓
```

视觉上可理解为这些零件沿螺栓轴线叠装。

### 8.3 先做模型验收页

正式接入 `demo.html` 前，建议先做一个简单 `model_viewer.html`：

- 加载 `models/optimized_fast/*.glb`
- 可切换 5 个模型
- 显示包围盒 / 中心点 / 当前缩放
- 检查方向、比例、材质、贴图

确认模型方向和比例后再接入主交互页，避免一边调业务逻辑一边处理模型轴向问题。

---

## 9. 下一步建议

### 第一步：加入 GLTFLoader

当前 `lib/` 里是 Three.js r128 的本地依赖，没有确认是否包含 `GLTFLoader.js`。

需要：

- 找到适配 Three.js r128 的 `GLTFLoader.js`
- 放到 `lib/GLTFLoader.js`
- 在 `demo.html` 里按正确顺序引入

如果不用本地文件，也可以改成 module 方式，但当前项目是传统 `<script>` 架构，建议保持本地非 module loader。

### 第二步：写模型加载封装

建议新增：

```js
const MODEL_PATHS = {
  bolt: 'models/optimized_fast/hex_bolt.glb',
  nut: 'models/optimized_fast/hex_nut.glb',
  flat: 'models/optimized_fast/flat_washer.glb',
  spring: 'models/optimized_fast/spring_washer.glb',
  serr: 'models/optimized_fast/serrated_washer.glb',
};
```

再写：

```js
loadModel(id)
normalizeModel(root, targetSize)
cloneModel(id)
```

由于当前 Tripo 模型都是单节点单 mesh，缓存后 clone 应该比较直接。

### 第三步：替换几何体工厂函数

当前 `demo.html` 中有：

```js
makeBolt()
makeNut()
makeFlatWasher()
makeSpringWasher()
makeSerratedWasher()
buildAssemblyModel()
```

后续要改成加载 GLB，而不是代码几何体。

注意：原函数是同步返回 `THREE.Group`，而 GLB 加载是异步。需要处理 UI 进入产品时的 loading 状态，或启动时预加载全部模型。

推荐方案：启动后预加载 5 个 GLB，完成后再允许进入展示。

### 第四步：调方向和缩放

根据解析，模型包围盒大致如下：

```text
bolt:   细长，Y 轴约 1.0
nut:    高度/宽度接近 1.0
washer: 薄片，Y 轴约 0.12
```

但实际视觉方向仍需在浏览器里检查。可能要对每个模型单独设置：

```js
rotation
scale
position
```

### 第五步：组装总成

用独立模型组成 `STACK`，继续保留现有逻辑：

```js
userData = { home, lift, order }
```

这样现有组装动画和手势逻辑改动最小。

---

## 10. 当前还没做的事

> 2026-06-15 由 Claude 接手,第 1-5 项已完成,详见下方「第 12 章 进展更新」。

- ✅ 已把 GLB 接入 `demo.html`(并同步到 en / th)
- ✅ 已添加 `GLTFLoader.js`(另加了 `OrbitControls.js` 供验收页用)
- ✅ 已做模型验收页 `model_viewer.html`
- ✅ 已调模型方向、缩放、中心点(规范化模板,见第 12 章)
- ✅ 已同步改 `demo_en.html` / `demo_th.html`
- ⬜ 还没有提交 Git
- ⬜ 还没有让客户/用户在真机摄像头做最终手势验收(预览环境无摄像头)

---

## 11. 给 Claude 的建议

优先顺序：

1. 先做 `model_viewer.html` 验 5 个 GLB。
2. 加 `GLTFLoader.js`。
3. 在 `demo.html` 中做模型预加载和 GLB 替换。
4. 单件展示跑通后，再做组装总成。
5. 中文版稳定后，再同步英文 / 泰文。

不要先大改手势系统。当前手势体系已经比较完整，GLB 接入应尽量只动模型层。

---

## 12. 进展更新（2026-06-15，Claude 接手）

### 12.1 GLB 已接入（demo.html + en + th）

接入方式：**保持原 `make*()` 同步接口不变**，把代码几何体换成「预加载 GLB 模板的 clone」。
所以 `buildSatellite` / `enterProduct` / `buildAssemblyModel` 和全部手势 / 组装 / 单件动画**逻辑零改动**。

核心新增（在 `demo.html` 工厂函数区）：

- `MODEL_PATHS`：指向 `models/optimized_fast/*.glb`
- `MODEL_NORM`：每个零件的规范化参数（朝向 / 缩放基准 / 目标尺寸 / 材质）
- `normalizeToTemplate(id, gltfScene)`：把 GLB 规范化成「轴线=Y、原点居中、尺寸对齐原代码几何体」的双层 Group 模板（外层 wrapper 留给动画，内层放 GLB）
- `loadAllModels(onProgress)`：启动屏点击后预加载 5 个 GLB，完成才建场景
- `make*()`：改为 `return MODEL_TPL.xxx.clone(true)`

启动流程：`#boot-btn` 点击 → `await loadAllModels()`（`#boot-status` 显示 0/5 进度）→ `initScene()`。

### 12.2 各零件规范化参数（MODEL_NORM）

GLB 原始朝向不统一，已在模板里校正（验证后组装时 5 件 **cx=cz=0 完全同轴**）：

| 零件 | 旋转校正 | 缩放基准 | 目标尺寸 | 材质 |
|---|---|---|---|---|
| 螺栓 bolt | 无（头朝下，与原版一致） | 全高 Y | 4.8 | `M.steel()` |
| 螺母 nut | 绕 Z 转 90°（孔轴 X→Y） | 横向直径 | 1.84 | `M.steel()` |
| 平垫 flat | 无 | 横向直径 | 2.10 | `M.steelDark()` |
| 弹簧 spring | 绕 Z 转 90°（孔轴 X→Y） | 横向直径 | 2.04 | `M.steel()` |
| 锯齿 serr | 无 | 横向直径 | 2.16 | `M.zinc()` |

如需微调叠装贴合 / 单件大小，改 `MODEL_NORM` 的 `target`；组装叠放间距改 `buildAssemblyModel` 的 `home`。

### 12.3 材质决策：真实几何 + 干净金属（不要 AI 贴图）

用户反馈 Tripo GLB 自带的 PBR 贴图（基色 / 法线 / 粗糙度 / 金属度）显脏。
**最终方案：保留 GLB 真实几何（螺纹是立体几何，不靠贴图），但在 `normalizeToTemplate` 里把材质换成原代码那套纯色金属**（`M.steel/steelDark/zinc`），并 `disposeMaterial()` 释放贴图。
→ 干净工业风 + 真实形状，两者优点都要。若以后想恢复贴图质感，删掉 `normalizeToTemplate` 里的材质替换段即可。

### 12.4 交互增强（只动旋转手感 + 返回阈值，没动 classify）

- **甩动「硬币」旋转**：`tbMove` 用 EMA 平滑摆手速度；`tbRelease` 检测到快摆（`sp>0.006`）就放大成惯性冲量（`BOOST=2.2`，上限 `MAXV=0.06`），慢拖不触发（保留精确控制）；`animate` 里 Y 轴自转慢衰减 `*=.972`（像硬币）、X 轴俯仰快衰减 `*=.93`。实测快摆约 3 转 / 秒、滑行约 3.5 秒。
  - 手感旋钮：转速→`MAXV`；时长→`.972`（越接近 1 越久）；甩动门槛→`sp>0.006`。
- **返回更省事**：举顶感应区 `0.12→0.16`、触发时间 `550ms→300ms`（在 onHandResults 顶部返回段）。

### 12.5 三语同步方式

JS 逻辑三文件一致（差异只在 UI 文案），用 `diff demo.html.bak demo.html` 生成补丁、`patch` 套到 en / th。
注意：顶部返回那段注释在 en / th 是中英 / 中泰混合（`组装`→`Build`/`ประกอบ`），所以那个 hunk 需手工改；新增的加载进度文案也按语言各自本地化。**以后再同步 JS 改动，这两处仍需手工处理。**

### 12.6 备份与文件

- 备份：`demo.html.bak` / `demo_en.html.bak` / `demo_th.html.bak`（改前快照，确认无误后可删）
- 新增：`model_viewer.html`（模型验收页）、`lib/GLTFLoader.js`、`lib/OrbitControls.js`、`.claude/launch.json`

### 12.7 已知遗留 / 注意

- **预览工具截不了 demo 的图**（mediapipe `<video>` 元素导致），视觉验收只能在真实浏览器做；集成正确性已用程序化检查（读包围盒 / 材质 / 同轴）验证。
- 组装叠放衔接有约 0.1 的微小缝隙 / 重叠（GLB 厚度与原代码略不同），不影响观感；要更严丝合缝就微调 `home`。
- 手势手感（甩动 / 返回）的最终调校需真人摄像头实测。
- 尚未提交 Git。

### 12.8 UI 友好性优化（第一批，三语已同步）

从「访客第一次能不能用起来」出发，先落地了高收益、改动可控的兜底：

- **可点击 / 可触摸后备**（关键健壮性）：选择页产品标签 `.sat-label` 可点 / 可触摸进入；新增常驻 **`#back-btn` 返回按钮**（鼠标 / 触摸 / 防迷失出口）。手势识别不稳或触摸屏 kiosk 也能用。
- **键盘提示显性化**：选择页提示改成「悬停或点击产品 · 键盘 1-6」（en：`Hover or click a product · Keys 1-6`；th：`ชี้ค้างหรือคลิกสินค้า · ปุ่ม 1-6`）。
- **实现要点**：HUD 元素默认 `pointer-events:none`（不挡手势），需要可点的元素单独开 `auto`；产品标签进入单件 / 组装后设 `pointerEvents='none'` 防误触；`#back-btn` 在 `enterProduct` 显示、`enterSelect` 隐藏，点击 = `enterSelect()`。
- 返回按钮文案：返回 / Back / กลับ。

**还可继续的友好性优化**（已和用户过了一遍清单，按优先级）：完整新手引导（图标化启动屏 / 首次手势演示）、缩放可视化、`flashHint` 延时、attract mode 招揽态、音效反馈、页内语言切换角标、手势识别质量提示。信息卡文案待客户给真实参数。

### 12.9 新手引导（A，第二批，三语已同步）

- **图标化启动屏**：把原来密集的文字段换成 **3 步图标卡片**（🖐️ 伸手入画面 / 👆 悬停或点击 / 🤏 转·缩放·组装，`.boot-steps`/`.boot-step`），每步含图标+标题+说明，并明确写出「也可用鼠标 / 触摸」「键盘 1-6」；底部 `.boot-sub` 一行补充自动演示 / 返回说明。
- **首次手势引导**：新增 `#hand-hint`，选择页未检测到手时显示「🖐️ 把手伸进画面 · 或用鼠标 / 键盘 1-6 选择」，检测到手自动隐藏，进入产品隐藏。无摄像头时也一直提示可用鼠标，不会误导。
- **实现**：`setHandUI(d)` 末尾按 `!d && STATE.mode==='select'` 切换 `#hand-hint`；`enterSelect` 显示、`enterProduct` 隐藏。这些锚点都是语言无关，三语用同一改动 + 文案各自翻译。
- 三语文案均已翻译（启动屏三步、boot-sub、hand-hint）。

